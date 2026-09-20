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
class _MeasurementFilesystemIdentity:
    device: int
    inode: int
    object_type: int
    file_attributes: int | None


@dataclass(frozen=True, slots=True)
class _MeasurementFilesystemVersion:
    size: int
    mtime_ns: int
    ctime_ns: int | None


@dataclass(frozen=True, slots=True)
class _MeasurementSnapshot:
    data: bytes
    case_identity: _MeasurementFilesystemIdentity
    case_version: _MeasurementFilesystemVersion
    directory_identity: _MeasurementFilesystemIdentity
    directory_version: _MeasurementFilesystemVersion
    target_identity: _MeasurementFilesystemIdentity
    target_version: _MeasurementFilesystemVersion


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


def _filesystem_identity(metadata: os.stat_result) -> _MeasurementFilesystemIdentity:
    attributes = getattr(metadata, "st_file_attributes", None)
    return _MeasurementFilesystemIdentity(
        device=int(metadata.st_dev),
        inode=int(metadata.st_ino),
        object_type=stat.S_IFMT(metadata.st_mode),
        file_attributes=None if attributes is None else int(attributes),
    )


def _filesystem_version(metadata: os.stat_result) -> _MeasurementFilesystemVersion:
    ctime_ns = getattr(metadata, "st_ctime_ns", None)
    return _MeasurementFilesystemVersion(
        size=int(metadata.st_size),
        mtime_ns=int(metadata.st_mtime_ns),
        ctime_ns=None if ctime_ns is None else int(ctime_ns),
    )


def _require_measurements_directory(metadata: os.stat_result) -> None:
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or _is_reparse(metadata)
    ):
        _fail("The case-local measurements path must be a normal directory.")


def _require_measurement_target(metadata: os.stat_result) -> None:
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or _is_reparse(metadata)
    ):
        _fail("The Measurement Reference must be a normal file, not a link or reparse path.")


def _measurement_location(
    case_path: Path,
    measurement_id: str,
) -> tuple[Path, Path, os.stat_result, os.stat_result]:
    measurements = case_path / "measurements"
    target = measurements / f"{measurement_id}.json"
    try:
        parent_metadata = os.lstat(measurements)
        target_metadata = os.lstat(target)
    except OSError as exc:
        _fail("The derived Measurement Reference does not exist or is unreadable.", exc)
    _require_measurements_directory(parent_metadata)
    _require_measurement_target(target_metadata)
    try:
        resolved_parent = measurements.resolve(strict=True)
        resolved_target = target.resolve(strict=True)
    except OSError as exc:
        _fail("The derived Measurement Reference does not exist or is unreadable.", exc)
    if resolved_parent != measurements or resolved_target.parent != resolved_parent:
        _fail("The Measurement Reference must resolve directly under the case measurements directory.")
    if resolved_target != resolved_parent / f"{measurement_id}.json":
        _fail("The Measurement Reference path does not match the requested measurement ID.")
    return measurements, target, parent_metadata, target_metadata


def _read_descriptor_bytes(descriptor: int) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk = os.read(descriptor, 64 * 1024)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _measurement_snapshot(case_path: Path, measurement_id: str) -> _MeasurementSnapshot:
    try:
        case_before = os.lstat(case_path)
    except OSError as exc:
        _fail("The authoritative case directory is unreadable.", exc)
    _require_measurements_directory(case_before)
    measurements, target, directory_before, target_before = _measurement_location(
        case_path, measurement_id
    )
    case_identity = _filesystem_identity(case_before)
    case_version = _filesystem_version(case_before)
    directory_identity = _filesystem_identity(directory_before)
    directory_version = _filesystem_version(directory_before)
    target_identity = _filesystem_identity(target_before)
    target_version = _filesystem_version(target_before)

    flags = os.O_RDONLY
    flags |= getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(target, flags)
    except OSError as exc:
        _fail("The Measurement Reference could not be opened without following links.", exc)
    try:
        opened = os.fstat(descriptor)
        _require_measurement_target(opened)
        if _filesystem_identity(opened) != target_identity:
            _fail("The Measurement Reference changed between lstat and descriptor open.")
        opened_version = _filesystem_version(opened)
        data = _read_descriptor_bytes(descriptor)
        after_read = os.fstat(descriptor)
        if (
            _filesystem_identity(after_read) != target_identity
            or _filesystem_version(after_read) != opened_version
        ):
            _fail("The opened Measurement Reference changed during descriptor read.")
    except OSError as exc:
        _fail("The Measurement Reference descriptor read failed.", exc)
    finally:
        os.close(descriptor)

    _, _, directory_after, target_after = _measurement_location(case_path, measurement_id)
    try:
        case_after = os.lstat(case_path)
    except OSError as exc:
        _fail("The authoritative case directory became unreadable.", exc)
    _require_measurements_directory(case_after)
    if (
        _filesystem_identity(case_after) != case_identity
        or _filesystem_version(case_after) != case_version
    ):
        _fail("The authoritative case directory changed during descriptor read.")
    if (
        _filesystem_identity(directory_after) != directory_identity
        or _filesystem_version(directory_after) != directory_version
    ):
        _fail("The measurements directory changed during descriptor read.")
    if (
        _filesystem_identity(target_after) != target_identity
        or _filesystem_version(target_after) != target_version
    ):
        _fail("The Measurement Reference pathname changed during descriptor read.")
    return _MeasurementSnapshot(
        data=data,
        case_identity=case_identity,
        case_version=case_version,
        directory_identity=directory_identity,
        directory_version=directory_version,
        target_identity=target_identity,
        target_version=target_version,
    )


def _validated_measurement(case_path: Path, measurement_id: str) -> dict[str, Any]:
    target = case_path / "measurements" / f"{measurement_id}.json"
    try:
        before = _measurement_snapshot(case_path, measurement_id)
        validation = validate_measurement_reference(case_path, target)
        after = _measurement_snapshot(case_path, measurement_id)
    except (OSError, TypeError, ValueError) as exc:
        _fail("Measurement Reference validation could not complete.", exc)
    if before.data != after.data:
        _fail("Measurement Reference bytes changed during validation.")
    if before.case_identity != after.case_identity or before.case_version != after.case_version:
        _fail("Case-directory identity or version changed during measurement validation.")
    if before.directory_identity != after.directory_identity:
        _fail("Measurements-directory identity changed during validation.")
    if before.directory_version != after.directory_version:
        _fail("Measurements-directory version changed during validation.")
    if before.target_identity != after.target_identity:
        _fail("Measurement Reference filesystem identity changed during validation.")
    if before.target_version != after.target_version:
        _fail("Measurement Reference filesystem version changed during validation.")
    if validation.status == "FAIL":
        _fail("Measurement Reference repository validation returned FAIL.")
    if validation.status not in {"PASS", "WARN"}:
        _fail("Measurement Reference validation returned an unknown status.")
    try:
        measurement = json.loads(after.data)
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
