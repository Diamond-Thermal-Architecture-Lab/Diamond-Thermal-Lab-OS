from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from labos.decision_record.package import load_json, load_verified_review_package
from labos.decision_record.validator import validate_decision_record

from .manifest import build_manifest, numbered_case_hashes, sha256_bytes, sha256_file
from .models import CanonicalProposalResult, PROPOSAL_FILES
from .renderer import manifest_json, render_application_checklist, render_diff, render_proposed_board


def build_canonical_decision_proposal(
    case_path: Path,
    review_package_dir: Path,
    record_path: Path,
    output_dir: Path,
    repo_root: Path,
    force: bool = False,
) -> CanonicalProposalResult:
    """Generate a separate proposal package without changing its source artifacts."""
    repo_root = repo_root.resolve(strict=True)
    case_path = case_path.resolve(strict=True)
    record_path = record_path.resolve(strict=True)
    output_dir = _resolve_output_dir(output_dir)
    _validate_case_path(case_path, repo_root)
    _validate_output_path(output_dir, case_path, review_package_dir.resolve(strict=True), repo_root)

    context = load_verified_review_package(review_package_dir)
    validation = validate_decision_record(context.path, record_path)
    if validation.status != "PASS":
        raise ValueError(f"Human Decision Record must validate PASS, not {validation.status}.")

    record = load_json(record_path)
    case_id = _text(record.get("case_id"))
    if case_id != case_path.name or case_id != _text(context.manifest.get("case_id")):
        raise ValueError("Canonical case directory, review package, and Human Decision Record must have the same case_id.")
    if _text(record.get("record_status")) != "final" or _text(record.get("review_outcome")) == "pending":
        raise ValueError("Canonical proposals require a final, non-pending Human Decision Record.")

    current_hashes = numbered_case_hashes(case_path)
    expected_hashes = context.manifest.get("source_case_sha256")
    binding = record.get("review_package_binding")
    binding_hashes = binding.get("source_case_sha256") if isinstance(binding, dict) else None
    if current_hashes != expected_hashes or current_hashes != binding_hashes:
        raise ValueError("Canonical case hashes do not match the bound review package and Human Decision Record.")

    current_board_path = case_path / "02_decision_board.md"
    if not current_board_path.is_file():
        raise ValueError("Canonical case is missing 02_decision_board.md.")
    current_board = current_board_path.read_text(encoding="utf-8")
    proposed_board = render_proposed_board(record, context.decision_board)
    proposed_diff = render_diff(current_board, proposed_board, case_id)
    checklist = render_application_checklist()
    artifact_hashes = {
        "proposed_02_decision_board.md": sha256_bytes(proposed_board.encode("utf-8")),
        "proposed_02_decision_board.diff": sha256_bytes(proposed_diff.encode("utf-8")),
        "canonical_application_checklist.md": sha256_bytes(checklist.encode("utf-8")),
    }
    manifest = build_manifest(
        case_id=case_id,
        review_manifest_sha256=context.manifest_sha256,
        record_path=record_path,
        record_sha256=sha256_file(record_path),
        record=record,
        review_manifest=context.manifest,
        validator_ruleset_version=validation.validator_ruleset_version,
        current_board_sha256=sha256_file(current_board_path),
        source_case_sha256=current_hashes,
        artifact_sha256=artifact_hashes,
    )
    artifacts = {
        "proposed_02_decision_board.md": proposed_board,
        "proposed_02_decision_board.diff": proposed_diff,
        "canonical_proposal_manifest.json": manifest_json(manifest),
        "canonical_application_checklist.md": checklist,
    }
    _validate_overwrite(output_dir, force)
    _write_artifacts(output_dir, artifacts)
    return CanonicalProposalResult(case_id, _text(record.get("review_outcome")), output_dir, PROPOSAL_FILES, manifest)


def _validate_case_path(case_path: Path, repo_root: Path) -> None:
    cases_root = (repo_root / "cases").resolve(strict=True)
    if not case_path.is_dir() or cases_root not in case_path.parents:
        raise ValueError("Canonical case path must be a case directory under cases/.")


def _resolve_output_dir(output_dir: Path) -> Path:
    candidate = output_dir if output_dir.is_absolute() else Path.cwd() / output_dir
    if candidate.exists():
        return candidate.resolve(strict=True)
    missing: list[str] = []
    current = candidate
    while not current.exists():
        missing.append(current.name)
        current = current.parent
    resolved = current.resolve(strict=True)
    for part in reversed(missing):
        resolved /= part
    return resolved


def _validate_output_path(output_dir: Path, case_path: Path, review_path: Path, repo_root: Path) -> None:
    if output_dir == repo_root:
        raise ValueError("Proposal output directory must not be the repository root.")
    protected = (case_path, review_path, repo_root / "patterns", repo_root / "memory", repo_root / ".git")
    for path in protected:
        parent = path.resolve(strict=False)
        if output_dir == parent or parent in output_dir.parents:
            raise ValueError(f"Unsafe proposal output directory: {output_dir}")


def _validate_overwrite(output_dir: Path, force: bool) -> None:
    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError(f"Proposal output path is not a directory: {output_dir}")
    existing = [name for name in PROPOSAL_FILES if (output_dir / name).exists()]
    if existing and not force:
        raise FileExistsError(f"Proposal file(s) already exist: {', '.join(existing)}")


def _write_artifacts(output_dir: Path, artifacts: dict[str, str]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    temporary: list[tuple[Path, Path]] = []
    try:
        for name in PROPOSAL_FILES:
            target = output_dir / name
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=output_dir, delete=False) as handle:
                handle.write(artifacts[name])
                temporary.append((Path(handle.name), target))
        for temp_path, target in temporary:
            os.replace(temp_path, target)
    finally:
        for temp_path, _ in temporary:
            if temp_path.exists():
                temp_path.unlink()


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""
