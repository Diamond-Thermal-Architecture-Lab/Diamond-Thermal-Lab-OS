"""Immutable persisted M16A Engineering Problem Representation (EPR)."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .quantities import QuantityKind, QuantifiedValue, UNIT_REGISTRY_VERSION
from .serialization import CANONICAL_JSON_VERSION, canonical_json_bytes, canonical_sha256


PROBLEM_FORMAT_VERSION = "m16a-engineering-problem-1.0"
EPR_CONTENT_IDENTITY_VERSION = "m16a-epr-content-identity-1.0"
CANDIDATE_CONTENT_IDENTITY_VERSION = "m16a-candidate-content-identity-1.0"
COMPILER_POLICY_VERSION = "m16a-epr-compiler-1.0"
HEAT_SOURCE_CONSISTENCY_POLICY_VERSION = "m16a-heat-source-consistency-1.0"

_TOP_LEVEL_FIELDS = (
    "problem_format_version", "problem_id", "case_id", "title", "purpose",
    "source_case_sha256", "requirements", "heat_sources", "geometry",
    "materials", "interfaces", "boundary_conditions", "constraints",
    "candidates", "unknowns", "compilation", "confidentiality_level",
    "compiled_content_sha256",
)
_CANDIDATE_FIELDS = (
    "candidate_id", "candidate_role", "label", "parent_requirement_id",
    "geometry", "materials", "interfaces", "boundary_conditions",
    "changed_field_paths", "applicable_constraint_ids", "assumption_paths",
    "evidence_required_paths", "resolved_content_sha256",
)
_ELIGIBLE_SOURCE_FILES = (
    "00_problem_intake.yml", "01_thermal_design_passport.yml",
    "02_decision_board.md", "03_architecture_genomes.yml",
    "04_design_space_scorecard.md", "05_red_flags.md",
    "06_next_best_action.md", "07_validation_plan.md",
    "08_supplier_specification.md", "09_customer_memo.md",
    "10_claim_ledger.yml", "11_engineering_memory_entry.md",
)
_CANONICAL_UNITS = {
    QuantityKind.POWER: "W",
    QuantityKind.HEAT_FLUX: "W/m^2",
    QuantityKind.LENGTH: "m",
    QuantityKind.AREA: "m^2",
    QuantityKind.THERMAL_CONDUCTIVITY: "W/(m*K)",
    QuantityKind.AREA_THERMAL_RESISTANCE: "m^2*K/W",
    QuantityKind.ABSOLUTE_THERMAL_RESISTANCE: "K/W",
    QuantityKind.AREA_THERMAL_CONDUCTANCE: "W/(m^2*K)",
    QuantityKind.ABSOLUTE_TEMPERATURE: "K",
    QuantityKind.TEMPERATURE_DIFFERENCE: "K",
    QuantityKind.PHYSICAL_DIMENSIONLESS: "1",
}
_ID_PATTERNS = {
    "problem_id": re.compile(r"^EPR-[0-9]{3}$"),
    "case_id": re.compile(r"^[a-z0-9_-]+$"),
    "requirement_id": re.compile(r"^REQ-[0-9]{3}$"),
    "source_id": re.compile(r"^HSR-[0-9]{3}$"),
    "stack_id": re.compile(r"^STK-[0-9]{3}$"),
    "layer_id": re.compile(r"^LYR-[0-9]{3}$"),
    "material_id": re.compile(r"^MAT-[0-9]{3}$"),
    "property_id": re.compile(r"^PRP-[0-9]{3}$"),
    "interface_id": re.compile(r"^IFC-[0-9]{3}$"),
    "constraint_id": re.compile(r"^CON-[0-9]{3}$"),
    "candidate_id": re.compile(r"^CND-[0-9]{3}$"),
    "unknown_id": re.compile(r"^UNK-[0-9]{3}$"),
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_POINTER = re.compile(r"^(?:/(?:[^~/]|~[01])*)+$")
_FINDING_ID = re.compile(
    r"^M16A-EPR-(?:SCHEMA|ID|QTY|PROV|UNC|REF|SOURCE|HEAT|GEOM|MAT|IFC|BC|CND|UNKNOWN|CONF)-[0-9]{3}$"
)


class EngineeringProblemValidationError(ValueError):
    """Raised when persisted EPR data violates the I2A contract."""


def _fail(path: str, message: str) -> None:
    raise EngineeringProblemValidationError(f"{path}: {message}")


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(path, "must be an object")
    if any(type(key) is not str for key in value):
        _fail(path, "object keys must be strings")
    return value


def _closed(
    value: Any,
    required: Sequence[str],
    path: str,
    optional: Sequence[str] = (),
) -> Mapping[str, Any]:
    result = _mapping(value, path)
    expected = set(required) | set(optional)
    missing = set(required) - set(result)
    unknown = set(result) - expected
    if missing:
        _fail(path, f"missing required fields: {sorted(missing)!r}")
    if unknown:
        _fail(path, f"unknown fields: {sorted(unknown)!r}")
    return result


def _non_empty(value: Any, path: str) -> str:
    if type(value) is not str or not value:
        _fail(path, "must be a non-empty string")
    return value


def _enum(value: Any, allowed: set[str], path: str) -> str:
    if type(value) is not str or value not in allowed:
        _fail(path, f"must be one of {sorted(allowed)!r}")
    return value


def _identifier(value: Any, kind: str, path: str) -> str:
    if type(value) is not str or _ID_PATTERNS[kind].fullmatch(value) is None:
        _fail(path, f"has invalid {kind} syntax")
    return value


def _sha(value: Any, path: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        _fail(path, "must be a lowercase SHA-256 string")
    return value


def _pointer(value: Any, path: str) -> str:
    if type(value) is not str or _POINTER.fullmatch(value) is None:
        _fail(path, "must be a non-empty RFC 6901 JSON Pointer")
    return value


def _list(value: Any, path: str, *, minimum: int = 0) -> list[Any]:
    if type(value) is not list or len(value) < minimum:
        _fail(path, f"must be an array with at least {minimum} item(s)")
    return value


def _ordered_unique(values: list[str], path: str) -> None:
    if len(values) != len(set(values)):
        _fail(path, "contains duplicates")
    if values != sorted(values):
        _fail(path, "must use canonical lexical order")


def _validate_reference(value: Any, path: str) -> None:
    reference = _non_empty(value, path)
    if "\\" in reference or reference.startswith("/") or re.match(r"^[A-Za-z]:", reference):
        _fail(path, "must be an opaque reference or repository-relative POSIX reference")
    if any(part in {".", ".."} for part in reference.split("/")):
        _fail(path, "must not contain dot or traversal components")


def _validate_provenance(value: Any, path: str, status: str | None = None) -> None:
    fields = (
        "source_type", "reference", "evidence_object_ids",
        "measurement_reference_ids", "source_sha256", "review_status", "rationale",
    )
    item = _closed(value, fields, path)
    source_type = _enum(item["source_type"], {
        "requirement", "evidence_object", "measurement_reference", "literature",
        "supplier", "expert_judgment", "assumption", "synthetic_fixture",
    }, f"{path}/source_type")
    _validate_reference(item["reference"], f"{path}/reference")
    evd = _list(item["evidence_object_ids"], f"{path}/evidence_object_ids")
    msr = _list(item["measurement_reference_ids"], f"{path}/measurement_reference_ids")
    if len(evd) > 1 or len(msr) > 1:
        _fail(path, "evidence and measurement ID arrays have maximum cardinality one")
    for index, identifier in enumerate(evd):
        if type(identifier) is not str or re.fullmatch(r"EVD-[0-9]{3}", identifier) is None:
            _fail(f"{path}/evidence_object_ids/{index}", "has invalid EVD ID syntax")
    for index, identifier in enumerate(msr):
        if type(identifier) is not str or re.fullmatch(r"MSR-[0-9]{3}", identifier) is None:
            _fail(f"{path}/measurement_reference_ids/{index}", "has invalid MSR ID syntax")
    _ordered_unique(evd, f"{path}/evidence_object_ids")
    _ordered_unique(msr, f"{path}/measurement_reference_ids")
    if source_type == "evidence_object" and (len(evd) != 1 or msr):
        _fail(path, "evidence_object provenance requires one EVD and no MSR")
    if source_type == "measurement_reference" and (len(evd) != 1 or len(msr) != 1):
        _fail(path, "measurement_reference provenance requires one EVD and one MSR")
    if source_type not in {"evidence_object", "measurement_reference"} and (evd or msr):
        _fail(path, "this provenance source type cannot carry EVD or MSR IDs")
    if item["source_sha256"] is not None:
        _sha(item["source_sha256"], f"{path}/source_sha256")
    review_status = _enum(item["review_status"], {
        "unverified", "source_documented", "reviewed", "rejected", "not_applicable",
    }, f"{path}/review_status")
    rationale = item["rationale"]
    if rationale is not None and (type(rationale) is not str or not rationale):
        _fail(f"{path}/rationale", "must be null or a non-empty string")
    if status == "assumed" and not rationale:
        _fail(f"{path}/rationale", "assumed values require a rationale")
    if source_type == "assumption" and status != "assumed":
        _fail(path, "assumption provenance requires status assumed")
    if review_status == "rejected" and status not in {"conflicting", "evidence_required"}:
        _fail(path, "rejected provenance requires conflicting or evidence_required status")


def _i1_from_parts(value: Mapping[str, Any], path: str) -> QuantifiedValue:
    try:
        return QuantifiedValue.from_dict({
            "quantity_kind": value["quantity_kind"],
            "canonical_value": value["value"],
            "canonical_unit": value["unit"],
            "conversion": value["conversion"],
        })
    except (KeyError, TypeError, ValueError) as exc:
        _fail(path, f"does not reconstruct through I1: {exc}")


def _validate_helper(value: Any, path: str) -> QuantifiedValue:
    item = _closed(value, ("value", "unit", "quantity_kind", "conversion"), path)
    if type(item["value"]) is not str:
        _fail(f"{path}/value", "physical values must be decimal strings")
    return _i1_from_parts(item, path)


def _validate_uncertainty(
    value: Any,
    path: str,
    central: QuantifiedValue | None,
    expected_kind: QuantityKind,
) -> None:
    item = _mapping(value, path)
    kind = item.get("kind")
    if kind in {"not_provided", "not_applicable"}:
        item = _closed(item, ("kind", "basis"), path)
    elif kind == "absolute":
        item = _closed(item, ("kind", "basis", "amount"), path)
    elif kind == "relative":
        item = _closed(item, ("kind", "basis", "fraction"), path)
    elif kind == "interval":
        item = _closed(item, ("kind", "basis", "lower", "upper"), path)
    else:
        _fail(f"{path}/kind", "must identify one of the five uncertainty forms")
    _non_empty(item["basis"], f"{path}/basis")
    if kind == "absolute":
        amount = _validate_helper(item["amount"], f"{path}/amount")
        required = (QuantityKind.TEMPERATURE_DIFFERENCE
                    if expected_kind is QuantityKind.ABSOLUTE_TEMPERATURE else expected_kind)
        if amount.quantity_kind is not required:
            _fail(f"{path}/amount", "has the wrong quantity kind")
        if amount.canonical_value < 0:
            _fail(f"{path}/amount/value", "must be non-negative")
    elif kind == "relative":
        fraction = _validate_helper(item["fraction"], f"{path}/fraction")
        if (fraction.quantity_kind is not QuantityKind.PHYSICAL_DIMENSIONLESS
                or fraction.canonical_unit != "1"):
            _fail(f"{path}/fraction", "must be physical_dimensionless with unit 1")
        if fraction.canonical_value < 0:
            _fail(f"{path}/fraction/value", "must be non-negative")
    elif kind == "interval":
        lower = _validate_helper(item["lower"], f"{path}/lower")
        upper = _validate_helper(item["upper"], f"{path}/upper")
        if lower.quantity_kind is not expected_kind or upper.quantity_kind is not expected_kind:
            _fail(path, "interval bounds must have the envelope quantity kind")
        if lower.canonical_unit != upper.canonical_unit:
            _fail(path, "interval bounds must have the same canonical unit")
        if lower.canonical_value > upper.canonical_value:
            _fail(path, "interval lower bound exceeds upper bound")
        if central is not None and not (
            lower.canonical_value <= central.canonical_value <= upper.canonical_value
        ):
            _fail(path, "usable central value must lie inside the interval")


def _validate_envelope(value: Any, expected_kind: QuantityKind, path: str) -> None:
    fields = ("value", "unit", "quantity_kind", "provenance", "uncertainty", "confidence", "status", "conversion")
    item = _closed(value, fields, path)
    status = _enum(item["status"], {
        "provided", "assumed", "missing", "conflicting", "evidence_required",
    }, f"{path}/status")
    if item["quantity_kind"] != expected_kind.value:
        _fail(f"{path}/quantity_kind", f"must be {expected_kind.value!r}")
    if item["unit"] != _CANONICAL_UNITS[expected_kind]:
        _fail(f"{path}/unit", f"must be canonical unit {_CANONICAL_UNITS[expected_kind]!r}")
    _enum(item["confidence"], {"unknown", "low", "medium", "high", "not_applicable"}, f"{path}/confidence")
    _validate_provenance(item["provenance"], f"{path}/provenance", status)
    central: QuantifiedValue | None = None
    if status == "missing":
        if item["value"] is not None or item["conversion"] is not None:
            _fail(path, "missing values require null value and conversion")
        if item["confidence"] != "unknown":
            _fail(f"{path}/confidence", "missing values require unknown confidence")
        if not isinstance(item["uncertainty"], Mapping) or item["uncertainty"].get("kind") != "not_provided":
            _fail(f"{path}/uncertainty", "missing values require not_provided uncertainty")
    else:
        if type(item["value"]) is not str:
            _fail(f"{path}/value", "non-missing physical values must be decimal strings")
        if not isinstance(item["conversion"], Mapping):
            _fail(f"{path}/conversion", "non-missing physical values require conversion data")
        central = _i1_from_parts(item, path)
    usable_central = None if status == "conflicting" else central
    _validate_uncertainty(item["uncertainty"], f"{path}/uncertainty", usable_central, expected_kind)


def _validate_geometry(value: Any, path: str) -> tuple[list[str], dict[str, int]]:
    item = _closed(value, ("stack_id", "source_to_sink_direction", "layers"), path)
    _identifier(item["stack_id"], "stack_id", f"{path}/stack_id")
    _non_empty(item["source_to_sink_direction"], f"{path}/source_to_sink_direction")
    layers = _list(item["layers"], f"{path}/layers", minimum=1)
    layer_ids: list[str] = []
    for index, raw in enumerate(layers):
        layer_path = f"{path}/layers/{index}"
        layer = _closed(raw, ("layer_id", "order", "role", "material_id", "thickness", "footprint_dimensions", "footprint_area", "orientation"), layer_path)
        layer_ids.append(_identifier(layer["layer_id"], "layer_id", f"{layer_path}/layer_id"))
        if type(layer["order"]) is not int or layer["order"] < 0:
            _fail(f"{layer_path}/order", "must be a non-negative integer")
        _non_empty(layer["role"], f"{layer_path}/role")
        _identifier(layer["material_id"], "material_id", f"{layer_path}/material_id")
        _validate_envelope(layer["thickness"], QuantityKind.LENGTH, f"{layer_path}/thickness")
        dimensions = _list(layer["footprint_dimensions"], f"{layer_path}/footprint_dimensions", minimum=1)
        for dimension_index, dimension in enumerate(dimensions):
            _validate_envelope(dimension, QuantityKind.LENGTH, f"{layer_path}/footprint_dimensions/{dimension_index}")
        _validate_envelope(layer["footprint_area"], QuantityKind.AREA, f"{layer_path}/footprint_area")
        orientation = _closed(layer["orientation"], ("stack_normal_axis", "rotation_description"), f"{layer_path}/orientation")
        _enum(orientation["stack_normal_axis"], {"x", "y", "z", "other"}, f"{layer_path}/orientation/stack_normal_axis")
        if orientation["rotation_description"] is not None:
            _non_empty(orientation["rotation_description"], f"{layer_path}/orientation/rotation_description")
    if len(layer_ids) != len(set(layer_ids)):
        _fail(f"{path}/layers", "layer IDs must be unique")
    expected = sorted(layers, key=lambda layer: (layer["order"], layer["layer_id"]))
    if layers != expected or [layer["order"] for layer in layers] != list(range(len(layers))):
        _fail(f"{path}/layers", "must use contiguous zero-based canonical order")
    return layer_ids, {layer_id: index for index, layer_id in enumerate(layer_ids)}


def _validate_materials(value: Any, path: str) -> list[str]:
    materials = _list(value, path, minimum=1)
    material_ids: list[str] = []
    for index, raw in enumerate(materials):
        material_path = f"{path}/{index}"
        item = _closed(raw, ("material_id", "label", "material_class", "anisotropy_representation", "thermal_properties"), material_path)
        material_ids.append(_identifier(item["material_id"], "material_id", f"{material_path}/material_id"))
        _non_empty(item["label"], f"{material_path}/label")
        _non_empty(item["material_class"], f"{material_path}/material_class")
        _enum(item["anisotropy_representation"], {"isotropic", "principal_components", "rotated_tensor", "other"}, f"{material_path}/anisotropy_representation")
        properties = _list(item["thermal_properties"], f"{material_path}/thermal_properties", minimum=1)
        property_ids: list[str] = []
        for prop_index, raw_property in enumerate(properties):
            prop_path = f"{material_path}/thermal_properties/{prop_index}"
            prop = _closed(raw_property, ("property_id", "component", "thermal_conductivity", "temperature_basis", "condition_basis"), prop_path)
            property_ids.append(_identifier(prop["property_id"], "property_id", f"{prop_path}/property_id"))
            _enum(prop["component"], {"isotropic", "x", "y", "z", "xy", "xz", "yz", "other"}, f"{prop_path}/component")
            _validate_envelope(prop["thermal_conductivity"], QuantityKind.THERMAL_CONDUCTIVITY, f"{prop_path}/thermal_conductivity")
            _non_empty(prop["temperature_basis"], f"{prop_path}/temperature_basis")
            _non_empty(prop["condition_basis"], f"{prop_path}/condition_basis")
        _ordered_unique(property_ids, f"{material_path}/thermal_properties")
    _ordered_unique(material_ids, path)
    return material_ids


def _validate_interfaces(value: Any, layer_order: Mapping[str, int], path: str) -> None:
    interfaces = _list(value, path)
    ordered_layers = sorted(layer_order, key=layer_order.__getitem__)
    expected_pairs = list(zip(ordered_layers, ordered_layers[1:]))
    if len(interfaces) != len(expected_pairs):
        _fail(path, f"must contain exactly {len(expected_pairs)} interface(s), one per adjacent layer pair")
    ids: list[str] = []
    pairs: list[tuple[str, str]] = []
    for index, raw in enumerate(interfaces):
        interface_path = f"{path}/{index}"
        item = _closed(raw, ("interface_id", "upstream_layer_id", "downstream_layer_id", "representation_type", "value", "effective_area", "condition_basis"), interface_path)
        ids.append(_identifier(item["interface_id"], "interface_id", f"{interface_path}/interface_id"))
        upstream = _identifier(item["upstream_layer_id"], "layer_id", f"{interface_path}/upstream_layer_id")
        downstream = _identifier(item["downstream_layer_id"], "layer_id", f"{interface_path}/downstream_layer_id")
        if upstream not in layer_order or downstream not in layer_order:
            _fail(interface_path, "interface layer references must resolve")
        if layer_order[downstream] != layer_order[upstream] + 1:
            _fail(interface_path, "interface layers must be adjacent and source-to-sink ordered")
        pairs.append((upstream, downstream))
        representation = _enum(item["representation_type"], {"area_normalized_resistance", "absolute_resistance", "area_normalized_conductance", "ideal_zero"}, f"{interface_path}/representation_type")
        expected_kind = {
            "area_normalized_resistance": QuantityKind.AREA_THERMAL_RESISTANCE,
            "absolute_resistance": QuantityKind.ABSOLUTE_THERMAL_RESISTANCE,
            "area_normalized_conductance": QuantityKind.AREA_THERMAL_CONDUCTANCE,
            "ideal_zero": QuantityKind.AREA_THERMAL_RESISTANCE,
        }[representation]
        _validate_envelope(item["value"], expected_kind, f"{interface_path}/value")
        if representation == "ideal_zero" and item["value"].get("value") != "0":
            _fail(f"{interface_path}/value", "ideal_zero requires canonical value 0")
        _validate_envelope(item["effective_area"], QuantityKind.AREA, f"{interface_path}/effective_area")
        _non_empty(item["condition_basis"], f"{interface_path}/condition_basis")
    if len(ids) != len(set(ids)):
        _fail(path, "interface IDs must be unique")
    if len(pairs) != len(set(pairs)):
        _fail(path, "each adjacent layer pair must have exactly one interface")
    if set(pairs) != set(expected_pairs):
        _fail(path, "interfaces must cover every adjacent layer pair exactly once")
    expected = sorted(interfaces, key=lambda interface: (layer_order[interface["upstream_layer_id"]], interface["interface_id"]))
    if interfaces != expected:
        _fail(path, "interfaces must use upstream-layer then ID canonical order")


def _validate_boundary(value: Any, path: str) -> None:
    item = _closed(value, ("source_side", "downstream"), path)
    source = _closed(item["source_side"], ("heat_flow_fraction", "path_disposition"), f"{path}/source_side")
    _validate_envelope(source["heat_flow_fraction"], QuantityKind.PHYSICAL_DIMENSIONLESS, f"{path}/source_side/heat_flow_fraction")
    _enum(source["path_disposition"], {"adiabatic_other_paths", "declared_parallel_paths", "unknown"}, f"{path}/source_side/path_disposition")
    downstream = _mapping(item["downstream"], f"{path}/downstream")
    representation = downstream.get("representation_type")
    if representation == "fixed_temperature":
        downstream = _closed(downstream, ("representation_type", "terminal_plane", "reference_temperature"), f"{path}/downstream")
        _non_empty(downstream["terminal_plane"], f"{path}/downstream/terminal_plane")
        _validate_envelope(downstream["reference_temperature"], QuantityKind.ABSOLUTE_TEMPERATURE, f"{path}/downstream/reference_temperature")
    elif representation == "absolute_resistance":
        downstream = _closed(downstream, ("representation_type", "resistance", "reference_temperature", "operating_basis"), f"{path}/downstream")
        _validate_envelope(downstream["resistance"], QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, f"{path}/downstream/resistance")
        _validate_envelope(downstream["reference_temperature"], QuantityKind.ABSOLUTE_TEMPERATURE, f"{path}/downstream/reference_temperature")
        _non_empty(downstream["operating_basis"], f"{path}/downstream/operating_basis")
    elif representation == "direct_convection":
        downstream = _closed(downstream, ("representation_type", "heat_transfer_coefficient", "boundary_area", "ambient_temperature", "operating_basis"), f"{path}/downstream")
        _validate_envelope(downstream["heat_transfer_coefficient"], QuantityKind.AREA_THERMAL_CONDUCTANCE, f"{path}/downstream/heat_transfer_coefficient")
        _validate_envelope(downstream["boundary_area"], QuantityKind.AREA, f"{path}/downstream/boundary_area")
        _validate_envelope(downstream["ambient_temperature"], QuantityKind.ABSOLUTE_TEMPERATURE, f"{path}/downstream/ambient_temperature")
        _non_empty(downstream["operating_basis"], f"{path}/downstream/operating_basis")
    elif representation == "other":
        downstream = _closed(downstream, ("representation_type", "description"), f"{path}/downstream")
        _non_empty(downstream["description"], f"{path}/downstream/description")
    else:
        _fail(f"{path}/downstream/representation_type", "has an invalid representation")


def _validate_complete_problem_view(
    geometry: Any,
    materials: Any,
    interfaces: Any,
    boundary: Any,
    path: str,
) -> None:
    layer_ids, layer_order = _validate_geometry(geometry, f"{path}/geometry")
    material_ids = _validate_materials(materials, f"{path}/materials")
    referenced_materials = {layer["material_id"] for layer in geometry["layers"]}
    if not referenced_materials.issubset(set(material_ids)):
        _fail(f"{path}/geometry/layers", "all layer material references must resolve")
    _validate_interfaces(interfaces, layer_order, f"{path}/interfaces")
    _validate_boundary(boundary, f"{path}/boundary_conditions")
    if not layer_ids:
        _fail(f"{path}/geometry/layers", "must not be empty")


def _validate_heat_sources(value: Any, layer_ids: set[str], path: str) -> None:
    sources = _list(value, path, minimum=1)
    ids: list[str] = []
    for index, raw in enumerate(sources):
        source_path = f"{path}/{index}"
        item = _closed(raw, ("source_id", "source_location", "total_power", "heat_flux", "footprint", "heated_area", "spatial_profile", "operating_mode", "duty_cycle"), source_path)
        ids.append(_identifier(item["source_id"], "source_id", f"{source_path}/source_id"))
        location = _closed(item["source_location"], ("layer_id", "location_type", "region_name"), f"{source_path}/source_location")
        layer_id = _identifier(location["layer_id"], "layer_id", f"{source_path}/source_location/layer_id")
        if layer_id not in layer_ids:
            _fail(f"{source_path}/source_location/layer_id", "must reference a top-level layer")
        location_type = _enum(location["location_type"], {"source_side", "sink_side", "named_region"}, f"{source_path}/source_location/location_type")
        if location_type == "named_region":
            _non_empty(location["region_name"], f"{source_path}/source_location/region_name")
        elif location["region_name"] is not None:
            _fail(f"{source_path}/source_location/region_name", "must be null for a layer face")
        _validate_envelope(item["total_power"], QuantityKind.POWER, f"{source_path}/total_power")
        _validate_envelope(item["heat_flux"], QuantityKind.HEAT_FLUX, f"{source_path}/heat_flux")
        footprint = _closed(item["footprint"], ("shape", "dimensions", "profile_reference"), f"{source_path}/footprint")
        _non_empty(footprint["shape"], f"{source_path}/footprint/shape")
        dimensions = _list(footprint["dimensions"], f"{source_path}/footprint/dimensions", minimum=1)
        for dimension_index, dimension in enumerate(dimensions):
            _validate_envelope(dimension, QuantityKind.LENGTH, f"{source_path}/footprint/dimensions/{dimension_index}")
        if footprint["profile_reference"] is not None:
            _non_empty(footprint["profile_reference"], f"{source_path}/footprint/profile_reference")
        _validate_envelope(item["heated_area"], QuantityKind.AREA, f"{source_path}/heated_area")
        _enum(item["spatial_profile"], {"uniform_surface", "nonuniform_surface", "volumetric", "distributed", "other"}, f"{source_path}/spatial_profile")
        _enum(item["operating_mode"], {"steady_state", "transient", "pulsed", "other"}, f"{source_path}/operating_mode")
        if item["duty_cycle"] is not None:
            _validate_envelope(item["duty_cycle"], QuantityKind.PHYSICAL_DIMENSIONLESS, f"{source_path}/duty_cycle")
    _ordered_unique(ids, path)


def _validate_findings(value: Any, path: str) -> None:
    findings = _list(value, path)
    sort_keys: list[tuple[str, tuple[str, ...], str]] = []
    for index, raw in enumerate(findings):
        finding_path = f"{path}/{index}"
        item = _closed(raw, ("rule_id", "classification", "field_paths", "message", "required_action"), finding_path)
        if type(item["rule_id"]) is not str or _FINDING_ID.fullmatch(item["rule_id"]) is None:
            _fail(f"{finding_path}/rule_id", "has invalid finding rule syntax")
        if item["classification"] != "STRUCTURAL_MODEL_INDEPENDENT":
            _fail(f"{finding_path}/classification", "has invalid classification")
        field_paths = _list(item["field_paths"], f"{finding_path}/field_paths")
        for field_index, field_path in enumerate(field_paths):
            _pointer(field_path, f"{finding_path}/field_paths/{field_index}")
        _ordered_unique(field_paths, f"{finding_path}/field_paths")
        message = _non_empty(item["message"], f"{finding_path}/message")
        _non_empty(item["required_action"], f"{finding_path}/required_action")
        sort_keys.append((item["rule_id"], tuple(field_paths), message))
    if sort_keys != sorted(sort_keys):
        _fail(path, "findings must use rule/path/message canonical order")


def _resolve_pointer(document: Any, pointer: str, path: str) -> None:
    current = document
    for token in pointer.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, Mapping):
            if token not in current:
                _fail(path, "JSON Pointer does not resolve")
            current = current[token]
        elif type(current) is list:
            if not token.isdigit() or str(int(token)) != token or int(token) >= len(current):
                _fail(path, "JSON Pointer array index does not resolve canonically")
            current = current[int(token)]
        else:
            _fail(path, "JSON Pointer does not resolve")


def _candidate_content_projection(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Return the explicit I2A candidate identity projection."""
    item = _mapping(candidate, "candidate")
    if set(item) != set(_CANDIDATE_FIELDS):
        _fail("candidate", "must contain the exact persisted candidate fields")
    return {field: copy.deepcopy(item[field]) for field in _CANDIDATE_FIELDS[:-1]}


def candidate_content_sha256(candidate: Mapping[str, Any]) -> str:
    """Hash every persisted candidate field except its self hash."""
    return canonical_sha256(_candidate_content_projection(candidate))


def _engineering_problem_content_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return the explicit I2A EPR identity projection."""
    item = _mapping(value, "engineering_problem")
    if set(item) != set(_TOP_LEVEL_FIELDS):
        _fail("engineering_problem", "must contain the exact persisted top-level fields")
    return {field: copy.deepcopy(item[field]) for field in _TOP_LEVEL_FIELDS[:-1]}


def engineering_problem_content_sha256(value: Mapping[str, Any]) -> str:
    """Hash every authoritative EPR field except its self hash."""
    return canonical_sha256(_engineering_problem_content_projection(value))


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_thaw(item) for item in value]
    return value


def _validate_epr(value: Mapping[str, Any]) -> None:
    item = _closed(value, _TOP_LEVEL_FIELDS, "engineering_problem")
    if item["problem_format_version"] != PROBLEM_FORMAT_VERSION:
        _fail("/problem_format_version", f"must equal {PROBLEM_FORMAT_VERSION!r}")
    _identifier(item["problem_id"], "problem_id", "/problem_id")
    _identifier(item["case_id"], "case_id", "/case_id")
    _non_empty(item["title"], "/title")
    _non_empty(item["purpose"], "/purpose")
    sources = _mapping(item["source_case_sha256"], "/source_case_sha256")
    if not sources or "00_problem_intake.yml" not in sources:
        _fail("/source_case_sha256", "must include 00_problem_intake.yml")
    if list(sources) != sorted(sources):
        _fail("/source_case_sha256", "keys must use canonical lexical order")
    for key, digest in sources.items():
        if key not in _ELIGIBLE_SOURCE_FILES:
            _fail(f"/source_case_sha256/{key}", "is not an eligible canonical numbered filename")
        _sha(digest, f"/source_case_sha256/{key}")

    requirements = _list(item["requirements"], "/requirements", minimum=1)
    requirement_ids: list[str] = []
    for index, raw in enumerate(requirements):
        requirement_path = f"/requirements/{index}"
        requirement = _closed(raw, ("requirement_id", "description", "target_path", "provenance"), requirement_path, ("target",))
        requirement_ids.append(_identifier(requirement["requirement_id"], "requirement_id", f"{requirement_path}/requirement_id"))
        _non_empty(requirement["description"], f"{requirement_path}/description")
        _pointer(requirement["target_path"], f"{requirement_path}/target_path")
        if "target" in requirement:
            target = _mapping(requirement["target"], f"{requirement_path}/target")
            try:
                target_kind = QuantityKind(target.get("quantity_kind"))
            except (TypeError, ValueError):
                _fail(f"{requirement_path}/target/quantity_kind", "has invalid quantity kind")
            _validate_envelope(target, target_kind, f"{requirement_path}/target")
        _validate_provenance(requirement["provenance"], f"{requirement_path}/provenance")
    _ordered_unique(requirement_ids, "/requirements")

    layer_ids, layer_order = _validate_geometry(item["geometry"], "/geometry")
    material_ids = _validate_materials(item["materials"], "/materials")
    if not {layer["material_id"] for layer in item["geometry"]["layers"]}.issubset(set(material_ids)):
        _fail("/geometry/layers", "all material references must resolve")
    _validate_interfaces(item["interfaces"], layer_order, "/interfaces")
    _validate_boundary(item["boundary_conditions"], "/boundary_conditions")
    _validate_heat_sources(item["heat_sources"], set(layer_ids), "/heat_sources")

    constraints = _list(item["constraints"], "/constraints")
    constraint_ids: list[str] = []
    for index, raw in enumerate(constraints):
        constraint_path = f"/constraints/{index}"
        constraint = _closed(raw, ("constraint_id", "target_path", "operator", "threshold", "severity", "provenance", "evaluation_disposition"), constraint_path)
        constraint_ids.append(_identifier(constraint["constraint_id"], "constraint_id", f"{constraint_path}/constraint_id"))
        _pointer(constraint["target_path"], f"{constraint_path}/target_path")
        operator = _enum(constraint["operator"], {"lt", "le", "eq", "ge", "gt", "in", "not_in", "review_only"}, f"{constraint_path}/operator")
        if operator == "review_only" and constraint["threshold"] is not None:
            _fail(f"{constraint_path}/threshold", "review_only requires a null threshold")
        if operator != "review_only" and constraint["threshold"] is None:
            _fail(f"{constraint_path}/threshold", "quantitative operators require a threshold")
        if constraint["threshold"] is not None:
            threshold = _mapping(constraint["threshold"], f"{constraint_path}/threshold")
            try:
                threshold_kind = QuantityKind(threshold.get("quantity_kind"))
            except (TypeError, ValueError):
                _fail(f"{constraint_path}/threshold/quantity_kind", "has invalid quantity kind")
            _validate_envelope(threshold, threshold_kind, f"{constraint_path}/threshold")
        _enum(constraint["severity"], {"blocking", "warning", "advisory"}, f"{constraint_path}/severity")
        _validate_provenance(constraint["provenance"], f"{constraint_path}/provenance")
        _enum(constraint["evaluation_disposition"], {"machine_evaluable", "review_required", "not_evaluable_in_epr"}, f"{constraint_path}/evaluation_disposition")
    _ordered_unique(constraint_ids, "/constraints")

    candidates = _list(item["candidates"], "/candidates", minimum=2)
    candidate_ids: list[str] = []
    roles: list[str] = []
    for index, raw in enumerate(candidates):
        candidate_path = f"/candidates/{index}"
        candidate = _closed(raw, _CANDIDATE_FIELDS, candidate_path)
        candidate_ids.append(_identifier(candidate["candidate_id"], "candidate_id", f"{candidate_path}/candidate_id"))
        roles.append(_enum(candidate["candidate_role"], {"baseline", "variant"}, f"{candidate_path}/candidate_role"))
        _non_empty(candidate["label"], f"{candidate_path}/label")
        parent = _identifier(
            candidate["parent_requirement_id"],
            "requirement_id",
            f"{candidate_path}/parent_requirement_id",
        )
        if parent not in requirement_ids:
            _fail(f"{candidate_path}/parent_requirement_id", "must reference an existing requirement")
        _validate_complete_problem_view(candidate["geometry"], candidate["materials"], candidate["interfaces"], candidate["boundary_conditions"], candidate_path)
        for field in ("changed_field_paths", "assumption_paths", "evidence_required_paths"):
            pointers = _list(candidate[field], f"{candidate_path}/{field}")
            for pointer_index, pointer in enumerate(pointers):
                _pointer(pointer, f"{candidate_path}/{field}/{pointer_index}")
                if field == "changed_field_paths" and pointer.split("/", 2)[1] not in {
                    "geometry", "materials", "interfaces", "boundary_conditions",
                }:
                    _fail(
                        f"{candidate_path}/{field}/{pointer_index}",
                        "changed paths must address a persisted baseline-authority root",
                    )
                _resolve_pointer(candidate, pointer, f"{candidate_path}/{field}/{pointer_index}")
            _ordered_unique(pointers, f"{candidate_path}/{field}")
        applicable = _list(candidate["applicable_constraint_ids"], f"{candidate_path}/applicable_constraint_ids")
        for applicable_index, constraint_id in enumerate(applicable):
            if _identifier(constraint_id, "constraint_id", f"{candidate_path}/applicable_constraint_ids/{applicable_index}") not in constraint_ids:
                _fail(f"{candidate_path}/applicable_constraint_ids/{applicable_index}", "must reference an existing constraint")
        _ordered_unique(applicable, f"{candidate_path}/applicable_constraint_ids")
        supplied_candidate_hash = _sha(candidate["resolved_content_sha256"], f"{candidate_path}/resolved_content_sha256")
        if supplied_candidate_hash != candidate_content_sha256(candidate):
            _fail(f"{candidate_path}/resolved_content_sha256", "does not match candidate content")
    if len(candidate_ids) != len(set(candidate_ids)):
        _fail("/candidates", "candidate IDs must be unique")
    if roles.count("baseline") != 1 or roles.count("variant") < 1:
        _fail("/candidates", "requires exactly one baseline and at least one variant")
    if roles[0] != "baseline" or roles[1:] != ["variant"] * (len(roles) - 1):
        _fail("/candidates", "baseline must be first")
    if candidate_ids[1:] != sorted(candidate_ids[1:]):
        _fail("/candidates", "variants must use candidate ID canonical order")
    baseline = candidates[0]
    for field in ("geometry", "materials", "interfaces", "boundary_conditions"):
        if canonical_json_bytes(baseline[field]) != canonical_json_bytes(item[field]):
            _fail(f"/candidates/0/{field}", "baseline candidate must mirror top-level baseline")
    if baseline["changed_field_paths"] != []:
        _fail("/candidates/0/changed_field_paths", "baseline changed paths must be empty")

    unknowns = _list(item["unknowns"], "/unknowns")
    unknown_keys: list[tuple[str, str, str]] = []
    unknown_ids: set[str] = set()
    for index, raw in enumerate(unknowns):
        unknown_path = f"/unknowns/{index}"
        unknown = _closed(raw, ("unknown_id", "field_path", "state", "reason", "consequence", "readiness_impact", "next_evidence_action"), unknown_path)
        unknown_id = _identifier(unknown["unknown_id"], "unknown_id", f"{unknown_path}/unknown_id")
        if unknown_id in unknown_ids:
            _fail("/unknowns", "unknown IDs must be unique")
        unknown_ids.add(unknown_id)
        field_path = _pointer(unknown["field_path"], f"{unknown_path}/field_path")
        state = _enum(unknown["state"], {"missing", "assumed", "conflicting", "evidence_required"}, f"{unknown_path}/state")
        _non_empty(unknown["reason"], f"{unknown_path}/reason")
        _non_empty(unknown["consequence"], f"{unknown_path}/consequence")
        _enum(unknown["readiness_impact"], {"blocking", "requires_later_acknowledgement", "non_blocking"}, f"{unknown_path}/readiness_impact")
        _non_empty(unknown["next_evidence_action"], f"{unknown_path}/next_evidence_action")
        unknown_keys.append((field_path, state, unknown_id))
    if unknown_keys != sorted(unknown_keys):
        _fail("/unknowns", "must use field-path/state/ID canonical order")

    compilation = _closed(item["compilation"], ("compiler_policy_version", "unit_registry_version", "canonical_json_version", "heat_source_consistency_policy_version", "outcome", "blocking_findings", "non_blocking_findings", "warnings", "assumptions_present", "assumptions_requiring_later_acknowledgement"), "/compilation")
    expected_versions = {
        "compiler_policy_version": COMPILER_POLICY_VERSION,
        "unit_registry_version": UNIT_REGISTRY_VERSION,
        "canonical_json_version": CANONICAL_JSON_VERSION,
        "heat_source_consistency_policy_version": HEAT_SOURCE_CONSISTENCY_POLICY_VERSION,
    }
    for field, expected in expected_versions.items():
        if compilation[field] != expected:
            _fail(f"/compilation/{field}", f"must equal {expected!r}")
    _enum(compilation["outcome"], {"FAIL", "HOLD_FOR_INPUT", "READY_WITH_ASSUMPTIONS", "READY"}, "/compilation/outcome")
    for field in ("blocking_findings", "non_blocking_findings", "warnings"):
        _validate_findings(compilation[field], f"/compilation/{field}")
        for finding_index, finding in enumerate(compilation[field]):
            for pointer_index, pointer in enumerate(finding["field_paths"]):
                _resolve_pointer(
                    item,
                    pointer,
                    f"/compilation/{field}/{finding_index}/field_paths/{pointer_index}",
                )
    for field in ("assumptions_present", "assumptions_requiring_later_acknowledgement"):
        pointers = _list(compilation[field], f"/compilation/{field}")
        for pointer_index, pointer in enumerate(pointers):
            _pointer(pointer, f"/compilation/{field}/{pointer_index}")
            _resolve_pointer(item, pointer, f"/compilation/{field}/{pointer_index}")
        _ordered_unique(pointers, f"/compilation/{field}")
    if not set(compilation["assumptions_requiring_later_acknowledgement"]).issubset(
        set(compilation["assumptions_present"])
    ):
        _fail(
            "/compilation/assumptions_requiring_later_acknowledgement",
            "must be a subset of assumptions_present",
        )
    _enum(item["confidentiality_level"], {"public", "internal", "customer-confidential", "restricted"}, "/confidentiality_level")

    # Resolve only pointers whose target is owned by the persisted representation.
    for index, requirement in enumerate(requirements):
        _resolve_pointer(item, requirement["target_path"], f"/requirements/{index}/target_path")
    for index, constraint in enumerate(constraints):
        _resolve_pointer(item, constraint["target_path"], f"/constraints/{index}/target_path")
    for index, unknown in enumerate(unknowns):
        _resolve_pointer(item, unknown["field_path"], f"/unknowns/{index}/field_path")

    supplied_hash = _sha(item["compiled_content_sha256"], "/compiled_content_sha256")
    if supplied_hash != engineering_problem_content_sha256(item):
        _fail("/compiled_content_sha256", "does not match authoritative EPR content")


@dataclass(frozen=True)
class EngineeringProblem:
    """Deeply immutable, validated reconstruction of one persisted EPR mapping."""

    _content: Mapping[str, Any]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EngineeringProblem":
        if not isinstance(value, Mapping):
            _fail("engineering_problem", "must be an object")
        detached = copy.deepcopy(dict(value))
        _validate_epr(detached)
        return cls(_freeze(detached))

    @property
    def problem_id(self) -> str:
        return self._content["problem_id"]

    @property
    def content_sha256(self) -> str:
        return self._content["compiled_content_sha256"]

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._content)

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self._content)
