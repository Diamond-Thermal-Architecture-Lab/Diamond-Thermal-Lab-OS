from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .ids import valid_id, valid_sha256
from .loader import claim_ids, iter_sidecar_json, load_json, read_case_id, require_case, scalar_text, unsafe_reference
from .models import EvidenceRule, ValidationResult, decimal_text


CONFIDENTIALITY_LEVELS = {"public", "internal", "customer-confidential", "restricted"}
EVIDENCE_TYPES = {"measurement", "simulation", "literature", "supplier_claim", "expert_judgment", "production_data", "field_data"}
EVIDENCE_STATUSES = {"draft", "reviewed", "rejected", "deprecated"}
EVIDENCE_LEVELS = {"unverified", "source_documented", "independently_measured", "customer_validated", "production_validated", "field_validated"}
MEASUREMENT_STATUSES = {"planned", "completed", "reviewed", "rejected"}
PREDICTION_STATUSES = {"draft", "comparable", "reviewed", "rejected"}
LEARNING_DISPOSITIONS = {"pending_review", "accepted_for_calibration", "rejected_from_calibration", "information_only"}
ERROR_SOURCES = {"parameter", "model_form", "boundary_condition", "geometry", "manufacturing", "measurement", "operating_condition", "unknown"}


class _Collector:
    def __init__(self, object_type: str, object_id: str, case_id: str) -> None:
        self.object_type, self.object_id, self.case_id = object_type, object_id, case_id
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.rules: list[EvidenceRule] = []

    def fail(self, rule_id: str, finding: str, evidence: str, action: str) -> None:
        self.errors.append(finding)
        self.rules.append(EvidenceRule(rule_id, "FAIL", finding, evidence, action))

    def warn(self, rule_id: str, finding: str, evidence: str, action: str) -> None:
        self.warnings.append(finding)
        self.rules.append(EvidenceRule(rule_id, "WARN", finding, evidence, action))

    def result(self, comparison: dict[str, Any] | None = None) -> ValidationResult:
        return ValidationResult(
            self.object_type,
            self.object_id,
            self.case_id,
            "FAIL" if self.errors else "WARN" if self.warnings else "PASS",
            self.errors,
            self.warnings,
            self.rules,
            comparison,
        )


def _get_record(path: Path) -> dict[str, Any]:
    return load_json(path)


def _text(value: object) -> str:
    return scalar_text(value)


def _list_of_text(value: object) -> list[str]:
    return [item for item in value if isinstance(item, str) and item.strip()] if isinstance(value, list) else []


def _decimal(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _require_fields(data: dict[str, Any], fields: tuple[str, ...], collector: _Collector, family: str) -> None:
    for field in fields:
        if field not in data:
            collector.fail(f"{family}-001", f"Missing required field: {field}", field, "Add the required field.")


def _validate_common(data: dict[str, Any], case_path: Path, collector: _Collector, kind: str, family: str) -> None:
    case_id = read_case_id(case_path)
    if _text(data.get("case_id")) != case_id:
        collector.fail(f"{family}-002", "Object case_id does not match the canonical case.", _text(data.get("case_id")), "Bind the object to this case.")
    if not valid_id(kind, data.get(f"{kind}_id") if kind != "prediction_reality" else data.get("record_id")):
        label = "record_id" if kind == "prediction_reality" else f"{kind}_id"
        collector.fail(f"{family}-003", f"Invalid {label} format.", label, "Use the required case-scoped ID format.")
    confidentiality = _text(data.get("confidentiality_level"))
    if confidentiality not in CONFIDENTIALITY_LEVELS:
        collector.fail(f"{family}-004", "Unknown confidentiality_level.", confidentiality, "Use public, internal, customer-confidential, or restricted.")


def _find_by_id(case_path: Path, folder: str, id_field: str, object_id: str) -> dict[str, Any] | None:
    matches: list[dict[str, Any]] = []
    for path in iter_sidecar_json(case_path, folder):
        try:
            data = load_json(path)
        except ValueError:
            continue
        if _text(data.get(id_field)) == object_id:
            matches.append(data)
    return matches[0] if len(matches) == 1 else None


def validate_evidence(case_path: Path, path: Path) -> ValidationResult:
    case_path = require_case(case_path)
    data = _get_record(path)
    evidence_id = _text(data.get("evidence_id"))
    collector = _Collector("evidence", evidence_id, read_case_id(case_path))
    _require_fields(data, ("evidence_format_version", "evidence_id", "case_id", "title", "evidence_type", "status", "evidence_level", "source", "method_summary", "applicability", "uncertainty_summary", "supports_claim_ids", "contradicts_claim_ids", "measurement_reference_ids", "public_summary", "confidentiality_level", "reviewed_by", "review_notes"), collector, "EVIDENCE-SCHEMA")
    _validate_common(data, case_path, collector, "evidence", "EVIDENCE-SCHEMA")
    evidence_type, status, level = _text(data.get("evidence_type")), _text(data.get("status")), _text(data.get("evidence_level"))
    if evidence_type not in EVIDENCE_TYPES:
        collector.fail("EVIDENCE-SCHEMA-005", "Unknown evidence_type.", evidence_type, "Use an allowed evidence type.")
    if status not in EVIDENCE_STATUSES:
        collector.fail("EVIDENCE-SCHEMA-006", "Unknown evidence status.", status, "Use draft, reviewed, rejected, or deprecated.")
    if level not in EVIDENCE_LEVELS:
        collector.fail("EVIDENCE-SCHEMA-007", "Unknown evidence_level.", level, "Use an allowed evidence level.")
    if status == "reviewed" and not _text(data.get("reviewed_by")):
        collector.fail("EVIDENCE-REVIEW-001", "Reviewed evidence requires human-entered reviewed_by.", "reviewed_by", "Add the reviewer declaration; identity is not verified by this system.")
    if evidence_type == "supplier_claim" and level not in {"unverified", "source_documented"}:
        collector.fail("EVIDENCE-LEVEL-001", "Supplier claim cannot be promoted beyond source_documented without independent evidence.", level, "Use unverified/source_documented or create independent evidence.")
    method_source = f"{data.get('source', '')} {_text(data.get('method_summary'))}".lower()
    if evidence_type == "simulation" and ("model" not in method_source or "input" not in method_source):
        collector.warn("EVIDENCE-METHOD-001", "Simulation evidence should identify model and input basis.", "source/method_summary", "Document the model and controlled input basis.")
    if evidence_type in {"measurement", "production_data", "field_data"} and not _text(data.get("method_summary")):
        collector.fail("EVIDENCE-METHOD-002", "Measurement-derived evidence requires a data-collection method.", "method_summary", "Document the collection method.")
    known_claims = claim_ids(case_path)
    supports, contradicts = _list_of_text(data.get("supports_claim_ids")), _list_of_text(data.get("contradicts_claim_ids"))
    overlap = set(supports) & set(contradicts)
    if overlap:
        collector.fail("EVIDENCE-CLAIM-001", "One evidence object cannot support and contradict the same claim.", ", ".join(sorted(overlap)), "Separate or revise the claim relationship.")
    for claim_id in sorted(set(supports + contradicts) - known_claims):
        collector.fail("EVIDENCE-CLAIM-002", f"Unknown Claim Ledger ID: {claim_id}", claim_id, "Use an existing 10_claim_ledger.yml claim_id.")
    for measurement_id in _list_of_text(data.get("measurement_reference_ids")):
        if _find_by_id(case_path, "measurements", "measurement_id", measurement_id) is None:
            collector.fail("EVIDENCE-REFERENCE-001", f"Unknown Measurement Reference ID: {measurement_id}", measurement_id, "Use an existing Measurement Reference or leave the list empty.")
    source = data.get("source")
    source_reference = source.get("reference") if isinstance(source, dict) else source
    source_hash = source.get("sha256") if isinstance(source, dict) else None
    if source_hash is not None and not valid_sha256(source_hash):
        collector.fail("EVIDENCE-SOURCE-001", "Invalid source SHA256.", "source.sha256", "Use a lowercase 64-character SHA256 or null.")
    if unsafe_reference(source_reference) or unsafe_reference(data.get("public_summary")):
        collector.fail("EVIDENCE-CONF-001", "Unsafe absolute path or credential-like reference detected.", "source/public_summary", "Use an opaque controlled reference without credentials or local paths.")
    if status == "draft":
        collector.warn("EVIDENCE-STATUS-001", "Draft evidence is not reviewed or technically validated.", "status: draft", "Complete human review when evidence is ready.")
    return collector.result()


def validate_measurement_reference(case_path: Path, path: Path) -> ValidationResult:
    case_path = require_case(case_path)
    data = _get_record(path)
    measurement_id = _text(data.get("measurement_id"))
    collector = _Collector("measurement_reference", measurement_id, read_case_id(case_path))
    _require_fields(data, ("measurement_format_version", "measurement_id", "case_id", "evidence_id", "status", "quantity", "value", "unit", "sample_id", "method", "operating_conditions", "uncertainty", "raw_data_reference", "raw_data_sha256", "confidentiality_level", "reviewed_by", "review_notes"), collector, "MEASUREMENT-SCHEMA")
    _validate_common(data, case_path, collector, "measurement", "MEASUREMENT-SCHEMA")
    status = _text(data.get("status"))
    if status not in MEASUREMENT_STATUSES:
        collector.fail("MEASUREMENT-SCHEMA-005", "Unknown measurement status.", status, "Use planned, completed, reviewed, or rejected.")
    sample_id = _text(data.get("sample_id"))
    if not sample_id or not sample_id.startswith("ANON-"):
        collector.fail("MEASUREMENT-PRIVACY-001", "sample_id must use an anonymized ANON- identifier.", sample_id, "Use an anonymized sample identifier.")
    evidence_id = _text(data.get("evidence_id"))
    evidence = _find_by_id(case_path, "evidence", "evidence_id", evidence_id)
    if evidence is None:
        collector.fail("MEASUREMENT-REFERENCE-001", "Measurement references an unknown or duplicate evidence_id.", evidence_id, "Create one matching Evidence Object first.")
    elif _text(evidence.get("evidence_type")) not in {"measurement", "production_data", "field_data"}:
        collector.fail("MEASUREMENT-REFERENCE-002", "Referenced Evidence Object is not measurement-compatible.", _text(evidence.get("evidence_type")), "Use measurement, production_data, or field_data evidence.")
    value, unit = _decimal(data.get("value")), _text(data.get("unit"))
    if status in {"completed", "reviewed"} and (value is None or not unit):
        collector.fail("MEASUREMENT-VALUE-001", "Completed or reviewed measurement requires numeric value and unit.", "value/unit", "Add a numeric value and unit.")
    if status == "planned" and value is None:
        collector.warn("MEASUREMENT-STATUS-001", "Planned measurement has no measured value yet.", "status: planned", "Capture and review the measurement before comparison.")
    if status == "reviewed" and not _text(data.get("reviewed_by")):
        collector.fail("MEASUREMENT-REVIEW-001", "Reviewed measurement requires human-entered reviewed_by.", "reviewed_by", "Add reviewer declaration; identity is not verified.")
    raw_hash = data.get("raw_data_sha256")
    if raw_hash is not None and not valid_sha256(raw_hash):
        collector.fail("MEASUREMENT-SOURCE-001", "Invalid raw_data_sha256.", "raw_data_sha256", "Use a lowercase 64-character SHA256 or null.")
    if status == "reviewed" and raw_hash is None:
        collector.warn("MEASUREMENT-SOURCE-002", "Reviewed measurement normally includes raw_data_sha256.", "raw_data_sha256", "Record the controlled raw-data hash when available.")
    uncertainty = data.get("uncertainty")
    if not isinstance(uncertainty, dict) or not _text(uncertainty.get("basis")):
        collector.fail("MEASUREMENT-UNCERTAINTY-001", "Measurement uncertainty requires an explicit basis and limitation.", "uncertainty", "Document uncertainty basis even when numeric uncertainty is unavailable.")
    elif uncertainty.get("numeric_value") is None:
        collector.warn("MEASUREMENT-UNCERTAINTY-002", "Measurement has no numeric uncertainty; basis remains qualitative.", "uncertainty", "Add numeric uncertainty when available.")
    if unsafe_reference(data.get("raw_data_reference")):
        collector.fail("MEASUREMENT-CONF-001", "Unsafe absolute path or credential-like raw data reference detected.", "raw_data_reference", "Use an opaque controlled reference.")
    return collector.result()


def validate_prediction_reality_record(case_path: Path, path: Path) -> ValidationResult:
    case_path = require_case(case_path)
    data = _get_record(path)
    record_id = _text(data.get("record_id"))
    collector = _Collector("prediction_reality", record_id, read_case_id(case_path))
    _require_fields(data, ("prediction_reality_format_version", "record_id", "case_id", "status", "quantity", "prediction", "reality_measurement_id", "prediction_evidence_ids", "comparison_context", "candidate_error_sources", "decision_impact", "learning_disposition", "confidentiality_level", "reviewed_by", "review_notes"), collector, "PREDICTION-SCHEMA")
    _validate_common(data, case_path, collector, "prediction_reality", "PREDICTION-SCHEMA")
    status, disposition = _text(data.get("status")), _text(data.get("learning_disposition"))
    if status not in PREDICTION_STATUSES:
        collector.fail("PREDICTION-SCHEMA-005", "Unknown prediction-reality status.", status, "Use draft, comparable, reviewed, or rejected.")
    if disposition not in LEARNING_DISPOSITIONS:
        collector.fail("PREDICTION-SCHEMA-006", "Unknown learning_disposition.", disposition, "Use an allowed learning disposition.")
    sources = _list_of_text(data.get("candidate_error_sources"))
    if not sources or any(source not in ERROR_SOURCES for source in sources):
        collector.fail("PREDICTION-SCHEMA-007", "candidate_error_sources contains an unknown value.", ", ".join(sources), "Use only supported candidate error sources.")
    prediction = data.get("prediction")
    if not isinstance(prediction, dict):
        collector.fail("PREDICTION-SCHEMA-008", "prediction must be an object.", "prediction", "Add prediction value, unit, model, and input basis.")
        return collector.result()
    for field in ("value", "unit", "lower_bound", "upper_bound", "model_name", "model_version", "input_reference", "input_sha256"):
        if field not in prediction:
            collector.fail("PREDICTION-SCHEMA-009", f"Prediction missing required field: {field}", field, "Add the required prediction field.")
    if prediction.get("input_sha256") is not None and not valid_sha256(prediction.get("input_sha256")):
        collector.fail("PREDICTION-SOURCE-001", "Invalid prediction input_sha256.", "prediction.input_sha256", "Use a lowercase 64-character SHA256 or null.")
    if unsafe_reference(prediction.get("input_reference")):
        collector.fail("PREDICTION-CONF-001", "Unsafe absolute path or credential-like prediction input reference detected.", "prediction.input_reference", "Use an opaque controlled input reference.")
    measurement_id = _text(data.get("reality_measurement_id"))
    measurement = _find_by_id(case_path, "measurements", "measurement_id", measurement_id)
    if measurement is None:
        collector.fail("PREDICTION-REFERENCE-001", "Prediction-reality record references an unknown or duplicate measurement_id.", measurement_id, "Create one matching Measurement Reference first.")
    for evidence_id in _list_of_text(data.get("prediction_evidence_ids")):
        if _find_by_id(case_path, "evidence", "evidence_id", evidence_id) is None:
            collector.fail("PREDICTION-REFERENCE-002", f"Unknown prediction evidence ID: {evidence_id}", evidence_id, "Use an existing Evidence Object.")
    if disposition == "accepted_for_calibration" and (status != "reviewed" or not _text(data.get("reviewed_by"))):
        collector.fail("PREDICTION-LEARNING-001", "accepted_for_calibration requires explicit reviewed human record.", "learning_disposition", "Keep pending_review until human review is complete.")
    prediction_value, prediction_unit = _decimal(prediction.get("value")), _text(prediction.get("unit"))
    if prediction_value is None or not prediction_unit:
        collector.warn("PREDICTION-COMPARISON-001", "Prediction is incomplete; no numeric comparison was calculated.", "prediction.value/unit", "Add prediction value and exact unit when available.")
    comparison = _comparison(data, prediction, measurement, collector)
    return collector.result(comparison)


def _comparison(data: dict[str, Any], prediction: dict[str, Any], measurement: dict[str, Any] | None, collector: _Collector) -> dict[str, Any] | None:
    if measurement is None:
        return None
    record_quantity, measurement_quantity = _text(data.get("quantity")), _text(measurement.get("quantity"))
    if record_quantity and measurement_quantity and record_quantity != measurement_quantity:
        collector.fail("PREDICTION-COMPARISON-002", "Prediction and measurement quantities do not match.", f"{record_quantity} != {measurement_quantity}", "Use the same quantity before comparison.")
        return None
    prediction_value, reality_value = _decimal(prediction.get("value")), _decimal(measurement.get("value"))
    prediction_unit, reality_unit = _text(prediction.get("unit")), _text(measurement.get("unit"))
    if reality_value is None:
        collector.warn("PREDICTION-COMPARISON-003", "Referenced measurement has no reality value; no comparison was calculated.", "measurement.value", "Complete the measurement first.")
        return None
    if prediction_value is None or not prediction_unit:
        return None
    if prediction_unit != reality_unit:
        collector.warn("PREDICTION-COMPARISON-004", "Prediction and measurement units do not match; no numeric comparison was calculated.", f"{prediction_unit} != {reality_unit}", "Use identical unit strings; unit conversion is out of scope.")
        return {"record_id": _text(data.get("record_id")), "comparable": False, "reason": "unit_mismatch"}
    signed = reality_value - prediction_value
    absolute = abs(signed)
    relative: Decimal | None = None
    if reality_value == 0:
        collector.warn("PREDICTION-COMPARISON-005", "Reality value is zero; relative_error_percent is unavailable.", "measurement.value: 0", "Use signed and absolute error only.")
    else:
        relative = absolute / abs(reality_value) * Decimal("100")
    lower, upper = _decimal(prediction.get("lower_bound")), _decimal(prediction.get("upper_bound"))
    interval = None if lower is None or upper is None else lower <= reality_value <= upper
    return {
        "record_id": _text(data.get("record_id")),
        "comparable": True,
        "quantity": _text(data.get("quantity")),
        "unit": reality_unit,
        "reality_value": decimal_text(reality_value),
        "prediction_value": decimal_text(prediction_value),
        "signed_error": decimal_text(signed),
        "absolute_error": decimal_text(absolute),
        "relative_error_percent": decimal_text(relative),
        "reality_within_prediction_interval": interval,
    }
