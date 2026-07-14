from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .ids import valid_id, valid_sha256
from .loader import claim_ids, iter_sidecar_json, load_json, read_case_id, require_case, scalar_text, unsafe_reference
from .models import EvidenceRule, ValidationResult


SUPPORTED_FORMAT_VERSION = "1.0"
CONFIDENTIALITY_LEVELS = {"public", "internal", "customer-confidential", "restricted"}
EVIDENCE_TYPES = {"measurement", "simulation", "literature", "supplier_claim", "expert_judgment", "production_data", "field_data"}
EVIDENCE_STATUSES = {"draft", "reviewed", "rejected", "deprecated"}
EVIDENCE_LEVELS = {"unverified", "source_documented", "independently_measured", "customer_validated", "production_validated", "field_validated"}
MEASUREMENT_STATUSES = {"planned", "completed", "reviewed", "rejected"}
REQUIRED_EVIDENCE_FIELDS = (
    "evidence_format_version", "evidence_id", "case_id", "title", "evidence_type", "status", "evidence_level", "source", "method_summary", "applicability", "uncertainty_summary", "supports_claim_ids", "contradicts_claim_ids", "measurement_reference_ids", "public_summary", "confidentiality_level", "reviewed_by", "review_notes",
)
REQUIRED_MEASUREMENT_FIELDS = (
    "measurement_format_version", "measurement_id", "case_id", "evidence_id", "status", "quantity", "value", "unit", "sample_id", "method", "operating_conditions", "uncertainty", "raw_data_reference", "raw_data_sha256", "confidentiality_level", "reviewed_by", "review_notes",
)


class ValidationCollector:
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


def text(value: object) -> str:
    return scalar_text(value)


def decimal_value(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def is_number_or_null(value: object) -> bool:
    return value is None or (not isinstance(value, bool) and decimal_value(value) is not None)


def load_validation_data(case_path: Path, path: Path, object_type: str, id_field: str) -> tuple[Path, dict[str, Any] | None, ValidationCollector]:
    """Convert normal user-file JSON problems into a structured FAIL result."""
    case_path = require_case(case_path)
    case_id = read_case_id(case_path)
    fallback_id = path.stem if path.suffix.lower() == ".json" else "unknown"
    try:
        data = load_json(path)
    except (OSError, ValueError) as exc:
        collector = ValidationCollector(object_type, fallback_id, case_id)
        collector.fail(f"{object_type.upper().replace('_', '-')}-SCHEMA-000", str(exc), path.name, "Correct the JSON object and retry validation.")
        return case_path, None, collector
    return case_path, data, ValidationCollector(object_type, text(data.get(id_field)), case_id)


def require_fields(data: dict[str, Any], fields: tuple[str, ...], collector: ValidationCollector, family: str) -> None:
    for field in fields:
        if field not in data:
            collector.fail(f"{family}-001", f"Missing required field: {field}", field, "Add the required field.")


def reject_extra_fields(data: dict[str, Any], fields: tuple[str, ...], collector: ValidationCollector, rule_id: str) -> None:
    for field in sorted(set(data) - set(fields)):
        collector.fail(rule_id, f"Unexpected field not permitted by the schema contract: {field}", field, "Remove the unexpected field.")


def validate_string_fields(data: dict[str, Any], fields: tuple[str, ...], collector: ValidationCollector, rule_id: str, *, nonempty: bool = False) -> None:
    for field in fields:
        value = data.get(field)
        if not isinstance(value, str):
            collector.fail(rule_id, f"Field must be a string: {field}", field, "Use a JSON string.")
        elif nonempty and not value.strip():
            collector.fail(rule_id, f"Field must not be empty: {field}", field, "Provide a non-empty value.")


def validate_string_array(data: dict[str, Any], field: str, collector: ValidationCollector, rule_id: str) -> list[str]:
    value = data.get(field)
    if not isinstance(value, list):
        collector.fail(rule_id, f"Field must be an array: {field}", field, "Use a JSON array of non-empty strings.")
        return []
    values: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            collector.fail(rule_id, f"Array contains a non-empty string requirement violation: {field}", field, "Use non-empty string IDs only.")
        else:
            values.append(item.strip())
    return values


def validate_common(data: dict[str, Any], case_path: Path, collector: ValidationCollector, kind: str, family: str) -> None:
    case_id = read_case_id(case_path)
    if text(data.get("case_id")) != case_id:
        collector.fail(f"{family}-002", "Object case_id does not match the canonical case.", text(data.get("case_id")), "Bind the object to this case.")
    identifier = data.get("record_id") if kind == "prediction_reality" else data.get(f"{kind}_id")
    if not valid_id(kind, identifier):
        label = "record_id" if kind == "prediction_reality" else f"{kind}_id"
        collector.fail(f"{family}-003", f"Invalid {label} format.", label, "Use the required case-scoped ID format.")
    confidentiality = text(data.get("confidentiality_level"))
    if confidentiality not in CONFIDENTIALITY_LEVELS:
        collector.fail(f"{family}-004", "Unknown confidentiality_level.", confidentiality, "Use public, internal, customer-confidential, or restricted.")


def find_by_id(case_path: Path, folder: str, id_field: str, object_id: str) -> dict[str, Any] | None:
    matches: list[dict[str, Any]] = []
    for candidate in iter_sidecar_json(case_path, folder):
        try:
            data = load_json(candidate)
        except ValueError:
            continue
        if text(data.get(id_field)) == object_id:
            matches.append(data)
    return matches[0] if len(matches) == 1 else None


def validate_evidence(case_path: Path, path: Path) -> ValidationResult:
    case_path, data, collector = load_validation_data(case_path, path, "evidence", "evidence_id")
    if data is None:
        return collector.result()
    require_fields(data, REQUIRED_EVIDENCE_FIELDS, collector, "EVIDENCE-SCHEMA")
    reject_extra_fields(data, REQUIRED_EVIDENCE_FIELDS, collector, "EVIDENCE-SCHEMA-010")
    validate_string_fields(data, ("evidence_format_version", "evidence_id", "case_id", "title", "evidence_type", "status", "evidence_level", "method_summary", "applicability", "uncertainty_summary", "public_summary", "confidentiality_level", "reviewed_by", "review_notes"), collector, "EVIDENCE-SCHEMA-008")
    validate_common(data, case_path, collector, "evidence", "EVIDENCE-SCHEMA")
    if data.get("evidence_format_version") != SUPPORTED_FORMAT_VERSION:
        collector.fail("EVIDENCE-SCHEMA-009", "Unsupported evidence_format_version.", text(data.get("evidence_format_version")), f"Use {SUPPORTED_FORMAT_VERSION}.")
    evidence_type, status, level = text(data.get("evidence_type")), text(data.get("status")), text(data.get("evidence_level"))
    if evidence_type not in EVIDENCE_TYPES:
        collector.fail("EVIDENCE-SCHEMA-005", "Unknown evidence_type.", evidence_type, "Use an allowed evidence type.")
    if status not in EVIDENCE_STATUSES:
        collector.fail("EVIDENCE-SCHEMA-006", "Unknown evidence status.", status, "Use draft, reviewed, rejected, or deprecated.")
    if level not in EVIDENCE_LEVELS:
        collector.fail("EVIDENCE-SCHEMA-007", "Unknown evidence_level.", level, "Use an allowed evidence level.")
    supports = validate_string_array(data, "supports_claim_ids", collector, "EVIDENCE-CLAIM-003")
    contradicts = validate_string_array(data, "contradicts_claim_ids", collector, "EVIDENCE-CLAIM-003")
    measurement_ids = validate_string_array(data, "measurement_reference_ids", collector, "EVIDENCE-REFERENCE-002")
    if status == "reviewed" and not text(data.get("reviewed_by")):
        collector.fail("EVIDENCE-REVIEW-001", "Reviewed evidence requires human-entered reviewed_by.", "reviewed_by", "Add the reviewer declaration; identity is not verified by this system.")
    if evidence_type == "supplier_claim" and level not in {"unverified", "source_documented"}:
        collector.fail("EVIDENCE-LEVEL-001", "Supplier claim cannot be promoted beyond source_documented without independent evidence.", level, "Use unverified/source_documented or create independent evidence.")
    source = data.get("source")
    if not isinstance(source, dict) or set(source) != {"reference", "sha256"}:
        collector.fail("EVIDENCE-SOURCE-002", "source must contain only reference and sha256.", "source", "Use the documented source object.")
        source_reference, source_hash = "", None
    else:
        source_reference, source_hash = source.get("reference"), source.get("sha256")
        if not isinstance(source_reference, str):
            collector.fail("EVIDENCE-SOURCE-003", "source.reference must be a string.", "source.reference", "Use an opaque controlled reference.")
        if source_hash is not None and not valid_sha256(source_hash):
            collector.fail("EVIDENCE-SOURCE-001", "Invalid source SHA256.", "source.sha256", "Use a lowercase 64-character SHA256 or null.")
    if status == "reviewed" and not text(source_reference):
        collector.fail("EVIDENCE-SOURCE-004", "Reviewed evidence requires a non-empty source reference.", "source.reference", "Record an opaque controlled source reference.")
    method_source = f"{source_reference} {text(data.get('method_summary'))}".lower()
    if evidence_type == "simulation" and ("model" not in method_source or "input" not in method_source):
        collector.warn("EVIDENCE-METHOD-001", "Simulation evidence should identify model and input basis.", "source/method_summary", "Document the model and controlled input basis.")
    if evidence_type in {"measurement", "production_data", "field_data"} and not text(data.get("method_summary")):
        collector.fail("EVIDENCE-METHOD-002", "Measurement-derived evidence requires a data-collection method.", "method_summary", "Document the collection method.")
    known_claims = claim_ids(case_path)
    overlap = set(supports) & set(contradicts)
    if overlap:
        collector.fail("EVIDENCE-CLAIM-001", "One evidence object cannot support and contradict the same claim.", ", ".join(sorted(overlap)), "Separate or revise the claim relationship.")
    for claim_id in sorted(set(supports + contradicts) - known_claims):
        collector.fail("EVIDENCE-CLAIM-002", f"Unknown Claim Ledger ID: {claim_id}", claim_id, "Use an existing 10_claim_ledger.yml claim_id.")
    for measurement_id in measurement_ids:
        if not valid_id("measurement", measurement_id):
            collector.fail("EVIDENCE-REFERENCE-003", f"Invalid Measurement Reference ID: {measurement_id}", measurement_id, "Use MSR-### format.")
        elif find_by_id(case_path, "measurements", "measurement_id", measurement_id) is None:
            collector.fail("EVIDENCE-REFERENCE-001", f"Unknown Measurement Reference ID: {measurement_id}", measurement_id, "Use an existing Measurement Reference or leave the list empty.")
    if unsafe_reference(source_reference) or unsafe_reference(data.get("public_summary")):
        collector.fail("EVIDENCE-CONF-001", "Unsafe absolute path or credential-like reference detected.", "source/public_summary", "Use an opaque controlled reference without credentials or local paths.")
    if status == "draft":
        collector.warn("EVIDENCE-STATUS-001", "Draft evidence is not reviewed or technically validated.", "status: draft", "Complete human review when evidence is ready.")
    return collector.result()


def validate_measurement_reference(case_path: Path, path: Path) -> ValidationResult:
    case_path, data, collector = load_validation_data(case_path, path, "measurement_reference", "measurement_id")
    if data is None:
        return collector.result()
    require_fields(data, REQUIRED_MEASUREMENT_FIELDS, collector, "MEASUREMENT-SCHEMA")
    reject_extra_fields(data, REQUIRED_MEASUREMENT_FIELDS, collector, "MEASUREMENT-SCHEMA-010")
    validate_string_fields(data, ("measurement_format_version", "measurement_id", "case_id", "evidence_id", "status", "quantity", "sample_id", "method", "operating_conditions", "raw_data_reference", "confidentiality_level", "reviewed_by", "review_notes"), collector, "MEASUREMENT-SCHEMA-008")
    validate_common(data, case_path, collector, "measurement", "MEASUREMENT-SCHEMA")
    if data.get("measurement_format_version") != SUPPORTED_FORMAT_VERSION:
        collector.fail("MEASUREMENT-SCHEMA-009", "Unsupported measurement_format_version.", text(data.get("measurement_format_version")), f"Use {SUPPORTED_FORMAT_VERSION}.")
    status = text(data.get("status"))
    if status not in MEASUREMENT_STATUSES:
        collector.fail("MEASUREMENT-SCHEMA-005", "Unknown measurement status.", status, "Use planned, completed, reviewed, or rejected.")
    evidence_id = text(data.get("evidence_id"))
    if not valid_id("evidence", evidence_id):
        collector.fail("MEASUREMENT-REFERENCE-003", "Invalid evidence_id format.", evidence_id, "Use EVD-### format.")
    sample_id = text(data.get("sample_id"))
    if not sample_id or not sample_id.startswith("ANON-") or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for character in sample_id[5:]):
        collector.fail("MEASUREMENT-PRIVACY-001", "sample_id must use an anonymized ANON- identifier.", sample_id, "Use an anonymized sample identifier.")
    value, unit = decimal_value(data.get("value")), data.get("unit")
    if not is_number_or_null(data.get("value")):
        collector.fail("MEASUREMENT-VALUE-002", "value must be numeric or null, not bool or text.", "value", "Use a JSON number or null.")
    if unit is not None and not isinstance(unit, str):
        collector.fail("MEASUREMENT-VALUE-003", "unit must be a string or null.", "unit", "Use a unit string or null.")
    if status in {"completed", "reviewed"} and (value is None or not text(unit)):
        collector.fail("MEASUREMENT-VALUE-001", "Completed or reviewed measurement requires numeric value and unit.", "value/unit", "Add a numeric value and unit.")
    if status == "planned" and value is None:
        collector.warn("MEASUREMENT-STATUS-001", "Planned measurement has no measured value yet.", "status: planned", "Capture and review the measurement before comparison.")
    evidence = find_by_id(case_path, "evidence", "evidence_id", evidence_id) if valid_id("evidence", evidence_id) else None
    if evidence is None:
        collector.fail("MEASUREMENT-REFERENCE-001", "Measurement references an unknown or duplicate evidence_id.", evidence_id, "Create one matching Evidence Object first.")
    elif text(evidence.get("evidence_type")) not in {"measurement", "production_data", "field_data"}:
        collector.fail("MEASUREMENT-REFERENCE-002", "Referenced Evidence Object is not measurement-compatible.", text(evidence.get("evidence_type")), "Use measurement, production_data, or field_data evidence.")
    if status == "reviewed" and not text(data.get("reviewed_by")):
        collector.fail("MEASUREMENT-REVIEW-001", "Reviewed measurement requires human-entered reviewed_by.", "reviewed_by", "Add reviewer declaration; identity is not verified.")
    raw_hash = data.get("raw_data_sha256")
    if raw_hash is not None and not valid_sha256(raw_hash):
        collector.fail("MEASUREMENT-SOURCE-001", "Invalid raw_data_sha256.", "raw_data_sha256", "Use a lowercase 64-character SHA256 or null.")
    if status == "reviewed" and raw_hash is None:
        collector.warn("MEASUREMENT-SOURCE-002", "Reviewed measurement normally includes raw_data_sha256.", "raw_data_sha256", "Record the controlled raw-data hash when available.")
    uncertainty = data.get("uncertainty")
    if not isinstance(uncertainty, dict) or set(uncertainty) != {"numeric_value", "unit", "basis"}:
        collector.fail("MEASUREMENT-UNCERTAINTY-001", "uncertainty must contain numeric_value, unit, and basis.", "uncertainty", "Use the documented uncertainty object.")
    else:
        if not is_number_or_null(uncertainty.get("numeric_value")):
            collector.fail("MEASUREMENT-UNCERTAINTY-003", "uncertainty.numeric_value must be numeric or null.", "uncertainty.numeric_value", "Use a JSON number or null.")
        if uncertainty.get("unit") is not None and not isinstance(uncertainty.get("unit"), str):
            collector.fail("MEASUREMENT-UNCERTAINTY-004", "uncertainty.unit must be a string or null.", "uncertainty.unit", "Use a unit string or null.")
        if not text(uncertainty.get("basis")):
            collector.fail("MEASUREMENT-UNCERTAINTY-002", "Measurement uncertainty requires an explicit basis and limitation.", "uncertainty.basis", "Document uncertainty basis even when numeric uncertainty is unavailable.")
        elif uncertainty.get("numeric_value") is None:
            collector.warn("MEASUREMENT-UNCERTAINTY-005", "Measurement has no numeric uncertainty; basis remains qualitative.", "uncertainty", "Add numeric uncertainty when available.")
    if unsafe_reference(data.get("raw_data_reference")):
        collector.fail("MEASUREMENT-CONF-001", "Unsafe absolute path or credential-like raw data reference detected.", "raw_data_reference", "Use an opaque controlled reference.")
    return collector.result()


def validate_prediction_reality_record(case_path: Path, path: Path) -> ValidationResult:
    """Compatibility import; Prediction-Reality validation lives in its focused package."""
    from labos.prediction_reality.validator import validate_prediction_reality_record as validate

    return validate(case_path, path)
