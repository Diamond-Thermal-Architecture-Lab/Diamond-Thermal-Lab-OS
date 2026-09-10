"""Immutable M16A evaluation-plan, model-manifest, and EER contracts."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Any

from .quantities import (
    UNIT_REGISTRY_VERSION,
    QuantifiedValue,
    QuantityKind,
    canonical_decimal_text,
    convert_quantity,
    parse_decimal,
)
from .serialization import CANONICAL_JSON_VERSION, canonical_json_bytes, canonical_sha256


EVALUATION_PLAN_FORMAT_VERSION = "m16a-evaluation-plan-1.0"
ENGINEERING_EVALUATION_RESULT_FORMAT_VERSION = "m16a-engineering-evaluation-result-1.0"
MODEL_MANIFEST_FORMAT_VERSION = "m16a-model-manifest-1.0"
EVALUATION_PLAN_IDENTITY_VERSION = "m16a-evaluation-plan-content-identity-1.0"
MODEL_MANIFEST_IDENTITY_VERSION = "m16a-model-manifest-content-identity-1.0"
EVALUATION_INPUT_IDENTITY_VERSION = "m16a-evaluation-input-identity-1.0"
EER_CONTENT_IDENTITY_VERSION = "m16a-eer-content-identity-1.0"
DETERMINISTIC_RUNTIME_POLICY_VERSION = "m16a-evaluation-runtime-1.0"
CALCULATION_NOT_APPROVAL_NOTICE = (
    "This is a model result, not validation, approval, or a canonical engineering decision."
)


_PLAN_FIELDS = (
    "evaluation_plan_format_version",
    "case_id",
    "problem_id",
    "epr_compiled_content_sha256",
    "model_request",
    "selected_candidate_ids",
    "objective",
    "constraint_handling",
    "parameter_sweeps",
    "sensitivity_request",
    "assumption_acknowledgements",
    "model_options",
    "maximum_requested_combination_count",
)
_MANIFEST_FIELDS = (
    "model_manifest_format_version",
    "model_id",
    "model_version",
    "equation_set_version",
    "implementation_version",
    "applicability_policy_version",
    "applicability_rule_ids",
    "numerical_policy_version",
    "input_binding_policy_version",
    "serialization_policy_version",
    "result_payload_schema_id",
    "result_payload_schema_version",
    "required_input_features",
    "prohibited_input_features",
    "accepted_quantity_kinds",
    "canonical_units",
    "known_limitations",
    "source_references",
    "implementation_git_commit",
)
_EER_FIELDS = (
    "engineering_evaluation_result_format_version",
    "evaluation_id",
    "case_id",
    "problem_id",
    "epr_reference",
    "epr_compiled_content_sha256",
    "epr_file_sha256",
    "evaluation_plan",
    "evaluation_plan_sha256",
    "model_manifest",
    "model_manifest_sha256",
    "unit_registry_version",
    "deterministic_runtime_policy_version",
    "evaluation_input_sha256",
    "execution_outcome",
    "candidate_execution",
    "assumptions_used",
    "result_payload",
    "prediction_outputs",
    "findings",
    "warnings",
    "confidentiality_level",
    "calculation_not_approval_notice",
    "eer_content_sha256",
)

_CASE_ID = re.compile(r"^[a-z0-9_-]+$")
_PROBLEM_ID = re.compile(r"^EPR-[0-9]{3}$")
_CANDIDATE_ID = re.compile(r"^CND-[0-9]{3}$")
_REQUIREMENT_ID = re.compile(r"^REQ-[0-9]{3}$")
_SWEEP_ID = re.compile(r"^SWP-[0-9]{3}$")
_EVALUATION_ID = re.compile(r"^EER-[0-9]{3}$")
_OUTPUT_ID = re.compile(r"^(EER-[0-9]{3})-OUT-([0-9]{3})$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_POINTER = re.compile(r"^(?:/(?:[^~/]|~[01])*)+$")

_OBJECTIVE_DIRECTIONS = {
    "source_temperature": "minimize",
    "total_thermal_resistance": "minimize",
    "temperature_margin": "maximize",
}
_CONSTRAINT_HANDLING = {"exclude_violating_from_rank", "report_only"}
_CONFIDENTIALITY_LEVELS = {"public", "internal", "customer-confidential", "restricted"}


class EngineeringEvaluationValidationError(ValueError):
    """Raised when persisted I3A evaluation data violates its contract."""


def _fail(path: str, message: str) -> None:
    raise EngineeringEvaluationValidationError(f"{path}: {message}")


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(path, "must be an object")
    if any(type(key) is not str for key in value):
        _fail(path, "object keys must be strings")
    return value


def _closed(value: Any, required: Sequence[str], path: str) -> Mapping[str, Any]:
    item = _mapping(value, path)
    expected = set(required)
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


def _matches(value: Any, pattern: re.Pattern[str], label: str, path: str) -> str:
    if type(value) is not str or pattern.fullmatch(value) is None:
        _fail(path, f"has invalid {label} syntax")
    return value


def _sha(value: Any, path: str) -> str:
    return _matches(value, _SHA256, "lowercase SHA-256", path)


def _pointer(value: Any, path: str) -> str:
    return _matches(value, _POINTER, "non-empty RFC 6901 JSON Pointer", path)


def _ordered_unique_strings(
    value: Any,
    path: str,
    *,
    minimum: int = 0,
    pattern: re.Pattern[str] | None = None,
    label: str = "identifier",
) -> list[str]:
    items = _array(value, path, minimum=minimum)
    for index, item in enumerate(items):
        if pattern is None:
            _non_empty(item, f"{path}/{index}")
        else:
            _matches(item, pattern, label, f"{path}/{index}")
    if len(items) != len(set(items)):
        _fail(path, "contains duplicates")
    if items != sorted(items):
        _fail(path, "must use canonical lexical order")
    return items


def _canonical_json_value(value: Any, path: str) -> None:
    if value is None or type(value) in {bool, str, int}:
        return
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            _fail(path, "canonical JSON object keys must be strings")
        for key, item in value.items():
            _canonical_json_value(item, f"{path}/{key}")
        return
    if type(value) is list:
        for index, item in enumerate(value):
            _canonical_json_value(item, f"{path}/{index}")
        return
    _fail(path, f"unsupported canonical JSON value type: {type(value).__name__}")


def _quantity(value: Any, path: str) -> QuantifiedValue:
    item = _closed(value, ("value", "unit", "quantity_kind", "conversion"), path)
    if type(item["value"]) is not str:
        _fail(f"{path}/value", "physical values must be decimal strings")
    try:
        return QuantifiedValue.from_dict(
            {
                "quantity_kind": item["quantity_kind"],
                "canonical_value": item["value"],
                "canonical_unit": item["unit"],
                "conversion": item["conversion"],
            }
        )
    except (KeyError, TypeError, ValueError) as exc:
        _fail(path, f"does not reconstruct through I1: {exc}")


def _ack_key(item: Mapping[str, Any]) -> tuple[str, int, str, str]:
    """Return the frozen scope/candidate-null-first/path acknowledgement order."""
    candidate_id = item["candidate_id"]
    return (item["scope"], 0 if candidate_id is None else 1, candidate_id or "", item["field_path"])


def _validate_acknowledgements(
    value: Any,
    path: str,
    selected_candidates: set[str] | None = None,
) -> list[Mapping[str, Any]]:
    items = _array(value, path)
    keys: list[tuple[str, int, str, str]] = []
    serialized: set[bytes] = set()
    for index, raw in enumerate(items):
        item_path = f"{path}/{index}"
        item = _closed(raw, ("scope", "candidate_id", "field_path"), item_path)
        scope = item["scope"]
        if scope not in {"candidate", "global"}:
            _fail(f"{item_path}/scope", "must be 'candidate' or 'global'")
        candidate_id = item["candidate_id"]
        if scope == "global":
            if candidate_id is not None:
                _fail(f"{item_path}/candidate_id", "must be null for global scope")
        else:
            _matches(candidate_id, _CANDIDATE_ID, "candidate ID", f"{item_path}/candidate_id")
            if selected_candidates is not None and candidate_id not in selected_candidates:
                _fail(f"{item_path}/candidate_id", "must reference a selected candidate")
        _pointer(item["field_path"], f"{item_path}/field_path")
        encoded = canonical_json_bytes(item)
        if encoded in serialized:
            _fail(path, "contains duplicate acknowledgement records")
        serialized.add(encoded)
        keys.append(_ack_key(item))
    if keys != sorted(keys):
        _fail(path, "must use scope, null-first candidate-ID, then field-path canonical order")
    return items


def _range_progression(start: QuantifiedValue, stop: QuantifiedValue, step: QuantifiedValue, path: str) -> tuple[int, int]:
    delta = stop.canonical_value - start.canonical_value
    increment = step.canonical_value
    if increment.is_zero():
        _fail(f"{path}/step/value", "range step must be non-zero")
    if delta.is_zero():
        _fail(path, "range start and stop must be distinct")
    if (delta > 0) != (increment > 0):
        _fail(f"{path}/step/value", "step direction must move from start toward stop")
    delta_num, delta_den = abs(delta).as_integer_ratio()
    step_num, step_den = abs(increment).as_integer_ratio()
    quotient, remainder = divmod(delta_num * step_den, delta_den * step_num)
    return quotient, remainder


def _validate_value_specification(value: Any, path: str) -> int:
    item = _mapping(value, path)
    kind = item.get("kind")
    if kind == "grid":
        item = _closed(item, ("kind", "values"), path)
        values = _array(item["values"], f"{path}/values", minimum=1)
        quantities = [_quantity(raw, f"{path}/values/{index}") for index, raw in enumerate(values)]
        first_kind = quantities[0].quantity_kind
        if any(quantity.quantity_kind is not first_kind for quantity in quantities):
            _fail(f"{path}/values", "grid values must use one QuantityKind")
        identities = [quantity.numeric_identity for quantity in quantities]
        if len(identities) != len(set(identities)):
            _fail(f"{path}/values", "contains duplicate normalized numeric points")
        return len(values)
    if kind == "range":
        item = _closed(item, ("kind", "start", "stop", "step", "endpoint_policy"), path)
        start = _quantity(item["start"], f"{path}/start")
        stop = _quantity(item["stop"], f"{path}/stop")
        step = _quantity(item["step"], f"{path}/step")
        if start.quantity_kind is not stop.quantity_kind:
            _fail(path, "range start and stop must use the same QuantityKind")
        required_step_kind = (
            QuantityKind.TEMPERATURE_DIFFERENCE
            if start.quantity_kind is QuantityKind.ABSOLUTE_TEMPERATURE
            else start.quantity_kind
        )
        if step.quantity_kind is not required_step_kind:
            _fail(f"{path}/step/quantity_kind", f"must equal {required_step_kind.value!r}")
        policy = item["endpoint_policy"]
        if policy not in {"include_stop", "exclude_stop"}:
            _fail(f"{path}/endpoint_policy", "must be 'include_stop' or 'exclude_stop'")
        quotient, remainder = _range_progression(start, stop, step, path)
        if remainder == 0:
            return quotient + (1 if policy == "include_stop" else 0)
        return quotient + 1
    _fail(f"{path}/kind", "must be 'grid' or 'range'")


def _validate_sweeps(
    value: Any,
    selected_candidates: list[str],
    path: str,
) -> int:
    sweeps = _array(value, path)
    selected = set(selected_candidates)
    ids: list[str] = []
    counts: dict[str, int] = {candidate_id: 1 for candidate_id in selected_candidates}
    for index, raw in enumerate(sweeps):
        sweep_path = f"{path}/{index}"
        item = _closed(raw, ("sweep_id", "candidate_id", "field_path", "value_specification"), sweep_path)
        ids.append(_matches(item["sweep_id"], _SWEEP_ID, "sweep ID", f"{sweep_path}/sweep_id"))
        candidate_id = _matches(item["candidate_id"], _CANDIDATE_ID, "candidate ID", f"{sweep_path}/candidate_id")
        if candidate_id not in selected:
            _fail(f"{sweep_path}/candidate_id", "must reference a selected candidate")
        _pointer(item["field_path"], f"{sweep_path}/field_path")
        point_count = _validate_value_specification(item["value_specification"], f"{sweep_path}/value_specification")
        counts[candidate_id] *= point_count
    if len(ids) != len(set(ids)):
        _fail(path, "contains duplicate sweep IDs")
    if ids != sorted(ids):
        _fail(path, "must use canonical sweep-ID order")
    return sum(counts.values())


def _validate_sensitivity(value: Any, selected_candidates: set[str], path: str) -> None:
    if value is None:
        return
    item = _closed(value, ("method", "baseline_candidate_id", "output_metric", "parameters"), path)
    if item["method"] != "oat":
        _fail(f"{path}/method", "must equal 'oat'")
    baseline = _matches(item["baseline_candidate_id"], _CANDIDATE_ID, "candidate ID", f"{path}/baseline_candidate_id")
    if baseline not in selected_candidates:
        _fail(f"{path}/baseline_candidate_id", "must reference a selected candidate")
    if item["output_metric"] not in _OBJECTIVE_DIRECTIONS:
        _fail(f"{path}/output_metric", "has unsupported metric")
    parameters = _array(item["parameters"], f"{path}/parameters", minimum=1)
    field_paths: list[str] = []
    for index, raw in enumerate(parameters):
        parameter_path = f"{path}/parameters/{index}"
        parameter = _closed(raw, ("candidate_id", "field_path", "minus_value", "plus_value"), parameter_path)
        candidate_id = _matches(parameter["candidate_id"], _CANDIDATE_ID, "candidate ID", f"{parameter_path}/candidate_id")
        if candidate_id != baseline:
            _fail(f"{parameter_path}/candidate_id", "must equal baseline_candidate_id")
        field_paths.append(_pointer(parameter["field_path"], f"{parameter_path}/field_path"))
        minus = _quantity(parameter["minus_value"], f"{parameter_path}/minus_value")
        plus = _quantity(parameter["plus_value"], f"{parameter_path}/plus_value")
        if minus.quantity_kind is not plus.quantity_kind:
            _fail(parameter_path, "minus_value and plus_value must use the same QuantityKind")
        if minus.canonical_unit != plus.canonical_unit:
            _fail(parameter_path, "minus_value and plus_value must use compatible canonical units")
        if minus.canonical_value == plus.canonical_value:
            _fail(parameter_path, "minus_value and plus_value must be numerically distinct")
    if len(field_paths) != len(set(field_paths)):
        _fail(f"{path}/parameters", "contains duplicate field paths")
    if field_paths != sorted(field_paths):
        _fail(f"{path}/parameters", "must use canonical field-path order")


def _validate_plan(value: Mapping[str, Any]) -> int:
    item = _closed(value, _PLAN_FIELDS, "evaluation_plan")
    if item["evaluation_plan_format_version"] != EVALUATION_PLAN_FORMAT_VERSION:
        _fail("/evaluation_plan_format_version", f"must equal {EVALUATION_PLAN_FORMAT_VERSION!r}")
    _matches(item["case_id"], _CASE_ID, "case ID", "/case_id")
    _matches(item["problem_id"], _PROBLEM_ID, "problem ID", "/problem_id")
    _sha(item["epr_compiled_content_sha256"], "/epr_compiled_content_sha256")
    request = _closed(item["model_request"], ("model_id", "model_version"), "/model_request")
    _non_empty(request["model_id"], "/model_request/model_id")
    _non_empty(request["model_version"], "/model_request/model_version")
    selected = _ordered_unique_strings(
        item["selected_candidate_ids"],
        "/selected_candidate_ids",
        minimum=1,
        pattern=_CANDIDATE_ID,
        label="candidate ID",
    )
    objective = _closed(item["objective"], ("metric", "direction", "reference_requirement_id"), "/objective")
    metric = objective["metric"]
    if metric not in _OBJECTIVE_DIRECTIONS:
        _fail("/objective/metric", "has unsupported metric")
    if objective["direction"] != _OBJECTIVE_DIRECTIONS[metric]:
        _fail("/objective/direction", f"must equal {_OBJECTIVE_DIRECTIONS[metric]!r} for {metric!r}")
    reference = objective["reference_requirement_id"]
    if reference is not None:
        _matches(reference, _REQUIREMENT_ID, "requirement ID", "/objective/reference_requirement_id")
    if metric == "temperature_margin" and reference is None:
        _fail("/objective/reference_requirement_id", "temperature_margin requires a requirement ID")
    if item["constraint_handling"] not in _CONSTRAINT_HANDLING:
        _fail("/constraint_handling", "has unsupported constraint-handling policy")
    total = _validate_sweeps(item["parameter_sweeps"], selected, "/parameter_sweeps")
    _validate_sensitivity(item["sensitivity_request"], set(selected), "/sensitivity_request")
    _validate_acknowledgements(item["assumption_acknowledgements"], "/assumption_acknowledgements", set(selected))
    _mapping(item["model_options"], "/model_options")
    _canonical_json_value(item["model_options"], "/model_options")
    maximum = item["maximum_requested_combination_count"]
    if type(maximum) is not int or maximum <= 0:
        _fail("/maximum_requested_combination_count", "must be a positive integer")
    if maximum < total:
        _fail("/maximum_requested_combination_count", f"must be at least the exact requested total {total}")
    return total


def _validate_manifest(value: Mapping[str, Any]) -> None:
    item = _closed(value, _MANIFEST_FIELDS, "model_manifest")
    if item["model_manifest_format_version"] != MODEL_MANIFEST_FORMAT_VERSION:
        _fail("/model_manifest_format_version", f"must equal {MODEL_MANIFEST_FORMAT_VERSION!r}")
    for field in (
        "model_id", "model_version", "equation_set_version", "implementation_version",
        "applicability_policy_version", "numerical_policy_version", "input_binding_policy_version",
        "result_payload_schema_id", "result_payload_schema_version",
    ):
        _non_empty(item[field], f"/{field}")
    if item["serialization_policy_version"] != CANONICAL_JSON_VERSION:
        _fail("/serialization_policy_version", f"must equal {CANONICAL_JSON_VERSION!r}")
    for field in (
        "applicability_rule_ids", "required_input_features", "prohibited_input_features",
        "known_limitations", "source_references",
    ):
        _ordered_unique_strings(item[field], f"/{field}")
    required = set(item["required_input_features"])
    prohibited = set(item["prohibited_input_features"])
    if required & prohibited:
        _fail("/required_input_features", "must not overlap prohibited_input_features")
    kinds = _ordered_unique_strings(item["accepted_quantity_kinds"], "/accepted_quantity_kinds", minimum=1)
    for index, kind_text in enumerate(kinds):
        try:
            QuantityKind(kind_text)
        except ValueError:
            _fail(f"/accepted_quantity_kinds/{index}", "must be an I1 QuantityKind")
    units = _mapping(item["canonical_units"], "/canonical_units")
    if set(units) != set(kinds):
        _fail("/canonical_units", "keys must exactly equal accepted_quantity_kinds")
    for kind_text in kinds:
        unit = _non_empty(units[kind_text], f"/canonical_units/{kind_text}")
        try:
            reconstructed = convert_quantity(QuantityKind(kind_text), "0", unit)
        except (TypeError, ValueError) as exc:
            _fail(f"/canonical_units/{kind_text}", f"is not registered for its QuantityKind: {exc}")
        if reconstructed.canonical_unit != unit:
            _fail(f"/canonical_units/{kind_text}", "must be the exact I1 canonical unit")
    commit = item["implementation_git_commit"]
    if commit is not None:
        _matches(commit, _GIT_COMMIT, "full lowercase Git commit", "/implementation_git_commit")


def _validate_diagnostics(value: Any, path: str) -> None:
    items = _array(value, path)
    keys: list[tuple[str, tuple[str, ...], str]] = []
    encoded: set[bytes] = set()
    for index, raw in enumerate(items):
        item_path = f"{path}/{index}"
        item = _closed(raw, ("rule_id", "classification", "field_paths", "message", "required_action"), item_path)
        rule_id = _non_empty(item["rule_id"], f"{item_path}/rule_id")
        _non_empty(item["classification"], f"{item_path}/classification")
        field_paths = _array(item["field_paths"], f"{item_path}/field_paths")
        for field_index, field_path in enumerate(field_paths):
            _pointer(field_path, f"{item_path}/field_paths/{field_index}")
        if len(field_paths) != len(set(field_paths)):
            _fail(f"{item_path}/field_paths", "contains duplicate pointers")
        if field_paths != sorted(field_paths):
            _fail(f"{item_path}/field_paths", "must use canonical pointer order")
        message = _non_empty(item["message"], f"{item_path}/message")
        _non_empty(item["required_action"], f"{item_path}/required_action")
        representation = canonical_json_bytes(item)
        if representation in encoded:
            _fail(path, "contains duplicate diagnostics")
        encoded.add(representation)
        keys.append((rule_id, tuple(field_paths), message))
    if keys != sorted(keys):
        _fail(path, "must use rule/path/message canonical order")


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


def _exact_projection(value: Mapping[str, Any], fields: Sequence[str], path: str) -> dict[str, Any]:
    item = _mapping(value, path)
    if set(item) != set(fields):
        _fail(path, "must contain the exact persisted fields")
    return {field: copy.deepcopy(item[field]) for field in fields}


def evaluation_plan_sha256(value: "EvaluationPlan | Mapping[str, Any]") -> str:
    """Hash the complete plan in the frozen I3A plan-identity domain."""
    plan = value.to_dict() if isinstance(value, EvaluationPlan) else _exact_projection(value, _PLAN_FIELDS, "evaluation_plan")
    return canonical_sha256({
        "evaluation_plan_identity_version": EVALUATION_PLAN_IDENTITY_VERSION,
        "evaluation_plan": plan,
    })


def model_manifest_sha256(value: "ModelManifest | Mapping[str, Any]") -> str:
    """Hash the complete manifest in the frozen I3A manifest-identity domain."""
    manifest = value.to_dict() if isinstance(value, ModelManifest) else _exact_projection(value, _MANIFEST_FIELDS, "model_manifest")
    return canonical_sha256({
        "model_manifest_identity_version": MODEL_MANIFEST_IDENTITY_VERSION,
        "model_manifest": manifest,
    })


def evaluation_input_sha256(
    *,
    epr_compiled_content_sha256: str,
    evaluation_plan_sha256: str,
    model_manifest_sha256: str,
    unit_registry_version: str,
    deterministic_runtime_policy_version: str,
) -> str:
    """Hash exactly the model-independent evaluation-input allowlist."""
    _sha(epr_compiled_content_sha256, "/epr_compiled_content_sha256")
    _sha(evaluation_plan_sha256, "/evaluation_plan_sha256")
    _sha(model_manifest_sha256, "/model_manifest_sha256")
    _non_empty(unit_registry_version, "/unit_registry_version")
    _non_empty(deterministic_runtime_policy_version, "/deterministic_runtime_policy_version")
    return canonical_sha256({
        "evaluation_input_identity_version": EVALUATION_INPUT_IDENTITY_VERSION,
        "epr_compiled_content_sha256": epr_compiled_content_sha256,
        "evaluation_plan_sha256": evaluation_plan_sha256,
        "model_manifest_sha256": model_manifest_sha256,
        "unit_registry_version": unit_registry_version,
        "deterministic_runtime_policy_version": deterministic_runtime_policy_version,
    })


def result_payload_content_sha256(value: Mapping[str, Any]) -> str:
    """Hash the explicit generic payload-wrapper projection."""
    item = _closed(value, ("schema_id", "schema_version", "content", "content_sha256"), "result_payload")
    return canonical_sha256({
        "schema_id": copy.deepcopy(item["schema_id"]),
        "schema_version": copy.deepcopy(item["schema_version"]),
        "content": copy.deepcopy(item["content"]),
    })


def engineering_evaluation_result_content_sha256(
    value: "EngineeringEvaluationResult | Mapping[str, Any]",
) -> str:
    """Hash every authoritative EER field except the EER self-hash."""
    eer = value.to_dict() if isinstance(value, EngineeringEvaluationResult) else _exact_projection(value, _EER_FIELDS, "engineering_evaluation_result")
    projection = {field: copy.deepcopy(eer[field]) for field in _EER_FIELDS[:-1]}
    return canonical_sha256({"eer_identity_version": EER_CONTENT_IDENTITY_VERSION, **projection})


@dataclass(frozen=True)
class EvaluationPlan:
    """Deeply immutable reconstruction of one persisted Evaluation Plan."""

    _content: Mapping[str, Any]
    _total_requested_combination_count: int

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EvaluationPlan":
        if not isinstance(value, Mapping):
            _fail("evaluation_plan", "must be an object")
        detached = copy.deepcopy(dict(value))
        total = _validate_plan(detached)
        return cls(_freeze(detached), total)

    @property
    def content_sha256(self) -> str:
        return evaluation_plan_sha256(self)

    @property
    def total_requested_combination_count(self) -> int:
        return self._total_requested_combination_count

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._content)

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self._content)


@dataclass(frozen=True)
class ModelManifest:
    """Deeply immutable reconstruction of one persisted Model Manifest."""

    _content: Mapping[str, Any]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ModelManifest":
        if not isinstance(value, Mapping):
            _fail("model_manifest", "must be an object")
        detached = copy.deepcopy(dict(value))
        _validate_manifest(detached)
        return cls(_freeze(detached))

    @property
    def content_sha256(self) -> str:
        return model_manifest_sha256(self)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._content)

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self._content)


def _validate_eer(value: Mapping[str, Any]) -> None:
    item = _closed(value, _EER_FIELDS, "engineering_evaluation_result")
    if item["engineering_evaluation_result_format_version"] != ENGINEERING_EVALUATION_RESULT_FORMAT_VERSION:
        _fail("/engineering_evaluation_result_format_version", f"must equal {ENGINEERING_EVALUATION_RESULT_FORMAT_VERSION!r}")
    evaluation_id = _matches(item["evaluation_id"], _EVALUATION_ID, "evaluation ID", "/evaluation_id")
    case_id = _matches(item["case_id"], _CASE_ID, "case ID", "/case_id")
    problem_id = _matches(item["problem_id"], _PROBLEM_ID, "problem ID", "/problem_id")
    if item["epr_reference"] != f"engineering/problems/{problem_id}.json":
        _fail("/epr_reference", "must be the exact case-local EPR reference")
    epr_hash = _sha(item["epr_compiled_content_sha256"], "/epr_compiled_content_sha256")
    _sha(item["epr_file_sha256"], "/epr_file_sha256")

    plan = EvaluationPlan.from_dict(item["evaluation_plan"])
    plan_data = plan.to_dict()
    supplied_plan_hash = _sha(item["evaluation_plan_sha256"], "/evaluation_plan_sha256")
    if supplied_plan_hash != plan.content_sha256:
        _fail("/evaluation_plan_sha256", "does not match the embedded Evaluation Plan")
    if (plan_data["case_id"], plan_data["problem_id"], plan_data["epr_compiled_content_sha256"]) != (case_id, problem_id, epr_hash):
        _fail("/evaluation_plan", "EPR binding must match the EER")

    manifest = ModelManifest.from_dict(item["model_manifest"])
    manifest_data = manifest.to_dict()
    supplied_manifest_hash = _sha(item["model_manifest_sha256"], "/model_manifest_sha256")
    if supplied_manifest_hash != manifest.content_sha256:
        _fail("/model_manifest_sha256", "does not match the embedded Model Manifest")
    request = plan_data["model_request"]
    if (manifest_data["model_id"], manifest_data["model_version"]) != (request["model_id"], request["model_version"]):
        _fail("/model_manifest", "model identity must match evaluation_plan.model_request")

    if item["unit_registry_version"] != UNIT_REGISTRY_VERSION:
        _fail("/unit_registry_version", f"must equal {UNIT_REGISTRY_VERSION!r}")
    if item["deterministic_runtime_policy_version"] != DETERMINISTIC_RUNTIME_POLICY_VERSION:
        _fail("/deterministic_runtime_policy_version", f"must equal {DETERMINISTIC_RUNTIME_POLICY_VERSION!r}")
    supplied_input_hash = _sha(item["evaluation_input_sha256"], "/evaluation_input_sha256")
    expected_input_hash = evaluation_input_sha256(
        epr_compiled_content_sha256=epr_hash,
        evaluation_plan_sha256=supplied_plan_hash,
        model_manifest_sha256=supplied_manifest_hash,
        unit_registry_version=item["unit_registry_version"],
        deterministic_runtime_policy_version=item["deterministic_runtime_policy_version"],
    )
    if supplied_input_hash != expected_input_hash:
        _fail("/evaluation_input_sha256", "does not match the authoritative evaluation inputs")

    selected = plan_data["selected_candidate_ids"]
    selected_set = set(selected)
    plan_acknowledgements = plan_data["assumption_acknowledgements"]
    plan_ack_bytes = {canonical_json_bytes(ack) for ack in plan_acknowledgements}
    executions = _array(item["candidate_execution"], "/candidate_execution")
    if len(executions) != len(selected):
        _fail("/candidate_execution", "must contain exactly one record per selected candidate")
    evaluated_candidates: set[str] = set()
    used_union: dict[bytes, Mapping[str, Any]] = {}
    for index, raw in enumerate(executions):
        execution_path = f"/candidate_execution/{index}"
        execution = _closed(
            raw,
            ("candidate_id", "execution_status", "applicability_status", "applicability_findings", "assumption_acknowledgements_used", "result_presence"),
            execution_path,
        )
        if execution["candidate_id"] != selected[index]:
            _fail(f"{execution_path}/candidate_id", "must exactly follow selected_candidate_ids order")
        status = execution["execution_status"]
        applicability = execution["applicability_status"]
        result_presence = execution["result_presence"]
        if type(result_presence) is not bool:
            _fail(f"{execution_path}/result_presence", "must be a boolean")
        allowed = {
            "evaluated": ({"applicable", "applicable_with_warnings"}, True),
            "blocked": ({"not_evaluated"}, False),
            "not_applicable": ({"not_applicable"}, False),
        }
        if status not in allowed:
            _fail(f"{execution_path}/execution_status", "has unsupported status")
        allowed_applicability, required_presence = allowed[status]
        if applicability not in allowed_applicability or result_presence is not required_presence:
            _fail(execution_path, "execution, applicability, and result-presence values are inconsistent")
        if status == "evaluated":
            evaluated_candidates.add(execution["candidate_id"])
        _validate_diagnostics(execution["applicability_findings"], f"{execution_path}/applicability_findings")
        used = _validate_acknowledgements(
            execution["assumption_acknowledgements_used"],
            f"{execution_path}/assumption_acknowledgements_used",
            selected_set,
        )
        for acknowledgement in used:
            encoded = canonical_json_bytes(acknowledgement)
            if encoded not in plan_ack_bytes:
                _fail(f"{execution_path}/assumption_acknowledgements_used", "must be a subset of Plan acknowledgements")
            if acknowledgement["scope"] == "candidate" and acknowledgement["candidate_id"] != execution["candidate_id"]:
                _fail(f"{execution_path}/assumption_acknowledgements_used", "candidate-scoped acknowledgement belongs to another candidate")
            used_union[encoded] = acknowledgement

    derived_outcome = (
        "completed" if len(evaluated_candidates) == len(selected)
        else "partial" if evaluated_candidates
        else "not_evaluated"
    )
    if item["execution_outcome"] != derived_outcome:
        _fail("/execution_outcome", f"must equal derived outcome {derived_outcome!r}")

    top_used = _validate_acknowledgements(item["assumptions_used"], "/assumptions_used", selected_set)
    if [canonical_json_bytes(ack) for ack in top_used] != sorted(used_union, key=lambda encoded: _ack_key(used_union[encoded])):
        _fail("/assumptions_used", "must equal the canonical union of candidate execution acknowledgements")

    payload = item["result_payload"]
    if payload is None:
        if derived_outcome != "not_evaluated":
            _fail("/result_payload", "may be null only when execution_outcome is not_evaluated")
        payload_content = None
    else:
        payload = _closed(payload, ("schema_id", "schema_version", "content", "content_sha256"), "/result_payload")
        _non_empty(payload["schema_id"], "/result_payload/schema_id")
        _non_empty(payload["schema_version"], "/result_payload/schema_version")
        _canonical_json_value(payload["content"], "/result_payload/content")
        supplied_payload_hash = _sha(payload["content_sha256"], "/result_payload/content_sha256")
        if (payload["schema_id"], payload["schema_version"]) != (
            manifest_data["result_payload_schema_id"], manifest_data["result_payload_schema_version"]
        ):
            _fail("/result_payload", "schema identity must match the embedded Model Manifest")
        if supplied_payload_hash != result_payload_content_sha256(payload):
            _fail("/result_payload/content_sha256", "does not match schema identity and content")
        payload_content = payload["content"]

    outputs = _array(item["prediction_outputs"], "/prediction_outputs")
    output_ids: list[str] = []
    for index, raw in enumerate(outputs):
        output_path = f"/prediction_outputs/{index}"
        output = _closed(
            raw,
            ("output_id", "candidate_id", "quantity_label", "quantity_kind", "value", "unit", "lower_bound", "upper_bound", "result_pointer"),
            output_path,
        )
        match = _OUTPUT_ID.fullmatch(output["output_id"]) if type(output["output_id"]) is str else None
        if match is None:
            _fail(f"{output_path}/output_id", "has invalid prediction output ID syntax")
        if match.group(1) != evaluation_id:
            _fail(f"{output_path}/output_id", "prefix must equal evaluation_id")
        output_ids.append(output["output_id"])
        candidate_id = _matches(output["candidate_id"], _CANDIDATE_ID, "candidate ID", f"{output_path}/candidate_id")
        if candidate_id not in evaluated_candidates:
            _fail(f"{output_path}/candidate_id", "must reference an evaluated candidate with result presence")
        _non_empty(output["quantity_label"], f"{output_path}/quantity_label")
        try:
            kind = QuantityKind(output["quantity_kind"])
        except (TypeError, ValueError):
            _fail(f"{output_path}/quantity_kind", "must be an I1 QuantityKind")
        unit = _non_empty(output["unit"], f"{output_path}/unit")
        try:
            canonical = convert_quantity(kind, "0", unit).canonical_unit
        except (TypeError, ValueError) as exc:
            _fail(f"{output_path}/unit", f"is not registered for its QuantityKind: {exc}")
        if canonical != unit:
            _fail(f"{output_path}/unit", "must be the exact I1 canonical unit")
        decimals: dict[str, Decimal | None] = {}
        for field in ("value", "lower_bound", "upper_bound"):
            raw_decimal = output[field]
            if field != "value" and raw_decimal is None:
                decimals[field] = None
                continue
            if type(raw_decimal) is not str:
                _fail(f"{output_path}/{field}", "must be a canonical M16A decimal string")
            try:
                parsed = parse_decimal(raw_decimal)
            except ValueError as exc:
                _fail(f"{output_path}/{field}", f"has invalid decimal syntax: {exc}")
            if canonical_decimal_text(parsed) != raw_decimal:
                _fail(f"{output_path}/{field}", "must use canonical M16A decimal text")
            decimals[field] = parsed
        central_value = decimals["value"]
        if central_value is None:  # Defensive; value is required and validated above.
            _fail(f"{output_path}/value", "must be a canonical M16A decimal string")
        if decimals["lower_bound"] is not None and decimals["lower_bound"] > central_value:
            _fail(output_path, "lower_bound must be less than or equal to value")
        if decimals["upper_bound"] is not None and central_value > decimals["upper_bound"]:
            _fail(output_path, "value must be less than or equal to upper_bound")
        pointer = _pointer(output["result_pointer"], f"{output_path}/result_pointer")
        if payload_content is None:
            _fail(output_path, "prediction output requires a non-null result payload")
        _resolve_pointer(payload_content, pointer, f"{output_path}/result_pointer")
    if len(output_ids) != len(set(output_ids)):
        _fail("/prediction_outputs", "contains duplicate output IDs")
    if output_ids != sorted(output_ids):
        _fail("/prediction_outputs", "must use canonical output-ID order")
    if payload is None and outputs:
        _fail("/prediction_outputs", "must be empty when result_payload is null")

    _validate_diagnostics(item["findings"], "/findings")
    _validate_diagnostics(item["warnings"], "/warnings")
    if item["confidentiality_level"] not in _CONFIDENTIALITY_LEVELS:
        _fail("/confidentiality_level", "has unsupported confidentiality level")
    if item["calculation_not_approval_notice"] != CALCULATION_NOT_APPROVAL_NOTICE:
        _fail("/calculation_not_approval_notice", "must equal the exact mandatory notice")
    supplied_eer_hash = _sha(item["eer_content_sha256"], "/eer_content_sha256")
    if supplied_eer_hash != engineering_evaluation_result_content_sha256(item):
        _fail("/eer_content_sha256", "does not match authoritative EER content")


@dataclass(frozen=True)
class EngineeringEvaluationResult:
    """Deeply immutable reconstruction of one persisted Engineering Evaluation Result."""

    _content: Mapping[str, Any]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EngineeringEvaluationResult":
        if not isinstance(value, Mapping):
            _fail("engineering_evaluation_result", "must be an object")
        detached = copy.deepcopy(dict(value))
        _validate_eer(detached)
        return cls(_freeze(detached))

    @property
    def evaluation_id(self) -> str:
        return self._content["evaluation_id"]

    @property
    def content_sha256(self) -> str:
        return self._content["eer_content_sha256"]

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._content)

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self._content)
