"""EPR-bound Evaluation Plans and stale-source-safe EER persistence."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .evaluation import (
    EngineeringEvaluationResult,
    EvaluationPlan,
)
from .problem import EngineeringProblem
from .quantities import QuantifiedValue, QuantityKind
from .serialization import canonical_json_bytes


__all__ = [
    "EngineeringEvaluationBindingError",
    "BoundEvaluationPlan",
    "PersistedEngineeringEvaluationResult",
    "bind_evaluation_plan",
    "load_engineering_evaluation_result",
    "write_engineering_evaluation_result",
]


_CASE_ID = re.compile(r"^[a-z0-9_-]+$")
_EVALUATION_ID = re.compile(r"^EER-[0-9]{3}$")
_CANDIDATE_ROOTS = {
    "geometry",
    "materials",
    "interfaces",
    "boundary_conditions",
}
_GLOBAL_ROOTS = {"requirements", "heat_sources", "constraints"}
_ENVELOPE_FIELDS = {
    "value",
    "unit",
    "quantity_kind",
    "provenance",
    "uncertainty",
    "confidence",
    "status",
    "conversion",
}
_CONFIDENTIALITY_RANK = {
    "public": 0,
    "internal": 1,
    "customer-confidential": 2,
    "restricted": 3,
}


class EngineeringEvaluationBindingError(ValueError):
    """Raised when an I3B1 filesystem or EPR binding contract is violated."""


def _fail(path: str, message: str) -> None:
    raise EngineeringEvaluationBindingError(f"{path}: {message}")


@dataclass(frozen=True, slots=True)
class _FilesystemIdentity:
    device: int
    inode: int
    object_type: int


@dataclass(frozen=True, slots=True)
class _VerifiedDirectory:
    path: Path
    identity: _FilesystemIdentity


@dataclass(frozen=True, slots=True)
class _DescriptorRead:
    path: Path
    data: bytes
    identity: _FilesystemIdentity


@dataclass(frozen=True, slots=True, init=False)
class BoundEvaluationPlan:
    """Deeply immutable runtime binding to exact persisted EPR bytes."""

    _evaluation_plan: EvaluationPlan
    _engineering_problem: EngineeringProblem
    _case_path: Path
    _epr_path: Path
    _epr_bytes: bytes
    _epr_file_sha256: str
    _case_identity: _FilesystemIdentity
    _engineering_identity: _FilesystemIdentity
    _problems_identity: _FilesystemIdentity
    _epr_identity: _FilesystemIdentity

    def __init__(self) -> None:
        raise TypeError("BoundEvaluationPlan instances are created only by bind_evaluation_plan")

    @property
    def evaluation_plan(self) -> EvaluationPlan:
        return self._evaluation_plan

    @property
    def engineering_problem(self) -> EngineeringProblem:
        return self._engineering_problem

    @property
    def case_path(self) -> Path:
        return self._case_path

    @property
    def epr_path(self) -> Path:
        return self._epr_path

    @property
    def epr_bytes(self) -> bytes:
        return self._epr_bytes

    @property
    def epr_file_sha256(self) -> str:
        return self._epr_file_sha256

    @property
    def epr_reference(self) -> str:
        return f"engineering/problems/{self._engineering_problem.problem_id}.json"


@dataclass(frozen=True, slots=True, init=False)
class PersistedEngineeringEvaluationResult:
    """Deeply immutable runtime binding to exact persisted EER bytes."""

    _evaluation_result: EngineeringEvaluationResult
    _case_path: Path
    _eer_path: Path
    _eer_bytes: bytes
    _eer_file_sha256: str
    _case_identity: _FilesystemIdentity
    _engineering_identity: _FilesystemIdentity
    _evaluations_identity: _FilesystemIdentity
    _eer_identity: _FilesystemIdentity

    def __init__(self) -> None:
        raise TypeError(
            "PersistedEngineeringEvaluationResult instances are created only by "
            "load_engineering_evaluation_result"
        )

    @property
    def evaluation_result(self) -> EngineeringEvaluationResult:
        return self._evaluation_result

    @property
    def case_path(self) -> Path:
        return self._case_path

    @property
    def eer_path(self) -> Path:
        return self._eer_path

    @property
    def eer_bytes(self) -> bytes:
        return self._eer_bytes

    @property
    def eer_file_sha256(self) -> str:
        return self._eer_file_sha256


def _new_bound_evaluation_plan(
    plan: EvaluationPlan,
    problem: EngineeringProblem,
    case: _VerifiedDirectory,
    engineering: _VerifiedDirectory,
    problems: _VerifiedDirectory,
    persisted: _DescriptorRead,
    digest: str,
) -> BoundEvaluationPlan:
    bound = object.__new__(BoundEvaluationPlan)
    values = {
        "_evaluation_plan": plan,
        "_engineering_problem": problem,
        "_case_path": case.path,
        "_epr_path": persisted.path,
        "_epr_bytes": persisted.data,
        "_epr_file_sha256": digest,
        "_case_identity": case.identity,
        "_engineering_identity": engineering.identity,
        "_problems_identity": problems.identity,
        "_epr_identity": persisted.identity,
    }
    for field, value in values.items():
        object.__setattr__(bound, field, value)
    return bound


def _new_persisted_evaluation_result(
    result: EngineeringEvaluationResult,
    case: _VerifiedDirectory,
    engineering: _VerifiedDirectory,
    evaluations: _VerifiedDirectory,
    persisted: _DescriptorRead,
) -> PersistedEngineeringEvaluationResult:
    loaded = object.__new__(PersistedEngineeringEvaluationResult)
    values = {
        "_evaluation_result": result,
        "_case_path": case.path,
        "_eer_path": persisted.path,
        "_eer_bytes": persisted.data,
        "_eer_file_sha256": hashlib.sha256(persisted.data).hexdigest(),
        "_case_identity": case.identity,
        "_engineering_identity": engineering.identity,
        "_evaluations_identity": evaluations.identity,
        "_eer_identity": persisted.identity,
    }
    for field, value in values.items():
        object.__setattr__(loaded, field, value)
    return loaded


def _is_windows_reparse_point(metadata: Any) -> bool:
    """Return whether stat metadata carries the Windows reparse-point bit."""

    reparse_bit = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(getattr(metadata, "st_file_attributes", 0) & reparse_bit)


def _filesystem_identity(metadata: Any) -> _FilesystemIdentity:
    return _FilesystemIdentity(
        int(metadata.st_dev),
        int(metadata.st_ino),
        stat.S_IFMT(metadata.st_mode),
    )


def _timestamp_ns(metadata: Any, field: str) -> int:
    nanoseconds = getattr(metadata, f"{field}_ns", None)
    if nanoseconds is not None:
        return int(nanoseconds)
    return int(getattr(metadata, field) * 1_000_000_000)


def _file_version(metadata: Any) -> tuple[_FilesystemIdentity, int, int]:
    return (
        _filesystem_identity(metadata),
        int(metadata.st_size),
        _timestamp_ns(metadata, "st_mtime"),
    )


def _require_safe_metadata(metadata: Any, *, directory: bool, label: str) -> None:
    if stat.S_ISLNK(metadata.st_mode):
        raise OSError(f"{label} is a symlink")
    if _is_windows_reparse_point(metadata):
        raise OSError(f"{label} is a Windows reparse point")
    predicate = stat.S_ISDIR if directory else stat.S_ISREG
    if not predicate(metadata.st_mode):
        kind = "directory" if directory else "regular file"
        raise OSError(f"{label} is not a {kind}")
    if int(metadata.st_ino) == 0:
        raise OSError(f"{label} has no stable filesystem object identity")


def _absolute_path(path: str | os.PathLike[str]) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _verify_directory_path(
    path: str | os.PathLike[str],
    *,
    label: str,
    expected_parent: _VerifiedDirectory | None = None,
) -> _VerifiedDirectory:
    candidate = _absolute_path(path)
    try:
        if expected_parent is not None:
            _assert_directory_identity(expected_parent)
            if candidate.parent != expected_parent.path:
                raise OSError("directory is not the exact expected child path")
        before = os.lstat(candidate)
        _require_safe_metadata(before, directory=True, label=label)
        resolved = candidate.resolve(strict=True)
        if resolved != candidate:
            raise OSError("directory path is not exact and canonical")
        after = os.lstat(candidate)
        _require_safe_metadata(after, directory=True, label=label)
        if _filesystem_identity(before) != _filesystem_identity(after):
            raise OSError("directory object identity changed during verification")
        verified = _VerifiedDirectory(candidate, _filesystem_identity(after))
        if expected_parent is not None:
            _assert_directory_identity(expected_parent)
    except (OSError, RuntimeError) as exc:
        _fail("/filesystem", f"unsafe {label}: {exc}")
    return verified


def _assert_directory_identity(directory: _VerifiedDirectory) -> None:
    try:
        current = os.lstat(directory.path)
        _require_safe_metadata(current, directory=True, label=str(directory.path))
        if directory.path.resolve(strict=True) != directory.path:
            raise OSError("directory is no longer exact and canonical")
        if _filesystem_identity(current) != directory.identity:
            raise OSError("directory object identity changed")
    except (OSError, RuntimeError) as exc:
        _fail("/filesystem", f"verified directory became unsafe: {exc}")


def _safe_case_directory(case_path: str | os.PathLike[str]) -> _VerifiedDirectory:
    case = _verify_directory_path(case_path, label="case directory")
    if _CASE_ID.fullmatch(case.path.name) is None:
        _fail("/case_path", "case directory name has invalid case ID syntax")
    return case


def _safe_directory(
    parent: _VerifiedDirectory,
    name: str,
    *,
    create: bool = False,
) -> _VerifiedDirectory:
    candidate = parent.path / name
    _assert_directory_identity(parent)
    if create:
        try:
            os.mkdir(candidate)
        except FileExistsError:
            pass
        except OSError as exc:
            _fail("/filesystem", f"cannot create safe {name!r} directory: {exc}")
    child = _verify_directory_path(candidate, label=f"{name!r} directory", expected_parent=parent)
    _assert_directory_identity(parent)
    return child


def _safe_regular_file(parent: _VerifiedDirectory, filename: str) -> _DescriptorRead:
    if Path(filename).name != filename or filename in {"", ".", ".."}:
        _fail("/filesystem", "file name must be one exact child name")
    candidate = parent.path / filename
    descriptor: int | None = None
    try:
        _assert_directory_identity(parent)
        before = os.lstat(candidate)
        _require_safe_metadata(before, directory=False, label=filename)
        if candidate.resolve(strict=True) != candidate:
            raise OSError("file path is not exact and canonical")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_CLOEXEC", 0)
        if os.name != "nt":
            flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(candidate, flags)
        opened = os.fstat(descriptor)
        _require_safe_metadata(opened, directory=False, label=filename)
        if _filesystem_identity(before) != _filesystem_identity(opened):
            raise OSError("opened file does not match pre-open pathname identity")
        if _file_version(before) != _file_version(opened):
            raise OSError("file changed between lstat and descriptor open")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        final_descriptor = os.fstat(descriptor)
        _require_safe_metadata(final_descriptor, directory=False, label=filename)
        if _file_version(opened) != _file_version(final_descriptor):
            raise OSError("opened file changed during descriptor-bound read")
        after = os.lstat(candidate)
        _require_safe_metadata(after, directory=False, label=filename)
        if _file_version(final_descriptor) != _file_version(after):
            raise OSError("pathname no longer identifies the descriptor-bound file")
        if candidate.resolve(strict=True) != candidate:
            raise OSError("file path changed or became non-canonical during read")
        _assert_directory_identity(parent)
        return _DescriptorRead(candidate, b"".join(chunks), _filesystem_identity(opened))
    except (OSError, RuntimeError) as exc:
        _fail("/filesystem", f"cannot safely read {filename!r}: {exc}")
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _structured_json(data: bytes, path: str) -> Mapping[str, Any]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        _fail(path, f"exact persisted bytes are not UTF-8: {exc}")
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        _fail(path, f"exact persisted bytes are not valid JSON: {exc}")
    if not isinstance(value, Mapping):
        _fail(path, "persisted JSON must be a structured object")
    return value


def _read_epr(
    case_dir: _VerifiedDirectory,
    problem_id: str,
) -> tuple[_VerifiedDirectory, _VerifiedDirectory, _DescriptorRead, EngineeringProblem, str]:
    engineering = _safe_directory(case_dir, "engineering")
    problems = _safe_directory(engineering, "problems")
    persisted = _safe_regular_file(problems, f"{problem_id}.json")
    data = persisted.data
    _assert_directory_identity(case_dir)
    _assert_directory_identity(engineering)
    _assert_directory_identity(problems)
    value = _structured_json(data, "/epr")
    try:
        problem = EngineeringProblem.from_dict(value)
    except (KeyError, TypeError, ValueError) as exc:
        _fail("/epr", f"EngineeringProblem reconstruction failed: {exc}")
    if canonical_json_bytes(problem.to_dict()) != data:
        _fail("/epr", "persisted EPR bytes are not the exact canonical representation")
    problem_data = problem.to_dict()
    if problem_data["case_id"] != case_dir.path.name:
        _fail("/epr/case_id", "does not equal the canonical case directory name")
    if problem.problem_id != problem_id or persisted.path.stem != problem.problem_id:
        _fail("/epr/problem_id", "does not equal the requested EPR filename identity")
    return engineering, problems, persisted, problem, hashlib.sha256(data).hexdigest()


def _decode_pointer(pointer: Any, path: str) -> tuple[str, ...]:
    if type(pointer) is not str or not pointer.startswith("/"):
        _fail(path, "must be a non-empty RFC 6901 JSON Pointer")
    tokens: list[str] = []
    for raw in pointer[1:].split("/"):
        decoded: list[str] = []
        index = 0
        while index < len(raw):
            if raw[index] != "~":
                decoded.append(raw[index])
                index += 1
                continue
            if index + 1 >= len(raw) or raw[index + 1] not in {"0", "1"}:
                _fail(path, "contains a malformed RFC 6901 escape")
            decoded.append("~" if raw[index + 1] == "0" else "/")
            index += 2
        token = "".join(decoded)
        if token == "-":
            _fail(path, "JSON Patch append tokens are forbidden")
        if token == "*":
            _fail(path, "wildcard semantics are forbidden")
        tokens.append(token)
    return tuple(tokens)


def _resolve_pointer(document: Any, pointer: Any, path: str) -> Any:
    current = document
    for token in _decode_pointer(pointer, path):
        if isinstance(current, Mapping):
            if token not in current:
                _fail(path, "JSON Pointer does not resolve")
            current = current[token]
        elif type(current) is list:
            if not token.isdigit() or (token != "0" and token.startswith("0")):
                _fail(path, "JSON Pointer array index is not canonical")
            position = int(token)
            if position >= len(current):
                _fail(path, "JSON Pointer array index does not resolve")
            current = current[position]
        else:
            _fail(path, "JSON Pointer does not resolve")
    return current


def _root(pointer: str, path: str) -> str:
    tokens = _decode_pointer(pointer, path)
    if not tokens:
        _fail(path, "must identify an authority-rooted field")
    return tokens[0]


def _envelope_kind(value: Any, path: str, *, require_numeric: bool = False) -> QuantityKind:
    if not isinstance(value, Mapping) or set(value) != _ENVELOPE_FIELDS:
        _fail(path, "must resolve to the quantified-value envelope itself")
    try:
        kind = QuantityKind(value["quantity_kind"])
    except (KeyError, TypeError, ValueError) as exc:
        _fail(path, f"has an invalid QuantityKind: {exc}")
    if require_numeric:
        if type(value["value"]) is not str:
            _fail(path, "target must have a non-null numeric physical value")
        try:
            QuantifiedValue.from_dict(
                {
                    "quantity_kind": value["quantity_kind"],
                    "canonical_value": value["value"],
                    "canonical_unit": value["unit"],
                    "conversion": value["conversion"],
                }
            )
        except (KeyError, TypeError, ValueError) as exc:
            _fail(path, f"target does not reconstruct through I1: {exc}")
    return kind


def _plan_quantity_kind(value: Any, path: str) -> QuantityKind:
    if not isinstance(value, Mapping):
        _fail(path, "must be a quantified value")
    try:
        quantity = QuantifiedValue.from_dict(
            {
                "quantity_kind": value["quantity_kind"],
                "canonical_value": value["value"],
                "canonical_unit": value["unit"],
                "conversion": value["conversion"],
            }
        )
    except (KeyError, TypeError, ValueError) as exc:
        _fail(path, f"does not reconstruct through I1: {exc}")
    return quantity.quantity_kind


def _candidate_by_id(problem: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {candidate["candidate_id"]: candidate for candidate in problem["candidates"]}


def _validate_target_pointer(
    candidate: Mapping[str, Any],
    pointer: str,
    path: str,
    *,
    require_numeric: bool,
) -> QuantityKind:
    if _root(pointer, path) not in _CANDIDATE_ROOTS:
        _fail(path, "must begin at geometry, materials, interfaces, or boundary_conditions")
    target = _resolve_pointer(candidate, pointer, path)
    return _envelope_kind(target, path, require_numeric=require_numeric)


def _validate_bound_plan(plan: EvaluationPlan, problem: EngineeringProblem) -> None:
    plan_data = plan.to_dict()
    problem_data = problem.to_dict()
    selected_ids = plan_data["selected_candidate_ids"]
    candidates = _candidate_by_id(problem_data)
    missing = [candidate_id for candidate_id in selected_ids if candidate_id not in candidates]
    if missing:
        _fail("/selected_candidate_ids", f"unknown EPR candidates: {missing!r}")
    parents = {candidates[candidate_id]["parent_requirement_id"] for candidate_id in selected_ids}
    if len(parents) != 1:
        _fail("/selected_candidate_ids", "selected candidates must share one parent_requirement_id")

    objective = plan_data["objective"]
    if objective["metric"] == "temperature_margin":
        requirement = next(
            (
                item
                for item in problem_data["requirements"]
                if item["requirement_id"] == objective["reference_requirement_id"]
            ),
            None,
        )
        if requirement is None:
            _fail("/objective/reference_requirement_id", "does not exist in the bound EPR")
        target = requirement.get("target")
        if target is None:
            _fail("/objective/reference_requirement_id", "requirement has no quantified target")
        if _envelope_kind(target, "/objective/reference_requirement_id") is not QuantityKind.ABSOLUTE_TEMPERATURE:
            _fail("/objective/reference_requirement_id", "requirement target must be absolute_temperature")

    for index, sweep in enumerate(plan_data["parameter_sweeps"]):
        sweep_path = f"/parameter_sweeps/{index}"
        candidate = candidates[sweep["candidate_id"]]
        target_kind = _validate_target_pointer(
            candidate,
            sweep["field_path"],
            f"{sweep_path}/field_path",
            require_numeric=True,
        )
        specification = sweep["value_specification"]
        if specification["kind"] == "grid":
            points = specification["values"]
            point_paths = [f"{sweep_path}/value_specification/values/{i}" for i in range(len(points))]
        else:
            points = [specification["start"], specification["stop"]]
            point_paths = [
                f"{sweep_path}/value_specification/start",
                f"{sweep_path}/value_specification/stop",
            ]
        for point, point_path in zip(points, point_paths):
            if _plan_quantity_kind(point, point_path) is not target_kind:
                _fail(point_path, f"QuantityKind must equal target kind {target_kind.value!r}")

    sensitivity = plan_data["sensitivity_request"]
    if sensitivity is not None:
        baseline = sensitivity["baseline_candidate_id"]
        candidate = candidates[baseline]
        for index, parameter in enumerate(sensitivity["parameters"]):
            parameter_path = f"/sensitivity_request/parameters/{index}"
            if parameter["candidate_id"] != baseline:
                _fail(f"{parameter_path}/candidate_id", "must equal baseline_candidate_id")
            target_kind = _validate_target_pointer(
                candidate,
                parameter["field_path"],
                f"{parameter_path}/field_path",
                require_numeric=True,
            )
            for field in ("minus_value", "plus_value"):
                if _plan_quantity_kind(parameter[field], f"{parameter_path}/{field}") is not target_kind:
                    _fail(f"{parameter_path}/{field}", f"QuantityKind must equal target kind {target_kind.value!r}")

    selected = set(selected_ids)
    for index, acknowledgement in enumerate(plan_data["assumption_acknowledgements"]):
        acknowledgement_path = f"/assumption_acknowledgements/{index}"
        pointer = acknowledgement["field_path"]
        if acknowledgement["scope"] == "candidate":
            candidate_id = acknowledgement["candidate_id"]
            if candidate_id not in selected:
                _fail(f"{acknowledgement_path}/candidate_id", "must reference a selected candidate")
            if _root(pointer, f"{acknowledgement_path}/field_path") not in _CANDIDATE_ROOTS:
                _fail(f"{acknowledgement_path}/field_path", "candidate scope uses a non-candidate authority root")
            candidate = candidates[candidate_id]
            target = _resolve_pointer(candidate, pointer, f"{acknowledgement_path}/field_path")
            _envelope_kind(target, f"{acknowledgement_path}/field_path")
            if pointer not in candidate["assumption_paths"]:
                _fail(f"{acknowledgement_path}/field_path", "is not this candidate's exact assumption path")
        else:
            if acknowledgement["candidate_id"] is not None:
                _fail(f"{acknowledgement_path}/candidate_id", "must be null for global scope")
            if _root(pointer, f"{acknowledgement_path}/field_path") not in _GLOBAL_ROOTS:
                _fail(f"{acknowledgement_path}/field_path", "global scope uses a non-global authority root")
            target = _resolve_pointer(problem_data, pointer, f"{acknowledgement_path}/field_path")
            _envelope_kind(target, f"{acknowledgement_path}/field_path")
        if target["status"] != "assumed":
            _fail(f"{acknowledgement_path}/field_path", "acknowledged envelope status must be exactly 'assumed'")


def bind_evaluation_plan(
    case_path: str | os.PathLike[str],
    evaluation_plan: EvaluationPlan | Mapping[str, Any],
) -> BoundEvaluationPlan:
    """Bind one validated plan to exact canonical bytes of its case-local EPR."""

    if isinstance(evaluation_plan, EvaluationPlan):
        plan = evaluation_plan
    elif isinstance(evaluation_plan, Mapping):
        try:
            plan = EvaluationPlan.from_dict(evaluation_plan)
        except (KeyError, TypeError, ValueError) as exc:
            _fail("/evaluation_plan", f"EvaluationPlan reconstruction failed: {exc}")
    else:
        raise TypeError("evaluation_plan must be an EvaluationPlan or mapping")
    plan_data = plan.to_dict()
    case_dir = _safe_case_directory(case_path)
    if plan_data["case_id"] != case_dir.path.name:
        _fail("/evaluation_plan/case_id", "does not equal the canonical case directory name")
    engineering, problems, persisted, problem, epr_file_sha256 = _read_epr(
        case_dir,
        plan_data["problem_id"],
    )
    problem_data = problem.to_dict()
    if plan_data["case_id"] != problem_data["case_id"]:
        _fail("/evaluation_plan/case_id", "does not equal the persisted EPR case_id")
    if plan_data["problem_id"] != problem.problem_id:
        _fail("/evaluation_plan/problem_id", "does not equal the persisted EPR problem_id")
    if plan_data["epr_compiled_content_sha256"] != problem.content_sha256:
        _fail("/evaluation_plan/epr_compiled_content_sha256", "does not equal persisted EPR content identity")
    if problem_data["compilation"]["outcome"] == "FAIL":
        _fail("/epr/compilation/outcome", "FAIL EPRs cannot produce an executable plan or EER")
    _validate_bound_plan(plan, problem)
    return _new_bound_evaluation_plan(
        plan,
        problem,
        case_dir,
        engineering,
        problems,
        persisted,
        epr_file_sha256,
    )


def _assert_epr_fresh(bound_plan: BoundEvaluationPlan) -> None:
    case = _safe_case_directory(bound_plan.case_path)
    engineering, problems, persisted, problem, digest = _read_epr(
        case,
        bound_plan.engineering_problem.problem_id,
    )
    plan_data = bound_plan.evaluation_plan.to_dict()
    problem_data = problem.to_dict()
    if persisted.path != bound_plan.epr_path:
        _fail("/epr", "canonical EPR path changed after binding")
    if problem_data["case_id"] != plan_data["case_id"]:
        _fail("/epr/case_id", "case identity changed after binding")
    if problem.problem_id != plan_data["problem_id"]:
        _fail("/epr/problem_id", "problem identity changed after binding")
    if problem.content_sha256 != plan_data["epr_compiled_content_sha256"]:
        _fail("/epr/compiled_content_sha256", "compiled content identity changed after binding")
    if digest != bound_plan.epr_file_sha256 or persisted.data != bound_plan.epr_bytes:
        _fail("/epr", "exact persisted EPR bytes changed after binding")
    identities = (
        (case.identity, bound_plan._case_identity, "case"),
        (engineering.identity, bound_plan._engineering_identity, "engineering"),
        (problems.identity, bound_plan._problems_identity, "problems"),
        (persisted.identity, bound_plan._epr_identity, "EPR"),
    )
    for current, original, label in identities:
        if current != original:
            _fail("/epr", f"{label} filesystem object identity changed after binding")


def _validate_writer_binding(
    bound_plan: BoundEvaluationPlan,
    evaluation_result: EngineeringEvaluationResult,
) -> EngineeringEvaluationResult:
    try:
        result = EngineeringEvaluationResult.from_dict(evaluation_result.to_dict())
    except (KeyError, TypeError, ValueError) as exc:
        _fail("/engineering_evaluation_result", f"final reconstruction failed: {exc}")
    eer = result.to_dict()
    plan = bound_plan.evaluation_plan
    plan_data = plan.to_dict()
    expected = {
        "case_id": plan_data["case_id"],
        "problem_id": plan_data["problem_id"],
        "epr_reference": bound_plan.epr_reference,
        "epr_compiled_content_sha256": bound_plan.engineering_problem.content_sha256,
        "epr_file_sha256": bound_plan.epr_file_sha256,
        "evaluation_plan_sha256": plan.content_sha256,
    }
    for field, value in expected.items():
        if eer[field] != value:
            _fail(f"/engineering_evaluation_result/{field}", "does not match the bound Plan/EPR snapshot")
    if canonical_json_bytes(eer["evaluation_plan"]) != plan.canonical_bytes():
        _fail("/engineering_evaluation_result/evaluation_plan", "does not exactly match the bound EvaluationPlan")
    epr_level = bound_plan.engineering_problem.to_dict()["confidentiality_level"]
    if _CONFIDENTIALITY_RANK[eer["confidentiality_level"]] < _CONFIDENTIALITY_RANK[epr_level]:
        _fail("/engineering_evaluation_result/confidentiality_level", "must not downgrade EPR confidentiality")
    return result


def _independently_rebind(bound_plan: BoundEvaluationPlan) -> BoundEvaluationPlan:
    try:
        rebound = bind_evaluation_plan(bound_plan.case_path, bound_plan.evaluation_plan)
        comparisons = (
            (rebound.case_path, bound_plan.case_path, "canonical case path"),
            (rebound.epr_path, bound_plan.epr_path, "canonical EPR path"),
            (rebound.epr_bytes, bound_plan.epr_bytes, "exact EPR bytes"),
            (rebound.epr_file_sha256, bound_plan.epr_file_sha256, "exact EPR file SHA-256"),
            (
                rebound.engineering_problem.canonical_bytes(),
                bound_plan.engineering_problem.canonical_bytes(),
                "EngineeringProblem canonical content",
            ),
            (
                rebound.evaluation_plan.canonical_bytes(),
                bound_plan.evaluation_plan.canonical_bytes(),
                "EvaluationPlan canonical content",
            ),
        )
    except EngineeringEvaluationBindingError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        _fail("/bound_plan", f"cannot independently reconstruct supplied binding: {exc}")
    for actual, supplied, label in comparisons:
        if actual != supplied:
            _fail("/bound_plan", f"supplied wrapper differs from independently verified {label}")
    return rebound


def _existing_target(
    evaluations: _VerifiedDirectory,
    filename: str,
    data: bytes,
) -> _DescriptorRead | None:
    target = evaluations.path / filename
    try:
        os.lstat(target)
    except FileNotFoundError:
        return None
    except OSError as exc:
        _fail("/writer", f"cannot inspect EER target: {exc}")
    persisted = _safe_regular_file(evaluations, filename)
    if persisted.data != data:
        _fail("/writer", "different bytes already exist for this immutable EER ID")
    return persisted


def _open_directory_descriptor(directory: _VerifiedDirectory) -> int | None:
    if os.name == "nt" or not hasattr(os, "O_DIRECTORY"):
        return None
    flags = os.O_RDONLY | os.O_DIRECTORY
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor: int | None = None
    try:
        descriptor = os.open(directory.path, flags)
        metadata = os.fstat(descriptor)
        _require_safe_metadata(metadata, directory=True, label=str(directory.path))
        if _filesystem_identity(metadata) != directory.identity:
            raise OSError("opened publication directory has a different identity")
    except OSError as exc:
        if descriptor is not None:
            os.close(descriptor)
        _fail("/writer", f"cannot bind publication directory descriptor: {exc}")
    return descriptor


def _assert_temporary_identity(path: Path, identity: _FilesystemIdentity) -> None:
    try:
        metadata = os.lstat(path)
        _require_safe_metadata(metadata, directory=False, label="temporary EER file")
        if _filesystem_identity(metadata) != identity:
            raise OSError("temporary file pathname identity changed")
        if path.resolve(strict=True) != path:
            raise OSError("temporary file path is not exact and canonical")
    except (OSError, RuntimeError) as exc:
        _fail("/writer", f"temporary file became unsafe: {exc}")


def _link_temporary(
    temporary: Path,
    target: Path,
    directory_descriptor: int | None,
) -> None:
    if directory_descriptor is not None and os.link in os.supports_dir_fd:
        os.link(
            temporary.name,
            target.name,
            src_dir_fd=directory_descriptor,
            dst_dir_fd=directory_descriptor,
            follow_symlinks=False,
        )
    else:
        os.link(temporary, target)


def _cleanup_temporary(
    temporary: Path,
    identity: _FilesystemIdentity,
    directory_descriptor: int | None,
) -> None:
    try:
        if directory_descriptor is not None and os.stat in os.supports_dir_fd:
            try:
                metadata = os.stat(
                    temporary.name,
                    dir_fd=directory_descriptor,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                pass
            else:
                _require_safe_metadata(metadata, directory=False, label="temporary EER file")
                if _filesystem_identity(metadata) != identity:
                    raise OSError("temporary cleanup path identifies a different object")
                os.unlink(temporary.name, dir_fd=directory_descriptor)
                return
        try:
            metadata = os.lstat(temporary)
        except FileNotFoundError:
            return
        _require_safe_metadata(metadata, directory=False, label="temporary EER file")
        if _filesystem_identity(metadata) != identity:
            raise OSError("temporary cleanup path identifies a different object")
        os.unlink(temporary)
    except OSError as exc:
        raise EngineeringEvaluationBindingError(f"/writer: temporary cleanup failed: {exc}") from exc


def write_engineering_evaluation_result(
    bound_plan: BoundEvaluationPlan,
    evaluation_result: EngineeringEvaluationResult,
) -> Path:
    """Persist one EER atomically, idempotently, and without overwrite."""

    if not isinstance(bound_plan, BoundEvaluationPlan):
        raise TypeError("bound_plan must be a BoundEvaluationPlan")
    if not isinstance(evaluation_result, EngineeringEvaluationResult):
        raise TypeError("evaluation_result must be an EngineeringEvaluationResult")
    rebound = _independently_rebind(bound_plan)
    result = _validate_writer_binding(rebound, evaluation_result)
    data = canonical_json_bytes(result.to_dict())
    try:
        if EngineeringEvaluationResult.from_dict(json.loads(data.decode("utf-8"))).canonical_bytes() != data:
            _fail("/writer", "bytes being written do not reconstruct to the same canonical EER")
    except (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError, ValueError) as exc:
        _fail("/writer", f"bytes being written fail final EER reconstruction: {exc}")

    _assert_epr_fresh(rebound)
    case = _safe_case_directory(rebound.case_path)
    engineering = _safe_directory(case, "engineering")
    evaluations = _safe_directory(engineering, "evaluations", create=True)
    evaluation_id = result.evaluation_id
    if _EVALUATION_ID.fullmatch(evaluation_id) is None:
        _fail("/engineering_evaluation_result/evaluation_id", "must use exact EER-### syntax")
    target_name = f"{evaluation_id}.json"
    target = evaluations.path / target_name
    if _existing_target(evaluations, target_name, data) is not None:
        return target

    directory_descriptor = _open_directory_descriptor(evaluations)
    descriptor: int | None = None
    stream: Any = None
    temporary: Path | None = None
    temporary_identity: _FilesystemIdentity | None = None
    operation_error: Exception | None = None
    close_error: Exception | None = None
    cleanup_error: Exception | None = None
    valid_target_present = False
    try:
        _assert_directory_identity(case)
        _assert_directory_identity(engineering)
        _assert_directory_identity(evaluations)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{evaluation_id}.",
            suffix=".tmp",
            dir=evaluations.path,
        )
        temporary = _absolute_path(temporary_name)
        descriptor_metadata = os.fstat(descriptor)
        _require_safe_metadata(
            descriptor_metadata,
            directory=False,
            label="temporary EER descriptor",
        )
        temporary_identity = _filesystem_identity(descriptor_metadata)
        _assert_temporary_identity(temporary, temporary_identity)
        _assert_directory_identity(case)
        _assert_directory_identity(engineering)
        _assert_directory_identity(evaluations)
        if temporary.parent != evaluations.path:
            _fail("/writer", "temporary file is outside the verified evaluations directory")

        stream = os.fdopen(descriptor, "w+b")
        descriptor = None
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
        final_temporary = os.fstat(stream.fileno())
        _require_safe_metadata(
            final_temporary,
            directory=False,
            label="temporary EER descriptor",
        )
        if _filesystem_identity(final_temporary) != temporary_identity:
            _fail("/writer", "temporary descriptor identity changed during write")

        _assert_directory_identity(case)
        _assert_directory_identity(engineering)
        _assert_directory_identity(evaluations)
        _assert_temporary_identity(temporary, temporary_identity)
        _assert_epr_fresh(rebound)
        try:
            _link_temporary(temporary, target, directory_descriptor)
        except FileExistsError:
            if _existing_target(evaluations, target_name, data) is None:
                _fail("/writer", "EER target disappeared during collision verification")
            valid_target_present = True
        else:
            published = _safe_regular_file(evaluations, target_name)
            if published.data != data:
                _fail("/writer", "published EER bytes differ from the intended canonical bytes")
            if published.identity != temporary_identity:
                _fail("/writer", "published EER is not the verified temporary file object")
            valid_target_present = True
        _assert_directory_identity(case)
        _assert_directory_identity(engineering)
        _assert_directory_identity(evaluations)
    except Exception as exc:
        operation_error = exc
    finally:
        try:
            if stream is not None:
                stream.close()
            elif descriptor is not None:
                os.close(descriptor)
        except Exception as exc:
            close_error = exc
        if temporary is not None and temporary_identity is not None:
            try:
                _cleanup_temporary(temporary, temporary_identity, directory_descriptor)
            except Exception as exc:
                cleanup_error = exc
        if directory_descriptor is not None:
            try:
                os.close(directory_descriptor)
            except Exception as exc:
                if close_error is None:
                    close_error = exc
    if cleanup_error is not None:
        state = "a valid immutable EER is present" if valid_target_present else "publication did not complete"
        prior = operation_error or close_error
        detail = f"; prior operation error: {prior}" if prior is not None else ""
        raise EngineeringEvaluationBindingError(
            f"/writer: {state}, but deterministic temporary cleanup failed: {cleanup_error}{detail}"
        ) from cleanup_error
    if close_error is not None:
        state = "a valid immutable EER is present" if valid_target_present else "publication did not complete"
        raise EngineeringEvaluationBindingError(
            f"/writer: {state}, but closing the verified temporary descriptor failed: {close_error}"
        ) from close_error
    if operation_error is not None:
        if valid_target_present:
            raise EngineeringEvaluationBindingError(
                "/writer: a valid immutable EER was verified, but publication safety did not "
                f"complete: {operation_error}"
            ) from operation_error
        raise operation_error
    return target


def load_engineering_evaluation_result(
    case_path: str | os.PathLike[str],
    evaluation_id: str,
) -> PersistedEngineeringEvaluationResult:
    """Safely load and bind one exact canonical persisted EER file."""

    if type(evaluation_id) is not str or _EVALUATION_ID.fullmatch(evaluation_id) is None:
        _fail("/evaluation_id", "must use exact EER-### syntax")
    case_dir = _safe_case_directory(case_path)
    engineering = _safe_directory(case_dir, "engineering")
    evaluations = _safe_directory(engineering, "evaluations")
    persisted = _safe_regular_file(evaluations, f"{evaluation_id}.json")
    data = persisted.data
    _assert_directory_identity(case_dir)
    _assert_directory_identity(engineering)
    _assert_directory_identity(evaluations)
    value = _structured_json(data, "/engineering_evaluation_result")
    try:
        result = EngineeringEvaluationResult.from_dict(value)
    except (KeyError, TypeError, ValueError) as exc:
        _fail("/engineering_evaluation_result", f"reconstruction failed: {exc}")
    if result.evaluation_id != evaluation_id or persisted.path.stem != result.evaluation_id:
        _fail("/engineering_evaluation_result/evaluation_id", "does not match requested filename identity")
    if result.to_dict()["case_id"] != case_dir.path.name:
        _fail("/engineering_evaluation_result/case_id", "does not equal canonical case directory name")
    if canonical_json_bytes(result.to_dict()) != data:
        _fail("/engineering_evaluation_result", "persisted EER bytes are not the exact canonical representation")
    return _new_persisted_evaluation_result(
        result,
        case_dir,
        engineering,
        evaluations,
        persisted,
    )
