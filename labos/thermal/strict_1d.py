"""Strict steady-state constant-area 1D thermal kernel for M16A-I4A."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import (
    Context,
    Decimal,
    DivisionByZero,
    Inexact,
    InvalidOperation,
    Overflow,
    ROUND_HALF_EVEN,
    Rounded,
    localcontext,
)
from types import MappingProxyType
from typing import Any

from labos.engineering import (
    CANONICAL_JSON_VERSION,
    EngineeringProblem,
    EvaluationPlan,
    MODEL_MANIFEST_FORMAT_VERSION,
    ModelManifest,
    QuantifiedValue,
    QuantityKind,
    canonical_decimal_text,
    canonical_json_bytes,
)


MODEL_ID = "m16a-strict-1d-thermal"
MODEL_VERSION = "1.0.0"
EQUATION_SET_VERSION = "m16a-strict-1d-equations-1.0"
IMPLEMENTATION_VERSION = "m16a-strict-1d-runtime-1.0"
APPLICABILITY_POLICY_VERSION = "m16a-strict-1d-applicability-1.0"
NUMERICAL_POLICY_VERSION = "m16a-strict-1d-decimal-1.0"
INPUT_BINDING_POLICY_VERSION = "m16a-strict-1d-input-binding-1.0"
RESULT_PAYLOAD_SCHEMA_ID = "m16a-strict-1d-result"
RESULT_PAYLOAD_SCHEMA_VERSION = "1.0"
SCENARIO_POLICY_VERSION = "m16a-strict-1d-scenario-aggregation-1.0"
CONSTRAINT_POLICY_VERSION = "m16a-strict-1d-constraints-1.0"
RANKING_POLICY_VERSION = "m16a-strict-1d-ranking-1.0"
OAT_POLICY_VERSION = "m16a-strict-1d-oat-1.0"

APPLICABILITY_RULE_IDS = (
    "I4-APP-CONSTANT-AREA",
    "I4-APP-CONSTANT-PROPERTIES",
    "I4-APP-CONVECTION-COMMON-AREA",
    "I4-APP-EXPLICIT-SOURCE-PLANE",
    "I4-APP-FULL-POWER-PATH",
    "I4-APP-INTERFACE-COMMON-AREA",
    "I4-APP-NO-COUPLED-PHYSICS",
    "I4-APP-NO-DISTRIBUTED-GENERATION",
    "I4-APP-NO-LATERAL-MISMATCH",
    "I4-APP-NO-TEMPERATURE-LAW",
    "I4-APP-NORMAL-CONDUCTIVITY",
    "I4-APP-SINGLE-HEAT-SOURCE",
    "I4-APP-SINGLE-SERIES-PATH",
    "I4-APP-STEADY-STATE",
    "I4-APP-SUPPORTED-BOUNDARY",
    "I4-APP-SUPPORTED-INTERFACE",
    "I4-APP-UNIFORM-SURFACE-SOURCE",
)

REQUIRED_INPUT_FEATURES = (
    "candidate.boundary.downstream.supported",
    "candidate.boundary.source_side.full_power_single_path",
    "candidate.geometry.constant_area_ordered_stack",
    "candidate.interfaces.same_area_tbr",
    "candidate.materials.explicit_normal_constant_conductivity",
    "global.constraints.explicit_applicable_set",
    "global.heat_source.single_uniform_steady_surface_source",
    "global.model_options.strict_1d_validity_assertions",
    "global.objective.explicit_metric_direction_reference",
)

PROHIBITED_INPUT_FEATURES = (
    "candidate.boundary.hidden_area_or_fin_correction",
    "candidate.geometry.lateral_spreading_or_constriction",
    "candidate.interfaces.unsupported_representation",
    "candidate.materials.rotated_tensor_or_temperature_law",
    "global.heat_source.distributed_or_multiple",
    "global.physics.coupled",
    "global.physics.fluid_or_radiation",
    "global.physics.parallel_path_or_power_split",
    "global.physics.transient",
)

ACCEPTED_QUANTITY_KINDS = (
    "absolute_temperature",
    "absolute_thermal_resistance",
    "area",
    "area_thermal_conductance",
    "area_thermal_resistance",
    "length",
    "physical_dimensionless",
    "power",
    "temperature_difference",
    "thermal_conductivity",
)

CANONICAL_UNITS = {
    "absolute_temperature": "K",
    "absolute_thermal_resistance": "K/W",
    "area": "m^2",
    "area_thermal_conductance": "W/(m^2*K)",
    "area_thermal_resistance": "m^2*K/W",
    "length": "m",
    "physical_dimensionless": "1",
    "power": "W",
    "temperature_difference": "K",
    "thermal_conductivity": "W/(m*K)",
}

KNOWN_LIMITATIONS = (
    "Black-box absolute boundary resistance is consumed without a claim about its internal physics.",
    "Calculation is not validation, approval, recommendation, or a canonical engineering decision.",
    "The model cannot quantify coupled physics, fluid flow, lateral spreading or constriction, phase change, radiation, spatially varying sink temperature, or transient response.",
    "The model requires one steady-state source, one full-power series path, one constant area, and constant layer properties.",
)

SOURCE_REFERENCES = (
    "docs/M16A_ENGINEERING_PROBLEM_COMPILER.md#6.2",
    "internal-normative-reference:steady-state-fourier-conduction-and-series-energy-balance",
)

_ASSERTION_KEYS = (
    "constant_layer_properties_over_evaluated_range",
    "no_coupled_physics",
    "no_fluid_or_radiation_model",
    "no_temperature_dependent_material_law",
    "no_unrepresented_parallel_paths_or_power_splits",
)
_CANDIDATE_ROOTS = {"geometry", "materials", "interfaces", "boundary_conditions"}
_GIT_COMMIT = re.compile(r"^[0-9a-f]{40}$")


class Strict1DValidationError(ValueError):
    """Raised for structural misuse of the strict-1D public API."""


class _ScenarioEnvelope(dict[str, Any]):
    """Detached envelope whose effective number is scenario-local only."""

    def __init__(self, source: Mapping[str, Any], quantity: QuantifiedValue) -> None:
        super().__init__(copy.deepcopy(dict(source)))
        self.scenario_quantity = quantity


def _fail(path: str, message: str) -> None:
    raise Strict1DValidationError(f"{path}: {message}")


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


def _decode_pointer(pointer: str) -> tuple[str, ...]:
    if type(pointer) is not str or not pointer.startswith("/"):
        _fail("field_path", "must be a non-empty RFC 6901 pointer")
    tokens: list[str] = []
    for raw in pointer.split("/")[1:]:
        index = 0
        while index < len(raw):
            if raw[index] == "~" and (index + 1 >= len(raw) or raw[index + 1] not in "01"):
                _fail("field_path", "contains invalid RFC 6901 escaping")
            index += 2 if raw[index] == "~" else 1
        tokens.append(raw.replace("~1", "/").replace("~0", "~"))
    return tuple(tokens)


def _resolve_pointer(document: Any, pointer: str) -> Any:
    current = document
    for token in _decode_pointer(pointer):
        if isinstance(current, Mapping):
            if token not in current:
                _fail(pointer, "does not resolve")
            current = current[token]
        elif type(current) is list:
            if not token.isdigit() or str(int(token)) != token or int(token) >= len(current):
                _fail(pointer, "does not resolve to a canonical array index")
            current = current[int(token)]
        else:
            _fail(pointer, "does not resolve")
    return current


def _ack_key(item: Mapping[str, Any]) -> tuple[int, str, str]:
    return (0 if item["scope"] == "global" else 1, item["candidate_id"] or "", item["field_path"])


def _path_key(item: Mapping[str, Any]) -> tuple[int, str, str]:
    return _ack_key(item)


def _consumed(scope: str, candidate_id: str | None, field_path: str) -> dict[str, Any]:
    return {"scope": scope, "candidate_id": candidate_id, "field_path": field_path}


def _diagnostic(
    rule_id: str,
    classification: str,
    field_paths: Sequence[str],
    message: str,
    required_action: str,
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "classification": classification,
        "field_paths": sorted(set(field_paths)),
        "message": message,
        "required_action": required_action,
    }


def _diagnostic_key(item: Mapping[str, Any]) -> tuple[str, tuple[str, ...], str, bytes]:
    return (
        item["rule_id"],
        tuple(item["field_paths"]),
        item["message"],
        canonical_json_bytes(item),
    )


def _deduplicate_diagnostics(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    unique = {canonical_json_bytes(item): copy.deepcopy(dict(item)) for item in items}
    return sorted(unique.values(), key=_diagnostic_key)


def _quantity_from_envelope(envelope: Mapping[str, Any], path: str) -> QuantifiedValue | None:
    if isinstance(envelope, _ScenarioEnvelope):
        return envelope.scenario_quantity
    if envelope.get("value") is None or envelope.get("conversion") is None:
        return None
    try:
        return QuantifiedValue.from_dict(
            {
                "quantity_kind": envelope["quantity_kind"],
                "canonical_value": envelope["value"],
                "canonical_unit": envelope["unit"],
                "conversion": envelope["conversion"],
            }
        )
    except (KeyError, TypeError, ValueError) as exc:
        _fail(path, f"does not reconstruct through frozen I1 quantity authority: {exc}")


def _decimal_from_envelope(envelope: Mapping[str, Any], path: str) -> Decimal | None:
    quantity = _quantity_from_envelope(envelope, path)
    return None if quantity is None else quantity.canonical_value


def _result_quantity(value: Decimal, kind: QuantityKind, unit: str) -> dict[str, str]:
    return {
        "value": canonical_decimal_text(value),
        "unit": unit,
        "quantity_kind": kind.value,
    }


def _scenario_envelope(
    envelope: Mapping[str, Any], quantity: QuantifiedValue
) -> Mapping[str, Any]:
    """Return a detached numeric view while preserving every source-envelope field."""
    return _ScenarioEnvelope(envelope, quantity)


def _scenario_envelope_value(envelope: Mapping[str, Any]) -> Any:
    """Keep source status while exposing a scenario-local numeric value to binding."""
    if isinstance(envelope, _ScenarioEnvelope):
        return canonical_decimal_text(envelope.scenario_quantity.canonical_value)
    return envelope.get("value")


def _machine_constraint_threshold(constraint: Mapping[str, Any]) -> bool:
    """Determine whether the exact source-temperature threshold is numerically usable."""
    threshold = constraint.get("threshold")
    if not (
        constraint["evaluation_disposition"] == "machine_evaluable"
        and constraint["target_path"] == "/heat_sources/0/source_location"
        and constraint["operator"] in {"lt", "le", "eq", "ge", "gt"}
        and isinstance(threshold, Mapping)
        and threshold.get("quantity_kind") == QuantityKind.ABSOLUTE_TEMPERATURE.value
        and threshold.get("status") in {"provided", "assumed", "evidence_required"}
        and threshold.get("value") is not None
        and threshold.get("conversion") is not None
    ):
        return False
    quantity = _quantity_from_envelope(threshold, "/constraints/threshold")
    return quantity is not None and quantity.canonical_value >= 0


def build_strict_1d_model_manifest(
    implementation_git_commit: str | None = None,
) -> ModelManifest:
    """Build the exact frozen strict-1D Model Manifest snapshot."""
    if implementation_git_commit is not None and (
        type(implementation_git_commit) is not str
        or _GIT_COMMIT.fullmatch(implementation_git_commit) is None
    ):
        _fail("implementation_git_commit", "must be null or a full lowercase 40-hex Git commit")
    return ModelManifest.from_dict(
        {
            "model_manifest_format_version": MODEL_MANIFEST_FORMAT_VERSION,
            "model_id": MODEL_ID,
            "model_version": MODEL_VERSION,
            "equation_set_version": EQUATION_SET_VERSION,
            "implementation_version": IMPLEMENTATION_VERSION,
            "applicability_policy_version": APPLICABILITY_POLICY_VERSION,
            "applicability_rule_ids": list(APPLICABILITY_RULE_IDS),
            "numerical_policy_version": NUMERICAL_POLICY_VERSION,
            "input_binding_policy_version": INPUT_BINDING_POLICY_VERSION,
            "serialization_policy_version": CANONICAL_JSON_VERSION,
            "result_payload_schema_id": RESULT_PAYLOAD_SCHEMA_ID,
            "result_payload_schema_version": RESULT_PAYLOAD_SCHEMA_VERSION,
            "required_input_features": list(REQUIRED_INPUT_FEATURES),
            "prohibited_input_features": list(PROHIBITED_INPUT_FEATURES),
            "accepted_quantity_kinds": list(ACCEPTED_QUANTITY_KINDS),
            "canonical_units": dict(CANONICAL_UNITS),
            "known_limitations": list(KNOWN_LIMITATIONS),
            "source_references": list(SOURCE_REFERENCES),
            "implementation_git_commit": implementation_git_commit,
        }
    )


def _validate_model_request(plan: Mapping[str, Any]) -> None:
    request = plan["model_request"]
    if (request["model_id"], request["model_version"]) != (MODEL_ID, MODEL_VERSION):
        _fail("/model_request", f"must request {MODEL_ID!r} version {MODEL_VERSION!r}")


def _validate_model_options(options: Any) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    expected_top = {"strict_1d_validity_assertions"}
    if not isinstance(options, Mapping) or set(options) != expected_top:
        findings.append(
            _diagnostic(
                "I4-BIND-MISSING-INPUT",
                "MODEL_INPUT_BINDING",
                ["/model_options"],
                "The strict-1D model options do not have the exact required closed shape.",
                "Supply exactly the five required strict-1D validity assertions.",
            )
        )
        return findings
    assertions = options["strict_1d_validity_assertions"]
    if not isinstance(assertions, Mapping) or set(assertions) != set(_ASSERTION_KEYS):
        findings.append(
            _diagnostic(
                "I4-BIND-MISSING-INPUT",
                "MODEL_INPUT_BINDING",
                ["/model_options/strict_1d_validity_assertions"],
                "The strict-1D validity assertion set is incomplete or contains an unknown key.",
                "Supply every required assertion and no additional assertion.",
            )
        )
        return findings
    invalid = [key for key in _ASSERTION_KEYS if assertions[key] is not True]
    if invalid:
        findings.append(
            _diagnostic(
                "I4-BIND-MISSING-INPUT",
                "MODEL_INPUT_BINDING",
                [f"/model_options/strict_1d_validity_assertions/{key}" for key in invalid],
                "Every strict-1D validity assertion must be the literal JSON boolean true.",
                "Correct the model-scope declarations before evaluation.",
            )
        )
    return findings


def _selected_properties(
    candidate: Mapping[str, Any], layer: Mapping[str, Any]
) -> list[tuple[int, Mapping[str, Any]]]:
    material_index = next(
        index
        for index, material in enumerate(candidate["materials"])
        if material["material_id"] == layer["material_id"]
    )
    material = candidate["materials"][material_index]
    representation = material["anisotropy_representation"]
    if representation == "isotropic":
        selected = [
            (index, prop)
            for index, prop in enumerate(material["thermal_properties"])
            if prop["component"] == "isotropic"
        ]
    elif representation == "principal_components":
        axis = layer["orientation"]["stack_normal_axis"]
        selected = [
            (index, prop)
            for index, prop in enumerate(material["thermal_properties"])
            if prop["component"] == axis
        ]
    else:
        selected = []
    return [(material_index, {"index": index, **prop}) for index, prop in selected]


def _candidate_consumed_paths(
    problem: Mapping[str, Any],
    candidate: Mapping[str, Any],
    plan: Mapping[str, Any],
    *,
    include_machine_constraint_thresholds: bool = False,
) -> tuple[list[dict[str, Any]], set[str], set[str]]:
    candidate_id = candidate["candidate_id"]
    paths: list[dict[str, Any]] = []
    numeric_candidate: set[str] = set()
    numeric_global: set[str] = set()

    def global_path(path: str, *, numeric: bool = False) -> None:
        paths.append(_consumed("global", None, path))
        if numeric:
            numeric_global.add(path)

    def candidate_path(path: str, *, numeric: bool = False) -> None:
        paths.append(_consumed("candidate", candidate_id, path))
        if numeric:
            numeric_candidate.add(path)

    global_path("/heat_sources")
    if problem["heat_sources"]:
        source = problem["heat_sources"][0]
        for path in (
            "/heat_sources/0/source_location/layer_id",
            "/heat_sources/0/source_location/location_type",
            "/heat_sources/0/total_power",
            "/heat_sources/0/heated_area",
        ):
            global_path(path, numeric=path.endswith(("total_power", "heated_area")))
        for index in range(len(source["footprint"]["dimensions"])):
            global_path(f"/heat_sources/0/footprint/dimensions/{index}", numeric=True)
        global_path("/heat_sources/0/spatial_profile")
        global_path("/heat_sources/0/operating_mode")

    objective = plan["objective"]
    if objective["reference_requirement_id"] is not None:
        for index, requirement in enumerate(problem["requirements"]):
            if requirement["requirement_id"] == objective["reference_requirement_id"]:
                global_path(f"/requirements/{index}/target", numeric=True)
                global_path(f"/requirements/{index}/target_path")
                break

    applicable_constraints = set(candidate["applicable_constraint_ids"])
    for index, constraint in enumerate(problem["constraints"]):
        if constraint["constraint_id"] in applicable_constraints:
            global_path(f"/constraints/{index}")
            if include_machine_constraint_thresholds and _machine_constraint_threshold(constraint):
                global_path(f"/constraints/{index}/threshold", numeric=True)

    candidate_path("/geometry/layers")
    candidate_path("/materials")
    candidate_path("/interfaces")
    for layer_index, layer in enumerate(candidate["geometry"]["layers"]):
        base = f"/geometry/layers/{layer_index}"
        for field in ("layer_id", "order", "material_id"):
            candidate_path(f"{base}/{field}")
        candidate_path(f"{base}/thickness", numeric=True)
        for dimension_index in range(len(layer["footprint_dimensions"])):
            candidate_path(f"{base}/footprint_dimensions/{dimension_index}", numeric=True)
        candidate_path(f"{base}/footprint_area", numeric=True)
        candidate_path(f"{base}/orientation/stack_normal_axis")
        candidate_path(f"{base}/orientation/rotation_description")

        material_index = next(
            index
            for index, material in enumerate(candidate["materials"])
            if material["material_id"] == layer["material_id"]
        )
        material = candidate["materials"][material_index]
        material_base = f"/materials/{material_index}"
        candidate_path(f"{material_base}/material_id")
        candidate_path(f"{material_base}/anisotropy_representation")
        for _, selected in _selected_properties(candidate, layer):
            property_index = selected["index"]
            property_base = f"{material_base}/thermal_properties/{property_index}"
            for field in ("property_id", "component"):
                candidate_path(f"{property_base}/{field}")
            candidate_path(f"{property_base}/thermal_conductivity", numeric=True)
            candidate_path(f"{property_base}/temperature_basis")
            candidate_path(f"{property_base}/condition_basis")

    for interface_index, _interface in enumerate(candidate["interfaces"]):
        base = f"/interfaces/{interface_index}"
        for field in (
            "interface_id",
            "upstream_layer_id",
            "downstream_layer_id",
            "representation_type",
        ):
            candidate_path(f"{base}/{field}")
        candidate_path(f"{base}/value", numeric=True)
        candidate_path(f"{base}/effective_area", numeric=True)
        candidate_path(f"{base}/condition_basis")

    candidate_path("/boundary_conditions/source_side/heat_flow_fraction", numeric=True)
    candidate_path("/boundary_conditions/source_side/path_disposition")
    downstream = candidate["boundary_conditions"]["downstream"]
    candidate_path("/boundary_conditions/downstream/representation_type")
    selected_fields = {
        "fixed_temperature": ("terminal_plane", "reference_temperature"),
        "absolute_resistance": ("resistance", "reference_temperature", "operating_basis"),
        "direct_convection": (
            "heat_transfer_coefficient",
            "boundary_area",
            "ambient_temperature",
            "operating_basis",
        ),
        "other": ("description",),
    }[downstream["representation_type"]]
    numeric_fields = {
        "reference_temperature",
        "resistance",
        "heat_transfer_coefficient",
        "boundary_area",
        "ambient_temperature",
    }
    for field in selected_fields:
        candidate_path(
            f"/boundary_conditions/downstream/{field}",
            numeric=field in numeric_fields,
        )

    unique = {canonical_json_bytes(item): item for item in paths}
    ordered = sorted(unique.values(), key=_path_key)
    return ordered, numeric_candidate, numeric_global


def _validate_structural_acknowledgements(
    problem: Mapping[str, Any], plan: Mapping[str, Any], candidates: Mapping[str, Mapping[str, Any]]
) -> None:
    selected = set(plan["selected_candidate_ids"])
    for index, acknowledgement in enumerate(plan["assumption_acknowledgements"]):
        scope = acknowledgement["scope"]
        candidate_id = acknowledgement["candidate_id"]
        pointer = acknowledgement["field_path"]
        tokens = _decode_pointer(pointer)
        root = tokens[0] if tokens else ""
        if scope == "candidate":
            if candidate_id not in selected:
                _fail(f"/assumption_acknowledgements/{index}/candidate_id", "must reference a selected candidate")
            if root not in _CANDIDATE_ROOTS:
                _fail(f"/assumption_acknowledgements/{index}/field_path", "uses the wrong authority scope")
            target = _resolve_pointer(candidates[candidate_id], pointer)
            if pointer not in candidates[candidate_id]["assumption_paths"]:
                _fail(f"/assumption_acknowledgements/{index}/field_path", "is not the candidate's exact assumption path")
        else:
            if candidate_id is not None or root in _CANDIDATE_ROOTS:
                _fail(f"/assumption_acknowledgements/{index}", "global acknowledgement uses the wrong authority scope")
            target = _resolve_pointer(problem, pointer)
        if not isinstance(target, Mapping) or target.get("status") != "assumed":
            _fail(f"/assumption_acknowledgements/{index}/field_path", "must resolve to an assumed quantity envelope")


@dataclass(frozen=True, slots=True)
class _CandidateBinding:
    candidate: Mapping[str, Any]
    consumed_input_paths: tuple[Mapping[str, Any], ...]
    numeric_candidate_paths: frozenset[str]
    numeric_global_paths: frozenset[str]
    required_acknowledgements: tuple[Mapping[str, Any], ...]
    binding_findings: tuple[Mapping[str, Any], ...]
    evidence_warnings: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True, slots=True)
class Strict1DBoundEvaluation:
    """Immutable strict-1D input binding completed before thermal arithmetic."""

    _problem: EngineeringProblem
    _plan: EvaluationPlan
    _candidate_bindings: Mapping[str, _CandidateBinding]
    _global_binding_findings: tuple[Mapping[str, Any], ...]

    @property
    def engineering_problem(self) -> EngineeringProblem:
        return self._problem

    @property
    def evaluation_plan(self) -> EvaluationPlan:
        return self._plan

    @property
    def selected_candidate_ids(self) -> tuple[str, ...]:
        return tuple(self._plan.to_dict()["selected_candidate_ids"])

    def consumed_input_paths(self, candidate_id: str) -> list[dict[str, Any]]:
        binding = self._candidate_bindings.get(candidate_id)
        if binding is None:
            _fail("candidate_id", "must reference a selected candidate")
        return [_thaw(item) for item in binding.consumed_input_paths]


def _bind_strict_1d_inputs(
    engineering_problem: EngineeringProblem,
    evaluation_plan: EvaluationPlan,
    *,
    allow_parameter_sweeps: bool,
    include_machine_constraint_thresholds: bool,
) -> Strict1DBoundEvaluation:
    """Internal binding mode shared by I4A baseline and I4B orchestration."""
    if not isinstance(engineering_problem, EngineeringProblem):
        raise TypeError("engineering_problem must be an EngineeringProblem")
    if not isinstance(evaluation_plan, EvaluationPlan):
        raise TypeError("evaluation_plan must be an EvaluationPlan")
    problem = engineering_problem.to_dict()
    plan = evaluation_plan.to_dict()
    if problem["compilation"]["outcome"] == "FAIL":
        _fail("/compilation/outcome", "a failed EPR cannot be evaluated")
    if (plan["case_id"], plan["problem_id"], plan["epr_compiled_content_sha256"]) != (
        problem["case_id"],
        problem["problem_id"],
        problem["compiled_content_sha256"],
    ):
        _fail("/evaluation_plan", "does not bind the supplied immutable EPR")
    _validate_model_request(plan)
    if plan["parameter_sweeps"] and not allow_parameter_sweeps:
        _fail("/parameter_sweeps", "I4A accepts only an unswept baseline plan")
    if plan["sensitivity_request"] is not None:
        _fail("/sensitivity_request", "I4A does not execute OAT sensitivity")
    candidates = {candidate["candidate_id"]: candidate for candidate in problem["candidates"]}
    missing = [candidate_id for candidate_id in plan["selected_candidate_ids"] if candidate_id not in candidates]
    if missing:
        _fail("/selected_candidate_ids", f"contains unknown candidate IDs: {missing!r}")
    parents = {candidates[candidate_id]["parent_requirement_id"] for candidate_id in plan["selected_candidate_ids"]}
    if len(parents) != 1:
        _fail("/selected_candidate_ids", "selected candidates must share one parent requirement")
    objective = plan["objective"]
    if objective["metric"] == "temperature_margin":
        requirement = next(
            (
                item
                for item in problem["requirements"]
                if item["requirement_id"] == objective["reference_requirement_id"]
            ),
            None,
        )
        if requirement is None or requirement.get("target") is None:
            _fail("/objective/reference_requirement_id", "must resolve to a quantified EPR requirement")
        target = requirement["target"]
        if target.get("quantity_kind") != QuantityKind.ABSOLUTE_TEMPERATURE.value:
            _fail("/objective/reference_requirement_id", "requirement target must be absolute_temperature")
    _validate_structural_acknowledgements(problem, plan, candidates)

    option_findings = _validate_model_options(plan["model_options"])
    supplied = [copy.deepcopy(item) for item in plan["assumption_acknowledgements"]]
    supplied_candidate = {
        candidate_id: {
            canonical_json_bytes(item): item
            for item in supplied
            if item["scope"] == "candidate" and item["candidate_id"] == candidate_id
        }
        for candidate_id in plan["selected_candidate_ids"]
    }
    supplied_global = {
        canonical_json_bytes(item): item for item in supplied if item["scope"] == "global"
    }
    required_global_union: dict[bytes, dict[str, Any]] = {}
    pending: dict[str, tuple[Any, ...]] = {}

    for candidate_id in plan["selected_candidate_ids"]:
        candidate = candidates[candidate_id]
        consumed_paths, numeric_candidate, numeric_global = _candidate_consumed_paths(
            problem,
            candidate,
            plan,
            include_machine_constraint_thresholds=include_machine_constraint_thresholds,
        )
        required: list[dict[str, Any]] = []
        evidence_warnings: list[dict[str, Any]] = []
        missing_paths: list[str] = []
        for consumed_path in consumed_paths:
            scope = consumed_path["scope"]
            pointer = consumed_path["field_path"]
            is_numeric = (
                pointer in numeric_global if scope == "global" else pointer in numeric_candidate
            )
            if not is_numeric:
                continue
            document = problem if scope == "global" else candidate
            envelope = _resolve_pointer(document, pointer)
            if not isinstance(envelope, Mapping):
                _fail(pointer, "numeric consumed path does not resolve to a quantity envelope")
            status = envelope.get("status")
            if status == "assumed" and _scenario_envelope_value(envelope) is not None:
                acknowledgement = _consumed(scope, None if scope == "global" else candidate_id, pointer)
                required.append(acknowledgement)
                if scope == "global":
                    required_global_union[canonical_json_bytes(acknowledgement)] = acknowledgement
            elif status == "evidence_required" and _scenario_envelope_value(envelope) is not None:
                evidence_warnings.append(
                    _diagnostic(
                        "I4-BIND-EVIDENCE-REQUIRED",
                        "MODEL_INPUT_BINDING",
                        [pointer],
                        "A consumed value is executable but remains evidence-required.",
                        "Obtain applicable evidence before relying on the calculation beyond screening use.",
                    )
                )
            elif status in {"missing", "conflicting"} or _scenario_envelope_value(envelope) is None:
                missing_paths.append(pointer)
        required.sort(key=_ack_key)
        pending[candidate_id] = (
            candidate,
            consumed_paths,
            numeric_candidate,
            numeric_global,
            required,
            evidence_warnings,
            missing_paths,
        )

    extra_global = sorted(
        (item for encoded, item in supplied_global.items() if encoded not in required_global_union),
        key=_ack_key,
    )
    global_findings = list(option_findings)
    if extra_global:
        global_findings.append(
            _diagnostic(
                "I4-BIND-ACKNOWLEDGEMENT-CLOSURE",
                "MODEL_INPUT_BINDING",
                [item["field_path"] for item in extra_global],
                "The supplied global acknowledgement set contains a non-consumed assumption.",
                "Remove every global acknowledgement not required by the selected strict-1D evaluation.",
            )
        )

    bindings: dict[str, _CandidateBinding] = {}
    for candidate_id, state in pending.items():
        (
            candidate,
            consumed_paths,
            numeric_candidate,
            numeric_global,
            required,
            evidence_warnings,
            missing_paths,
        ) = state
        required_candidate = {
            canonical_json_bytes(item): item for item in required if item["scope"] == "candidate"
        }
        required_global = {
            canonical_json_bytes(item): item for item in required if item["scope"] == "global"
        }
        missing_acknowledgements = [
            item
            for encoded, item in {**required_candidate, **required_global}.items()
            if encoded not in supplied_candidate[candidate_id] and encoded not in supplied_global
        ]
        extra_candidate = [
            item
            for encoded, item in supplied_candidate[candidate_id].items()
            if encoded not in required_candidate
        ]
        findings: list[dict[str, Any]] = []
        if missing_paths:
            findings.append(
                _diagnostic(
                    "I4-BIND-MISSING-INPUT",
                    "MODEL_INPUT_BINDING",
                    missing_paths,
                    "A required strict-1D input is missing, conflicting, or null.",
                    "Supply one usable provenance-bearing value for every required input.",
                )
            )
        if missing_acknowledgements or extra_candidate:
            findings.append(
                _diagnostic(
                    "I4-BIND-ACKNOWLEDGEMENT-CLOSURE",
                    "MODEL_INPUT_BINDING",
                    [item["field_path"] for item in missing_acknowledgements + extra_candidate],
                    "The candidate's supplied acknowledgement set does not exactly close the consumed assumed inputs.",
                    "Supply exactly the required candidate/global acknowledgements and no extras.",
                )
            )
        bindings[candidate_id] = _CandidateBinding(
            candidate=_freeze(copy.deepcopy(candidate)),
            consumed_input_paths=tuple(_freeze(item) for item in consumed_paths),
            numeric_candidate_paths=frozenset(numeric_candidate),
            numeric_global_paths=frozenset(numeric_global),
            required_acknowledgements=tuple(_freeze(item) for item in required),
            binding_findings=tuple(_freeze(item) for item in _deduplicate_diagnostics(findings)),
            evidence_warnings=tuple(
                _freeze(item) for item in _deduplicate_diagnostics(evidence_warnings)
            ),
        )
    return Strict1DBoundEvaluation(
        _problem=engineering_problem,
        _plan=evaluation_plan,
        _candidate_bindings=MappingProxyType(bindings),
        _global_binding_findings=tuple(
            _freeze(item) for item in _deduplicate_diagnostics(global_findings)
        ),
    )


def bind_strict_1d_inputs(
    engineering_problem: EngineeringProblem,
    evaluation_plan: EvaluationPlan,
) -> Strict1DBoundEvaluation:
    """Bind exact I4A baseline inputs and acknowledgement closure without arithmetic."""
    return _bind_strict_1d_inputs(
        engineering_problem,
        evaluation_plan,
        allow_parameter_sweeps=False,
        include_machine_constraint_thresholds=False,
    )


def _applicability_findings(
    problem: Mapping[str, Any], candidate: Mapping[str, Any]
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    def add(rule_id: str, paths: Sequence[str], message: str, action: str) -> None:
        findings.append(_diagnostic(rule_id, "MODEL_APPLICABILITY", paths, message, action))

    sources = problem["heat_sources"]
    if len(sources) != 1:
        add(
            "I4-APP-SINGLE-HEAT-SOURCE",
            ["/heat_sources"],
            "Strict 1D requires exactly one heat source.",
            "Select a model that represents multiple sources or provide a reviewed single-source reduction.",
        )
        return _deduplicate_diagnostics(findings)
    source = sources[0]
    if source["operating_mode"] != "steady_state":
        add(
            "I4-APP-STEADY-STATE",
            ["/heat_sources/0/operating_mode"],
            "The heat source is not steady-state.",
            "Use a transient-capable model.",
        )
    if source["spatial_profile"] != "uniform_surface":
        rule = (
            "I4-APP-NO-DISTRIBUTED-GENERATION"
            if source["spatial_profile"] in {"volumetric", "distributed"}
            else "I4-APP-UNIFORM-SURFACE-SOURCE"
        )
        add(
            rule,
            ["/heat_sources/0/spatial_profile"],
            "Strict 1D requires one uniform surface source and no distributed generation.",
            "Use a model that represents the declared source distribution.",
        )
    layers = candidate["geometry"]["layers"]
    first_layer_id = layers[0]["layer_id"]
    if (
        source["source_location"]["location_type"] != "source_side"
        or source["source_location"]["layer_id"] != first_layer_id
    ):
        add(
            "I4-APP-EXPLICIT-SOURCE-PLANE",
            [
                "/heat_sources/0/source_location/layer_id",
                "/heat_sources/0/source_location/location_type",
            ],
            "The source is not injected at the source side of the first ordered layer.",
            "Use an equation set matching the declared injection plane.",
        )

    source_side = candidate["boundary_conditions"]["source_side"]
    if source_side["path_disposition"] != "adiabatic_other_paths":
        add(
            "I4-APP-SINGLE-SERIES-PATH",
            ["/boundary_conditions/source_side/path_disposition"],
            "The candidate does not establish one adiabatic-other-paths series route.",
            "Use a model that represents parallel paths or provide an applicable series candidate.",
        )
    fraction = _decimal_from_envelope(
        source_side["heat_flow_fraction"],
        "/boundary_conditions/source_side/heat_flow_fraction",
    )
    if fraction is not None and fraction != Decimal("1"):
        add(
            "I4-APP-FULL-POWER-PATH",
            ["/boundary_conditions/source_side/heat_flow_fraction"],
            "The modeled path does not carry exactly the full declared source power.",
            "Use a model that represents the declared power split.",
        )

    source_area = _decimal_from_envelope(source["heated_area"], "/heat_sources/0/heated_area")
    source_dimensions = [
        _decimal_from_envelope(item, f"/heat_sources/0/footprint/dimensions/{index}")
        for index, item in enumerate(source["footprint"]["dimensions"])
    ]
    if source_area is not None and source_area > 0:
        for index, layer in enumerate(layers):
            layer_area = _decimal_from_envelope(
                layer["footprint_area"], f"/geometry/layers/{index}/footprint_area"
            )
            if layer_area is not None and layer_area > 0 and layer_area != source_area:
                add(
                    "I4-APP-CONSTANT-AREA",
                    ["/heat_sources/0/heated_area", f"/geometry/layers/{index}/footprint_area"],
                    "The source and layer areas are not one exact common area.",
                    "Use a reviewed spreading/constriction-capable model.",
                )
            dimensions = [
                _decimal_from_envelope(
                    item, f"/geometry/layers/{index}/footprint_dimensions/{dimension_index}"
                )
                for dimension_index, item in enumerate(layer["footprint_dimensions"])
            ]
            dimensions_are_comparable = (
                len(dimensions) == len(source_dimensions)
                and all(value is not None and value > 0 for value in dimensions)
                and all(value is not None and value > 0 for value in source_dimensions)
            )
            if len(dimensions) != len(source_dimensions) or (
                dimensions_are_comparable and dimensions != source_dimensions
            ):
                add(
                    "I4-APP-NO-LATERAL-MISMATCH",
                    [
                        "/heat_sources/0/footprint/dimensions/0",
                        f"/geometry/layers/{index}/footprint_dimensions/0",
                    ],
                    "Equal-area inference is forbidden because footprint dimensions differ.",
                    "Use a model that represents the declared lateral geometry.",
                )

        for index, interface in enumerate(candidate["interfaces"]):
            interface_area = _decimal_from_envelope(
                interface["effective_area"], f"/interfaces/{index}/effective_area"
            )
            if interface_area is not None and interface_area > 0 and interface_area != source_area:
                add(
                    "I4-APP-INTERFACE-COMMON-AREA",
                    ["/heat_sources/0/heated_area", f"/interfaces/{index}/effective_area"],
                    "An interface effective area differs from the common 1D area.",
                    "Use an interface/model contract that represents the declared area transition.",
                )

    for layer_index, layer in enumerate(layers):
        material_index = next(
            index
            for index, material in enumerate(candidate["materials"])
            if material["material_id"] == layer["material_id"]
        )
        material = candidate["materials"][material_index]
        representation = material["anisotropy_representation"]
        selected = _selected_properties(candidate, layer)
        rotation = layer["orientation"]["rotation_description"]
        if representation not in {"isotropic", "principal_components"} or rotation is not None or len(selected) != 1:
            add(
                "I4-APP-NORMAL-CONDUCTIVITY",
                [
                    f"/geometry/layers/{layer_index}/orientation/stack_normal_axis",
                    f"/geometry/layers/{layer_index}/orientation/rotation_description",
                    f"/materials/{material_index}/anisotropy_representation",
                ],
                "The normal conductivity is rotated, off-axis, ambiguous, or unsupported.",
                "Supply one explicit constant conductivity aligned with the stack normal.",
            )
    for index, interface in enumerate(candidate["interfaces"]):
        if interface["representation_type"] not in {"area_normalized_resistance", "ideal_zero"}:
            add(
                "I4-APP-SUPPORTED-INTERFACE",
                [f"/interfaces/{index}/representation_type"],
                "The interface representation is outside strict-1D equation-set version 1.0.",
                "Use area-normalized resistance or explicit ideal zero, or select another equation set.",
            )

    downstream = candidate["boundary_conditions"]["downstream"]
    representation = downstream["representation_type"]
    if representation == "other":
        add(
            "I4-APP-SUPPORTED-BOUNDARY",
            ["/boundary_conditions/downstream/representation_type"],
            "The downstream boundary representation is unsupported.",
            "Supply fixed temperature, absolute resistance, or same-area direct convection.",
        )
    elif representation == "direct_convection" and source_area is not None and source_area > 0:
        boundary_area = _decimal_from_envelope(
            downstream["boundary_area"], "/boundary_conditions/downstream/boundary_area"
        )
        if boundary_area is not None and boundary_area > 0 and boundary_area != source_area:
            add(
                "I4-APP-CONVECTION-COMMON-AREA",
                ["/heat_sources/0/heated_area", "/boundary_conditions/downstream/boundary_area"],
                "Direct convection uses an area different from the common 1D area.",
                "Use a model that represents area enlargement, fins, or downstream fluid geometry.",
            )
    return _deduplicate_diagnostics(findings)


def _numeric_precondition_findings(
    problem: Mapping[str, Any], candidate: Mapping[str, Any]
) -> list[dict[str, Any]]:
    failures: list[str] = []

    def positive(envelope: Mapping[str, Any], path: str) -> None:
        value = _decimal_from_envelope(envelope, path)
        if value is not None and value <= 0:
            failures.append(path)

    def nonnegative(envelope: Mapping[str, Any], path: str) -> None:
        value = _decimal_from_envelope(envelope, path)
        if value is not None and value < 0:
            failures.append(path)

    source = problem["heat_sources"][0] if len(problem["heat_sources"]) == 1 else None
    if source is not None:
        positive(source["total_power"], "/heat_sources/0/total_power")
        positive(source["heated_area"], "/heat_sources/0/heated_area")
        for index, dimension in enumerate(source["footprint"]["dimensions"]):
            positive(dimension, f"/heat_sources/0/footprint/dimensions/{index}")
    for index, layer in enumerate(candidate["geometry"]["layers"]):
        positive(layer["thickness"], f"/geometry/layers/{index}/thickness")
        positive(layer["footprint_area"], f"/geometry/layers/{index}/footprint_area")
        for dimension_index, dimension in enumerate(layer["footprint_dimensions"]):
            positive(dimension, f"/geometry/layers/{index}/footprint_dimensions/{dimension_index}")
        for material_index, prop in _selected_properties(candidate, layer):
            positive(
                prop["thermal_conductivity"],
                f"/materials/{material_index}/thermal_properties/{prop['index']}/thermal_conductivity",
            )
    for index, interface in enumerate(candidate["interfaces"]):
        positive(interface["effective_area"], f"/interfaces/{index}/effective_area")
        if interface["representation_type"] in {"area_normalized_resistance", "ideal_zero"}:
            nonnegative(interface["value"], f"/interfaces/{index}/value")
    fraction = candidate["boundary_conditions"]["source_side"]["heat_flow_fraction"]
    fraction_value = _decimal_from_envelope(
        fraction, "/boundary_conditions/source_side/heat_flow_fraction"
    )
    if fraction_value is not None and fraction_value != Decimal("1"):
        # This is an applicability failure and is not duplicated as a numeric blocker.
        pass
    downstream = candidate["boundary_conditions"]["downstream"]
    representation = downstream["representation_type"]
    if representation == "fixed_temperature":
        nonnegative(
            downstream["reference_temperature"],
            "/boundary_conditions/downstream/reference_temperature",
        )
    elif representation == "absolute_resistance":
        nonnegative(downstream["resistance"], "/boundary_conditions/downstream/resistance")
        nonnegative(
            downstream["reference_temperature"],
            "/boundary_conditions/downstream/reference_temperature",
        )
    elif representation == "direct_convection":
        positive(
            downstream["heat_transfer_coefficient"],
            "/boundary_conditions/downstream/heat_transfer_coefficient",
        )
        positive(downstream["boundary_area"], "/boundary_conditions/downstream/boundary_area")
        nonnegative(
            downstream["ambient_temperature"],
            "/boundary_conditions/downstream/ambient_temperature",
        )
    if not failures:
        return []
    return [
        _diagnostic(
            "I4-NUM-NONPHYSICAL-BASE-INPUT",
            "MODEL_EXECUTION",
            failures,
            "A bound baseline input violates the strict-1D numerical preconditions.",
            "Correct the nonphysical base value before executing this model.",
        )
    ]


def _decimal_context() -> Context:
    context = Context(
        prec=50,
        rounding=ROUND_HALF_EVEN,
        Emin=-999999,
        Emax=999999,
        capitals=1,
        clamp=0,
    )
    context.traps[InvalidOperation] = True
    context.traps[DivisionByZero] = True
    context.traps[Overflow] = True
    context.traps[Inexact] = False
    context.traps[Rounded] = False
    context.clear_flags()
    return context


def _normal_property(
    candidate: Mapping[str, Any], layer: Mapping[str, Any]
) -> tuple[int, Mapping[str, Any]]:
    selected = _selected_properties(candidate, layer)
    if len(selected) != 1:
        _fail("/materials", "applicable candidate must select exactly one normal property")
    material_index, property_with_index = selected[0]
    return material_index, property_with_index


def _compute_numerical_result(
    problem: Mapping[str, Any], candidate: Mapping[str, Any]
) -> dict[str, Any]:
    source = problem["heat_sources"][0]
    common_area = _decimal_from_envelope(source["heated_area"], "/heat_sources/0/heated_area")
    power = _decimal_from_envelope(source["total_power"], "/heat_sources/0/total_power")
    if common_area is None or power is None:
        _fail("/heat_sources/0", "applicable execution requires bound area and power")

    context_template = _decimal_context()
    with localcontext(context_template) as context:
        context.clear_flags()
        layer_records: list[dict[str, Any]] = []
        layer_resistances: list[tuple[str, Decimal]] = []
        for layer_index, layer in enumerate(candidate["geometry"]["layers"]):
            material_index, prop = _normal_property(candidate, layer)
            thickness = _decimal_from_envelope(layer["thickness"], f"/geometry/layers/{layer_index}/thickness")
            conductivity = _decimal_from_envelope(
                prop["thermal_conductivity"],
                f"/materials/{material_index}/thermal_properties/{prop['index']}/thermal_conductivity",
            )
            if thickness is None or conductivity is None:
                _fail("/geometry/layers", "applicable execution requires bound layer quantities")
            product = context.multiply(conductivity, common_area)
            resistance = context.divide(thickness, product)
            layer_resistances.append((layer["layer_id"], resistance))
            layer_records.append(
                {
                    "layer_id": layer["layer_id"],
                    "material_id": layer["material_id"],
                    "property_id": prop["property_id"],
                    "thickness": _result_quantity(thickness, QuantityKind.LENGTH, "m"),
                    "normal_conductivity": _result_quantity(
                        conductivity, QuantityKind.THERMAL_CONDUCTIVITY, "W/(m*K)"
                    ),
                    "area": _result_quantity(common_area, QuantityKind.AREA, "m^2"),
                    "resistance": _result_quantity(
                        resistance, QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "K/W"
                    ),
                    "fraction_of_total": None,
                }
            )

        interface_records: list[dict[str, Any]] = []
        interface_resistances: list[tuple[str, str, Decimal]] = []
        for interface_index, interface in enumerate(candidate["interfaces"]):
            tbr = _decimal_from_envelope(interface["value"], f"/interfaces/{interface_index}/value")
            if tbr is None:
                _fail("/interfaces", "applicable execution requires bound interface quantities")
            resistance = context.divide(tbr, common_area)
            interface_resistances.append(
                (interface["upstream_layer_id"], interface["interface_id"], resistance)
            )
            interface_records.append(
                {
                    "interface_id": interface["interface_id"],
                    "upstream_layer_id": interface["upstream_layer_id"],
                    "downstream_layer_id": interface["downstream_layer_id"],
                    "tbr": _result_quantity(
                        tbr, QuantityKind.AREA_THERMAL_RESISTANCE, "m^2*K/W"
                    ),
                    "area": _result_quantity(common_area, QuantityKind.AREA, "m^2"),
                    "resistance": _result_quantity(
                        resistance, QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "K/W"
                    ),
                    "fraction_of_total": None,
                }
            )

        downstream = candidate["boundary_conditions"]["downstream"]
        representation = downstream["representation_type"]
        supplied_resistance = None
        heat_transfer_coefficient = None
        boundary_area = None
        if representation == "fixed_temperature":
            boundary_resistance = Decimal("0")
            reference_temperature = _decimal_from_envelope(
                downstream["reference_temperature"],
                "/boundary_conditions/downstream/reference_temperature",
            )
        elif representation == "absolute_resistance":
            boundary_resistance = _decimal_from_envelope(
                downstream["resistance"], "/boundary_conditions/downstream/resistance"
            )
            reference_temperature = _decimal_from_envelope(
                downstream["reference_temperature"],
                "/boundary_conditions/downstream/reference_temperature",
            )
            if boundary_resistance is not None:
                supplied_resistance = _result_quantity(
                    boundary_resistance, QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "K/W"
                )
        else:
            h = _decimal_from_envelope(
                downstream["heat_transfer_coefficient"],
                "/boundary_conditions/downstream/heat_transfer_coefficient",
            )
            area = _decimal_from_envelope(
                downstream["boundary_area"], "/boundary_conditions/downstream/boundary_area"
            )
            reference_temperature = _decimal_from_envelope(
                downstream["ambient_temperature"],
                "/boundary_conditions/downstream/ambient_temperature",
            )
            if h is None or area is None:
                _fail("/boundary_conditions/downstream", "convection inputs are unavailable")
            product = context.multiply(h, area)
            boundary_resistance = context.divide(Decimal("1"), product)
            heat_transfer_coefficient = _result_quantity(
                h, QuantityKind.AREA_THERMAL_CONDUCTANCE, "W/(m^2*K)"
            )
            boundary_area = _result_quantity(area, QuantityKind.AREA, "m^2")
        if boundary_resistance is None or reference_temperature is None:
            _fail("/boundary_conditions/downstream", "applicable execution requires bound boundary values")

        layer_sum = Decimal("0")
        for _layer_id, resistance in layer_resistances:
            layer_sum = context.add(layer_sum, resistance)
        interface_sum = Decimal("0")
        for _upstream, _interface_id, resistance in interface_resistances:
            interface_sum = context.add(interface_sum, resistance)
        total_resistance = context.add(
            context.add(layer_sum, interface_sum), boundary_resistance
        )
        temperature_rise = context.multiply(power, total_resistance)
        source_temperature = context.add(reference_temperature, temperature_rise)

        layer_by_id = {record["layer_id"]: record for record in layer_records}
        interface_by_id = {record["interface_id"]: record for record in interface_records}
        interface_after = {
            upstream: (interface_id, resistance)
            for upstream, interface_id, resistance in interface_resistances
        }
        series_elements: list[tuple[str, Decimal, str]] = []
        for layer_id, resistance in layer_resistances:
            series_elements.append((layer_id, resistance, "layer"))
            if layer_id in interface_after:
                interface_id, interface_resistance = interface_after[layer_id]
                series_elements.append((interface_id, interface_resistance, "interface"))
        series_elements.append(("BND-DOWNSTREAM", boundary_resistance, "boundary"))

        boundary_fraction = Decimal("0")
        for element_id, resistance, element_kind in series_elements:
            fraction = context.divide(resistance, total_resistance)
            quantity = _result_quantity(fraction, QuantityKind.PHYSICAL_DIMENSIONLESS, "1")
            if element_kind == "layer":
                layer_by_id[element_id]["fraction_of_total"] = quantity
            elif element_kind == "interface":
                interface_by_id[element_id]["fraction_of_total"] = quantity
            else:
                boundary_fraction = fraction

        suffixes: list[Decimal] = [Decimal("0")] * (len(series_elements) + 1)
        cumulative = Decimal("0")
        for index in range(len(series_elements) - 1, -1, -1):
            cumulative = context.add(series_elements[index][1], cumulative)
            suffixes[index] = cumulative
        node_temperatures: list[dict[str, Any]] = []
        for index, cumulative_resistance in enumerate(suffixes):
            rise = context.multiply(power, cumulative_resistance)
            temperature = context.add(reference_temperature, rise)
            node_temperatures.append(
                {
                    "node_id": f"NODE-{index:03d}",
                    "node_role": (
                        "source"
                        if index == 0
                        else "reference"
                        if index == len(series_elements)
                        else "internal"
                    ),
                    "upstream_element_id": None if index == 0 else series_elements[index - 1][0],
                    "downstream_element_id": (
                        None if index == len(series_elements) else series_elements[index][0]
                    ),
                    "temperature": _result_quantity(
                        temperature, QuantityKind.ABSOLUTE_TEMPERATURE, "K"
                    ),
                }
            )

        numerical_exactness = (
            "context_rounded" if context.flags[Inexact] or context.flags[Rounded] else "exact"
        )

    return {
        "common_area": _result_quantity(common_area, QuantityKind.AREA, "m^2"),
        "source_power": _result_quantity(power, QuantityKind.POWER, "W"),
        "reference_temperature": _result_quantity(
            reference_temperature, QuantityKind.ABSOLUTE_TEMPERATURE, "K"
        ),
        "layer_resistance_contributions": layer_records,
        "interface_resistance_contributions": interface_records,
        "boundary_resistance_contribution": {
            "boundary_id": "BND-DOWNSTREAM",
            "representation_type": representation,
            "supplied_resistance": supplied_resistance,
            "heat_transfer_coefficient": heat_transfer_coefficient,
            "boundary_area": boundary_area,
            "resistance": _result_quantity(
                boundary_resistance, QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "K/W"
            ),
            "fraction_of_total": _result_quantity(
                boundary_fraction, QuantityKind.PHYSICAL_DIMENSIONLESS, "1"
            ),
        },
        "total_thermal_resistance": _result_quantity(
            total_resistance, QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "K/W"
        ),
        "temperature_rise": _result_quantity(
            temperature_rise, QuantityKind.TEMPERATURE_DIFFERENCE, "K"
        ),
        "source_temperature": _result_quantity(
            source_temperature, QuantityKind.ABSOLUTE_TEMPERATURE, "K"
        ),
        "node_temperatures": node_temperatures,
        "numerical_exactness": numerical_exactness,
    }


@dataclass(frozen=True, slots=True)
class Strict1DScenarioResult:
    """Immutable closed result for one unswept I4A baseline scenario."""

    _content: Mapping[str, Any]

    @property
    def disposition(self) -> str:
        return self._content["disposition"]

    @property
    def applicability_status(self) -> str:
        return self._content["applicability_status"]

    @property
    def numerical_result(self) -> Mapping[str, Any] | None:
        result = self._content["numerical_result"]
        return None if result is None else _freeze(_thaw(result))

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._content)

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self._content)


def _evaluate_strict_1d_scenario(
    bound_evaluation: Strict1DBoundEvaluation,
    candidate_id: str,
    *,
    scenario_id: str,
    problem: Mapping[str, Any] | None = None,
    candidate: Mapping[str, Any] | None = None,
    sweep_coordinates: Sequence[Mapping[str, Any]] = (),
    input_overrides: Sequence[Mapping[str, Any]] = (),
    invalid_override_paths: Sequence[str] = (),
) -> Strict1DScenarioResult:
    """Execute one detached scenario through the single I4A physics primitive."""
    if not isinstance(bound_evaluation, Strict1DBoundEvaluation):
        raise TypeError("bound_evaluation must be a Strict1DBoundEvaluation")
    if type(candidate_id) is not str or candidate_id not in bound_evaluation._candidate_bindings:
        _fail("candidate_id", "must reference one selected bound candidate")
    problem_view = (
        bound_evaluation.engineering_problem.to_dict()
        if problem is None
        else copy.deepcopy(dict(problem))
    )
    binding = bound_evaluation._candidate_bindings[candidate_id]
    candidate_view = _thaw(binding.candidate) if candidate is None else copy.deepcopy(dict(candidate))
    applicability_findings = _applicability_findings(problem_view, candidate_view)
    binding_findings = [
        _thaw(item)
        for item in (*bound_evaluation._global_binding_findings, *binding.binding_findings)
    ]
    numerical_findings = _numeric_precondition_findings(problem_view, candidate_view)
    warnings = [_thaw(item) for item in binding.evidence_warnings]

    if invalid_override_paths:
        disposition = "invalid"
        applicability_status = "not_evaluated"
        execution_findings = _deduplicate_diagnostics(
            binding_findings
            + [
                _diagnostic(
                    "I4-SCENARIO-INVALID-OVERRIDE",
                    "MODEL_EXECUTION",
                    invalid_override_paths,
                    "An explicit scenario override violates a strict-1D numerical precondition.",
                    "Correct the explicit requested override value.",
                )
            ]
        )
        numerical_result = None
        acknowledgements_used = []
    elif applicability_findings:
        disposition = "not_applicable"
        applicability_status = "not_applicable"
        execution_findings = _deduplicate_diagnostics(binding_findings + numerical_findings)
        numerical_result = None
        acknowledgements_used: list[dict[str, Any]] = []
    elif binding_findings or numerical_findings:
        disposition = "blocked"
        applicability_status = "not_evaluated"
        execution_findings = _deduplicate_diagnostics(binding_findings + numerical_findings)
        numerical_result = None
        acknowledgements_used = []
    else:
        try:
            numerical_result = _compute_numerical_result(problem_view, candidate_view)
        except (DivisionByZero, InvalidOperation, Overflow):
            numerical_result = None
            disposition = "blocked"
            applicability_status = "not_evaluated"
            execution_findings = [
                _diagnostic(
                    "I4-NUM-NONPHYSICAL-BASE-INPUT",
                    "MODEL_EXECUTION",
                    ["/geometry/layers"],
                    "The strict-1D arithmetic preconditions were not satisfied.",
                    "Correct the bound baseline inputs before execution.",
                )
            ]
            acknowledgements_used = []
        else:
            disposition = "evaluated"
            applicability_status = "applicable_with_warnings" if warnings else "applicable"
            execution_findings = _deduplicate_diagnostics(warnings)
            acknowledgements_used = sorted(
                [_thaw(item) for item in binding.required_acknowledgements], key=_ack_key
            )

    content = {
        "scenario_id": scenario_id,
        "scenario_kind": "core",
        "candidate_id": candidate_id,
        "sweep_coordinates": [copy.deepcopy(dict(item)) for item in sweep_coordinates],
        "oat_coordinate": None,
        "input_overrides": [copy.deepcopy(dict(item)) for item in input_overrides],
        "disposition": disposition,
        "applicability_status": applicability_status,
        "reused_core_scenario_id": None,
        "consumed_input_paths": [
            _thaw(item) for item in binding.consumed_input_paths
        ],
        "assumption_acknowledgements_used": acknowledgements_used,
        "applicability_findings": applicability_findings,
        "execution_findings": execution_findings,
        "constraint_results": [],
        "numerical_result": numerical_result,
    }
    return Strict1DScenarioResult(_freeze(content))


def evaluate_strict_1d_baseline(
    bound_evaluation: Strict1DBoundEvaluation,
    candidate_id: str,
) -> Strict1DScenarioResult:
    """Evaluate one selected candidate's sole unswept strict-1D baseline."""
    if not isinstance(bound_evaluation, Strict1DBoundEvaluation):
        raise TypeError("bound_evaluation must be a Strict1DBoundEvaluation")
    if type(candidate_id) is not str or candidate_id not in bound_evaluation._candidate_bindings:
        _fail("candidate_id", "must reference one selected bound candidate")
    candidate_position = bound_evaluation.selected_candidate_ids.index(candidate_id) + 1
    return _evaluate_strict_1d_scenario(
        bound_evaluation,
        candidate_id,
        scenario_id=f"SCN-C{candidate_position:03d}-K000001",
    )


__all__ = [
    "ACCEPTED_QUANTITY_KINDS",
    "APPLICABILITY_POLICY_VERSION",
    "APPLICABILITY_RULE_IDS",
    "CANONICAL_UNITS",
    "CONSTRAINT_POLICY_VERSION",
    "EQUATION_SET_VERSION",
    "IMPLEMENTATION_VERSION",
    "INPUT_BINDING_POLICY_VERSION",
    "KNOWN_LIMITATIONS",
    "MODEL_ID",
    "MODEL_VERSION",
    "NUMERICAL_POLICY_VERSION",
    "OAT_POLICY_VERSION",
    "PROHIBITED_INPUT_FEATURES",
    "RANKING_POLICY_VERSION",
    "REQUIRED_INPUT_FEATURES",
    "RESULT_PAYLOAD_SCHEMA_ID",
    "RESULT_PAYLOAD_SCHEMA_VERSION",
    "SCENARIO_POLICY_VERSION",
    "SOURCE_REFERENCES",
    "Strict1DBoundEvaluation",
    "Strict1DScenarioResult",
    "Strict1DValidationError",
    "bind_strict_1d_inputs",
    "build_strict_1d_model_manifest",
    "evaluate_strict_1d_baseline",
]
