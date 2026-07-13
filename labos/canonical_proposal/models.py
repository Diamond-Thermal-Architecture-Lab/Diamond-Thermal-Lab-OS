from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROPOSAL_FILES = (
    "proposed_02_decision_board.md",
    "proposed_02_decision_board.diff",
    "canonical_proposal_manifest.json",
    "canonical_application_checklist.md",
)


@dataclass(frozen=True)
class CanonicalProposalResult:
    case_id: str
    review_outcome: str
    output_dir: Path
    files: tuple[str, ...]
    manifest: dict[str, object]
