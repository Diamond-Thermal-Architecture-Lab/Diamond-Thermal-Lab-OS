"""Read-only M16A EER projection into legacy Prediction-Reality fields."""

from __future__ import annotations

import json
import math
import os
import re
import stat
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from labos.evidence import validate_measurement_reference

from .evaluation_binding import (
    PersistedEngineeringEvaluationResult,
    load_engineering_evaluation_result,
)
from .quantities import (
    QuantityKind,
    canonical_decimal_text,
    convert_canonical_to_unit,
    parse_decimal,
)


PREDICTION_REALITY_ADAPTER_VERSION = "m16a-prediction-reality-adapter-1.0"

_OUTPUT_ID = re.compile(r"^EER-[0-9]{3}-OUT-[0-9]{3}$")
_MEASUREMENT_ID = re.compile(r"^MSR-[0-9]{3}$")
_LEGACY_PREDICTION_FIELDS = {
    "value",
    "unit",
    "lower_bound",
    "upper_bound",
    "model_name",
    "model_version",
    "input_reference",
    "input_sha256",
}


class PredictionRealityProjectionError(ValueError):
    """Raised when an EER output cannot be projected without loss or inference."""


@dataclass(frozen=True, slots=True)
class PredictionRealityProjection:
    """Runtime-only traceable projection containing exact legacy prediction fields."""

    prediction_reality_adapter_version: str
    source_evaluation_id: str
    source_eer_content_sha256: str
    source_eer_file_sha256: str
    source_output_id: str
    source_candidate_id: str
    measurement_id: str
    quantity: str
    prediction: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.prediction_reality_adapter_version != PREDICTION_REALITY_ADAPTER_VERSION:
            raise PredictionRealityProjectionError("Projection has the wrong adapter version.")
        if set(self.prediction) != _LEGACY_PREDICTION_FIELDS:
            raise PredictionRealityProjectionError("Projection has an invalid legacy prediction shape.")
        object.__setattr__(self, "prediction", MappingProxyType(dict(self.prediction)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "prediction_reality_adapter_version": self.prediction_reality_adapter_version,
            "source_evaluation_id": self.source_evaluation_id,
            "source_eer_content_sha256": self.source_eer_content_sha256,
            "source_eer_file_sha256": self.source_eer_file_sha256,
            "source_output_id": self.source_output_id,
            "source_candidate_id": self.source_candidate_id,
            "measurement_id": self.measurement_id,
            "quantity": self.quantity,
            "prediction": dict(self.prediction),
        }

    def legacy_fields(self) -> dict[str, Any]:
        return {"quantity": self.quantity, "prediction": dict(self.prediction)}


def _fail(message: str, cause: BaseException | None = None) -> None:
    error = PredictionRealityProjectionError(message)
    if cause is None:
        raise error
    raise error from cause


def _authoritative_reload(
    supplied: PersistedEngineeringEvaluationResult,
) -> PersistedEngineeringEvaluationResult:
    if not isinstance(supplied, PersistedEngineeringEvaluationResult):
        _fail("persisted_eer must be a PersistedEngineeringEvaluationResult.")
    try:
        supplied_case_path = supplied.case_path
        supplied_result = supplied.evaluation_result
        evaluation_id = supplied_result.evaluation_id
        authoritative = load_engineering_evaluation_result(supplied_case_path, evaluation_id)
    except (AttributeError, OSError, TypeError, ValueError) as exc:
        _fail("The supplied persisted EER could not be independently reloaded.", exc)

    try:
        equivalent = (
            supplied.case_path == authoritative.case_path
            and supplied.eer_path == authoritative.eer_path
            and supplied.eer_bytes == authoritative.eer_bytes
            and supplied.eer_file_sha256 == authoritative.eer_file_sha256
            and supplied.evaluation_result.canonical_bytes()
            == authoritative.evaluation_result.canonical_bytes()
        )
    except (AttributeError, TypeError, ValueError) as exc:
        _fail("The supplied persisted EER snapshot is incomplete.", exc)
    if not equivalent:
        _fail("The supplied persisted EER snapshot differs from the authoritative reload.")
    return authoritative


def _is_reparse(metadata: os.stat_result) -> bool:
    reparse_bit = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(getattr(metadata, "st_file_attributes", 0) & reparse_bit)


def _measurement_path(case_path: Path, measurement_id: str) -> Path:
    measurements = case_path / "measurements"
    target = measurements / f"{measurement_id}.json"
    try:
        parent_metadata = os.lstat(measurements)
        target_metadata = os.lstat(target)
        resolved_parent = measurements.resolve(strict=True)
        resolved_target = target.resolve(strict=True)
    except OSError as exc:
        _fail("The derived Measurement Reference does not exist or is unreadable.", exc)
    if (
        not stat.S_ISDIR(parent_metadata.st_mode)
        or stat.S_ISLNK(parent_metadata.st_mode)
        or _is_reparse(parent_metadata)
    ):
        _fail("The case-local measurements path must be a normal directory.")
    if (
        not stat.S_ISREG(target_metadata.st_mode)
        or stat.S_ISLNK(target_metadata.st_mode)
        or _is_reparse(target_metadata)
    ):
        _fail("The Measurement Reference must be a normal file, not a link or reparse path.")
    if resolved_parent != measurements or resolved_target.parent != resolved_parent:
        _fail("The Measurement Reference must resolve directly under the case measurements directory.")
    if resolved_target != resolved_parent / f"{measurement_id}.json":
        _fail("The Measurement Reference path does not match the requested measurement ID.")
    return target


def _validated_measurement(case_path: Path, measurement_id: str) -> dict[str, Any]:
    target = _measurement_path(case_path, measurement_id)
    try:
        before = target.read_bytes()
        validation = validate_measurement_reference(case_path, target)
        target = _measurement_path(case_path, measurement_id)
        after = target.read_bytes()
    except (OSError, TypeError, ValueError) as exc:
        _fail("Measurement Reference validation could not complete.", exc)
    _measurement_path(case_path, measurement_id)
    if before != after:
        _fail("Measurement Reference bytes changed during validation.")
    if validation.status == "FAIL":
        _fail("Measurement Reference repository validation returned FAIL.")
    if validation.status not in {"PASS", "WARN"}:
        _fail("Measurement Reference validation returned an unknown status.")
    try:
        measurement = json.loads(after)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _fail("Measurement Reference bytes are not valid standard JSON.", exc)
    if type(measurement) is not dict:
        _fail("Measurement Reference JSON must be an object.")
    if measurement.get("measurement_id") != measurement_id:
        _fail("Measurement Reference identity does not match the request and filename.")
    return measurement


def _legacy_number(value: Decimal) -> int | float:
    token = canonical_decimal_text(value)
    try:
        decoded = json.loads(token)
    except json.JSONDecodeError as exc:
        _fail("Projected Decimal is not representable as a standard JSON number.", exc)
    if type(decoded) not in {int, float}:
        _fail("Projected Decimal did not decode as a standard JSON number.")
    if type(decoded) is float and not math.isfinite(decoded):
        _fail("Projected Decimal decoded as a non-finite legacy number.")
    if Decimal(str(decoded)) != value:
        _fail("Projected Decimal loses numeric identity in the legacy JSON-number domain.")
    return decoded


def _project_decimal(kind: QuantityKind, value: str, target_unit: str) -> int | float:
    try:
        canonical = parse_decimal(value)
        projected = convert_canonical_to_unit(kind, canonical, target_unit)
        target = parse_decimal(projected.conversion.original_value)
    except (TypeError, ValueError) as exc:
        _fail("EER prediction value cannot be exactly projected to the measurement unit.", exc)
    return _legacy_number(target)


def project_eer_prediction_to_measurement(
    persisted_eer: PersistedEngineeringEvaluationResult,
    output_id: str,
    measurement_id: str,
) -> PredictionRealityProjection:
    """Project one exact persisted EER output to legacy-compatible prediction fields."""
    if type(output_id) is not str or _OUTPUT_ID.fullmatch(output_id) is None:
        _fail("output_id must use exact EER-###-OUT-### syntax.")
    if type(measurement_id) is not str or _MEASUREMENT_ID.fullmatch(measurement_id) is None:
        _fail("measurement_id must use exact MSR-### syntax.")

    authoritative = _authoritative_reload(persisted_eer)
    eer = authoritative.evaluation_result.to_dict()
    matches = [item for item in eer["prediction_outputs"] if item["output_id"] == output_id]
    if len(matches) != 1:
        _fail("output_id must identify exactly one EER prediction output.")
    output = matches[0]
    measurement = _validated_measurement(authoritative.case_path, measurement_id)

    if measurement.get("case_id") != eer["case_id"]:
        _fail("Measurement Reference case_id does not exactly match the EER case_id.")
    if measurement.get("quantity") != output["quantity_label"]:
        _fail("Measurement quantity does not exactly match the EER output quantity label.")
    target_unit = measurement.get("unit")
    if type(target_unit) is not str or not target_unit:
        _fail("Measurement unit must be a non-empty exact registered unit token.")
    try:
        kind = QuantityKind(output["quantity_kind"])
    except (TypeError, ValueError) as exc:
        _fail("EER output quantity_kind is invalid.", exc)

    value = _project_decimal(kind, output["value"], target_unit)
    lower = (
        None
        if output["lower_bound"] is None
        else _project_decimal(kind, output["lower_bound"], target_unit)
    )
    upper = (
        None
        if output["upper_bound"] is None
        else _project_decimal(kind, output["upper_bound"], target_unit)
    )
    manifest = eer["model_manifest"]
    prediction = {
        "value": value,
        "unit": target_unit,
        "lower_bound": lower,
        "upper_bound": upper,
        "model_name": manifest["model_id"],
        "model_version": manifest["model_version"],
        "input_reference": f"engineering/evaluations/{eer['evaluation_id']}.json",
        "input_sha256": authoritative.eer_file_sha256,
    }
    return PredictionRealityProjection(
        prediction_reality_adapter_version=PREDICTION_REALITY_ADAPTER_VERSION,
        source_evaluation_id=eer["evaluation_id"],
        source_eer_content_sha256=eer["eer_content_sha256"],
        source_eer_file_sha256=authoritative.eer_file_sha256,
        source_output_id=output["output_id"],
        source_candidate_id=output["candidate_id"],
        measurement_id=measurement_id,
        quantity=measurement["quantity"],
        prediction=prediction,
    )
