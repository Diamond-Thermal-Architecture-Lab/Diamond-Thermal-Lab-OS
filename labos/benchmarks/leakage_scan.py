from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from labos.benchmarks.integrity import sha256_bytes
from labos.benchmarks.leakage_policy import (
    LEAKAGE_CATEGORIES,
    LEAKAGE_MATCH_MODES,
    LeakageToken,
    LoadedPrivateLeakagePolicy,
    load_private_leakage_policy,
)


LEAKAGE_AUDIT_REPORT_VERSION = "1.0"
MAX_SCANNABLE_FILE_BYTES = 16 * 1024 * 1024
ROOT_ID_PATTERN = r"^ROOT-[0-9]{4,8}$"
LEAKAGE_AUDIT_CODES = (
    "content_match",
    "directory_read_error",
    "entry_inspection_error",
    "file_read_error",
    "non_utf8_file",
    "oversize_file",
    "path_match",
    "unsafe_special_file",
    "unsafe_symlink",
)

_ROOT_ID_RE = re.compile(ROOT_ID_PATTERN)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MATCH_CODES = frozenset({"content_match", "path_match"})
_STRUCTURAL_CODES = frozenset(LEAKAGE_AUDIT_CODES) - _MATCH_CODES


@dataclass(frozen=True, repr=False)
class LeakageScanRoot:
    root_id: str
    path: Path


@dataclass(frozen=True)
class LeakageAuditFinding:
    code: str
    root_id: str
    path_sha256: str
    token_id: str | None
    category: str | None
    match_mode: str | None
    occurrence_count: int


@dataclass(frozen=True)
class LeakageAuditReport:
    report_version: str
    status: str
    policy_version: str
    policy_sha256: str
    policy_byte_length: int
    policy_token_count: int
    root_count: int
    entry_count: int
    regular_file_count: int
    decoded_file_count: int
    scanned_byte_count: int
    finding_count: int
    findings: tuple[LeakageAuditFinding, ...]


def scan_private_leakage(
    *,
    repo_root: Path,
    policy_root: Path,
    scan_roots: Iterable[LeakageScanRoot],
    additional_forbidden_roots: Iterable[Path] = (),
) -> LeakageAuditReport:
    try:
        roots = _validate_scan_roots(scan_roots)
        loaded = load_private_leakage_policy(
            repo_root=repo_root,
            policy_root=policy_root,
            additional_forbidden_roots=tuple(additional_forbidden_roots)
            + tuple(path for _, path in roots),
        )
    except (OSError, RuntimeError, UnicodeError) as exc:
        raise ValueError("private leakage audit could not be safely initialized") from exc

    findings: dict[tuple[str, str, str, str | None], LeakageAuditFinding] = {}
    counts = _ScanCounts()
    for root_id, root_path in roots:
        _scan_directory(root_id, root_path, "", loaded, findings, counts)
    ordered = tuple(sorted(findings.values(), key=_finding_sort_key))
    report = LeakageAuditReport(
        report_version=LEAKAGE_AUDIT_REPORT_VERSION,
        status="pass" if not ordered else "fail",
        policy_version=loaded.policy.policy_version,
        policy_sha256=loaded.sha256,
        policy_byte_length=loaded.byte_length,
        policy_token_count=len(loaded.policy.tokens),
        root_count=len(roots),
        entry_count=counts.entry_count,
        regular_file_count=counts.regular_file_count,
        decoded_file_count=counts.decoded_file_count,
        scanned_byte_count=counts.scanned_byte_count,
        finding_count=len(ordered),
        findings=ordered,
    )
    _validate_report(report)
    return report


def serialize_leakage_audit_report(report: LeakageAuditReport) -> bytes:
    _validate_report(report)
    payload = {
        "decoded_file_count": report.decoded_file_count,
        "entry_count": report.entry_count,
        "finding_count": report.finding_count,
        "findings": [
            {
                "category": finding.category,
                "code": finding.code,
                "match_mode": finding.match_mode,
                "occurrence_count": finding.occurrence_count,
                "path_sha256": finding.path_sha256,
                "root_id": finding.root_id,
                "token_id": finding.token_id,
            }
            for finding in report.findings
        ],
        "policy_byte_length": report.policy_byte_length,
        "policy_sha256": report.policy_sha256,
        "policy_token_count": report.policy_token_count,
        "policy_version": report.policy_version,
        "regular_file_count": report.regular_file_count,
        "report_version": report.report_version,
        "root_count": report.root_count,
        "scanned_byte_count": report.scanned_byte_count,
        "status": report.status,
    }
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def parse_leakage_audit_report_bytes(data: bytes) -> LeakageAuditReport:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("leakage audit report must be valid UTF-8") from exc
    try:
        payload = json.loads(text, object_pairs_hook=_reject_duplicate_object_keys)
    except json.JSONDecodeError as exc:
        raise ValueError("leakage audit report JSON is malformed") from exc
    except ValueError as exc:
        raise ValueError("leakage audit report JSON contains a duplicate key") from exc
    if not isinstance(payload, dict) or set(payload) != _REPORT_KEYS:
        raise ValueError("leakage audit report has unknown, missing, or invalid keys")
    findings_payload = payload["findings"]
    if not isinstance(findings_payload, list):
        raise ValueError("leakage audit report findings must be a list")
    findings = tuple(_finding_from_payload(item) for item in findings_payload)
    report = LeakageAuditReport(
        report_version=_required_string(payload, "report_version"),
        status=_required_string(payload, "status"),
        policy_version=_required_string(payload, "policy_version"),
        policy_sha256=_required_string(payload, "policy_sha256"),
        policy_byte_length=_required_count(payload, "policy_byte_length"),
        policy_token_count=_required_count(payload, "policy_token_count"),
        root_count=_required_count(payload, "root_count"),
        entry_count=_required_count(payload, "entry_count"),
        regular_file_count=_required_count(payload, "regular_file_count"),
        decoded_file_count=_required_count(payload, "decoded_file_count"),
        scanned_byte_count=_required_count(payload, "scanned_byte_count"),
        finding_count=_required_count(payload, "finding_count"),
        findings=findings,
    )
    _validate_report(report)
    return report


@dataclass
class _ScanCounts:
    entry_count: int = 0
    regular_file_count: int = 0
    decoded_file_count: int = 0
    scanned_byte_count: int = 0


_REPORT_KEYS = frozenset(
    {
        "decoded_file_count", "entry_count", "finding_count", "findings",
        "policy_byte_length", "policy_sha256", "policy_token_count",
        "policy_version", "regular_file_count", "report_version", "root_count",
        "scanned_byte_count", "status",
    }
)
_FINDING_KEYS = frozenset(
    {"category", "code", "match_mode", "occurrence_count", "path_sha256", "root_id", "token_id"}
)


def _validate_scan_roots(scan_roots: Iterable[LeakageScanRoot]) -> tuple[tuple[str, Path], ...]:
    try:
        supplied = tuple(scan_roots)
        if not supplied:
            raise ValueError("at least one scan root is required")
        records: list[tuple[str, Path]] = []
        prior_id = ""
        for item in supplied:
            if not isinstance(item, LeakageScanRoot) or not isinstance(item.root_id, str):
                raise ValueError("scan root configuration is invalid")
            if not _ROOT_ID_RE.fullmatch(item.root_id) or item.root_id <= prior_id:
                raise ValueError("scan root configuration is invalid")
            prior_id = item.root_id
            path = item.path
            if not isinstance(path, Path) or path.is_symlink() or not path.exists() or not path.is_dir():
                raise ValueError("scan root configuration is invalid")
            records.append((item.root_id, path.resolve()))
        for index, (_, first) in enumerate(records):
            for _, second in records[index + 1 :]:
                if _paths_overlap(first, second):
                    raise ValueError("scan roots must be disjoint")
        return tuple(records)
    except (OSError, RuntimeError) as exc:
        raise ValueError("scan root configuration could not be safely inspected") from exc


def _scan_directory(
    root_id: str,
    directory: Path,
    relative_directory: str,
    loaded: LoadedPrivateLeakagePolicy,
    findings: dict[tuple[str, str, str, str | None], LeakageAuditFinding],
    counts: _ScanCounts,
) -> None:
    try:
        with os.scandir(directory) as iterator:
            entries = sorted(iterator, key=lambda entry: entry.name)
    except (OSError, RuntimeError):
        _add_structural(findings, "directory_read_error", root_id, relative_directory)
        return
    for entry in entries:
        relative_path = entry.name if not relative_directory else relative_directory + "/" + entry.name
        counts.entry_count += 1
        _add_path_matches(findings, root_id, relative_path, loaded.policy.tokens)
        _scan_entry(root_id, entry, relative_path, loaded, findings, counts)


def _scan_entry(
    root_id: str,
    entry: os.DirEntry[str],
    relative_path: str,
    loaded: LoadedPrivateLeakagePolicy,
    findings: dict[tuple[str, str, str, str | None], LeakageAuditFinding],
    counts: _ScanCounts,
) -> None:
    try:
        if entry.is_symlink():
            _add_structural(findings, "unsafe_symlink", root_id, relative_path)
            return
        before = os.lstat(entry.path)
    except (OSError, RuntimeError):
        _add_structural(findings, "entry_inspection_error", root_id, relative_path)
        return
    if stat.S_ISDIR(before.st_mode):
        _scan_directory(root_id, Path(entry.path), relative_path, loaded, findings, counts)
        return
    if not stat.S_ISREG(before.st_mode):
        _add_structural(findings, "unsafe_special_file", root_id, relative_path)
        return
    counts.regular_file_count += 1
    result = _read_regular_file(Path(entry.path), before)
    if result[0] != "ok":
        _add_structural(findings, result[0], root_id, relative_path)
        return
    data = result[1]
    assert isinstance(data, bytes)
    counts.scanned_byte_count += len(data)
    try:
        decoded = data.decode("utf-8")
    except UnicodeDecodeError:
        _add_structural(findings, "non_utf8_file", root_id, relative_path)
        return
    counts.decoded_file_count += 1
    _add_content_matches(findings, root_id, relative_path, decoded, loaded.policy.tokens)


def _read_regular_file(path: Path, before: os.stat_result) -> tuple[str, bytes | None]:
    flags = os.O_RDONLY
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor: int | None = None
    try:
        try:
            descriptor = os.open(path, flags)
        except OSError:
            return _open_failure_code(path, before), None
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            return "entry_inspection_error", None
        if not _same_identity(before, opened):
            return "entry_inspection_error", None
        try:
            current = os.lstat(path)
        except OSError:
            return "entry_inspection_error", None
        if stat.S_ISLNK(current.st_mode):
            return "unsafe_symlink", None
        if not _same_identity(before, current):
            return "entry_inspection_error", None
        if opened.st_size > MAX_SCANNABLE_FILE_BYTES:
            return "oversize_file", None
        remaining = opened.st_size
        pieces: list[bytes] = []
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                return "entry_inspection_error", None
            pieces.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(descriptor)
        if not _same_identity(opened, after) or after.st_size != opened.st_size:
            return "entry_inspection_error", None
        return "ok", b"".join(pieces)
    except (OSError, RuntimeError):
        return "file_read_error", None
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass


def _open_failure_code(path: Path, before: os.stat_result) -> str:
    try:
        current = os.lstat(path)
        if stat.S_ISLNK(current.st_mode):
            return "unsafe_symlink"
        return "entry_inspection_error" if not _same_identity(before, current) else "file_read_error"
    except OSError:
        return "entry_inspection_error"


def _same_identity(first: os.stat_result, second: os.stat_result) -> bool:
    if first.st_dev and first.st_ino and second.st_dev and second.st_ino:
        return first.st_dev == second.st_dev and first.st_ino == second.st_ino
    return (
        stat.S_IFMT(first.st_mode) == stat.S_IFMT(second.st_mode)
        and first.st_size == second.st_size
        and first.st_mtime_ns == second.st_mtime_ns
    )


def _add_path_matches(findings: dict[tuple[str, str, str, str | None], LeakageAuditFinding], root_id: str, relative_path: str, tokens: tuple[LeakageToken, ...]) -> None:
    for token in tokens:
        count = _match_count(relative_path, token)
        if count:
            _add_match(findings, "path_match", root_id, relative_path, token, count)


def _add_content_matches(findings: dict[tuple[str, str, str, str | None], LeakageAuditFinding], root_id: str, relative_path: str, text: str, tokens: tuple[LeakageToken, ...]) -> None:
    for token in tokens:
        count = _match_count(text, token)
        if count:
            _add_match(findings, "content_match", root_id, relative_path, token, count)


def _match_count(text: str, token: LeakageToken) -> int:
    target = text if token.match_mode == "literal" else unicodedata.normalize("NFKC", text).casefold()
    return target.count(token.match_value)


def _add_match(findings: dict[tuple[str, str, str, str | None], LeakageAuditFinding], code: str, root_id: str, relative_path: str, token: LeakageToken, count: int) -> None:
    path_sha = _path_sha256(root_id, relative_path)
    key = (code, root_id, path_sha, token.token_id)
    existing = findings.get(key)
    if existing is None:
        findings[key] = LeakageAuditFinding(code, root_id, path_sha, token.token_id, token.category, token.match_mode, count)
    else:
        findings[key] = LeakageAuditFinding(code, root_id, path_sha, token.token_id, token.category, token.match_mode, existing.occurrence_count + count)


def _add_structural(findings: dict[tuple[str, str, str, str | None], LeakageAuditFinding], code: str, root_id: str, relative_path: str) -> None:
    path_sha = _path_sha256(root_id, relative_path)
    findings.setdefault((code, root_id, path_sha, None), LeakageAuditFinding(code, root_id, path_sha, None, None, None, 1))


def _path_sha256(root_id: str, relative_path: str) -> str:
    return sha256_bytes((root_id + "\0" + relative_path).encode("utf-8", "surrogatepass"))


def _paths_overlap(first: Path, second: Path) -> bool:
    try:
        first.relative_to(second)
        return True
    except ValueError:
        try:
            second.relative_to(first)
            return True
        except ValueError:
            return False


def _finding_sort_key(finding: LeakageAuditFinding) -> tuple[str, str, str, str]:
    return (finding.root_id, finding.path_sha256, finding.code, finding.token_id or "")


def _finding_from_payload(payload: object) -> LeakageAuditFinding:
    if not isinstance(payload, dict) or set(payload) != _FINDING_KEYS:
        raise ValueError("leakage audit finding has unknown, missing, or invalid keys")
    finding = LeakageAuditFinding(
        code=_required_string(payload, "code"),
        root_id=_required_string(payload, "root_id"),
        path_sha256=_required_string(payload, "path_sha256"),
        token_id=payload["token_id"],
        category=payload["category"],
        match_mode=payload["match_mode"],
        occurrence_count=_required_count(payload, "occurrence_count"),
    )
    return finding


def _validate_report(report: LeakageAuditReport) -> None:
    if not isinstance(report, LeakageAuditReport):
        raise ValueError("leakage audit report has invalid type")
    if report.report_version != LEAKAGE_AUDIT_REPORT_VERSION or report.policy_version != "1.0":
        raise ValueError("leakage audit report has an unsupported version")
    if report.status not in {"pass", "fail"}:
        raise ValueError("leakage audit report has an invalid status")
    if not _SHA256_RE.fullmatch(report.policy_sha256):
        raise ValueError("leakage audit report has an invalid policy SHA256")
    for value in (report.policy_byte_length, report.policy_token_count, report.root_count, report.entry_count, report.regular_file_count, report.decoded_file_count, report.scanned_byte_count, report.finding_count):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError("leakage audit report has an invalid count")
    if not isinstance(report.findings, tuple):
        raise ValueError("leakage audit report findings must be a tuple")
    if report.finding_count != len(report.findings) or (report.status == "pass") != (not report.findings):
        raise ValueError("leakage audit report has inconsistent finding status")
    if tuple(sorted(report.findings, key=_finding_sort_key)) != report.findings:
        raise ValueError("leakage audit findings are not canonically ordered")
    keys: set[tuple[str, str, str, str | None]] = set()
    for finding in report.findings:
        _validate_finding(finding)
        key = (finding.code, finding.root_id, finding.path_sha256, finding.token_id)
        if key in keys:
            raise ValueError("leakage audit report has duplicate findings")
        keys.add(key)


def _validate_finding(finding: LeakageAuditFinding) -> None:
    if not isinstance(finding, LeakageAuditFinding) or finding.code not in LEAKAGE_AUDIT_CODES:
        raise ValueError("leakage audit finding has an invalid code")
    if not isinstance(finding.root_id, str) or not _ROOT_ID_RE.fullmatch(finding.root_id):
        raise ValueError("leakage audit finding has an invalid root ID")
    if not isinstance(finding.path_sha256, str) or not _SHA256_RE.fullmatch(finding.path_sha256):
        raise ValueError("leakage audit finding has an invalid path SHA256")
    if not isinstance(finding.occurrence_count, int) or isinstance(finding.occurrence_count, bool):
        raise ValueError("leakage audit finding has an invalid occurrence count")
    if finding.code in _MATCH_CODES:
        if not isinstance(finding.token_id, str) or not re.fullmatch(r"LKG-[0-9]{4,8}", finding.token_id):
            raise ValueError("leakage audit match finding has invalid token metadata")
        if finding.category not in LEAKAGE_CATEGORIES or finding.match_mode not in LEAKAGE_MATCH_MODES or finding.occurrence_count <= 0:
            raise ValueError("leakage audit match finding has invalid token metadata")
    elif any(value is not None for value in (finding.token_id, finding.category, finding.match_mode)) or finding.occurrence_count != 1:
        raise ValueError("leakage audit structural finding has invalid token metadata")


def _required_string(payload: dict[str, object], key: str) -> str:
    value = payload[key]
    if not isinstance(value, str):
        raise ValueError("leakage audit report has an invalid string")
    return value


def _required_count(payload: dict[str, object], key: str) -> int:
    value = payload[key]
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("leakage audit report has an invalid count")
    return value


def _reject_duplicate_object_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result
