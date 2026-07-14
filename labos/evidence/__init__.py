"""Deterministic evidence sidecar support for Diamond Thermal Lab OS."""

from .summary import summarize_case
from .template import create_evidence_template, create_measurement_template, create_prediction_reality_template
from .validator import validate_evidence, validate_measurement_reference, validate_prediction_reality_record

__all__ = [
    "create_evidence_template",
    "create_measurement_template",
    "create_prediction_reality_template",
    "summarize_case",
    "validate_evidence",
    "validate_measurement_reference",
    "validate_prediction_reality_record",
]
