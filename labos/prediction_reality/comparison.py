from __future__ import annotations

from decimal import Decimal
from typing import Any

from labos.evidence.models import decimal_text
from labos.evidence.validator import ValidationCollector, decimal_value, text


def compare_prediction_to_measurement(
    record: dict[str, Any],
    prediction: dict[str, Any],
    measurement: dict[str, Any] | None,
    collector: ValidationCollector,
) -> dict[str, Any] | None:
    """Calculate only exact-unit, read-only prediction-versus-reality differences."""
    if measurement is None:
        return None
    record_quantity, measurement_quantity = text(record.get("quantity")), text(measurement.get("quantity"))
    if record_quantity and measurement_quantity and record_quantity != measurement_quantity:
        collector.fail("PREDICTION-COMPARISON-002", "Prediction and measurement quantities do not match.", f"{record_quantity} != {measurement_quantity}", "Use the same quantity before comparison.")
        return None
    prediction_value, reality_value = decimal_value(prediction.get("value")), decimal_value(measurement.get("value"))
    prediction_unit, reality_unit = text(prediction.get("unit")), text(measurement.get("unit"))
    if reality_value is None:
        collector.warn("PREDICTION-COMPARISON-003", "Referenced measurement has no reality value; no comparison was calculated.", "measurement.value", "Complete the measurement first.")
        return None
    if prediction_value is None or not prediction_unit:
        return None
    if prediction_unit != reality_unit:
        collector.warn("PREDICTION-COMPARISON-004", "Prediction and measurement units do not match; no numeric comparison was calculated.", f"{prediction_unit} != {reality_unit}", "Use identical unit strings; unit conversion is out of scope.")
        return {"record_id": text(record.get("record_id")), "comparable": False, "reason": "unit_mismatch"}
    signed = reality_value - prediction_value
    absolute = abs(signed)
    relative: Decimal | None = None
    if reality_value == 0:
        collector.warn("PREDICTION-COMPARISON-005", "Reality value is zero; relative_error_percent is unavailable.", "measurement.value: 0", "Use signed and absolute error only.")
    else:
        relative = absolute / abs(reality_value) * Decimal("100")
    lower, upper = decimal_value(prediction.get("lower_bound")), decimal_value(prediction.get("upper_bound"))
    interval = None if lower is None or upper is None else lower <= reality_value <= upper
    return {
        "record_id": text(record.get("record_id")),
        "comparable": True,
        "quantity": text(record.get("quantity")),
        "unit": reality_unit,
        "reality_value": decimal_text(reality_value),
        "prediction_value": decimal_text(prediction_value),
        "signed_error": decimal_text(signed),
        "absolute_error": decimal_text(absolute),
        "relative_error_percent": decimal_text(relative),
        "reality_within_prediction_interval": interval,
    }
