"""Model-independent M16A EPR compiler and explicit safe writer."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from decimal import Decimal, localcontext
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from labos.checkers.case_file_checker import REQUIRED_CASE_FILES
from labos.evidence.validator import validate_evidence, validate_measurement_reference

from .problem import (
    COMPILER_POLICY_VERSION,
    HEAT_SOURCE_CONSISTENCY_POLICY_VERSION,
    PROBLEM_FORMAT_VERSION,
    EngineeringProblem,
    EngineeringProblemValidationError,
    _validate_complete_problem_view,
    _validate_heat_sources,
    candidate_content_sha256,
    engineering_problem_content_sha256,
)
from .quantities import UNIT_REGISTRY_VERSION, QuantifiedValue, QuantityKind, convert_quantity
from .serialization import CANONICAL_JSON_VERSION, canonical_json_bytes


__all__ = [
    "CompilationFailure",
    "CompiledEngineeringProblem",
    "compile_engineering_problem",
    "write_engineering_problem",
]


_AUTHORING_FIELDS = {
    "problem_id", "case_id", "title", "purpose", "selected_source_filenames",
    "requirements", "heat_sources", "baseline", "constraints", "candidates",
    "confidentiality_level",
}
_BASELINE_FIELDS = {"geometry", "materials", "interfaces", "boundary_conditions"}
_CANDIDATE_AUTHORING_FIELDS = {"candidate_id", "label", "parent_requirement_id", "overrides"}
_OVERRIDE_FIELDS = {"path", "value"}
_PROVENANCE_FIELDS = {
    "source_type", "reference", "evidence_object_ids", "measurement_reference_ids",
    "source_sha256", "review_status", "rationale",
}
_ENVELOPE_FIELDS = {
    "value", "unit", "quantity_kind", "provenance", "uncertainty", "confidence",
    "status", "conversion",
}
_CANONICAL_SOURCE_NAMES = frozenset(REQUIRED_CASE_FILES)
_ALLOWED_OVERRIDE_ROOTS = {"geometry", "materials", "interfaces", "boundary_conditions"}
_CASE_ID = re.compile(r"^[a-z0-9_-]+$")
_PROBLEM_ID = re.compile(r"^EPR-[0-9]{3}$")
_CANDIDATE_ID = re.compile(r"^CND-[0-9]{3}$")
_INTAKE_CASE_ID = re.compile(
    r"^case_id:\s*(?:['\"](?P<quoted>[^'\"]+)['\"]|(?P<plain>[^\s#]+))\s*(?:#.*)?$",
    re.MULTILINE,
)
_USABLE_STATUSES = {"provided", "assumed", "evidence_required"}
_STATUS_RANK = {"unverified": 0, "source_documented": 1, "reviewed": 2}


@dataclass(frozen=True)
class CompilationDiagnostic:
    """One deterministic no-emit compiler diagnostic."""

    rule_id: str
    field_paths: tuple[str, ...]
    message: str
    required_action: str


class CompilationFailure(ValueError):
    """Raised when no schema-valid EPR can safely be emitted or persisted."""

    def __init__(self, *diagnostics: CompilationDiagnostic) -> None:
        ordered = tuple(sorted(diagnostics, key=lambda item: (item.rule_id, item.field_paths, item.message)))
        self.diagnostics = ordered
        summary = "; ".join(f"{item.rule_id}: {item.message}" for item in ordered)
        super().__init__(summary or "M16A EPR compilation failed.")


@dataclass(frozen=True)
class CompiledEngineeringProblem:
    """Immutable successful compile result plus first-read source identity."""

    engineering_problem: EngineeringProblem
    case_path: Path
    source_case_sha256: Mapping[str, str]
    _sidecar_sha256: Mapping[str, str]

    @property
    def canonical_bytes(self) -> bytes:
        return self.engineering_problem.canonical_bytes()


def _diagnostic(rule_id: str, path: str, message: str, action: str) -> CompilationDiagnostic:
    return CompilationDiagnostic(rule_id, (path,), message, action)


def _abort(rule_id: str, path: str, message: str, action: str) -> None:
    raise CompilationFailure(_diagnostic(rule_id, path, message, action))


def _closed_mapping(value: Any, expected: set[str], path: str, rule_id: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or any(type(key) is not str for key in value):
        _abort(rule_id, path, "Expected a structured object.", "Supply the documented closed object shape.")
    missing = expected - set(value)
    extra = set(value) - expected
    if missing or extra:
        detail = []
        if missing:
            detail.append(f"missing {sorted(missing)!r}")
        if extra:
            detail.append(f"unexpected {sorted(extra)!r}")
        _abort(rule_id, path, "Invalid authoring shape: " + ", ".join(detail) + ".", "Use only the documented authoring fields.")
    return dict(value)


def _case_directory(case_path: str | os.PathLike[str]) -> Path:
    path = Path(case_path)
    try:
        if path.is_symlink():
            raise OSError("case path is a symlink")
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        _abort("M16A-EPR-SOURCE-001", "/case_path", f"Unsafe or missing case directory: {exc}", "Use a real canonical case directory.")
    if not resolved.is_dir() or not _CASE_ID.fullmatch(resolved.name):
        _abort("M16A-EPR-SOURCE-001", "/case_path", "Case path must resolve to a safely named directory.", "Use a canonical case directory named by its case_id.")
    return resolved


def _safe_relative_parts(reference: Any, path: str, *, rule_id: str) -> tuple[str, ...]:
    if type(reference) is not str or not reference:
        _abort(rule_id, path, "Reference must be a non-empty relative POSIX path.", "Supply a safe case-local reference.")
    candidate = Path(reference)
    parts = tuple(reference.split("/"))
    if candidate.is_absolute() or re.match(r"^[A-Za-z]:", reference) or "\\" in reference:
        _abort(rule_id, path, "Absolute paths and backslashes are forbidden.", "Use a case-relative POSIX path.")
    if not parts or any(part in {"", ".", ".."} for part in parts):
        _abort(rule_id, path, "Dot, traversal, and empty path components are forbidden.", "Use a direct canonical relative path.")
    return parts


def _read_numbered_source(case_dir: Path, filename: Any) -> tuple[bytes, str]:
    parts = _safe_relative_parts(filename, "/selected_source_filenames", rule_id="M16A-EPR-SOURCE-001")
    if len(parts) != 1 or filename not in _CANONICAL_SOURCE_NAMES:
        _abort("M16A-EPR-SOURCE-001", "/selected_source_filenames", f"Unapproved canonical source filename: {filename!r}.", "Select only an approved root-level numbered case filename.")
    path = case_dir / filename
    try:
        if path.is_symlink():
            raise OSError("source is a symlink")
        resolved = path.resolve(strict=True)
        if resolved.parent != case_dir or not resolved.is_file():
            raise OSError("source is not a regular case-root file")
        data = resolved.read_bytes()
    except (OSError, RuntimeError) as exc:
        _abort("M16A-EPR-SOURCE-001", f"/source_case_sha256/{filename}", f"Cannot safely read canonical source {filename!r}: {exc}", "Restore a non-symlink regular canonical source file.")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as exc:
        _abort("M16A-EPR-SOURCE-001", f"/source_case_sha256/{filename}", f"Canonical source is not valid UTF-8: {exc}", "Persist the canonical source as UTF-8.")
    return data, hashlib.sha256(data).hexdigest()


def _read_sources(case_dir: Path, selected: Any) -> tuple[dict[str, bytes], dict[str, str]]:
    if type(selected) is not list or any(type(item) is not str for item in selected):
        _abort("M16A-EPR-SOURCE-001", "/selected_source_filenames", "Selected sources must be an array of filename strings.", "Supply an explicit array of approved canonical filenames.")
    if len(selected) != len(set(selected)):
        _abort("M16A-EPR-SOURCE-001", "/selected_source_filenames", "Selected sources contain duplicates.", "Select each canonical filename at most once.")
    names = sorted(set(selected) | {"00_problem_intake.yml"})
    buffers: dict[str, bytes] = {}
    hashes: dict[str, str] = {}
    for name in names:
        data, digest = _read_numbered_source(case_dir, name)
        buffers[name] = data
        hashes[name] = digest
    return buffers, hashes


def _intake_case_id(data: bytes) -> str:
    text = data.decode("utf-8")
    matches = list(_INTAKE_CASE_ID.finditer(text))
    if len(matches) != 1:
        _abort("M16A-EPR-SOURCE-002", "/case_id", "Mandatory intake has no unambiguous top-level case_id.", "Add one explicit case_id scalar to 00_problem_intake.yml.")
    match = matches[0]
    value = match.group("quoted") or match.group("plain")
    if not _CASE_ID.fullmatch(value):
        _abort("M16A-EPR-SOURCE-002", "/case_id", "Mandatory intake case_id has invalid syntax.", "Use the canonical safe case ID.")
    return value


def _normalize_helper(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        _abort("M16A-EPR-QTY-001", path, "Uncertainty quantity helper must be an object.", "Supply value, unit, quantity_kind, and optional conversion.")
    allowed = {"value", "unit", "quantity_kind", "conversion"}
    required = {"value", "unit", "quantity_kind"}
    if required - set(value) or set(value) - allowed:
        _abort("M16A-EPR-QTY-001", path, "Uncertainty quantity helper has an invalid shape.", "Supply only value, unit, quantity_kind, and optional conversion.")
    quantity = _normalize_quantity(value, path, allow_missing=False)
    return {
        "value": quantity.to_dict()["canonical_value"],
        "unit": quantity.canonical_unit,
        "quantity_kind": quantity.quantity_kind.value,
        "conversion": quantity.conversion.to_dict(),
    }


def _normalize_quantity(value: Mapping[str, Any], path: str, *, allow_missing: bool) -> QuantifiedValue:
    kind_value = value.get("quantity_kind")
    raw_value = value.get("value")
    unit = value.get("unit")
    try:
        kind = QuantityKind(kind_value)
        if allow_missing and raw_value is None:
            return convert_quantity(kind, "0", unit)
        generated = convert_quantity(kind, raw_value, unit)
    except (TypeError, ValueError) as exc:
        _abort("M16A-EPR-QTY-001", path, f"Quantity cannot be normalized through I1: {exc}", "Supply an explicit decimal string and registered unit for the declared kind.")
    supplied = value.get("conversion")
    if supplied is None:
        return generated
    if supplied == generated.conversion.to_dict():
        return generated
    try:
        persisted = QuantifiedValue.from_dict({
            "quantity_kind": kind.value,
            "canonical_value": raw_value,
            "canonical_unit": unit,
            "conversion": supplied,
        })
    except (TypeError, ValueError) as exc:
        _abort("M16A-EPR-QTY-001", path, f"Supplied conversion does not reconstruct through I1: {exc}", "Remove the forged conversion or supply the exact I1 conversion record.")
    return persisted


def _normalize_uncertainty(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        _abort("M16A-EPR-UNC-001", path, "Uncertainty must be a structured object.", "Supply one documented uncertainty variant.")
    result = dict(value)
    kind = result.get("kind")
    expected = {
        "not_provided": {"kind", "basis"},
        "not_applicable": {"kind", "basis"},
        "absolute": {"kind", "basis", "amount"},
        "relative": {"kind", "basis", "fraction"},
        "interval": {"kind", "basis", "lower", "upper"},
    }.get(kind)
    if expected is None or set(result) != expected:
        _abort("M16A-EPR-UNC-001", path, "Uncertainty variant has an invalid closed shape.", "Use one documented uncertainty variant without extra fields.")
    for field in ("amount", "fraction", "lower", "upper"):
        if field in result:
            result[field] = _normalize_helper(result[field], f"{path}/{field}")
    return result


def _normalize_provenance(value: Any, path: str) -> dict[str, Any]:
    return copy.deepcopy(_closed_mapping(value, _PROVENANCE_FIELDS, path, "M16A-EPR-PROV-001"))


def _normalize_envelope(value: Mapping[str, Any], path: str) -> dict[str, Any]:
    keys = set(value)
    if keys - _ENVELOPE_FIELDS or (_ENVELOPE_FIELDS - {"conversion"}) - keys:
        _abort("M16A-EPR-QTY-001", path, "Quantity envelope has an invalid closed shape.", "Supply the documented envelope fields; conversion may be omitted before compilation.")
    status = value.get("status")
    if status not in {"provided", "assumed", "missing", "conflicting", "evidence_required"}:
        _abort("M16A-EPR-QTY-001", path, "Quantity status is invalid.", "Use a documented persisted quantity status.")
    quantity = _normalize_quantity(value, path, allow_missing=status == "missing")
    if status == "missing":
        if value.get("value") is not None or value.get("conversion") is not None:
            _abort("M16A-EPR-QTY-001", path, "Missing quantity must have null value and conversion.", "Use the exact missing-value envelope form.")
        normalized_value: str | None = None
        conversion: dict[str, Any] | None = None
    else:
        if type(value.get("value")) is not str:
            _abort("M16A-EPR-QTY-001", path, "Physical numeric input must be an explicit decimal string.", "Do not supply JSON numbers or free-text numeric values.")
        normalized_value = quantity.to_dict()["canonical_value"]
        conversion = quantity.conversion.to_dict()
    return {
        "value": normalized_value,
        "unit": quantity.canonical_unit,
        "quantity_kind": quantity.quantity_kind.value,
        "provenance": _normalize_provenance(value["provenance"], f"{path}/provenance"),
        "uncertainty": _normalize_uncertainty(value["uncertainty"], f"{path}/uncertainty"),
        "confidence": copy.deepcopy(value["confidence"]),
        "status": status,
        "conversion": conversion,
    }


def _normalize_tree(value: Any, path: str) -> Any:
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            _abort("M16A-EPR-SCHEMA-001", path or "/", "Structured object keys must be strings.", "Use JSON-compatible string keys only.")
        if {"value", "unit", "quantity_kind", "provenance", "uncertainty", "confidence", "status"}.issubset(value):
            return _normalize_envelope(value, path)
        return {key: _normalize_tree(item, f"{path}/{_escape(key)}") for key, item in value.items()}
    if type(value) is list:
        return [_normalize_tree(item, f"{path}/{index}") for index, item in enumerate(value)]
    return copy.deepcopy(value)


def _canonicalize_view(view: dict[str, Any]) -> dict[str, Any]:
    geometry = view["geometry"]
    geometry["layers"] = sorted(geometry["layers"], key=lambda item: (item.get("order", -1), item.get("layer_id", "")))
    materials = sorted(view["materials"], key=lambda item: item.get("material_id", ""))
    for material in materials:
        material["thermal_properties"] = sorted(material["thermal_properties"], key=lambda item: item.get("property_id", ""))
    layer_order = {layer.get("layer_id"): layer.get("order", -1) for layer in geometry["layers"]}
    interfaces = sorted(view["interfaces"], key=lambda item: (layer_order.get(item.get("upstream_layer_id"), -1), item.get("interface_id", "")))
    return {
        "geometry": geometry,
        "materials": materials,
        "interfaces": interfaces,
        "boundary_conditions": view["boundary_conditions"],
    }


def _escape(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def _decode_pointer(pointer: Any) -> tuple[str, ...]:
    if type(pointer) is not str or not pointer.startswith("/") or pointer == "/":
        raise ValueError("pointer must be a non-empty RFC 6901 path")
    tokens: list[str] = []
    for raw in pointer.split("/")[1:]:
        if re.search(r"~(?![01])", raw):
            raise ValueError("pointer contains an invalid RFC 6901 escape")
        token = raw.replace("~1", "/").replace("~0", "~")
        if not token or token in {"*", "-"} or "*" in token:
            raise ValueError("pointer contains a forbidden wildcard, insertion, or empty token")
        tokens.append(token)
    if tokens[0] not in _ALLOWED_OVERRIDE_ROOTS:
        raise ValueError("pointer root is outside baseline authority")
    return tuple(tokens)


def _pointer_target(document: Any, tokens: Sequence[str]) -> tuple[Any, str | int]:
    current = document
    for token in tokens[:-1]:
        if isinstance(current, Mapping):
            if token not in current:
                raise ValueError("pointer target does not exist")
            current = current[token]
        elif type(current) is list:
            if not token.isdigit() or str(int(token)) != token or int(token) >= len(current):
                raise ValueError("pointer array index does not resolve canonically")
            current = current[int(token)]
        else:
            raise ValueError("pointer traverses a scalar")
    final = tokens[-1]
    if isinstance(current, Mapping):
        if final not in current:
            raise ValueError("pointer target does not exist")
        return current, final
    if type(current) is list:
        if not final.isdigit() or str(int(final)) != final or int(final) >= len(current):
            raise ValueError("pointer array index does not resolve canonically")
        return current, int(final)
    raise ValueError("pointer target parent is a scalar")


def _finding(rule_id: str, paths: Sequence[str], message: str, action: str) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "classification": "STRUCTURAL_MODEL_INDEPENDENT",
        "field_paths": sorted(set(paths)),
        "message": message,
        "required_action": action,
    }


def _resolve_candidate(baseline: dict[str, Any], declaration: Mapping[str, Any], candidate_path: str) -> tuple[dict[str, Any], list[str], list[dict[str, Any]]]:
    declaration = _closed_mapping(declaration, _CANDIDATE_AUTHORING_FIELDS, candidate_path, "M16A-EPR-CND-001")
    overrides = declaration["overrides"]
    if type(overrides) is not list:
        _abort("M16A-EPR-CND-001", candidate_path + "/overrides", "Overrides must be an array.", "Supply replace-only override records.")
    parsed: list[tuple[str, tuple[str, ...], Any]] = []
    issues: list[str] = []
    for index, raw in enumerate(overrides):
        try:
            override = _closed_mapping(raw, _OVERRIDE_FIELDS, f"{candidate_path}/overrides/{index}", "M16A-EPR-CND-001")
            tokens = _decode_pointer(override["path"])
            _pointer_target(baseline, tokens)
            parsed.append((override["path"], tokens, override["value"]))
        except CompilationFailure:
            raise
        except (TypeError, ValueError) as exc:
            issues.append(str(exc))
    pointers = [item[0] for item in parsed]
    if len(pointers) != len(set(pointers)):
        issues.append("duplicate override pointer")
    ordered_tokens = sorted((item[1] for item in parsed), key=lambda item: "/".join(item))
    for left, right in zip(ordered_tokens, ordered_tokens[1:]):
        if len(left) < len(right) and right[:len(left)] == left:
            issues.append("ancestor/descendant override overlap")
    if issues:
        finding = _finding(
            "M16A-EPR-CND-003", [candidate_path],
            "Candidate override set is unresolved: " + "; ".join(sorted(set(issues))) + ".",
            "Correct the replace-only non-overlapping pointers and recompile.",
        )
        return copy.deepcopy(baseline), [], [finding]
    resolved = copy.deepcopy(baseline)
    for pointer, tokens, replacement in sorted(parsed, key=lambda item: item[0]):
        parent, key = _pointer_target(resolved, tokens)
        parent[key] = copy.deepcopy(replacement)
    try:
        normalized = _canonicalize_view(_normalize_tree(resolved, candidate_path))
        _validate_complete_problem_view(
            normalized["geometry"], normalized["materials"], normalized["interfaces"],
            normalized["boundary_conditions"], candidate_path,
        )
    except (CompilationFailure, EngineeringProblemValidationError, AttributeError, KeyError, TypeError) as exc:
        finding = _finding(
            "M16A-EPR-CND-003", [candidate_path],
            f"Candidate replacement does not resolve to a valid complete view: {exc}",
            "Correct the replacement shape or references and recompile.",
        )
        return copy.deepcopy(baseline), [], [finding]
    return normalized, sorted(pointers), []


def _walk_envelopes(value: Any, path: str = "") -> list[tuple[str, Mapping[str, Any]]]:
    found: list[tuple[str, Mapping[str, Any]]] = []
    if isinstance(value, Mapping):
        if _ENVELOPE_FIELDS.issubset(value):
            found.append((path, value))
        else:
            for key, item in value.items():
                found.extend(_walk_envelopes(item, f"{path}/{_escape(str(key))}"))
    elif type(value) is list:
        for index, item in enumerate(value):
            found.extend(_walk_envelopes(item, f"{path}/{index}"))
    return found


def _walk_provenance(value: Any, path: str = "", envelope_status: str | None = None) -> list[tuple[str, Mapping[str, Any], str | None]]:
    found: list[tuple[str, Mapping[str, Any], str | None]] = []
    if isinstance(value, Mapping):
        status = value.get("status") if _ENVELOPE_FIELDS.issubset(value) else envelope_status
        for key, item in value.items():
            child = f"{path}/{_escape(str(key))}"
            if key == "provenance" and isinstance(item, Mapping) and set(item) == _PROVENANCE_FIELDS:
                found.append((child, item, status))
            else:
                found.extend(_walk_provenance(item, child, status))
    elif type(value) is list:
        for index, item in enumerate(value):
            found.extend(_walk_provenance(item, f"{path}/{index}", envelope_status))
    return found


def _safe_sidecar(case_dir: Path, reference: str, expected_folder: str, expected_name: str) -> tuple[Path, bytes, dict[str, Any]]:
    parts = _safe_relative_parts(reference, "/provenance/reference", rule_id="M16A-EPR-PROV-001")
    if parts != (expected_folder, expected_name):
        raise ValueError(f"reference must equal {expected_folder}/{expected_name}")
    folder = case_dir / expected_folder
    if folder.is_symlink() or not folder.is_dir() or folder.resolve(strict=True).parent != case_dir:
        raise ValueError("sidecar parent is not a real case-local directory")
    path = case_dir.joinpath(*parts)
    if path.is_symlink():
        raise ValueError("sidecar is a symlink")
    resolved = path.resolve(strict=True)
    if resolved.parent != folder.resolve(strict=True) or not resolved.is_file():
        raise ValueError("sidecar is not a regular file in the expected case-local directory")
    data = resolved.read_bytes()
    parsed = json.loads(data.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("sidecar must contain a JSON object")
    return resolved, data, parsed


def _actual_review_status(source_type: str, sidecar_status: Any) -> str:
    if sidecar_status == "reviewed":
        return "reviewed"
    if sidecar_status == "rejected":
        return "rejected"
    if source_type == "evidence_object" and sidecar_status == "draft":
        return "source_documented"
    if source_type == "measurement_reference" and sidecar_status in {"completed"}:
        return "source_documented"
    return "unverified"


def _provenance_reality(case_dir: Path, problem: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    findings: list[dict[str, Any]] = []
    snapshots: dict[str, str] = {}
    for path, provenance, envelope_status in _walk_provenance(problem):
        source_type = provenance.get("source_type")
        if source_type not in {"evidence_object", "measurement_reference"}:
            continue
        try:
            evd_id = provenance["evidence_object_ids"][0]
            if source_type == "evidence_object":
                declared_id = evd_id
                sidecar_path, data, sidecar = _safe_sidecar(case_dir, provenance["reference"], "evidence", f"{evd_id}.json")
                validation = validate_evidence(case_dir, sidecar_path)
                id_field = "evidence_id"
            else:
                msr_id = provenance["measurement_reference_ids"][0]
                declared_id = msr_id
                sidecar_path, data, sidecar = _safe_sidecar(case_dir, provenance["reference"], "measurements", f"{msr_id}.json")
                validation = validate_measurement_reference(case_dir, sidecar_path)
                id_field = "measurement_id"
                evd_path, evd_data, evd = _safe_sidecar(case_dir, f"evidence/{evd_id}.json", "evidence", f"{evd_id}.json")
                evd_validation = validate_evidence(case_dir, evd_path)
                snapshots[f"evidence/{evd_id}.json"] = hashlib.sha256(evd_data).hexdigest()
                if evd_validation.status == "FAIL" or evd.get("evidence_id") != evd_id or evd.get("case_id") != problem["case_id"]:
                    raise ValueError("owning Evidence Object fails repository validation or identity binding")
                if sidecar.get("evidence_id") != evd_id:
                    raise ValueError("Measurement Reference points to the wrong Evidence Object")
            digest = hashlib.sha256(data).hexdigest()
            snapshots[provenance["reference"]] = digest
            if validation.status == "FAIL":
                raise ValueError("existing Evidence/Measurement validator rejected the sidecar")
            if sidecar.get(id_field) != declared_id:
                raise ValueError("declared ID does not match sidecar ID")
            if sidecar.get("case_id") != problem["case_id"]:
                raise ValueError("sidecar case_id does not match EPR case_id")
            if provenance.get("source_sha256") != digest:
                raise ValueError("declared source_sha256 does not match exact sidecar bytes")
            actual = _actual_review_status(source_type, sidecar.get("status"))
            declared = provenance.get("review_status")
            if declared in _STATUS_RANK and actual in _STATUS_RANK and _STATUS_RANK[declared] > _STATUS_RANK[actual]:
                raise ValueError("EPR review_status overclaims the linked sidecar status")
            if declared == "reviewed" and actual != "reviewed":
                raise ValueError("reviewed disposition requires a reviewed sidecar")
            if declared == "rejected" and actual != "rejected":
                raise ValueError("rejected disposition requires a rejected sidecar")
            if actual == "rejected" and envelope_status not in {"conflicting", "evidence_required"}:
                raise ValueError("rejected sidecar requires conflicting or evidence_required value status")
            if declared == "not_applicable":
                raise ValueError("linked sidecar cannot use not_applicable review disposition")
        except (CompilationFailure, IndexError, KeyError, OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
            findings.append(_finding(
                "M16A-EPR-PROV-001", [path], f"Linked provenance does not match repository reality: {exc}.",
                "Correct the safe sidecar reference, identity, hash, linkage, validation, or review disposition.",
            ))
    return findings, snapshots


def _candidate_state_paths(view: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    assumed: list[str] = []
    evidence: list[str] = []
    for path, envelope in _walk_envelopes(view):
        if envelope["status"] == "assumed":
            assumed.append(path)
        elif envelope["status"] == "evidence_required":
            evidence.append(path)
    return sorted(assumed), sorted(evidence)


def _unknowns_and_findings(problem: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str], bool, bool]:
    records: list[tuple[str, str, str, str, str, str]] = []
    blocking: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    assumptions: list[str] = []
    has_hold = False
    has_fail = False
    heat_alternatives: dict[str, bool] = {}
    for index, source in enumerate(problem["heat_sources"]):
        power_usable = source["total_power"]["status"] in _USABLE_STATUSES
        flux_usable = source["heat_flux"]["status"] in _USABLE_STATUSES
        heat_alternatives[f"/heat_sources/{index}/total_power"] = flux_usable
        heat_alternatives[f"/heat_sources/{index}/heat_flux"] = power_usable
    scan = {key: value for key, value in problem.items() if key not in {"unknowns", "compilation", "compiled_content_sha256"}}
    for path, envelope in _walk_envelopes(scan):
        state = envelope["status"]
        if envelope["uncertainty"]["kind"] == "not_provided":
            warnings.append(_finding("M16A-EPR-UNC-001", [path + "/uncertainty"], "Numeric uncertainty was not provided.", "Document uncertainty when available; do not treat it as zero."))
        if state not in {"missing", "assumed", "conflicting", "evidence_required"}:
            continue
        impact = "requires_later_acknowledgement" if state == "assumed" else "blocking"
        if state == "missing" and heat_alternatives.get(path, False):
            impact = "non_blocking"
        reason = {
            "missing": "The structured quantity is explicitly missing.",
            "assumed": "The structured quantity is explicitly assumed.",
            "conflicting": "The structured quantity is explicitly conflicting.",
            "evidence_required": "The structured quantity requires evidence disposition.",
        }[state]
        records.append((path, state, reason, "The state is visible to later engineering evaluation.", impact, "Resolve or acknowledge the explicit quantity state with traceable evidence."))
        if state == "assumed":
            assumptions.append(path)
        elif state == "conflicting":
            has_fail = True
            blocking.append(_finding("M16A-EPR-QTY-002", [path], "A persisted quantity is explicitly conflicting.", "Resolve the conflicting authoritative inputs before evaluation."))
        elif state == "evidence_required" or (state == "missing" and impact == "blocking"):
            has_hold = True
        if state != "missing" and envelope["value"] is not None:
            value = Decimal(envelope["value"])
            kind = envelope["quantity_kind"]
            if (kind != QuantityKind.TEMPERATURE_DIFFERENCE.value and value < 0) or (kind == QuantityKind.PHYSICAL_DIMENSIONLESS.value and value > 1):
                has_fail = True
                blocking.append(_finding("M16A-EPR-QTY-003", [path], "Quantity violates the model-independent physical range policy.", "Correct the explicit sign or fraction range."))
    unknowns: list[dict[str, Any]] = []
    for index, record in enumerate(sorted(set(records)), start=1):
        path, state, reason, consequence, impact, action = record
        unknowns.append({
            "unknown_id": f"UNK-{index:03d}", "field_path": path, "state": state,
            "reason": reason, "consequence": consequence, "readiness_impact": impact,
            "next_evidence_action": action,
        })
    return unknowns, blocking, warnings, sorted(set(assumptions)), has_hold, has_fail


def _heat_findings(problem: Mapping[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for index, source in enumerate(problem["heat_sources"]):
        power, flux, area = source["total_power"], source["heat_flux"], source["heated_area"]
        if all(item["status"] in _USABLE_STATUSES for item in (power, flux, area)):
            with localcontext() as context:
                context.prec = 384
                p = Decimal(power["value"])
                qa = Decimal(flux["value"]) * Decimal(area["value"])
                maximum = max(abs(p), abs(qa))
                consistent = (p == 0 and qa == 0) or abs(p - qa) <= Decimal("0.001") * maximum
            if not consistent:
                findings.append(_finding(
                    "M16A-EPR-HEAT-001",
                    [f"/heat_sources/{index}/heat_flux", f"/heat_sources/{index}/heated_area", f"/heat_sources/{index}/total_power"],
                    "Explicit power differs from heat flux multiplied by heated area beyond the 0.001 relative tolerance.",
                    "Resolve the conflicting source quantities; the compiler will not infer a replacement.",
                ))
    return findings


def _sort_findings(findings: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    unique = {(item["rule_id"], tuple(item["field_paths"]), item["message"], item["required_action"]): item for item in findings}
    return sorted(unique.values(), key=lambda item: (item["rule_id"], tuple(item["field_paths"]), item["message"]))


def _schema_family(message: str) -> str:
    lowered = message.lower()
    for marker, family in (
        ("interface", "IFC"), ("material", "MAT"), ("geometry", "GEOM"),
        ("boundary", "BC"), ("candidate", "CND"), ("reference", "REF"),
        ("unknown", "UNKNOWN"), ("confidentiality", "CONF"), ("quantity", "QTY"),
    ):
        if marker in lowered:
            return family
    return "SCHEMA"


def _compile_engineering_problem(
    case_path: str | os.PathLike[str],
    authoring: Mapping[str, Any],
) -> CompiledEngineeringProblem:
    """Compile explicit structured authoring data without writing to disk."""

    case_dir = _case_directory(case_path)
    raw = _closed_mapping(authoring, _AUTHORING_FIELDS, "/", "M16A-EPR-SCHEMA-001")
    buffers, source_hashes = _read_sources(case_dir, raw["selected_source_filenames"])
    intake_id = _intake_case_id(buffers["00_problem_intake.yml"])
    case_id = raw["case_id"]
    if type(case_id) is not str or not _CASE_ID.fullmatch(case_id):
        _abort("M16A-EPR-ID-001", "/case_id", "Authoring case_id has invalid syntax.", "Use the canonical safe case ID.")
    if not (case_dir.name == intake_id == case_id):
        _abort("M16A-EPR-SOURCE-002", "/case_id", "Case directory, intake case_id, and authoring case_id do not match.", "Bind all three identities before compilation.")
    if type(raw["problem_id"]) is not str or not _PROBLEM_ID.fullmatch(raw["problem_id"]):
        _abort("M16A-EPR-ID-001", "/problem_id", "Authoring problem_id has invalid syntax.", "Use EPR-###.")
    baseline_raw = _closed_mapping(raw["baseline"], _BASELINE_FIELDS, "/baseline", "M16A-EPR-SCHEMA-001")
    baseline = _canonicalize_view(_normalize_tree(baseline_raw, ""))
    try:
        _validate_complete_problem_view(
            baseline["geometry"], baseline["materials"], baseline["interfaces"],
            baseline["boundary_conditions"], "",
        )
    except (EngineeringProblemValidationError, KeyError, TypeError) as exc:
        family = _schema_family(str(exc))
        _abort(f"M16A-EPR-{family}-001", "/baseline", f"Normalized baseline is invalid under I2A: {exc}", "Correct the explicit baseline; no EPR was emitted.")
    requirements = _normalize_tree(raw["requirements"], "/requirements")
    heat_sources = _normalize_tree(raw["heat_sources"], "/heat_sources")
    constraints = _normalize_tree(raw["constraints"], "/constraints")
    if type(requirements) is not list or type(heat_sources) is not list or type(constraints) is not list:
        _abort("M16A-EPR-SCHEMA-001", "/", "Requirements, heat_sources, and constraints must be arrays.", "Supply the explicit structured arrays.")
    requirements.sort(key=lambda item: item.get("requirement_id", "") if isinstance(item, Mapping) else "")
    heat_sources.sort(key=lambda item: item.get("source_id", "") if isinstance(item, Mapping) else "")
    constraints.sort(key=lambda item: item.get("constraint_id", "") if isinstance(item, Mapping) else "")
    try:
        _validate_heat_sources(heat_sources, {layer["layer_id"] for layer in baseline["geometry"]["layers"]}, "/heat_sources")
    except (EngineeringProblemValidationError, KeyError, TypeError) as exc:
        _abort("M16A-EPR-HEAT-002", "/heat_sources", f"Heat-source authoring is invalid under I2A: {exc}", "Correct the explicit heat-source structure; no EPR was emitted.")
    if not requirements:
        _abort("M16A-EPR-REF-001", "/requirements", "At least one requirement is required to parent candidates.", "Add one explicit requirement.")
    candidate_declarations = raw["candidates"]
    if type(candidate_declarations) is not list or len(candidate_declarations) < 2:
        _abort("M16A-EPR-CND-001", "/candidates", "One baseline declaration and at least one variant declaration are required.", "Declare CND-001 with no overrides plus at least one variant.")
    normalized_declarations: list[dict[str, Any]] = []
    for index, declaration in enumerate(candidate_declarations):
        normalized_declarations.append(_closed_mapping(declaration, _CANDIDATE_AUTHORING_FIELDS, f"/candidates/{index}", "M16A-EPR-CND-001"))
    candidate_ids = [item["candidate_id"] for item in normalized_declarations]
    if any(type(item) is not str or _CANDIDATE_ID.fullmatch(item) is None for item in candidate_ids) or len(candidate_ids) != len(set(candidate_ids)):
        _abort("M16A-EPR-ID-001", "/candidates", "Candidate declarations require unique CND-### IDs.", "Correct the candidate IDs before compilation.")
    normalized_declarations.sort(key=lambda item: item["candidate_id"])
    if normalized_declarations[0]["candidate_id"] != "CND-001" or normalized_declarations[0]["overrides"] != []:
        _abort("M16A-EPR-CND-001", "/candidates", "CND-001 must explicitly declare the compiler-generated baseline with an empty override list.", "Declare baseline metadata explicitly without hand-authoring its resolved content.")
    baseline_declaration = normalized_declarations[0]
    candidate_declarations = normalized_declarations[1:]
    constraint_ids = sorted(item.get("constraint_id", "") for item in constraints if isinstance(item, Mapping))
    baseline_candidate = {
        "candidate_id": "CND-001", "candidate_role": "baseline",
        "label": copy.deepcopy(baseline_declaration["label"]),
        "parent_requirement_id": copy.deepcopy(baseline_declaration["parent_requirement_id"]),
        **copy.deepcopy(baseline), "changed_field_paths": [],
        "applicable_constraint_ids": constraint_ids,
    }
    baseline_assumed, baseline_evidence = _candidate_state_paths(baseline)
    baseline_candidate["assumption_paths"] = baseline_assumed
    baseline_candidate["evidence_required_paths"] = baseline_evidence
    baseline_candidate["resolved_content_sha256"] = "0" * 64
    baseline_candidate["resolved_content_sha256"] = candidate_content_sha256(baseline_candidate)
    candidates = [baseline_candidate]
    candidate_findings: list[dict[str, Any]] = []
    for index, declaration in enumerate(candidate_declarations, start=1):
        declaration_path = f"/candidates/{index}"
        resolved, changed, issues = _resolve_candidate(baseline, declaration, declaration_path)
        candidate = {
            "candidate_id": declaration.get("candidate_id") if isinstance(declaration, Mapping) else None,
            "candidate_role": "variant",
            "label": declaration.get("label") if isinstance(declaration, Mapping) else None,
            "parent_requirement_id": declaration.get("parent_requirement_id") if isinstance(declaration, Mapping) else None,
            **resolved,
            "changed_field_paths": changed,
            "applicable_constraint_ids": constraint_ids,
        }
        assumed, evidence = _candidate_state_paths(resolved)
        candidate["assumption_paths"] = assumed
        candidate["evidence_required_paths"] = evidence
        candidate["resolved_content_sha256"] = "0" * 64
        candidate["resolved_content_sha256"] = candidate_content_sha256(candidate)
        candidates.append(candidate)
        candidate_findings.extend(issues)
    candidates[1:] = sorted(candidates[1:], key=lambda item: item.get("candidate_id", ""))
    problem: dict[str, Any] = {
        "problem_format_version": PROBLEM_FORMAT_VERSION,
        "problem_id": copy.deepcopy(raw["problem_id"]), "case_id": case_id,
        "title": copy.deepcopy(raw["title"]), "purpose": copy.deepcopy(raw["purpose"]),
        "source_case_sha256": dict(source_hashes),
        "requirements": requirements, "heat_sources": heat_sources,
        **copy.deepcopy(baseline), "constraints": constraints, "candidates": candidates,
        "unknowns": [], "compilation": {},
        "confidentiality_level": copy.deepcopy(raw["confidentiality_level"]),
        "compiled_content_sha256": "0" * 64,
    }
    provenance_findings, sidecar_hashes = _provenance_reality(case_dir, problem)
    unknowns, quantity_findings, warnings, assumptions, has_hold, has_fail = _unknowns_and_findings(problem)
    blocking = candidate_findings + provenance_findings + quantity_findings + _heat_findings(problem)
    has_fail = has_fail or bool(blocking)
    problem["unknowns"] = unknowns
    outcome = "FAIL" if has_fail else "HOLD_FOR_INPUT" if has_hold else "READY_WITH_ASSUMPTIONS" if assumptions else "READY"
    problem["compilation"] = {
        "compiler_policy_version": COMPILER_POLICY_VERSION,
        "unit_registry_version": UNIT_REGISTRY_VERSION,
        "canonical_json_version": CANONICAL_JSON_VERSION,
        "heat_source_consistency_policy_version": HEAT_SOURCE_CONSISTENCY_POLICY_VERSION,
        "outcome": outcome,
        "blocking_findings": _sort_findings(blocking),
        "non_blocking_findings": [],
        "warnings": _sort_findings(warnings),
        "assumptions_present": assumptions,
        "assumptions_requiring_later_acknowledgement": assumptions,
    }
    problem["compiled_content_sha256"] = engineering_problem_content_sha256(problem)
    try:
        reconstructed = EngineeringProblem.from_dict(problem)
    except EngineeringProblemValidationError as exc:
        family = _schema_family(str(exc))
        _abort(f"M16A-EPR-{family}-001", "/", f"Final I2A validation rejected compiled content: {exc}", "Correct the structured authoring input; the compiler emitted no EPR.")
    return CompiledEngineeringProblem(
        reconstructed,
        case_dir,
        MappingProxyType(dict(source_hashes)),
        MappingProxyType(dict(sidecar_hashes)),
    )


def compile_engineering_problem(
    case_path: str | os.PathLike[str],
    authoring: Mapping[str, Any],
) -> CompiledEngineeringProblem:
    """Compile explicit structured authoring data without writing to disk."""

    try:
        return _compile_engineering_problem(case_path, authoring)
    except CompilationFailure:
        raise
    except (AttributeError, IndexError, KeyError, TypeError, ValueError) as exc:
        _abort(
            "M16A-EPR-SCHEMA-001", "/",
            f"Malformed authoring input prevented a schema-valid EPR: {exc}",
            "Correct the explicit closed authoring structure; no EPR was emitted.",
        )


def _assert_sources_fresh(result: CompiledEngineeringProblem) -> None:
    for filename, expected in result.source_case_sha256.items():
        try:
            _, actual = _read_numbered_source(result.case_path, filename)
        except CompilationFailure as exc:
            raise CompilationFailure(_diagnostic("M16A-EPR-SOURCE-004", f"/source_case_sha256/{filename}", f"Recorded source is stale or unsafe: {exc}", "Recompile from the current canonical sources.")) from exc
        if actual != expected:
            _abort("M16A-EPR-SOURCE-004", f"/source_case_sha256/{filename}", "Recorded source exact bytes changed after compilation.", "Recompile from the current canonical sources.")
    for reference, expected in result._sidecar_sha256.items():
        try:
            parts = _safe_relative_parts(reference, "/provenance/reference", rule_id="M16A-EPR-SOURCE-004")
            path = result.case_path.joinpath(*parts)
            if path.is_symlink():
                raise OSError("sidecar became a symlink")
            resolved = path.resolve(strict=True)
            if result.case_path not in resolved.parents or not resolved.is_file():
                raise OSError("sidecar left the case or changed type")
            actual = hashlib.sha256(resolved.read_bytes()).hexdigest()
        except (CompilationFailure, OSError, RuntimeError) as exc:
            _abort("M16A-EPR-SOURCE-004", "/provenance/reference", f"Recorded sidecar is stale or unsafe: {exc}", "Recompile from current sidecars.")
        if actual != expected:
            _abort("M16A-EPR-SOURCE-004", "/provenance/reference", "Recorded sidecar exact bytes changed after compilation.", "Recompile from current sidecars.")


def _ensure_safe_writer_directories(case_dir: Path) -> Path:
    current = case_dir
    for name in ("engineering", "problems"):
        candidate = current / name
        if candidate.exists() or candidate.is_symlink():
            if candidate.is_symlink() or not candidate.is_dir():
                _abort("M16A-EPR-SOURCE-003", "/writer", f"Writer parent {name!r} is not a real directory.", "Remove the unsafe path and retry explicitly.")
        else:
            candidate.mkdir()
        resolved = candidate.resolve(strict=True)
        if resolved.parent != current or candidate.is_symlink():
            _abort("M16A-EPR-SOURCE-003", "/writer", "Writer parent escaped case-local containment.", "Use real case-local engineering/problems directories.")
        current = resolved
    return current


def write_engineering_problem(result: CompiledEngineeringProblem) -> Path:
    """Persist one compiled EPR atomically, idempotently, and without overwrite."""

    if not isinstance(result, CompiledEngineeringProblem):
        raise TypeError("write_engineering_problem requires a CompiledEngineeringProblem")
    case_dir = _case_directory(result.case_path)
    problem = EngineeringProblem.from_dict(result.engineering_problem.to_dict())
    problem_mapping = problem.to_dict()
    if problem_mapping["case_id"] != case_dir.name:
        _abort("M16A-EPR-SOURCE-003", "/case_id", "Writer case directory does not match the EPR case_id.", "Persist only through the original bound case directory.")
    if dict(result.source_case_sha256) != problem_mapping["source_case_sha256"]:
        _abort("M16A-EPR-SOURCE-003", "/source_case_sha256", "Result source snapshot does not match the EPR source map.", "Use the immutable compiler result without reconstruction.")
    if problem.content_sha256 != engineering_problem_content_sha256(problem_mapping):
        _abort("M16A-EPR-SOURCE-003", "/compiled_content_sha256", "Final EPR content hash is invalid.", "Recompile before persistence.")
    data = canonical_json_bytes(problem_mapping)
    if data != result.canonical_bytes:
        _abort("M16A-EPR-SOURCE-003", "/writer", "Result canonical bytes changed after compilation.", "Use the immutable compiler result directly.")
    _assert_sources_fresh(result)
    problems = _ensure_safe_writer_directories(case_dir)
    problem_id = problem.problem_id
    if not _PROBLEM_ID.fullmatch(problem_id):
        _abort("M16A-EPR-ID-001", "/problem_id", "Unsafe problem ID at writer boundary.", "Use EPR-###.")
    target = problems / f"{problem_id}.json"
    if target.is_symlink():
        _abort("M16A-EPR-SOURCE-003", "/writer", "EPR target is a symlink.", "Remove the unsafe target; no write was performed.")
    if target.exists():
        if not target.is_file():
            _abort("M16A-EPR-SOURCE-003", "/writer", "EPR target exists but is not a regular file.", "Use the exact immutable EPR file path.")
        if target.read_bytes() == data:
            return target
        _abort("M16A-EPR-SOURCE-003", "/writer", "Different bytes already exist for this immutable EPR ID.", "Choose a new problem_id; overwrite is forbidden.")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{problem_id}.", suffix=".tmp", dir=problems)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        _assert_sources_fresh(result)
        try:
            os.link(temporary, target)
        except FileExistsError:
            if target.is_symlink() or not target.is_file() or target.read_bytes() != data:
                _abort("M16A-EPR-SOURCE-003", "/writer", "EPR target appeared with different or unsafe content.", "Choose a new immutable problem_id.")
        return target
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
