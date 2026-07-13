from __future__ import annotations

import json
from pathlib import Path

from labos.decision_board.models import DecisionBoardResult
from labos.decision_board.report import render as render_decision_board

from .models import ReviewPackageResult


PACKAGE_NOTE = "This review package contains a deterministic decision preview, not an approved engineering decision."
VALIDATION_NOTE = "This package is for human review and is not an approved engineering decision."


def decision_board_markdown(result: DecisionBoardResult) -> str:
    return "\n\n".join(("# Decision Board Preview", PACKAGE_NOTE, render_decision_board(result))) + "\n"


def decision_board_json(result: DecisionBoardResult) -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"


def human_review_checklist() -> str:
    return """# Human Review Checklist

Review status: pending
Reviewer:
Review date:
Engineering owner:
Decision owner:
Approved architecture:
Approval conditions:
Rejected routes:
Deferred routes:
Required additional evidence:
Customer-release approval:
Comments:

## Review Questions

- Are critical thermal inputs sufficiently defined?
- Is the triage classification reasonable?
- Are candidate routes legitimate screening candidates?
- Has any route been presented more confidently than the evidence supports?
- Are interface and package risks sufficiently bounded?
- Are measured, simulated, supplier-stated, and pattern-based claims clearly separated?
- Is customer-facing release still blocked where validation is incomplete?
- Is a final architecture decision justified?

## Review Boundary

This checklist is controlled by human reviewers. The exporter does not approve architectures or fill approval fields automatically.
"""


def manifest_json(manifest: dict[str, object]) -> str:
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"


def render_export_summary(result: ReviewPackageResult, repo_root: Path | None = None) -> str:
    output_dir = _display_path(result.output_dir, repo_root)
    return "\n\n".join(
        (
            "Decision Review Package exported",
            f"Case:\n{result.case_id}",
            f"Board status:\n{result.board_status}",
            f"Decision state:\n{result.decision_state}",
            f"Output directory:\n{output_dir}",
            "Files:\n" + "\n".join(f"- {name}" for name in result.files),
            f"Validation note:\n{VALIDATION_NOTE}",
        )
    )


def _display_path(path: Path, repo_root: Path | None) -> str:
    if repo_root is not None:
        try:
            return path.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            pass
    return str(path)
