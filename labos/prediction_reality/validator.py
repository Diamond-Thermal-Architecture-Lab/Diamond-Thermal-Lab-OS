from __future__ import annotations

from pathlib import Path
from typing import Any

from labos.evidence.ids import valid_id, valid_sha256
from labos.evidence.models import ValidationResult
from labos.evidence.validator import (
    SUPPORTED_FORMAT_VERSION,
    ValidationCollector,
    decimal_value,
    find_by_id,
    is_number_or_null,
    load_validation_data,
    require_fields,
    reject_extra_fields,
    text,
    validate_common,
    validate_string_array,
    validate_string_fields,
)
from labos.evidence.loader import unsafe_reference

from .comparison import compare_prediction_to_measurement


PREDICTION_STATUSES = {"draft", "comparable", "reviewed", "rejected"}
LEARNING_DISPOSITIONS = {"pending_review", "accepted_for_calibration", "rejected_from_calibration", "information_only"}
ERROR_SOURCES = {"parameter", "model_form", "boundary_condition", "geometry", "manufacturing", "measurement", "operating_condition", "unknown"}
REQUIRED_PREDICTION_FIELDS = (
    "prediction_reality_format_version", "record_id", "case_id", "status", "quantity", "prediction", "reality_measurement_id", "prediction_evidence_ids", "comparison_context", "candidate_error_sources", "decision_impact", "learning_disposition", "confidentiality_level", "reviewed_by", "review_notes",
)
PREDICTION_OBJECT_FIELDS = ("value", "unit", "lower_bound", "upper_bound", "model_name", "model_version", "input_reference", "input_sha256")


def validate_prediction_reality_record(case_path: Path, path: Path) -> ValidationResult:
    case_path, data, collector = load_validation_data(case_path, path, "prediction_reality", "record_id")
    if data is None:
        return collector.result()
    require_fields(data, REQUIRED_PREDICTION_FIELDS, collector, "PREDICTION-SCHEMA")
    reject_extra_fields(data, REQUIRED_PREDICTION_FIELDS, collector, "PREDICTION-SCHEMA-015")
    validate_string_fields(data, ("prediction_reality_format_version", "record_id", "case_id", "status", "quantity", "reality_measurement_id", "comparison_context", "decision_impact", "learning_disposition", "confidentiality_level", "reviewed_by", "review_notes"), collector, "PREDICTION-SCHEMA-010")
    validate_common(data, case_path, collector, "prediction_reality", "PREDICTION-SCHEMA")
    if data.get("prediction_reality_format_version") != SUPPORTED_FORMAT_VERSION:
        collector.fail("PREDICTION-SCHEMA-011", "Unsupported prediction_reality_format_version.", text(data.get("prediction_reality_format_version")), f"Use {SUPPORTED_FORMAT_VERSION}.")
    status, disposition = text(data.get("status")), text(data.get("learning_disposition"))
    if status not in PREDICTION_STATUSES:
        collector.fail("PREDICTION-SCHEMA-005", "Unknown prediction-reality status.", status, "Use draft, comparable, reviewed, or rejected.")
    if disposition not in LEARNING_DISPOSITIONS:
        collector.fail("PREDICTION-SCHEMA-006", "Unknown learning_disposition.", disposition, "Use an allowed learning disposition.")
    sources = validate_string_array(data, "candidate_error_sources", collector, "PREDICTION-SCHEMA-007")
    if not sources or any(source not in ERROR_SOURCES for source in sources):
        collector.fail("PREDICTION-SCHEMA-008", "candidate_error_sources contains an unknown value.", ", ".join(sources), "Use only supported candidate error sources.")
    evidence_ids = validate_string_array(data, "prediction_evidence_ids", collector, "PREDICTION-REFERENCE-003")
    measurement_id = text(data.get("reality_measurement_id"))
    if not valid_id("measurement", measurement_id):
        collector.fail("PREDICTION-REFERENCE-004", "Invalid reality_measurement_id format.", measurement_id, "Use MSR-### format.")
    measurement = find_by_id(case_path, "measurements", "measurement_id", measurement_id) if valid_id("measurement", measurement_id) else None
    if measurement is None:
        collector.fail("PREDICTION-REFERENCE-001", "Prediction-reality record references an unknown or duplicate measurement_id.", measurement_id, "Create one matching Measurement Reference first.")
    for evidence_id in evidence_ids:
        if not valid_id("evidence", evidence_id):
            collector.fail("PREDICTION-REFERENCE-005", f"Invalid prediction evidence ID: {evidence_id}", evidence_id, "Use EVD-### format.")
        elif find_by_id(case_path, "evidence", "evidence_id", evidence_id) is None:
            collector.fail("PREDICTION-REFERENCE-002", f"Unknown prediction evidence ID: {evidence_id}", evidence_id, "Use an existing Evidence Object.")
    prediction = data.get("prediction")
    if not isinstance(prediction, dict) or set(prediction) != set(PREDICTION_OBJECT_FIELDS):
        collector.fail("PREDICTION-SCHEMA-009", "prediction must contain exactly the documented prediction fields.", "prediction", "Use the complete prediction object.")
        return collector.result()
    for field in ("model_name", "model_version", "input_reference"):
        if not isinstance(prediction.get(field), str) or not text(prediction.get(field)):
            collector.fail("PREDICTION-SCHEMA-012", f"prediction.{field} must be a non-empty string.", field, "Provide the controlled model/input metadata.")
    for field in ("value", "lower_bound", "upper_bound"):
        if not is_number_or_null(prediction.get(field)):
            collector.fail("PREDICTION-SCHEMA-013", f"prediction.{field} must be numeric or null, not bool or text.", field, "Use a JSON number or null.")
    if prediction.get("unit") is not None and not isinstance(prediction.get("unit"), str):
        collector.fail("PREDICTION-SCHEMA-014", "prediction.unit must be a string or null.", "prediction.unit", "Use a unit string or null.")
    if prediction.get("input_sha256") is not None and not valid_sha256(prediction.get("input_sha256")):
        collector.fail("PREDICTION-SOURCE-001", "Invalid prediction input_sha256.", "prediction.input_sha256", "Use a lowercase 64-character SHA256 or null.")
    if unsafe_reference(prediction.get("input_reference")):
        collector.fail("PREDICTION-CONF-001", "Unsafe absolute path or credential-like prediction input reference detected.", "prediction.input_reference", "Use an opaque controlled input reference.")
    lower, upper = decimal_value(prediction.get("lower_bound")), decimal_value(prediction.get("upper_bound"))
    if lower is not None and upper is not None and lower > upper:
        collector.fail("PREDICTION-COMPARISON-006", "prediction.lower_bound must not exceed prediction.upper_bound.", "prediction bounds", "Correct the prediction interval.")
    prediction_value, prediction_unit = decimal_value(prediction.get("value")), text(prediction.get("unit"))
    usable_prediction = prediction_value is not None and bool(prediction_unit)
    if status in {"comparable", "reviewed"} and not usable_prediction:
        collector.fail("PREDICTION-COMPARISON-007", "Comparable or reviewed record requires prediction value and unit.", "prediction.value/unit", "Provide a usable prediction before comparison.")
    elif not usable_prediction:
        collector.warn("PREDICTION-COMPARISON-001", "Prediction is incomplete; no numeric comparison was calculated.", "prediction.value/unit", "Add prediction value and exact unit when available.")
    if status == "reviewed" and not text(data.get("reviewed_by")):
        collector.fail("PREDICTION-REVIEW-001", "Reviewed prediction-reality record requires human-entered reviewed_by.", "reviewed_by", "Add reviewer declaration; identity is not verified.")
    if disposition == "accepted_for_calibration" and (status != "reviewed" or not text(data.get("reviewed_by"))):
        collector.fail("PREDICTION-LEARNING-001", "accepted_for_calibration requires explicit reviewed human record.", "learning_disposition", "Keep pending_review until human review is complete.")
    comparison = compare_prediction_to_measurement(data, prediction, measurement, collector)
    return collector.result(comparison)
