from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Iterable

from labos.benchmarks.integrity import TREE_HASH_ALGORITHM, digest_tree, sha256_bytes


EXECUTION_BASELINE_RECORD_VERSION = "1.0"
EXECUTION_SCOPE_VERSION = "1.0"
M15B_PROTOCOL_VERSION = "1.0"
M15B_PROTOCOL_MERGE_COMMIT = "e35476d5fe4ccfa94f8438a7ef1fbf569fd67aa2"
M15B_PROTOCOL_PATH = "docs/benchmarks/M15B_PRE_REGISTRATION_PROTOCOL.md"
M15B_EXECUTION_SCOPE_PATH = "docs/benchmarks/M15B_EXECUTION_SCOPE_SPEC.json"
M15B_EXECUTION_BASELINE_RECORD_PATH = "docs/benchmarks/M15B_EXECUTION_BASELINE_RECORD.json"
M14_RULE_PATH = "labos/triage/thermomechanical.py"

PROTECTED_TREE_GROUPS = (
    ("production_code", ("labos",)),
    ("schemas", ("labos/schemas", "schemas")),
    ("scripts", ("scripts",)),
    ("workflows", (".github/workflows",)),
)

DEPENDENCY_MANIFEST_BASENAMES = (
    "Pipfile",
    "Pipfile.lock",
    "constraints.txt",
    "package-lock.json",
    "package.json",
    "pnpm-lock.yaml",
    "poetry.lock",
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
    "uv.lock",
    "yarn.lock",
)
DEPENDENCY_MANIFEST_GLOBS = ("requirements*.txt",)

_SCOPE_KEYS = frozenset(
    {
        "dependency_manifest_basenames",
        "dependency_manifest_globs",
        "m14_rule_path",
        "protected_trees",
        "protocol_path",
        "scope_version",
    }
)
_SCOPE_TREE_KEYS = frozenset({"group_id", "include_paths"})
_RECORD_KEYS = frozenset(
    {
        "dependency_manifests",
        "m14_rule_file",
        "protected_content_commit",
        "protected_trees",
        "protocol_file",
        "protocol_merge_commit",
        "protocol_version",
        "record_version",
        "recorded_at_utc",
        "scope_spec_sha256",
        "scope_version",
    }
)
_FILE_KEYS = frozenset({"byte_length", "path", "sha256"})
_TREE_KEYS = frozenset({"algorithm", "file_count", "group_id", "sha256"})
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}([0-9a-f]{24})?$")
_UTC_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


@dataclass(frozen=True)
class ExecutionScopeTree:
    group_id: str
    include_paths: tuple[str, ...]


@dataclass(frozen=True)
class ExecutionScope:
    scope_version: str
    protocol_path: str
    m14_rule_path: str
    protected_trees: tuple[ExecutionScopeTree, ...]
    dependency_manifest_basenames: tuple[str, ...]
    dependency_manifest_globs: tuple[str, ...]


@dataclass(frozen=True)
class BaselineFileRecord:
    path: str
    byte_length: int
    sha256: str


@dataclass(frozen=True)
class BaselineTreeRecord:
    group_id: str
    algorithm: str
    file_count: int
    sha256: str


@dataclass(frozen=True)
class ExecutionBaselineRecord:
    record_version: str
    protocol_version: str
    scope_version: str
    recorded_at_utc: str
    protected_content_commit: str
    protocol_merge_commit: str
    scope_spec_sha256: str
    protocol_file: BaselineFileRecord
    m14_rule_file: BaselineFileRecord
    protected_trees: tuple[BaselineTreeRecord, ...]
    dependency_manifests: tuple[BaselineFileRecord, ...]


@dataclass(frozen=True)
class ExecutionBaselineFinding:
    code: str
    target: str
    detail: str


def canonical_execution_scope() -> ExecutionScope:
    return ExecutionScope(
        scope_version=EXECUTION_SCOPE_VERSION,
        protocol_path=M15B_PROTOCOL_PATH,
        m14_rule_path=M14_RULE_PATH,
        protected_trees=tuple(
            ExecutionScopeTree(group_id=group_id, include_paths=include_paths)
            for group_id, include_paths in PROTECTED_TREE_GROUPS
        ),
        dependency_manifest_basenames=DEPENDENCY_MANIFEST_BASENAMES,
        dependency_manifest_globs=DEPENDENCY_MANIFEST_GLOBS,
    )


def serialize_execution_scope(scope: ExecutionScope) -> bytes:
    _validate_scope(scope)
    payload = {
        "dependency_manifest_basenames": list(scope.dependency_manifest_basenames),
        "dependency_manifest_globs": list(scope.dependency_manifest_globs),
        "m14_rule_path": scope.m14_rule_path,
        "protected_trees": [
            {"group_id": item.group_id, "include_paths": list(item.include_paths)}
            for item in scope.protected_trees
        ],
        "protocol_path": scope.protocol_path,
        "scope_version": scope.scope_version,
    }
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def parse_execution_scope_bytes(data: bytes) -> ExecutionScope:
    payload = _parse_json_object(data, "execution scope")
    if set(payload) != _SCOPE_KEYS:
        raise ValueError("execution scope has unknown, missing, or invalid top-level keys")
    tree_payloads = payload["protected_trees"]
    if not isinstance(tree_payloads, list):
        raise ValueError("protected_trees must be a list")
    trees: list[ExecutionScopeTree] = []
    for item in tree_payloads:
        if not isinstance(item, dict) or set(item) != _SCOPE_TREE_KEYS:
            raise ValueError("protected tree scope has unknown, missing, or invalid keys")
        include_paths = item["include_paths"]
        if not isinstance(include_paths, list):
            raise ValueError("protected tree include_paths must be a list")
        trees.append(
            ExecutionScopeTree(
                group_id=item["group_id"],
                include_paths=tuple(include_paths),
            )
        )
    basenames = payload["dependency_manifest_basenames"]
    globs = payload["dependency_manifest_globs"]
    if not isinstance(basenames, list) or not isinstance(globs, list):
        raise ValueError("dependency manifest names and globs must be lists")
    scope = ExecutionScope(
        scope_version=payload["scope_version"],
        protocol_path=payload["protocol_path"],
        m14_rule_path=payload["m14_rule_path"],
        protected_trees=tuple(trees),
        dependency_manifest_basenames=tuple(basenames),
        dependency_manifest_globs=tuple(globs),
    )
    _validate_scope(scope)
    if scope != canonical_execution_scope():
        raise ValueError("execution scope does not equal the approved Phase 0.5C scope")
    return scope


def load_execution_scope(path: Path) -> ExecutionScope:
    return parse_execution_scope_bytes(_read_regular_file(path, "execution scope"))


def build_execution_baseline_record(
    *,
    repo_root: Path,
    scope_path: Path,
    protected_content_commit: str,
    recorded_at_utc: str,
) -> ExecutionBaselineRecord:
    root = _resolve_repo_root(repo_root)
    scope_bytes = _read_canonical_scope(root, scope_path)
    scope = parse_execution_scope_bytes(scope_bytes)
    _validate_commit(protected_content_commit, "protected_content_commit")
    _validate_timestamp(recorded_at_utc)
    record = ExecutionBaselineRecord(
        record_version=EXECUTION_BASELINE_RECORD_VERSION,
        protocol_version=M15B_PROTOCOL_VERSION,
        scope_version=scope.scope_version,
        recorded_at_utc=recorded_at_utc,
        protected_content_commit=protected_content_commit,
        protocol_merge_commit=M15B_PROTOCOL_MERGE_COMMIT,
        scope_spec_sha256=sha256_bytes(scope_bytes),
        protocol_file=_digest_repo_file(root, scope.protocol_path),
        m14_rule_file=_digest_repo_file(root, scope.m14_rule_path),
        protected_trees=_build_tree_records(root, scope),
        dependency_manifests=_discover_dependency_manifests(root, scope),
    )
    _validate_record(record)
    return record


def serialize_execution_baseline_record(record: ExecutionBaselineRecord) -> bytes:
    _validate_record(record)
    payload = {
        "dependency_manifests": [_file_payload(item) for item in record.dependency_manifests],
        "m14_rule_file": _file_payload(record.m14_rule_file),
        "protected_content_commit": record.protected_content_commit,
        "protected_trees": [
            {
                "algorithm": item.algorithm,
                "file_count": item.file_count,
                "group_id": item.group_id,
                "sha256": item.sha256,
            }
            for item in record.protected_trees
        ],
        "protocol_file": _file_payload(record.protocol_file),
        "protocol_merge_commit": record.protocol_merge_commit,
        "protocol_version": record.protocol_version,
        "record_version": record.record_version,
        "recorded_at_utc": record.recorded_at_utc,
        "scope_spec_sha256": record.scope_spec_sha256,
        "scope_version": record.scope_version,
    }
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def parse_execution_baseline_record_bytes(data: bytes) -> ExecutionBaselineRecord:
    payload = _parse_json_object(data, "execution baseline record")
    if set(payload) != _RECORD_KEYS:
        raise ValueError("execution baseline record has unknown, missing, or invalid top-level keys")
    tree_payloads = payload["protected_trees"]
    dependency_payloads = payload["dependency_manifests"]
    if not isinstance(tree_payloads, list) or not isinstance(dependency_payloads, list):
        raise ValueError("protected_trees and dependency_manifests must be lists")
    trees: list[BaselineTreeRecord] = []
    for item in tree_payloads:
        if not isinstance(item, dict) or set(item) != _TREE_KEYS:
            raise ValueError("protected tree record has unknown, missing, or invalid keys")
        trees.append(
            BaselineTreeRecord(
                group_id=item["group_id"],
                algorithm=item["algorithm"],
                file_count=item["file_count"],
                sha256=item["sha256"],
            )
        )
    dependencies = tuple(_parse_file_payload(item) for item in dependency_payloads)
    record = ExecutionBaselineRecord(
        record_version=payload["record_version"],
        protocol_version=payload["protocol_version"],
        scope_version=payload["scope_version"],
        recorded_at_utc=payload["recorded_at_utc"],
        protected_content_commit=payload["protected_content_commit"],
        protocol_merge_commit=payload["protocol_merge_commit"],
        scope_spec_sha256=payload["scope_spec_sha256"],
        protocol_file=_parse_file_payload(payload["protocol_file"]),
        m14_rule_file=_parse_file_payload(payload["m14_rule_file"]),
        protected_trees=tuple(trees),
        dependency_manifests=dependencies,
    )
    _validate_record(record)
    return record


def load_execution_baseline_record(path: Path) -> ExecutionBaselineRecord:
    return parse_execution_baseline_record_bytes(
        _read_regular_file(path, "execution baseline record")
    )


def write_new_execution_baseline_record(path: Path, record: ExecutionBaselineRecord) -> None:
    _validate_record(record)
    if path.is_symlink():
        raise ValueError(f"execution baseline output must not be a symlink: {path}")
    if path.exists():
        raise ValueError(f"execution baseline output already exists: {path}")
    if not path.parent.is_dir():
        raise ValueError(f"execution baseline output parent does not exist: {path.parent}")
    data = serialize_execution_baseline_record(record)
    created = False
    try:
        with path.open("xb") as output:
            created = True
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
    except FileExistsError as exc:
        raise ValueError(f"execution baseline output already exists: {path}") from exc
    except OSError as exc:
        if not created:
            raise
        try:
            path.unlink()
        except OSError as cleanup_exc:
            raise OSError(
                f"failed to write execution baseline {path} and remove partial output: {cleanup_exc}"
            ) from exc
        raise


def verify_execution_baseline(
    record: ExecutionBaselineRecord,
    *,
    repo_root: Path,
    scope_path: Path,
) -> tuple[ExecutionBaselineFinding, ...]:
    _validate_record(record)
    root = _resolve_repo_root(repo_root)
    findings: list[ExecutionBaselineFinding] = []
    try:
        scope_bytes = _read_canonical_scope(root, scope_path)
        scope = parse_execution_scope_bytes(scope_bytes)
    except (OSError, ValueError) as exc:
        return (ExecutionBaselineFinding("invalid_scope", M15B_EXECUTION_SCOPE_PATH, _safe_detail(exc)),)
    if sha256_bytes(scope_bytes) != record.scope_spec_sha256:
        findings.append(
            ExecutionBaselineFinding(
                "scope_spec_sha256_mismatch", M15B_EXECUTION_SCOPE_PATH, "exact byte SHA256 differs"
            )
        )
    _compare_file_record(findings, record.protocol_file, root, "protocol_file_mismatch")
    _compare_file_record(findings, record.m14_rule_file, root, "m14_rule_file_mismatch")
    try:
        current_trees = {item.group_id: item for item in _build_tree_records(root, scope)}
    except (OSError, ValueError) as exc:
        findings.append(ExecutionBaselineFinding("protected_tree_unreadable", "protected_trees", _safe_detail(exc)))
    else:
        for expected in record.protected_trees:
            current = current_trees.get(expected.group_id)
            if current != expected:
                findings.append(
                    ExecutionBaselineFinding(
                        "protected_tree_mismatch", expected.group_id, "file set or exact bytes differ"
                    )
                )
    try:
        current_dependencies = _discover_dependency_manifests(root, scope)
    except (OSError, ValueError) as exc:
        findings.append(
            ExecutionBaselineFinding("dependency_manifest_unreadable", "dependency_manifests", _safe_detail(exc))
        )
    else:
        expected_by_path = {item.path: item for item in record.dependency_manifests}
        current_by_path = {item.path: item for item in current_dependencies}
        if set(expected_by_path) != set(current_by_path):
            findings.append(
                ExecutionBaselineFinding(
                    "dependency_manifest_set_mismatch",
                    "dependency_manifests",
                    "dependency manifest paths differ",
                )
            )
        for path in sorted(set(expected_by_path) & set(current_by_path)):
            if expected_by_path[path] != current_by_path[path]:
                findings.append(
                    ExecutionBaselineFinding(
                        "dependency_manifest_bytes_mismatch", path, "exact bytes differ"
                    )
                )
    return tuple(sorted(findings, key=lambda item: (item.target, item.code, item.detail)))


def verify_execution_baseline_git(
    record: ExecutionBaselineRecord,
    *,
    repo_root: Path,
    ref: str = "HEAD",
) -> tuple[ExecutionBaselineFinding, ...]:
    _validate_record(record)
    root = _resolve_repo_root(repo_root)
    findings: list[ExecutionBaselineFinding] = []
    git_env = os.environ.copy()
    git_env["GIT_NO_LAZY_FETCH"] = "1"
    git_env["GIT_TERMINAL_PROMPT"] = "0"
    ref_commit = _resolve_git_commit(root, ref, git_env)
    head_commit = _resolve_git_commit(root, "HEAD", git_env)
    if ref_commit is None:
        findings.append(ExecutionBaselineFinding("invalid_git_ref", ref, "commit is unavailable"))
        return tuple(sorted(findings, key=lambda item: (item.target, item.code, item.detail)))
    if head_commit is None:
        findings.append(
            ExecutionBaselineFinding("invalid_git_head", "HEAD", "checked-out commit is unavailable")
        )
    elif head_commit != ref_commit:
        findings.append(
            ExecutionBaselineFinding(
                "git_ref_not_checked_out",
                ref,
                "verification ref is not the currently checked-out HEAD",
            )
        )

    record_result = subprocess.run(
        ["git", "show", f"{ref}:{M15B_EXECUTION_BASELINE_RECORD_PATH}"],
        cwd=root,
        env=git_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if record_result.returncode != 0:
        findings.append(
            ExecutionBaselineFinding(
                "baseline_record_not_committed",
                M15B_EXECUTION_BASELINE_RECORD_PATH,
                "canonical execution baseline record is unavailable at verification ref",
            )
        )
    elif record_result.stdout != serialize_execution_baseline_record(record):
        findings.append(
            ExecutionBaselineFinding(
                "baseline_record_git_mismatch",
                M15B_EXECUTION_BASELINE_RECORD_PATH,
                "loaded record bytes differ from the canonical record committed at verification ref",
            )
        )

    checks = (
        (
            "protocol_not_ancestor",
            record.protocol_merge_commit,
            record.protected_content_commit,
            "protected content commit does not descend from protocol merge",
        ),
        (
            "protected_content_not_ancestor",
            record.protected_content_commit,
            ref,
            "verification ref does not descend from protected content commit",
        ),
    )
    for code, ancestor, descendant, detail in checks:
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=root,
            env=git_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            findings.append(ExecutionBaselineFinding(code, descendant, detail))
    protected_paths = sorted(
        {
            M15B_PROTOCOL_PATH,
            M15B_EXECUTION_SCOPE_PATH,
            M14_RULE_PATH,
            *(path for _, paths in PROTECTED_TREE_GROUPS for path in paths),
        }
    )
    result = subprocess.run(
        [
            "git",
            "diff",
            "--quiet",
            record.protected_content_commit,
            ref,
            "--",
            *protected_paths,
        ],
        cwd=root,
        env=git_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        findings.append(
            ExecutionBaselineFinding(
                "protected_scope_git_mismatch",
                ref,
                "protected paths differ from the protected content commit",
            )
        )

    dependency_result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--no-renames",
            "-z",
            record.protected_content_commit,
            ref,
            "--",
        ],
        cwd=root,
        env=git_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if dependency_result.returncode != 0:
        findings.append(
            ExecutionBaselineFinding(
                "dependency_manifest_git_unreadable",
                ref,
                "dependency manifest changes could not be checked",
            )
        )
    else:
        changed_paths = [
            value.decode("utf-8", errors="surrogateescape")
            for value in dependency_result.stdout.split(b"\0")
            if value
        ]
        scope = canonical_execution_scope()
        changed_manifests = sorted(
            path
            for path in changed_paths
            if _is_dependency_manifest(PurePosixPath(path).name, scope)
        )
        if changed_manifests:
            findings.append(
                ExecutionBaselineFinding(
                    "dependency_manifest_git_mismatch",
                    ref,
                    "dependency manifest paths or bytes differ from the protected content commit",
                )
            )
    return tuple(sorted(findings, key=lambda item: (item.target, item.code, item.detail)))


def _resolve_git_commit(root: Path, ref: str, git_env: dict[str, str]) -> str | None:
    if not isinstance(ref, str) or not ref or ref.startswith("-") or "\x00" in ref:
        return None
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"{ref}^{{commit}}"],
        cwd=root,
        env=git_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    value = result.stdout.strip()
    if result.returncode != 0 or not _COMMIT_RE.fullmatch(value):
        return None
    return value


def _build_tree_records(root: Path, scope: ExecutionScope) -> tuple[BaselineTreeRecord, ...]:
    records: list[BaselineTreeRecord] = []
    for tree in scope.protected_trees:
        digest = digest_tree(
            root,
            include_paths=tree.include_paths,
            ignored_directory_names=(".git", "__pycache__"),
        )
        records.append(
            BaselineTreeRecord(
                group_id=tree.group_id,
                algorithm=digest.algorithm,
                file_count=len(digest.files),
                sha256=digest.sha256,
            )
        )
    return tuple(records)


def _discover_dependency_manifests(
    root: Path, scope: ExecutionScope
) -> tuple[BaselineFileRecord, ...]:
    records: list[BaselineFileRecord] = []
    ignored = {".git", "__pycache__"}
    for current, directories, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        for directory in list(directories):
            child = current_path / directory
            if child.is_symlink():
                relative = child.relative_to(root).as_posix()
                raise ValueError(f"dependency scan found a symlinked directory: {relative}")
            if directory in ignored:
                directories.remove(directory)
        for filename in filenames:
            if not _is_dependency_manifest(filename, scope):
                continue
            path = current_path / filename
            relative = path.relative_to(root).as_posix()
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"dependency manifest is not a regular non-symlink file: {relative}")
            records.append(_digest_repo_file(root, relative))
    records.sort(key=lambda item: item.path)
    return tuple(records)


def _is_dependency_manifest(filename: str, scope: ExecutionScope) -> bool:
    if filename in scope.dependency_manifest_basenames:
        return True
    return any(fnmatch.fnmatchcase(filename, pattern) for pattern in scope.dependency_manifest_globs)


def _digest_repo_file(root: Path, relative: str) -> BaselineFileRecord:
    safe_path = _validate_relative_path(relative)
    path = root.joinpath(*PurePosixPath(safe_path).parts)
    data = _read_regular_file(path, "baseline file")
    return BaselineFileRecord(path=safe_path, byte_length=len(data), sha256=sha256_bytes(data))


def _compare_file_record(
    findings: list[ExecutionBaselineFinding],
    expected: BaselineFileRecord,
    root: Path,
    code: str,
) -> None:
    try:
        current = _digest_repo_file(root, expected.path)
    except (OSError, ValueError) as exc:
        findings.append(ExecutionBaselineFinding(code, expected.path, _safe_detail(exc)))
        return
    if current != expected:
        findings.append(ExecutionBaselineFinding(code, expected.path, "exact bytes differ"))


def _validate_scope(scope: ExecutionScope) -> None:
    if not isinstance(scope, ExecutionScope):
        raise ValueError("scope must be an ExecutionScope")
    if scope.scope_version != EXECUTION_SCOPE_VERSION:
        raise ValueError("scope_version must equal '1.0'")
    if scope.protocol_path != M15B_PROTOCOL_PATH or scope.m14_rule_path != M14_RULE_PATH:
        raise ValueError("execution scope protocol or M14 rule path is not approved")
    expected_trees = tuple(
        ExecutionScopeTree(group_id=group_id, include_paths=include_paths)
        for group_id, include_paths in PROTECTED_TREE_GROUPS
    )
    if scope.protected_trees != expected_trees:
        raise ValueError("protected tree scope is not the approved canonical scope")
    if scope.dependency_manifest_basenames != DEPENDENCY_MANIFEST_BASENAMES:
        raise ValueError("dependency manifest basenames are not the approved canonical set")
    if scope.dependency_manifest_globs != DEPENDENCY_MANIFEST_GLOBS:
        raise ValueError("dependency manifest globs are not the approved canonical set")
    for tree in scope.protected_trees:
        _validate_group_id(tree.group_id)
        for path in tree.include_paths:
            _validate_relative_path(path)


def _validate_record(record: ExecutionBaselineRecord) -> None:
    if not isinstance(record, ExecutionBaselineRecord):
        raise ValueError("record must be an ExecutionBaselineRecord")
    if record.record_version != EXECUTION_BASELINE_RECORD_VERSION:
        raise ValueError("record_version must equal '1.0'")
    if record.protocol_version != M15B_PROTOCOL_VERSION:
        raise ValueError("protocol_version must equal '1.0'")
    if record.scope_version != EXECUTION_SCOPE_VERSION:
        raise ValueError("scope_version must equal '1.0'")
    _validate_timestamp(record.recorded_at_utc)
    _validate_commit(record.protected_content_commit, "protected_content_commit")
    if record.protocol_merge_commit != M15B_PROTOCOL_MERGE_COMMIT:
        raise ValueError("protocol_merge_commit does not equal the frozen protocol merge")
    _validate_sha256(record.scope_spec_sha256, "scope_spec_sha256")
    _validate_file_record(record.protocol_file)
    _validate_file_record(record.m14_rule_file)
    if record.protocol_file.path != M15B_PROTOCOL_PATH:
        raise ValueError("protocol_file path is not canonical")
    if record.m14_rule_file.path != M14_RULE_PATH:
        raise ValueError("m14_rule_file path is not canonical")
    if not isinstance(record.protected_trees, tuple):
        raise ValueError("protected_trees must be a tuple")
    expected_ids = [group_id for group_id, _ in PROTECTED_TREE_GROUPS]
    actual_ids: list[str] = []
    for tree in record.protected_trees:
        if not isinstance(tree, BaselineTreeRecord):
            raise ValueError("protected tree records must be BaselineTreeRecord instances")
        _validate_group_id(tree.group_id)
        actual_ids.append(tree.group_id)
        if tree.algorithm != TREE_HASH_ALGORITHM:
            raise ValueError("protected tree algorithm is not approved")
        if isinstance(tree.file_count, bool) or not isinstance(tree.file_count, int) or tree.file_count <= 0:
            raise ValueError("protected tree file_count must be a positive integer")
        _validate_sha256(tree.sha256, "protected tree sha256")
    if actual_ids != expected_ids:
        raise ValueError("protected tree records do not equal the approved ordered group set")
    if not isinstance(record.dependency_manifests, tuple):
        raise ValueError("dependency_manifests must be a tuple")
    paths: list[str] = []
    scope = canonical_execution_scope()
    for item in record.dependency_manifests:
        _validate_file_record(item, allow_empty=True)
        if not _is_dependency_manifest(PurePosixPath(item.path).name, scope):
            raise ValueError("dependency manifest path is not in the approved name set")
        paths.append(item.path)
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise ValueError("dependency manifest records must have unique sorted paths")


def _validate_file_record(record: BaselineFileRecord, *, allow_empty: bool = False) -> None:
    if not isinstance(record, BaselineFileRecord):
        raise ValueError("baseline file must be a BaselineFileRecord")
    _validate_relative_path(record.path)
    if (
        isinstance(record.byte_length, bool)
        or not isinstance(record.byte_length, int)
        or record.byte_length < 0
        or (record.byte_length == 0 and not allow_empty)
    ):
        raise ValueError("baseline file byte_length is not valid for this record")
    _validate_sha256(record.sha256, "baseline file sha256")


def _parse_file_payload(payload: object) -> BaselineFileRecord:
    if not isinstance(payload, dict) or set(payload) != _FILE_KEYS:
        raise ValueError("baseline file record has unknown, missing, or invalid keys")
    return BaselineFileRecord(
        path=payload["path"], byte_length=payload["byte_length"], sha256=payload["sha256"]
    )


def _file_payload(record: BaselineFileRecord) -> dict[str, object]:
    return {"byte_length": record.byte_length, "path": record.path, "sha256": record.sha256}


def _parse_json_object(data: bytes, label: str) -> dict[str, object]:
    try:
        decoded = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} must be valid UTF-8") from exc
    try:
        payload = json.loads(decoded, object_pairs_hook=_reject_duplicate_object_keys)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"invalid {label} JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _reject_duplicate_object_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _validate_relative_path(path_text: str) -> str:
    if not isinstance(path_text, str) or not path_text:
        raise ValueError("path must be a non-empty repository-relative string")
    if "\\" in path_text or path_text.startswith("/") or PureWindowsPath(path_text).drive:
        raise ValueError("path must be a POSIX repository-relative path")
    if "//" in path_text:
        raise ValueError("path must not contain empty components")
    parts = PurePosixPath(path_text).parts
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("path must not contain traversal or dot components")
    return PurePosixPath(path_text).as_posix()


def _validate_group_id(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", value):
        raise ValueError("group_id must use lowercase snake_case")
    return value


def _validate_sha256(value: str, label: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{label} must be 64 lowercase hexadecimal characters")
    return value


def _validate_commit(value: str, label: str) -> str:
    if not isinstance(value, str) or not _COMMIT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a full lowercase Git commit SHA")
    return value


def _validate_timestamp(value: str) -> str:
    if not isinstance(value, str) or not _UTC_TIMESTAMP_RE.fullmatch(value):
        raise ValueError("recorded_at_utc must use YYYY-MM-DDTHH:MM:SSZ")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError("recorded_at_utc must be a real UTC calendar timestamp") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise ValueError("recorded_at_utc must use canonical UTC formatting")
    return value


def _read_regular_file(path: Path, label: str) -> bytes:
    if path.is_symlink():
        raise ValueError(f"{label} must not be a symlink: {path}")
    if not path.is_file():
        raise ValueError(f"{label} is not a regular file: {path}")
    return path.read_bytes()


def _read_canonical_scope(root: Path, supplied_path: Path) -> bytes:
    expected = root.joinpath(*PurePosixPath(M15B_EXECUTION_SCOPE_PATH).parts)
    if supplied_path.is_symlink():
        raise ValueError(f"execution scope must not be a symlink: {supplied_path}")
    try:
        supplied_resolved = supplied_path.resolve()
    except OSError as exc:
        raise ValueError("execution scope path could not be resolved") from exc
    if supplied_resolved != expected.resolve():
        raise ValueError("execution scope must use the canonical repository path")
    return _read_regular_file(expected, "execution scope")


def _resolve_repo_root(path: Path) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"repo_root must be an existing non-symlink directory: {path}")
    return path.resolve()


def _safe_detail(exc: BaseException) -> str:
    if isinstance(exc, ValueError):
        return str(exc)
    return exc.__class__.__name__
