from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PureWindowsPath
from typing import Iterable

from labos.benchmarks.integrity import sha256_bytes


M15B_SEALED_FILENAMES = (
    "RELEVANCE_REGISTRATION.md",
    "SCOPE_REGISTRATION.md",
    "SCORING_REGISTRATION.md",
    "SOURCE_DOSSIER.md",
)

_MANIFEST_KEYS = frozenset(
    {"manifest_version", "protocol_version", "registered_at_utc", "sealed_artifacts"}
)
_ARTIFACT_KEYS = frozenset({"filename", "byte_length", "sha256"})
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_UTC_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_VERIFICATION_CODES = frozenset(
    {
        "missing_artifact",
        "byte_length_mismatch",
        "sha256_mismatch",
        "unexpected_artifact",
        "unsafe_artifact_type",
    }
)
_PRESENCE_CODES = frozenset({"forbidden_filename_present", "unsafe_symlink_present"})


@dataclass(frozen=True)
class SealedArtifactRecord:
    filename: str
    byte_length: int
    sha256: str


@dataclass(frozen=True)
class SealedManifest:
    manifest_version: str
    protocol_version: str
    registered_at_utc: str
    sealed_artifacts: tuple[SealedArtifactRecord, ...]


@dataclass(frozen=True)
class SealedVerificationFinding:
    code: str
    filename: str
    detail: str


@dataclass(frozen=True)
class SealedPresenceFinding:
    code: str
    root: str
    path: str


def validate_sealed_filename(filename: str) -> str:
    if not isinstance(filename, str) or not filename:
        raise ValueError("sealed filename must be a non-empty string")
    if filename in (".", "..") or "/" in filename or "\\" in filename:
        raise ValueError(f"sealed filename must be a basename: {filename!r}")
    if PureWindowsPath(filename).drive or filename.startswith("/"):
        raise ValueError(f"sealed filename must not be drive-qualified or absolute: {filename!r}")
    return filename


def validate_registered_at_utc(value: str) -> str:
    if not isinstance(value, str) or not _UTC_TIMESTAMP_RE.fullmatch(value):
        raise ValueError("registered_at_utc must use YYYY-MM-DDTHH:MM:SSZ")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError("registered_at_utc must be a real UTC calendar timestamp") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise ValueError("registered_at_utc must use canonical UTC timestamp formatting")
    return value


def build_sealed_manifest(
    *,
    repo_root: Path,
    sealed_root: Path,
    artifact_filenames: Iterable[str],
    protocol_version: str,
    registered_at_utc: str,
    additional_forbidden_roots: Iterable[Path] = (),
) -> SealedManifest:
    resolved_sealed_root = _validate_external_storage(
        repo_root, sealed_root, additional_forbidden_roots
    )
    filenames = _canonical_filenames(artifact_filenames)
    if not isinstance(protocol_version, str) or not protocol_version:
        raise ValueError("protocol_version must be a non-empty string")
    validate_registered_at_utc(registered_at_utc)
    records: list[SealedArtifactRecord] = []
    for filename in filenames:
        artifact = resolved_sealed_root / filename
        _require_regular_artifact(artifact, filename)
        data = artifact.read_bytes()
        if not data:
            raise ValueError(f"sealed artifact must not be empty: {filename}")
        records.append(
            SealedArtifactRecord(filename=filename, byte_length=len(data), sha256=sha256_bytes(data))
        )
    manifest = SealedManifest(
        manifest_version="1.0",
        protocol_version=protocol_version,
        registered_at_utc=registered_at_utc,
        sealed_artifacts=tuple(records),
    )
    _validate_manifest(manifest)
    return manifest


def serialize_sealed_manifest(manifest: SealedManifest) -> bytes:
    _validate_manifest(manifest)
    payload = {
        "manifest_version": manifest.manifest_version,
        "protocol_version": manifest.protocol_version,
        "registered_at_utc": manifest.registered_at_utc,
        "sealed_artifacts": [
            {"filename": record.filename, "byte_length": record.byte_length, "sha256": record.sha256}
            for record in manifest.sealed_artifacts
        ],
    }
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def parse_sealed_manifest_bytes(
    data: bytes, *, expected_filenames: Iterable[str] | None = None
) -> SealedManifest:
    try:
        decoded = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("sealed manifest must be valid UTF-8") from exc
    try:
        payload = json.loads(decoded, object_pairs_hook=_reject_duplicate_object_keys)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"invalid sealed manifest JSON: {exc}") from exc
    if not isinstance(payload, dict) or set(payload) != _MANIFEST_KEYS:
        raise ValueError("sealed manifest has unknown, missing, or invalid top-level keys")
    artifacts = payload["sealed_artifacts"]
    if not isinstance(artifacts, list):
        raise ValueError("sealed_artifacts must be a list")
    records: list[SealedArtifactRecord] = []
    for artifact in artifacts:
        if not isinstance(artifact, dict) or set(artifact) != _ARTIFACT_KEYS:
            raise ValueError("sealed artifact has unknown, missing, or invalid keys")
        records.append(
            SealedArtifactRecord(
                filename=artifact["filename"],
                byte_length=artifact["byte_length"],
                sha256=artifact["sha256"],
            )
        )
    manifest = SealedManifest(
        manifest_version=payload["manifest_version"],
        protocol_version=payload["protocol_version"],
        registered_at_utc=payload["registered_at_utc"],
        sealed_artifacts=tuple(records),
    )
    _validate_manifest(manifest)
    if expected_filenames is not None:
        expected = set(_canonical_filenames(expected_filenames))
        actual = {record.filename for record in manifest.sealed_artifacts}
        if actual != expected:
            raise ValueError("sealed manifest filenames do not match the expected filename set")
    return manifest


def load_sealed_manifest(
    path: Path, *, expected_filenames: Iterable[str] | None = None
) -> SealedManifest:
    if path.is_symlink():
        raise ValueError(f"sealed manifest path must not be a symlink: {path}")
    if not path.is_file():
        raise ValueError(f"sealed manifest path is not a regular file: {path}")
    return parse_sealed_manifest_bytes(path.read_bytes(), expected_filenames=expected_filenames)


def write_new_sealed_manifest(path: Path, manifest: SealedManifest, *, sealed_root: Path) -> None:
    _validate_manifest(manifest)
    resolved_sealed_root = _resolve_existing_directory(sealed_root, "sealed_root")
    if path.is_symlink():
        raise ValueError(f"manifest output path must not be a symlink: {path}")
    if path.exists():
        if path.is_dir():
            raise ValueError(f"manifest output path is a directory: {path}")
        raise ValueError(f"manifest output already exists: {path}")
    if not path.parent.is_dir():
        raise ValueError(f"manifest output parent directory does not exist: {path.parent}")
    output_resolved = path.resolve()
    if _paths_overlap(output_resolved, resolved_sealed_root):
        raise ValueError("manifest output path must be outside sealed_root")
    data = serialize_sealed_manifest(manifest)
    created_output = False
    try:
        with path.open("xb") as output:
            created_output = True
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
    except FileExistsError as exc:
        raise ValueError(f"manifest output already exists: {path}") from exc
    except OSError as exc:
        if not created_output:
            raise
        try:
            path.unlink()
        except OSError as cleanup_exc:
            raise OSError(
                f"failed to write manifest output {path} and failed to remove partial output: {cleanup_exc}"
            ) from exc
        raise


def verify_sealed_manifest(
    manifest: SealedManifest,
    *,
    repo_root: Path,
    sealed_root: Path,
    additional_forbidden_roots: Iterable[Path] = (),
) -> tuple[SealedVerificationFinding, ...]:
    _validate_manifest(manifest)
    resolved_sealed_root = _validate_external_storage(
        repo_root, sealed_root, additional_forbidden_roots
    )
    expected = {record.filename: record for record in manifest.sealed_artifacts}
    findings: list[SealedVerificationFinding] = []
    actual_entries = {entry.name: entry for entry in resolved_sealed_root.iterdir()}
    for filename in sorted(expected):
        entry = actual_entries.get(filename)
        if entry is None:
            findings.append(SealedVerificationFinding("missing_artifact", filename, "registered artifact is absent"))
            continue
        if entry.is_symlink() or not entry.is_file():
            findings.append(SealedVerificationFinding("unsafe_artifact_type", filename, "artifact is not a regular non-symlink file"))
            continue
        data = entry.read_bytes()
        record = expected[filename]
        if len(data) != record.byte_length:
            findings.append(
                SealedVerificationFinding(
                    "byte_length_mismatch", filename, f"expected {record.byte_length} bytes, found {len(data)} bytes"
                )
            )
        current_sha256 = sha256_bytes(data)
        if current_sha256 != record.sha256:
            findings.append(SealedVerificationFinding("sha256_mismatch", filename, "exact byte SHA256 differs"))
    for filename, entry in actual_entries.items():
        if filename in expected:
            continue
        if entry.is_symlink() or not entry.is_file():
            findings.append(SealedVerificationFinding("unsafe_artifact_type", filename, "unexpected entry is not a regular non-symlink file"))
        else:
            findings.append(SealedVerificationFinding("unexpected_artifact", filename, "unexpected direct-child artifact"))
    return tuple(sorted(findings, key=lambda item: (item.filename, item.code, item.detail)))


def find_sealed_presence(
    *,
    roots: Iterable[Path],
    forbidden_filenames: Iterable[str],
    ignored_directory_names: Iterable[str] = (".git", "__pycache__"),
) -> tuple[SealedPresenceFinding, ...]:
    filenames = set(_canonical_filenames(forbidden_filenames))
    ignored = frozenset(ignored_directory_names)
    findings: list[SealedPresenceFinding] = []
    for supplied_root in roots:
        root = _resolve_existing_directory(supplied_root, "scan root")
        root_display = root.as_posix()
        for current, directories, files in os.walk(root, topdown=True, followlinks=False):
            current_path = Path(current)
            for directory in list(directories):
                child = current_path / directory
                relative = child.relative_to(root).as_posix()
                if child.is_symlink():
                    findings.append(SealedPresenceFinding("unsafe_symlink_present", root_display, relative))
                    if directory in filenames:
                        findings.append(SealedPresenceFinding("forbidden_filename_present", root_display, relative))
                    directories.remove(directory)
                    continue
                if directory in filenames:
                    findings.append(SealedPresenceFinding("forbidden_filename_present", root_display, relative))
                if directory in ignored:
                    directories.remove(directory)
            for filename in files:
                child = current_path / filename
                relative = child.relative_to(root).as_posix()
                if child.is_symlink():
                    findings.append(SealedPresenceFinding("unsafe_symlink_present", root_display, relative))
                if filename in filenames:
                    findings.append(SealedPresenceFinding("forbidden_filename_present", root_display, relative))
    return tuple(sorted(findings, key=lambda item: (item.root, item.path, item.code)))


def _reject_duplicate_object_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _canonical_filenames(filenames: Iterable[str]) -> tuple[str, ...]:
    values = tuple(validate_sealed_filename(filename) for filename in filenames)
    if not values:
        raise ValueError("at least one sealed artifact filename is required")
    if len(set(values)) != len(values):
        raise ValueError("sealed artifact filenames must be unique")
    return tuple(sorted(values))


def _validate_manifest(manifest: SealedManifest) -> None:
    if not isinstance(manifest, SealedManifest):
        raise ValueError("manifest must be a SealedManifest")
    if manifest.manifest_version != "1.0":
        raise ValueError("manifest_version must equal '1.0'")
    if not isinstance(manifest.protocol_version, str) or not manifest.protocol_version:
        raise ValueError("protocol_version must be a non-empty string")
    validate_registered_at_utc(manifest.registered_at_utc)
    records = manifest.sealed_artifacts
    if not isinstance(records, tuple) or not records:
        raise ValueError("sealed_artifacts must be a non-empty tuple")
    filenames: list[str] = []
    for record in records:
        if not isinstance(record, SealedArtifactRecord):
            raise ValueError("sealed artifact records must be SealedArtifactRecord instances")
        filenames.append(validate_sealed_filename(record.filename))
        if isinstance(record.byte_length, bool) or not isinstance(record.byte_length, int) or record.byte_length <= 0:
            raise ValueError("sealed artifact byte_length must be an integer greater than zero")
        if not isinstance(record.sha256, str) or not _SHA256_RE.fullmatch(record.sha256):
            raise ValueError("sealed artifact sha256 must be 64 lowercase hexadecimal characters")
    if len(set(filenames)) != len(filenames):
        raise ValueError("sealed artifact filenames must be unique")
    if filenames != sorted(filenames):
        raise ValueError("sealed artifact records must be sorted by filename")


def _validate_external_storage(
    repo_root: Path, sealed_root: Path, additional_forbidden_roots: Iterable[Path]
) -> Path:
    resolved_repo_root = _resolve_existing_directory(repo_root, "repo_root")
    resolved_sealed_root = _resolve_existing_directory(sealed_root, "sealed_root")
    forbidden_roots = [resolved_repo_root]
    for root in additional_forbidden_roots:
        forbidden_roots.append(_resolve_existing_directory(root, "forbidden root"))
    for forbidden_root in forbidden_roots:
        if _paths_overlap(resolved_sealed_root, forbidden_root):
            raise ValueError("sealed_root must be disjoint from repository and forbidden roots")
    return resolved_sealed_root


def _resolve_existing_directory(path: Path, label: str) -> Path:
    if path.is_symlink():
        raise ValueError(f"{label} must not be a symlink: {path}")
    if not path.exists() or not path.is_dir():
        raise ValueError(f"{label} must be an existing directory: {path}")
    return path.resolve()


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


def _require_regular_artifact(path: Path, filename: str) -> None:
    if path.is_symlink():
        raise ValueError(f"sealed artifact must not be a symlink: {filename}")
    if not path.exists():
        raise ValueError(f"sealed artifact does not exist: {filename}")
    if not path.is_file():
        raise ValueError(f"sealed artifact is not a regular file: {filename}")
