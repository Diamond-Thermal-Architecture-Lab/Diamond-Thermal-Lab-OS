from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from labos.decision_board.models import DecisionBoardResult


PACKAGE_FILES = (
    "decision_board_preview.md",
    "decision_board_preview.json",
    "review_manifest.json",
    "human_review_checklist.md",
)


@dataclass(frozen=True)
class ReviewPackageResult:
    case_id: str
    board_status: str
    decision_state: str
    output_dir: Path
    files: tuple[str, ...]
    decision_board: DecisionBoardResult
    manifest: dict[str, object]
