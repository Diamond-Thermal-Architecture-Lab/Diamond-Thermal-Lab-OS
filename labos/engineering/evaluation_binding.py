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
    evaluation_plan_sha256,
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
class BoundEvaluationPlan:
    """Deeply immutable runtime binding to exact persisted EPR bytes."""

    _evaluation_plan: EvaluationPlan
    _engineering_problem: EngineeringProblem
    _case_path: Path
    _epr_path: Path
    _epr_bytes: bytes
    _epr_file_sha256: str

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


@dataclass(frozen=True, slots=True)
class PersistedEngineeringEvaluationResult:
    """Deeply immutable runtime binding to exact persisted EER bytes."""

    _evaluation_result: EngineeringEvaluationResult
    _case_path: Path
    _eer_path: Path
    _eer_bytes: bytes
    _eer_file_sha256: str

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


def _safe_case_directory(case_path: str | os.PathLike[str]) -> Path:
    path = Path(case_path)
    try:
        if path.is_symlink():
            raise OSError("case path is a symlink")
        resolved = path.resolve(strict=True)
        if not resolved.is_dir() or resolved.is_symlink():
            raise OSError("case path is not a real directory")
    except (OSError, RuntimeError) as exc:
        _fail("/case_path", f"unsafe or missing case directory: {exc}")
    if _CASE_ID.fullmatch(resolved.name) is None:
        _fail("/case_path", "case directory name has invalid case ID syntax")
    return resolved


def _safe_directory(parent: Path, name: str, *, create: bool = False) -> Path:
    candidate = parent / name
    try:
        if not candidate.exists() and not candidate.is_symlink():
            if not create:
                raise OSError("directory is missing")
            try:
                candidate.mkdir()
            except FileExistsError:
                pass
        if candidate.is_symlink():
            raise OSError("directory is a symlink")
        resolved = candidate.resolve(strict=True)
        if resolved.parent != parent or not resolved.is_dir() or candidate.is_symlink():
            raise OSError("directory escaped case-local containment or is not real")
    except (OSError, RuntimeError) as exc:
        _fail("/filesystem", f"unsafe {name!r} directory: {exc}")
    return resolved


def _safe_regular_file(parent: Path, filename: str) -> tuple[Path, bytes]:
    candidate = parent / filename
    try:
        if candidate.is_symlink():
            raise OSError("target is a symlink")
        before = candidate.stat(follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode):
            raise OSError("target is not a regular file")
        resolved = candidate.resolve(strict=True)
        if resolved.parent != parent or resolved != candidate:
            raise OSError("target escaped its exact case-local directory")
        data = candidate.read_bytes()
        after = candidate.stat(follow_symlinks=False)
        if (before.st_dev, before.st_ino, before.st_size) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
        ):
            raise OSError("target changed during safe read")
        if candidate.is_symlink() or candidate.resolve(strict=True) != resolved:
            raise OSError("target changed or became unsafe during safe read")
    except (OSError, RuntimeError) as exc:
        _fail("/filesystem", f"cannot safely read {filename!r}: {exc}")
    return resolved, data


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


def _read_epr(case_dir: Path, problem_id: str) -> tuple[Path, bytes, EngineeringProblem, str]:
    engineering = _safe_directory(case_dir, "engineering")
    problems = _safe_directory(engineering, "problems")
    epr_path, data = _safe_regular_file(problems, f"{problem_id}.json")
    value = _structured_json(data, "/epr")
    try:
        problem = EngineeringProblem.from_dict(value)
    except (KeyError, TypeError, ValueError) as exc:
        _fail("/epr", f"EngineeringProblem reconstruction failed: {exc}")
    if canonical_json_bytes(problem.to_dict()) != data:
        _fail("/epr", "persisted EPR bytes are not the exact canonical representation")
    problem_data = problem.to_dict()
    if problem_data["case_id"] != case_dir.name:
        _fail("/epr/case_id", "does not equal the canonical case directory name")
    if problem.problem_id != problem_id or epr_path.stem != problem.problem_id:
        _fail("/epr/problem_id", "does not equal the requested EPR filename identity")
    return epr_path, data, problem, hashlib.sha256(data).hexdigest()


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
    if plan_data["case_id"] != case_dir.name:
        _fail("/evaluation_plan/case_id", "does not equal the canonical case directory name")
    epr_path, epr_bytes, problem, epr_file_sha256 = _read_epr(case_dir, plan_data["problem_id"])
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
    return BoundEvaluationPlan(
        plan,
        problem,
        case_dir,
        epr_path,
        epr_bytes,
        epr_file_sha256,
    )


def _assert_epr_fresh(bound_plan: BoundEvaluationPlan) -> None:
    epr_path, data, problem, digest = _read_epr(
        bound_plan.case_path,
        bound_plan.engineering_problem.problem_id,
    )
    plan_data = bound_plan.evaluation_plan.to_dict()
    problem_data = problem.to_dict()
    if epr_path != bound_plan.epr_path:
        _fail("/epr", "canonical EPR path changed after binding")
    if problem_data["case_id"] != plan_data["case_id"]:
        _fail("/epr/case_id", "case identity changed after binding")
    if problem.problem_id != plan_data["problem_id"]:
        _fail("/epr/problem_id", "problem identity changed after binding")
    if problem.content_sha256 != plan_data["epr_compiled_content_sha256"]:
        _fail("/epr/compiled_content_sha256", "compiled content identity changed after binding")
    if digest != bound_plan.epr_file_sha256 or data != bound_plan.epr_bytes:
        _fail("/epr", "exact persisted EPR bytes changed after binding")


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


def _existing_target(target: Path, parent: Path, data: bytes) -> bool:
    if target.is_symlink():
        _fail("/writer", "EER target is a symlink")
    if not target.exists():
        return False
    try:
        resolved = target.resolve(strict=True)
        if resolved.parent != parent or resolved != target or not target.is_file():
            raise OSError("target is not an exact case-local regular file")
        existing = target.read_bytes()
        if target.is_symlink() or target.resolve(strict=True) != resolved:
            raise OSError("target changed during collision verification")
    except (OSError, RuntimeError) as exc:
        _fail("/writer", f"unsafe EER target: {exc}")
    if existing != data:
        _fail("/writer", "different bytes already exist for this immutable EER ID")
    return True


def write_engineering_evaluation_result(
    bound_plan: BoundEvaluationPlan,
    evaluation_result: EngineeringEvaluationResult,
) -> Path:
    """Persist one EER atomically, idempotently, and without overwrite."""

    if not isinstance(bound_plan, BoundEvaluationPlan):
        raise TypeError("bound_plan must be a BoundEvaluationPlan")
    if not isinstance(evaluation_result, EngineeringEvaluationResult):
        raise TypeError("evaluation_result must be an EngineeringEvaluationResult")
    result = _validate_writer_binding(bound_plan, evaluation_result)
    data = canonical_json_bytes(result.to_dict())
    try:
        if EngineeringEvaluationResult.from_dict(json.loads(data.decode("utf-8"))).canonical_bytes() != data:
            _fail("/writer", "bytes being written do not reconstruct to the same canonical EER")
    except (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError, ValueError) as exc:
        _fail("/writer", f"bytes being written fail final EER reconstruction: {exc}")

    _assert_epr_fresh(bound_plan)
    engineering = _safe_directory(bound_plan.case_path, "engineering")
    evaluations = _safe_directory(engineering, "evaluations", create=True)
    evaluation_id = result.evaluation_id
    if _EVALUATION_ID.fullmatch(evaluation_id) is None:
        _fail("/engineering_evaluation_result/evaluation_id", "must use exact EER-### syntax")
    target = evaluations / f"{evaluation_id}.json"
    if _existing_target(target, evaluations, data):
        return target

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{evaluation_id}.",
        suffix=".tmp",
        dir=evaluations,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        _assert_epr_fresh(bound_plan)
        current_engineering = _safe_directory(bound_plan.case_path, "engineering")
        current_evaluations = _safe_directory(current_engineering, "evaluations")
        if current_evaluations != evaluations or temporary.parent != current_evaluations:
            _fail("/writer", "evaluations directory changed before publication")
        try:
            os.link(temporary, target)
        except FileExistsError:
            if not _existing_target(target, evaluations, data):
                _fail("/writer", "EER target appeared during publication")
        return target
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


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
    eer_path, data = _safe_regular_file(evaluations, f"{evaluation_id}.json")
    value = _structured_json(data, "/engineering_evaluation_result")
    try:
        result = EngineeringEvaluationResult.from_dict(value)
    except (KeyError, TypeError, ValueError) as exc:
        _fail("/engineering_evaluation_result", f"reconstruction failed: {exc}")
    if result.evaluation_id != evaluation_id or eer_path.stem != result.evaluation_id:
        _fail("/engineering_evaluation_result/evaluation_id", "does not match requested filename identity")
    if result.to_dict()["case_id"] != case_dir.name:
        _fail("/engineering_evaluation_result/case_id", "does not equal canonical case directory name")
    if canonical_json_bytes(result.to_dict()) != data:
        _fail("/engineering_evaluation_result", "persisted EER bytes are not the exact canonical representation")
    return PersistedEngineeringEvaluationResult(
        result,
        case_dir,
        eer_path,
        data,
        hashlib.sha256(data).hexdigest(),
    )
