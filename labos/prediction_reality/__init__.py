"""Read-only deterministic prediction-versus-reality comparison support."""

from .comparison import compare_prediction_to_measurement
from .validator import validate_prediction_reality_record

__all__ = ["compare_prediction_to_measurement", "validate_prediction_reality_record"]
