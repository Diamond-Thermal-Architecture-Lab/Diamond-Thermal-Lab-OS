"""Closed strict-1D result-content validation and frozen I3 wrapper binding."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

from labos.engineering import (
    QuantityKind,
    canonical_decimal_text,
    canonical_json_bytes,
    convert_quantity,
    parse_decimal,
    result_payload_content_sha256,
)

from .strict_1d import (
    CONSTRAINT_POLICY_VERSION,
    OAT_POLICY_VERSION,
    RANKING_POLICY_VERSION,
    RESULT_PAYLOAD_SCHEMA_ID,
    RESULT_PAYLOAD_SCHEMA_VERSION,
    SCENARIO_POLICY_VERSION,
)


_CANDIDATE_ID = re.compile(r"^CND-[0-9]{3}$")
_LAYER_ID = re.compile(r"^LYR-[0-9]{3}$")
_MATERIAL_ID = re.compile(r"^MAT-[0-9]{3}$")
_PROPERTY_ID = re.compile(r"^PRP-[0-9]{3}$")
_INTERFACE_ID = re.compile(r"^IFC-[0-9]{3}$")
_CONSTRAINT_ID = re.compile(r"^CON-[0-9]{3}$")
_SWEEP_ID = re.compile(r"^SWP-[0-9]{3}$")
_NODE_ID = re.compile(r"^NODE-[0-9]{3}$")
_SCENARIO_ID = re.compile(
    r"^SCN-C[0-9]{3}-(?:K[0-9]{6}|O000-REF|O[0-9]{3}-(?:MINUS|PLUS))$"
)
_POINTER = re.compile(r"^(?:/(?:[^~/]|~[01])*)+$")

_RESULT_QUANTITY_FIELDS = ("value", "unit", "quantity_kind")
_DIAGNOSTIC_FIELDS = (
    "rule_id",
    "classification",
    "field_paths",
    "message",
    "required_action",
)
_ACKNOWLEDGEMENT_FIELDS = ("scope", "candidate_id", "field_path")
_CONSUMED_PATH_FIELDS = ("scope", "candidate_id", "field_path")
_SCENARIO_FIELDS = (
    "scenario_id",
    "scenario_kind",
    "candidate_id",
    "sweep_coordinates",
    "oat_coordinate",
    "input_overrides",
    "disposition",
    "applicability_status",
    "reused_core_scenario_id",
    "consumed_input_paths",
    "assumption_acknowledgements_used",
    "applicability_findings",
    "execution_findings",
    "constraint_results",
    "numerical_result",
)
_NUMERICAL_RESULT_FIELDS = (
    "common_area",
    "source_power",
    "reference_temperature",
    "layer_resistance_contributions",
    "interface_resistance_contributions",
    "boundary_resistance_contribution",
    "total_thermal_resistance",
    "temperature_rise",
    "source_temperature",
    "node_temperatures",
    "numerical_exactness",
)


class Strict1DResultValidationError(ValueError):
    """Raised when strict-1D result content violates its closed contract."""


def _fail(path: str, message: str) -> None:
    raise Strict1DResultValidationError(f"{path}: {message}")


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(path, "must be an object")
    if any(type(key) is not str for key in value):
        _fail(path, "object keys must be strings")
    return value


def _closed(value: Any, fields: Sequence[str], path: str) -> Mapping[str, Any]:
    item = _mapping(value, path)
    expected = set(fields)
    missing = expected - set(item)
    unknown = set(item) - expected
    if missing:
        _fail(path, f"missing required fields: {sorted(missing)!r}")
    if unknown:
        _fail(path, f"unknown fields: {sorted(unknown)!r}")
    return item


def _array(value: Any, path: str, *, minimum: int = 0) -> list[Any]:
    if type(value) is not list or len(value) < minimum:
        _fail(path, f"must be an array with at least {minimum} item(s)")
    return value


def _non_empty(value: Any, path: str) -> str:
    if type(value) is not str or not value:
        _fail(path, "must be a non-empty string")
    return value


def _identifier(value: Any, pattern: re.Pattern[str], path: str, label: str) -> str:
    if type(value) is not str or pattern.fullmatch(value) is None:
        _fail(path, f"has invalid {label} syntax")
    return value


def _pointer(value: Any, path: str) -> str:
    return _identifier(value, _POINTER, path, "RFC 6901 pointer")


def _positive_integer(value: Any, path: str, *, allow_zero: bool = False) -> int:
    if type(value) is not int or value < (0 if allow_zero else 1):
        _fail(path, "must be a non-negative integer" if allow_zero else "must be a positive integer")
    return value


def _canonical_decimal(value: Any, path: str) -> Decimal:
    if type(value) is not str:
        _fail(path, "must be a canonical Decimal string")
    try:
        parsed = parse_decimal(value)
    except ValueError as exc:
        _fail(path, f"has invalid Decimal syntax: {exc}")
    if canonical_decimal_text(parsed) != value:
        _fail(path, "must use canonical Decimal text")
    return parsed


def _result_quantity(
    value: Any,
    path: str,
    *,
    expected_kind: QuantityKind | None = None,
    expected_unit: str | None = None,
) -> Decimal:
    item = _closed(value, _RESULT_QUANTITY_FIELDS, path)
    decimal = _canonical_decimal(item["value"], f"{path}/value")
    try:
        kind = QuantityKind(item["quantity_kind"])
    except (TypeError, ValueError):
        _fail(f"{path}/quantity_kind", "must be an I1 QuantityKind")
    unit = _non_empty(item["unit"], f"{path}/unit")
    try:
        canonical_unit = convert_quantity(kind, "0", unit).canonical_unit
    except (TypeError, ValueError) as exc:
        _fail(f"{path}/unit", f"is not registered for its QuantityKind: {exc}")
    if unit != canonical_unit:
        _fail(f"{path}/unit", "must be the exact I1 canonical unit")
    if expected_kind is not None and kind is not expected_kind:
        _fail(f"{path}/quantity_kind", f"must equal {expected_kind.value!r}")
    if expected_unit is not None and unit != expected_unit:
        _fail(f"{path}/unit", f"must equal {expected_unit!r}")
    return decimal


def _diagnostics(value: Any, path: str) -> None:
    items = _array(value, path)
    keys: list[tuple[str, tuple[str, ...], str, bytes]] = []
    encoded: set[bytes] = set()
    for index, raw in enumerate(items):
        item_path = f"{path}/{index}"
        item = _closed(raw, _DIAGNOSTIC_FIELDS, item_path)
        rule_id = _non_empty(item["rule_id"], f"{item_path}/rule_id")
        _non_empty(item["classification"], f"{item_path}/classification")
        pointers = _array(item["field_paths"], f"{item_path}/field_paths")
        for pointer_index, pointer in enumerate(pointers):
            _pointer(pointer, f"{item_path}/field_paths/{pointer_index}")
        if len(pointers) != len(set(pointers)) or pointers != sorted(pointers):
            _fail(f"{item_path}/field_paths", "must be unique and lexically ordered")
        message = _non_empty(item["message"], f"{item_path}/message")
        _non_empty(item["required_action"], f"{item_path}/required_action")
        representation = canonical_json_bytes(item)
        if representation in encoded:
            _fail(path, "contains duplicate diagnostics")
        encoded.add(representation)
        keys.append((rule_id, tuple(pointers), message, representation))
    if keys != sorted(keys):
        _fail(path, "must use rule/path/message canonical order")


def _scoped_records(
    value: Any,
    path: str,
    fields: Sequence[str],
    *,
    consumed: bool,
) -> None:
    items = _array(value, path)
    keys: list[tuple[int, str, str]] = []
    encodings: set[bytes] = set()
    for index, raw in enumerate(items):
        item_path = f"{path}/{index}"
        item = _closed(raw, fields, item_path)
        scope = item["scope"]
        if scope not in {"global", "candidate"}:
            _fail(f"{item_path}/scope", "must be 'global' or 'candidate'")
        candidate_id = item["candidate_id"]
        if scope == "global":
            if candidate_id is not None:
                _fail(f"{item_path}/candidate_id", "must be null for global scope")
        else:
            _identifier(candidate_id, _CANDIDATE_ID, f"{item_path}/candidate_id", "candidate ID")
        _pointer(item["field_path"], f"{item_path}/field_path")
        encoding = canonical_json_bytes(item)
        if encoding in encodings:
            _fail(path, "contains duplicate records")
        encodings.add(encoding)
        keys.append((0 if scope == "global" else 1, candidate_id or "", item["field_path"]))
    if keys != sorted(keys):
        label = "consumed paths" if consumed else "acknowledgements"
        _fail(path, f"{label} must use global-first, candidate-ID, field-path order")


def _sweep_coordinate(value: Any, path: str) -> None:
    item = _closed(value, ("sweep_id", "field_path", "point_ordinal", "value"), path)
    _identifier(item["sweep_id"], _SWEEP_ID, f"{path}/sweep_id", "sweep ID")
    _pointer(item["field_path"], f"{path}/field_path")
    _positive_integer(item["point_ordinal"], f"{path}/point_ordinal")
    _result_quantity(item["value"], f"{path}/value")


def _input_override(value: Any, path: str) -> None:
    item = _closed(
        value,
        ("source_kind", "source_id", "field_path", "point_ordinal", "side", "value"),
        path,
    )
    if item["source_kind"] not in {"sweep", "oat"}:
        _fail(f"{path}/source_kind", "must be 'sweep' or 'oat'")
    if item["source_kind"] == "sweep":
        _identifier(item["source_id"], _SWEEP_ID, f"{path}/source_id", "sweep ID")
        if item["side"] is not None:
            _fail(f"{path}/side", "must be null for sweep overrides")
    else:
        if item["source_id"] is not None:
            _fail(f"{path}/source_id", "must be null for OAT overrides")
        if item["side"] not in {"minus", "plus"}:
            _fail(f"{path}/side", "must be minus or plus for OAT overrides")
    _pointer(item["field_path"], f"{path}/field_path")
    _positive_integer(item["point_ordinal"], f"{path}/point_ordinal")
    _result_quantity(item["value"], f"{path}/value")


def _constraint_result(value: Any, path: str, scenario_id: str) -> None:
    item = _closed(
        value,
        (
            "constraint_id",
            "scenario_id",
            "status",
            "evaluated_quantity",
            "limit",
            "margin",
            "operator",
            "finding_ids",
        ),
        path,
    )
    _identifier(item["constraint_id"], _CONSTRAINT_ID, f"{path}/constraint_id", "constraint ID")
    if item["scenario_id"] != scenario_id:
        _fail(f"{path}/scenario_id", "must equal the owning scenario ID")
    if item["status"] not in {"pass", "fail", "not_evaluable"}:
        _fail(f"{path}/status", "has unsupported constraint status")
    for field in ("evaluated_quantity", "limit", "margin"):
        if item[field] is not None:
            _result_quantity(item[field], f"{path}/{field}")
    if item["status"] == "not_evaluable" and (
        item["evaluated_quantity"] is not None or item["margin"] is not None
    ):
        _fail(path, "not_evaluable constraints require null evaluated quantity and margin")
    if item["operator"] not in {"lt", "le", "eq", "ge", "gt", "in", "not_in", "review_only"}:
        _fail(f"{path}/operator", "has unsupported operator")
    finding_ids = _array(item["finding_ids"], f"{path}/finding_ids")
    if any(type(value) is not str or not value for value in finding_ids):
        _fail(f"{path}/finding_ids", "must contain non-empty rule IDs")
    if finding_ids != sorted(set(finding_ids)):
        _fail(f"{path}/finding_ids", "must be unique and lexically ordered")


def _layer_contribution(value: Any, path: str) -> Decimal:
    item = _closed(
        value,
        (
            "layer_id",
            "material_id",
            "property_id",
            "thickness",
            "normal_conductivity",
            "area",
            "resistance",
            "fraction_of_total",
        ),
        path,
    )
    _identifier(item["layer_id"], _LAYER_ID, f"{path}/layer_id", "layer ID")
    _identifier(item["material_id"], _MATERIAL_ID, f"{path}/material_id", "material ID")
    _identifier(item["property_id"], _PROPERTY_ID, f"{path}/property_id", "property ID")
    _result_quantity(item["thickness"], f"{path}/thickness", expected_kind=QuantityKind.LENGTH, expected_unit="m")
    _result_quantity(
        item["normal_conductivity"],
        f"{path}/normal_conductivity",
        expected_kind=QuantityKind.THERMAL_CONDUCTIVITY,
        expected_unit="W/(m*K)",
    )
    _result_quantity(item["area"], f"{path}/area", expected_kind=QuantityKind.AREA, expected_unit="m^2")
    resistance = _result_quantity(
        item["resistance"],
        f"{path}/resistance",
        expected_kind=QuantityKind.ABSOLUTE_THERMAL_RESISTANCE,
        expected_unit="K/W",
    )
    _result_quantity(
        item["fraction_of_total"],
        f"{path}/fraction_of_total",
        expected_kind=QuantityKind.PHYSICAL_DIMENSIONLESS,
        expected_unit="1",
    )
    return resistance


def _interface_contribution(value: Any, path: str) -> Decimal:
    item = _closed(
        value,
        (
            "interface_id",
            "upstream_layer_id",
            "downstream_layer_id",
            "tbr",
            "area",
            "resistance",
            "fraction_of_total",
        ),
        path,
    )
    _identifier(item["interface_id"], _INTERFACE_ID, f"{path}/interface_id", "interface ID")
    _identifier(item["upstream_layer_id"], _LAYER_ID, f"{path}/upstream_layer_id", "layer ID")
    _identifier(item["downstream_layer_id"], _LAYER_ID, f"{path}/downstream_layer_id", "layer ID")
    _result_quantity(
        item["tbr"],
        f"{path}/tbr",
        expected_kind=QuantityKind.AREA_THERMAL_RESISTANCE,
        expected_unit="m^2*K/W",
    )
    _result_quantity(item["area"], f"{path}/area", expected_kind=QuantityKind.AREA, expected_unit="m^2")
    resistance = _result_quantity(
        item["resistance"],
        f"{path}/resistance",
        expected_kind=QuantityKind.ABSOLUTE_THERMAL_RESISTANCE,
        expected_unit="K/W",
    )
    _result_quantity(
        item["fraction_of_total"],
        f"{path}/fraction_of_total",
        expected_kind=QuantityKind.PHYSICAL_DIMENSIONLESS,
        expected_unit="1",
    )
    return resistance


def _boundary_contribution(value: Any, path: str) -> Decimal:
    item = _closed(
        value,
        (
            "boundary_id",
            "representation_type",
            "supplied_resistance",
            "heat_transfer_coefficient",
            "boundary_area",
            "resistance",
            "fraction_of_total",
        ),
        path,
    )
    if item["boundary_id"] != "BND-DOWNSTREAM":
        _fail(f"{path}/boundary_id", "must equal 'BND-DOWNSTREAM'")
    representation = item["representation_type"]
    if representation not in {"fixed_temperature", "absolute_resistance", "direct_convection"}:
        _fail(f"{path}/representation_type", "has unsupported boundary representation")
    if item["supplied_resistance"] is not None:
        _result_quantity(
            item["supplied_resistance"],
            f"{path}/supplied_resistance",
            expected_kind=QuantityKind.ABSOLUTE_THERMAL_RESISTANCE,
            expected_unit="K/W",
        )
    if item["heat_transfer_coefficient"] is not None:
        _result_quantity(
            item["heat_transfer_coefficient"],
            f"{path}/heat_transfer_coefficient",
            expected_kind=QuantityKind.AREA_THERMAL_CONDUCTANCE,
            expected_unit="W/(m^2*K)",
        )
    if item["boundary_area"] is not None:
        _result_quantity(
            item["boundary_area"],
            f"{path}/boundary_area",
            expected_kind=QuantityKind.AREA,
            expected_unit="m^2",
        )
    required_shapes = {
        "fixed_temperature": (None, None, None),
        "absolute_resistance": ("required", None, None),
        "direct_convection": (None, "required", "required"),
    }[representation]
    actual = (
        "required" if item["supplied_resistance"] is not None else None,
        "required" if item["heat_transfer_coefficient"] is not None else None,
        "required" if item["boundary_area"] is not None else None,
    )
    if actual != required_shapes:
        _fail(path, "nullable supplied boundary fields do not match representation_type")
    resistance = _result_quantity(
        item["resistance"],
        f"{path}/resistance",
        expected_kind=QuantityKind.ABSOLUTE_THERMAL_RESISTANCE,
        expected_unit="K/W",
    )
    _result_quantity(
        item["fraction_of_total"],
        f"{path}/fraction_of_total",
        expected_kind=QuantityKind.PHYSICAL_DIMENSIONLESS,
        expected_unit="1",
    )
    return resistance


def _node_temperatures(
    value: Any,
    path: str,
    *,
    source_temperature: Decimal,
    reference_temperature: Decimal,
    expected_count: int,
) -> None:
    items = _array(value, path, minimum=2)
    if len(items) != expected_count:
        _fail(path, "must contain one source node and one node after every series element")
    temperatures: list[Decimal] = []
    for index, raw in enumerate(items):
        item_path = f"{path}/{index}"
        item = _closed(
            raw,
            (
                "node_id",
                "node_role",
                "upstream_element_id",
                "downstream_element_id",
                "temperature",
            ),
            item_path,
        )
        node_id = _identifier(item["node_id"], _NODE_ID, f"{item_path}/node_id", "node ID")
        if node_id != f"NODE-{index:03d}":
            _fail(f"{item_path}/node_id", "must use the zero-based three-digit array ordinal")
        expected_role = "source" if index == 0 else "reference" if index == len(items) - 1 else "internal"
        if item["node_role"] != expected_role:
            _fail(f"{item_path}/node_role", f"must equal {expected_role!r}")
        for field in ("upstream_element_id", "downstream_element_id"):
            if item[field] is not None:
                _non_empty(item[field], f"{item_path}/{field}")
        if index == 0 and item["upstream_element_id"] is not None:
            _fail(f"{item_path}/upstream_element_id", "must be null at the source node")
        if index == len(items) - 1 and item["downstream_element_id"] is not None:
            _fail(f"{item_path}/downstream_element_id", "must be null at the reference node")
        temperatures.append(
            _result_quantity(
                item["temperature"],
                f"{item_path}/temperature",
                expected_kind=QuantityKind.ABSOLUTE_TEMPERATURE,
                expected_unit="K",
            )
        )
    if temperatures[0] != source_temperature:
        _fail(f"{path}/0/temperature", "must equal source_temperature exactly")
    if temperatures[-1] != reference_temperature:
        _fail(f"{path}/{len(items) - 1}/temperature", "must equal reference_temperature exactly")


def _numerical_result(value: Any, path: str) -> None:
    item = _closed(value, _NUMERICAL_RESULT_FIELDS, path)
    _result_quantity(item["common_area"], f"{path}/common_area", expected_kind=QuantityKind.AREA, expected_unit="m^2")
    _result_quantity(item["source_power"], f"{path}/source_power", expected_kind=QuantityKind.POWER, expected_unit="W")
    reference_temperature = _result_quantity(
        item["reference_temperature"],
        f"{path}/reference_temperature",
        expected_kind=QuantityKind.ABSOLUTE_TEMPERATURE,
        expected_unit="K",
    )
    layers = _array(item["layer_resistance_contributions"], f"{path}/layer_resistance_contributions", minimum=1)
    layer_ids: list[str] = []
    for index, contribution in enumerate(layers):
        _layer_contribution(contribution, f"{path}/layer_resistance_contributions/{index}")
        layer_ids.append(contribution["layer_id"])
    if len(layer_ids) != len(set(layer_ids)):
        _fail(f"{path}/layer_resistance_contributions", "contains duplicate layer IDs")
    interfaces = _array(item["interface_resistance_contributions"], f"{path}/interface_resistance_contributions")
    interface_ids: list[str] = []
    for index, contribution in enumerate(interfaces):
        _interface_contribution(contribution, f"{path}/interface_resistance_contributions/{index}")
        interface_ids.append(contribution["interface_id"])
    if len(interface_ids) != len(set(interface_ids)):
        _fail(f"{path}/interface_resistance_contributions", "contains duplicate interface IDs")
    _boundary_contribution(item["boundary_resistance_contribution"], f"{path}/boundary_resistance_contribution")
    _result_quantity(
        item["total_thermal_resistance"],
        f"{path}/total_thermal_resistance",
        expected_kind=QuantityKind.ABSOLUTE_THERMAL_RESISTANCE,
        expected_unit="K/W",
    )
    _result_quantity(
        item["temperature_rise"],
        f"{path}/temperature_rise",
        expected_kind=QuantityKind.TEMPERATURE_DIFFERENCE,
        expected_unit="K",
    )
    source_temperature = _result_quantity(
        item["source_temperature"],
        f"{path}/source_temperature",
        expected_kind=QuantityKind.ABSOLUTE_TEMPERATURE,
        expected_unit="K",
    )
    _node_temperatures(
        item["node_temperatures"],
        f"{path}/node_temperatures",
        source_temperature=source_temperature,
        reference_temperature=reference_temperature,
        expected_count=len(layers) + len(interfaces) + 2,
    )
    if item["numerical_exactness"] not in {"exact", "context_rounded"}:
        _fail(f"{path}/numerical_exactness", "must be exact or context_rounded")


def _scenario(value: Any, path: str, *, expected_candidate_id: str | None = None) -> str:
    item = _closed(value, _SCENARIO_FIELDS, path)
    scenario_id = _identifier(item["scenario_id"], _SCENARIO_ID, f"{path}/scenario_id", "scenario ID")
    kind = item["scenario_kind"]
    if kind not in {"core", "oat_reference", "oat_minus", "oat_plus"}:
        _fail(f"{path}/scenario_kind", "has unsupported scenario kind")
    candidate_id = _identifier(item["candidate_id"], _CANDIDATE_ID, f"{path}/candidate_id", "candidate ID")
    if expected_candidate_id is not None and candidate_id != expected_candidate_id:
        _fail(f"{path}/candidate_id", "must equal the owning candidate ID")
    sweep_coordinates = _array(item["sweep_coordinates"], f"{path}/sweep_coordinates")
    for index, coordinate in enumerate(sweep_coordinates):
        _sweep_coordinate(coordinate, f"{path}/sweep_coordinates/{index}")
    oat_coordinate = item["oat_coordinate"]
    if oat_coordinate is not None:
        coordinate = _closed(
            oat_coordinate,
            ("parameter_ordinal", "field_path", "side"),
            f"{path}/oat_coordinate",
        )
        ordinal = _positive_integer(
            coordinate["parameter_ordinal"], f"{path}/oat_coordinate/parameter_ordinal", allow_zero=True
        )
        if coordinate["side"] == "reference":
            if ordinal != 0 or coordinate["field_path"] is not None:
                _fail(f"{path}/oat_coordinate", "reference requires ordinal zero and null field_path")
        elif coordinate["side"] in {"minus", "plus"}:
            if ordinal == 0:
                _fail(f"{path}/oat_coordinate/parameter_ordinal", "minus/plus ordinal must be positive")
            _pointer(coordinate["field_path"], f"{path}/oat_coordinate/field_path")
        else:
            _fail(f"{path}/oat_coordinate/side", "has unsupported OAT side")
    overrides = _array(item["input_overrides"], f"{path}/input_overrides")
    for index, override in enumerate(overrides):
        _input_override(override, f"{path}/input_overrides/{index}")
    disposition = item["disposition"]
    if disposition not in {"evaluated", "blocked", "not_applicable", "invalid"}:
        _fail(f"{path}/disposition", "has unsupported scenario disposition")
    applicability = item["applicability_status"]
    allowed = {
        "evaluated": {"applicable", "applicable_with_warnings"},
        "blocked": {"not_evaluated"},
        "invalid": {"not_evaluated"},
        "not_applicable": {"not_applicable"},
    }[disposition]
    if applicability not in allowed:
        _fail(f"{path}/applicability_status", "is inconsistent with disposition")
    if item["reused_core_scenario_id"] is not None:
        _identifier(
            item["reused_core_scenario_id"],
            _SCENARIO_ID,
            f"{path}/reused_core_scenario_id",
            "scenario ID",
        )
        if kind != "oat_reference":
            _fail(f"{path}/reused_core_scenario_id", "may be non-null only for oat_reference")
    _scoped_records(
        item["consumed_input_paths"],
        f"{path}/consumed_input_paths",
        _CONSUMED_PATH_FIELDS,
        consumed=True,
    )
    _scoped_records(
        item["assumption_acknowledgements_used"],
        f"{path}/assumption_acknowledgements_used",
        _ACKNOWLEDGEMENT_FIELDS,
        consumed=False,
    )
    _diagnostics(item["applicability_findings"], f"{path}/applicability_findings")
    _diagnostics(item["execution_findings"], f"{path}/execution_findings")
    constraints = _array(item["constraint_results"], f"{path}/constraint_results")
    constraint_ids: list[str] = []
    for index, constraint in enumerate(constraints):
        _constraint_result(constraint, f"{path}/constraint_results/{index}", scenario_id)
        constraint_ids.append(constraint["constraint_id"])
    if constraint_ids != sorted(set(constraint_ids)):
        _fail(f"{path}/constraint_results", "must use unique canonical constraint-ID order")
    if disposition == "evaluated":
        if item["numerical_result"] is None:
            _fail(f"{path}/numerical_result", "must be present for an evaluated scenario")
        _numerical_result(item["numerical_result"], f"{path}/numerical_result")
    elif item["numerical_result"] is not None:
        _fail(f"{path}/numerical_result", "must be null for a non-evaluated scenario")
    return scenario_id


def _coverage(value: Any, path: str, core_scenarios: Sequence[Mapping[str, Any]]) -> None:
    item = _closed(
        value,
        (
            "requested_core_scenarios",
            "evaluated_core_scenarios",
            "blocked_core_scenarios",
            "invalid_core_scenarios",
            "not_applicable_core_scenarios",
            "oat_coverage",
        ),
        path,
    )
    counts = {}
    for field in (
        "requested_core_scenarios",
        "evaluated_core_scenarios",
        "blocked_core_scenarios",
        "invalid_core_scenarios",
        "not_applicable_core_scenarios",
    ):
        counts[field] = _positive_integer(item[field], f"{path}/{field}", allow_zero=field != "requested_core_scenarios")
    actual = {
        "requested_core_scenarios": len(core_scenarios),
        "evaluated_core_scenarios": sum(s["disposition"] == "evaluated" for s in core_scenarios),
        "blocked_core_scenarios": sum(s["disposition"] == "blocked" for s in core_scenarios),
        "invalid_core_scenarios": sum(s["disposition"] == "invalid" for s in core_scenarios),
        "not_applicable_core_scenarios": sum(s["disposition"] == "not_applicable" for s in core_scenarios),
    }
    if counts != actual:
        _fail(path, "core coverage counts must equal the actual core scenario records")
    oat = item["oat_coverage"]
    if oat is not None:
        oat_item = _closed(
            oat,
            (
                "requested_oat_points",
                "evaluated_oat_points",
                "blocked_oat_points",
                "invalid_oat_points",
                "not_applicable_oat_points",
            ),
            f"{path}/oat_coverage",
        )
        oat_fields = (
            "requested_oat_points",
            "evaluated_oat_points",
            "blocked_oat_points",
            "invalid_oat_points",
            "not_applicable_oat_points",
        )
        oat_counts = [
            _positive_integer(
                oat_item[field],
                f"{path}/oat_coverage/{field}",
                allow_zero=field != "requested_oat_points",
            )
            for field in oat_fields
        ]
        if oat_counts[0] != sum(oat_counts[1:]):
            _fail(f"{path}/oat_coverage", "OAT disposition counts must sum to requested points")


def _sweep_result(value: Any, path: str, scenario_ids: Sequence[str]) -> None:
    if value is None:
        return
    item = _closed(value, ("sweep_ids", "field_paths", "enumeration_rule", "scenario_ids"), path)
    sweep_ids = _array(item["sweep_ids"], f"{path}/sweep_ids", minimum=1)
    for index, sweep_id in enumerate(sweep_ids):
        _identifier(sweep_id, _SWEEP_ID, f"{path}/sweep_ids/{index}", "sweep ID")
    if sweep_ids != sorted(set(sweep_ids)):
        _fail(f"{path}/sweep_ids", "must be unique and canonically ordered")
    field_paths = _array(item["field_paths"], f"{path}/field_paths", minimum=1)
    for index, pointer in enumerate(field_paths):
        _pointer(pointer, f"{path}/field_paths/{index}")
    if len(field_paths) != len(set(field_paths)):
        _fail(f"{path}/field_paths", "contains duplicate pointers")
    if item["enumeration_rule"] != "first_sweep_outermost_last_sweep_innermost":
        _fail(f"{path}/enumeration_rule", "has the wrong fixed enumeration rule")
    if item["scenario_ids"] != list(scenario_ids):
        _fail(f"{path}/scenario_ids", "must exactly list the owning core scenarios")


def _oat_result(value: Any, path: str, candidate_id: str) -> None:
    if value is None:
        return
    item = _closed(
        value,
        ("method", "output_metric", "reference_scenario", "parameters", "ranking_status", "sensitivity_ranking"),
        path,
    )
    if item["method"] != "oat":
        _fail(f"{path}/method", "must equal 'oat'")
    if item["output_metric"] not in {"source_temperature", "total_thermal_resistance", "temperature_margin"}:
        _fail(f"{path}/output_metric", "has unsupported metric")
    _scenario(item["reference_scenario"], f"{path}/reference_scenario", expected_candidate_id=candidate_id)
    parameters = _array(item["parameters"], f"{path}/parameters", minimum=1)
    parameter_paths: list[str] = []
    for index, raw in enumerate(parameters):
        parameter_path = f"{path}/parameters/{index}"
        parameter = _closed(
            raw,
            (
                "parameter_ordinal",
                "field_path",
                "x_reference",
                "minus_scenario",
                "plus_scenario",
                "disposition",
                "dimensional_derivative",
                "normalized_sensitivity",
                "normalized_sensitivity_disposition",
                "finding_ids",
            ),
            parameter_path,
        )
        if _positive_integer(parameter["parameter_ordinal"], f"{parameter_path}/parameter_ordinal") != index + 1:
            _fail(f"{parameter_path}/parameter_ordinal", "must equal its one-based canonical ordinal")
        parameter_paths.append(_pointer(parameter["field_path"], f"{parameter_path}/field_path"))
        _result_quantity(parameter["x_reference"], f"{parameter_path}/x_reference")
        _scenario(parameter["minus_scenario"], f"{parameter_path}/minus_scenario", expected_candidate_id=candidate_id)
        _scenario(parameter["plus_scenario"], f"{parameter_path}/plus_scenario", expected_candidate_id=candidate_id)
        if parameter["disposition"] not in {"complete", "incomplete"}:
            _fail(f"{parameter_path}/disposition", "must be complete or incomplete")
        derivative = parameter["dimensional_derivative"]
        if derivative is not None:
            derivative = _closed(
                derivative,
                ("value", "output_quantity_kind", "output_unit", "input_quantity_kind", "input_unit"),
                f"{parameter_path}/dimensional_derivative",
            )
            _canonical_decimal(derivative["value"], f"{parameter_path}/dimensional_derivative/value")
            for field in ("output_quantity_kind", "input_quantity_kind"):
                try:
                    QuantityKind(derivative[field])
                except (TypeError, ValueError):
                    _fail(f"{parameter_path}/dimensional_derivative/{field}", "must be an I1 QuantityKind")
            _non_empty(derivative["output_unit"], f"{parameter_path}/dimensional_derivative/output_unit")
            _non_empty(derivative["input_unit"], f"{parameter_path}/dimensional_derivative/input_unit")
        if parameter["normalized_sensitivity"] is not None:
            _result_quantity(
                parameter["normalized_sensitivity"],
                f"{parameter_path}/normalized_sensitivity",
                expected_kind=QuantityKind.PHYSICAL_DIMENSIONLESS,
                expected_unit="1",
            )
        if parameter["normalized_sensitivity_disposition"] not in {
            "evaluated",
            "incomplete",
            "zero_x_reference",
            "zero_y_reference",
            "absolute_temperature_not_normalized",
        }:
            _fail(f"{parameter_path}/normalized_sensitivity_disposition", "has unsupported value")
        finding_ids = _array(parameter["finding_ids"], f"{parameter_path}/finding_ids")
        if finding_ids != sorted(set(finding_ids)) or any(type(value) is not str or not value for value in finding_ids):
            _fail(f"{parameter_path}/finding_ids", "must contain unique ordered non-empty rule IDs")
    if parameter_paths != sorted(set(parameter_paths)):
        _fail(f"{path}/parameters", "must use unique lexical field-path order")
    if item["ranking_status"] not in {"performed", "not_performed"}:
        _fail(f"{path}/ranking_status", "has unsupported value")
    ranking = _array(item["sensitivity_ranking"], f"{path}/sensitivity_ranking")
    for index, raw in enumerate(ranking):
        rank_path = f"{path}/sensitivity_ranking/{index}"
        rank = _closed(raw, ("rank", "field_path", "normalized_sensitivity"), rank_path)
        if _positive_integer(rank["rank"], f"{rank_path}/rank") != index + 1:
            _fail(f"{rank_path}/rank", "must equal its one-based array ordinal")
        _pointer(rank["field_path"], f"{rank_path}/field_path")
        _result_quantity(
            rank["normalized_sensitivity"],
            f"{rank_path}/normalized_sensitivity",
            expected_kind=QuantityKind.PHYSICAL_DIMENSIONLESS,
            expected_unit="1",
        )
    if item["ranking_status"] == "not_performed" and ranking:
        _fail(f"{path}/sensitivity_ranking", "must be empty when ranking was not performed")


def _candidate_result(value: Any, path: str) -> str:
    item = _closed(
        value,
        ("candidate_id", "coverage_summary", "core_scenarios", "sweep_result", "oat_result", "findings", "warnings"),
        path,
    )
    candidate_id = _identifier(item["candidate_id"], _CANDIDATE_ID, f"{path}/candidate_id", "candidate ID")
    scenarios = _array(item["core_scenarios"], f"{path}/core_scenarios", minimum=1)
    scenario_ids: list[str] = []
    for index, scenario in enumerate(scenarios):
        scenario_mapping = _mapping(scenario, f"{path}/core_scenarios/{index}")
        if scenario_mapping.get("scenario_kind") != "core":
            _fail(f"{path}/core_scenarios/{index}/scenario_kind", "must equal 'core'")
        scenario_ids.append(
            _scenario(scenario, f"{path}/core_scenarios/{index}", expected_candidate_id=candidate_id)
        )
    if len(scenario_ids) != len(set(scenario_ids)):
        _fail(f"{path}/core_scenarios", "contains duplicate scenario IDs")
    _coverage(item["coverage_summary"], f"{path}/coverage_summary", scenarios)
    _sweep_result(item["sweep_result"], f"{path}/sweep_result", scenario_ids)
    _oat_result(item["oat_result"], f"{path}/oat_result", candidate_id)
    _diagnostics(item["findings"], f"{path}/findings")
    _diagnostics(item["warnings"], f"{path}/warnings")
    return candidate_id


def _objective(value: Any, path: str) -> None:
    item = _closed(value, ("metric", "direction", "reference_requirement_id"), path)
    directions = {
        "source_temperature": "minimize",
        "total_thermal_resistance": "minimize",
        "temperature_margin": "maximize",
    }
    if item["metric"] not in directions:
        _fail(f"{path}/metric", "has unsupported metric")
    if item["direction"] != directions[item["metric"]]:
        _fail(f"{path}/direction", "does not match the metric")
    reference = item["reference_requirement_id"]
    if reference is not None and (
        type(reference) is not str or re.fullmatch(r"REQ-[0-9]{3}", reference) is None
    ):
        _fail(f"{path}/reference_requirement_id", "has invalid requirement ID syntax")
    if item["metric"] == "temperature_margin" and reference is None:
        _fail(f"{path}/reference_requirement_id", "temperature_margin requires a reference")


def _candidate_comparison(value: Any, path: str, candidate_ids: set[str]) -> None:
    item = _closed(
        value,
        (
            "objective",
            "comparison_basis_rule",
            "constraint_handling",
            "ranking_status",
            "candidate_eligibility",
            "ranked_entries",
            "tie_rule",
            "calculation_notice",
        ),
        path,
    )
    _objective(item["objective"], f"{path}/objective")
    if item["comparison_basis_rule"] != "sole_unswept_baseline_only":
        _fail(f"{path}/comparison_basis_rule", "has the wrong fixed basis rule")
    if item["constraint_handling"] not in {"exclude_violating_from_rank", "report_only"}:
        _fail(f"{path}/constraint_handling", "has unsupported value")
    if item["ranking_status"] not in {"performed", "not_performed"}:
        _fail(f"{path}/ranking_status", "has unsupported value")
    eligibility = _array(item["candidate_eligibility"], f"{path}/candidate_eligibility")
    eligible_ids: list[str] = []
    for index, raw in enumerate(eligibility):
        entry_path = f"{path}/candidate_eligibility/{index}"
        entry = _closed(raw, ("candidate_id", "eligible", "basis_scenario_id", "reason_ids"), entry_path)
        candidate_id = _identifier(entry["candidate_id"], _CANDIDATE_ID, f"{entry_path}/candidate_id", "candidate ID")
        eligible_ids.append(candidate_id)
        if type(entry["eligible"]) is not bool:
            _fail(f"{entry_path}/eligible", "must be a boolean")
        if entry["basis_scenario_id"] is not None:
            _identifier(entry["basis_scenario_id"], _SCENARIO_ID, f"{entry_path}/basis_scenario_id", "scenario ID")
        reasons = _array(entry["reason_ids"], f"{entry_path}/reason_ids")
        if reasons != sorted(set(reasons)) or any(type(reason) is not str or not reason for reason in reasons):
            _fail(f"{entry_path}/reason_ids", "must contain unique ordered non-empty rule IDs")
    if set(eligible_ids) != candidate_ids or len(eligible_ids) != len(candidate_ids):
        _fail(f"{path}/candidate_eligibility", "must contain every candidate exactly once")
    ranked = _array(item["ranked_entries"], f"{path}/ranked_entries")
    ranked_ids: set[str] = set()
    for index, raw in enumerate(ranked):
        entry_path = f"{path}/ranked_entries/{index}"
        entry = _closed(
            raw,
            ("rank", "candidate_id", "scenario_id", "objective_metric", "objective_value"),
            entry_path,
        )
        if _positive_integer(entry["rank"], f"{entry_path}/rank") != index + 1:
            _fail(f"{entry_path}/rank", "must equal its one-based array ordinal")
        candidate_id = _identifier(entry["candidate_id"], _CANDIDATE_ID, f"{entry_path}/candidate_id", "candidate ID")
        if candidate_id not in candidate_ids or candidate_id in ranked_ids:
            _fail(f"{entry_path}/candidate_id", "must be a unique candidate in this content")
        ranked_ids.add(candidate_id)
        _identifier(entry["scenario_id"], _SCENARIO_ID, f"{entry_path}/scenario_id", "scenario ID")
        if entry["objective_metric"] != item["objective"]["metric"]:
            _fail(f"{entry_path}/objective_metric", "must equal the comparison objective metric")
        _result_quantity(entry["objective_value"], f"{entry_path}/objective_value")
    if item["ranking_status"] == "not_performed" and ranked:
        _fail(f"{path}/ranked_entries", "must be empty when ranking was not performed")
    if item["tie_rule"] != "objective_value_then_candidate_id":
        _fail(f"{path}/tie_rule", "has the wrong fixed tie rule")
    if item["calculation_notice"] != "Ranking is a conditional calculation, not a recommendation or approval.":
        _fail(f"{path}/calculation_notice", "has the wrong exact calculation notice")


def validate_strict_1d_result_content(content: Mapping[str, Any]) -> None:
    """Validate the exact closed strict-1D v1 model-specific content contract."""
    item = _closed(
        content,
        (
            "scenario_policy_version",
            "constraint_policy_version",
            "ranking_policy_version",
            "oat_policy_version",
            "candidate_results",
            "candidate_comparison",
            "findings",
            "warnings",
        ),
        "strict_1d_result_content",
    )
    exact_versions = {
        "scenario_policy_version": SCENARIO_POLICY_VERSION,
        "constraint_policy_version": CONSTRAINT_POLICY_VERSION,
        "ranking_policy_version": RANKING_POLICY_VERSION,
        "oat_policy_version": OAT_POLICY_VERSION,
    }
    for field, expected in exact_versions.items():
        if item[field] != expected:
            _fail(f"/{field}", f"must equal {expected!r}")
    candidates = _array(item["candidate_results"], "/candidate_results", minimum=1)
    candidate_ids: list[str] = []
    for index, candidate in enumerate(candidates):
        candidate_ids.append(_candidate_result(candidate, f"/candidate_results/{index}"))
    if len(candidate_ids) != len(set(candidate_ids)):
        _fail("/candidate_results", "contains duplicate candidate IDs")
    _candidate_comparison(item["candidate_comparison"], "/candidate_comparison", set(candidate_ids))
    _diagnostics(item["findings"], "/findings")
    _diagnostics(item["warnings"], "/warnings")
    expected_findings = {
        canonical_json_bytes(diagnostic): diagnostic
        for candidate in candidates
        for diagnostic in candidate["findings"]
    }
    expected_warnings = {
        canonical_json_bytes(diagnostic): diagnostic
        for candidate in candidates
        for diagnostic in candidate["warnings"]
    }
    actual_findings = [canonical_json_bytes(diagnostic) for diagnostic in item["findings"]]
    actual_warnings = [canonical_json_bytes(diagnostic) for diagnostic in item["warnings"]]
    ordered_findings = [
        canonical_json_bytes(diagnostic)
        for diagnostic in sorted(expected_findings.values(), key=lambda value: (
            value["rule_id"], tuple(value["field_paths"]), value["message"], canonical_json_bytes(value)
        ))
    ]
    ordered_warnings = [
        canonical_json_bytes(diagnostic)
        for diagnostic in sorted(expected_warnings.values(), key=lambda value: (
            value["rule_id"], tuple(value["field_paths"]), value["message"], canonical_json_bytes(value)
        ))
    ]
    if actual_findings != ordered_findings:
        _fail("/findings", "must equal the canonical union of candidate findings")
    if actual_warnings != ordered_warnings:
        _fail("/warnings", "must equal the canonical union of candidate warnings")


def build_strict_1d_result_payload(content: Mapping[str, Any]) -> Mapping[str, Any]:
    """Validate content and build the exact unchanged frozen I3 payload wrapper."""
    validate_strict_1d_result_content(content)
    wrapper: dict[str, Any] = {
        "schema_id": RESULT_PAYLOAD_SCHEMA_ID,
        "schema_version": RESULT_PAYLOAD_SCHEMA_VERSION,
        "content": copy.deepcopy(dict(content)),
        "content_sha256": "",
    }
    wrapper["content_sha256"] = result_payload_content_sha256(wrapper)
    return wrapper


__all__ = [
    "Strict1DResultValidationError",
    "build_strict_1d_result_payload",
    "validate_strict_1d_result_content",
]
