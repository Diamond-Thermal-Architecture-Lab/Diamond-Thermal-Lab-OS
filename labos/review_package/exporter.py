from __future__ import annotations

from pathlib import Path

from labos.decision_board.builder import build_decision_board

from .manifest import build_manifest
from .models import PACKAGE_FILES, ReviewPackageResult
from .report import decision_board_json, decision_board_markdown, human_review_checklist, manifest_json


def export_decision_review_package(
    case_path: Path, output_dir: Path, repo_root: Path, force: bool = False
) -> ReviewPackageResult:
    case_path = case_path.resolve(strict=False)
    repo_root = repo_root.resolve(strict=True)
    output_dir_resolved = _resolve_output_dir(output_dir)
    _validate_output_path(case_path, output_dir_resolved, repo_root)

    decision_board = build_decision_board(case_path)
    artifacts = {
        "decision_board_preview.md": decision_board_markdown(decision_board),
        "decision_board_preview.json": decision_board_json(decision_board),
        "human_review_checklist.md": human_review_checklist(),
    }
    manifest = build_manifest(case_path, decision_board, artifacts)
    artifacts["review_manifest.json"] = manifest_json(manifest)

    _validate_overwrite(output_dir_resolved, force)
    output_dir_resolved.mkdir(parents=True, exist_ok=True)
    for name in PACKAGE_FILES:
        (output_dir_resolved / name).write_text(artifacts[name], encoding="utf-8", newline="\n")

    return ReviewPackageResult(
        case_id=decision_board.case_id,
        board_status=decision_board.board_status,
        decision_state=decision_board.decision_state,
        output_dir=output_dir_resolved,
        files=PACKAGE_FILES,
        decision_board=decision_board,
        manifest=manifest,
    )


def _resolve_output_dir(output_dir: Path) -> Path:
    candidate = output_dir if output_dir.is_absolute() else Path.cwd() / output_dir
    if candidate.exists():
        return candidate.resolve(strict=True)

    missing_parts: list[str] = []
    current = candidate
    while not current.exists():
        missing_parts.append(current.name)
        current = current.parent

    resolved = current.resolve(strict=True)
    for part in reversed(missing_parts):
        resolved = resolved / part
    return resolved


def _validate_output_path(case_path: Path, output_dir: Path, repo_root: Path) -> None:
    protected = (case_path, repo_root / "patterns", repo_root / "memory", repo_root / ".git")
    if output_dir == repo_root:
        raise ValueError("Output directory must not be the repository root.")
    for protected_path in protected:
        protected_resolved = protected_path.resolve(strict=False)
        if _is_same_or_inside(output_dir, protected_resolved):
            raise ValueError(f"Unsafe output directory: {output_dir}")


def _validate_overwrite(output_dir: Path, force: bool) -> None:
    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError(f"Output path exists and is not a directory: {output_dir}")
    existing = [name for name in PACKAGE_FILES if (output_dir / name).exists()]
    if existing and not force:
        raise FileExistsError(f"Review package file(s) already exist: {', '.join(existing)}")


def _is_same_or_inside(candidate: Path, parent: Path) -> bool:
    return candidate == parent or parent in candidate.parents
