from __future__ import annotations

import hashlib
from pathlib import Path

from labos.review_package.manifest import source_hashes


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def numbered_case_hashes(case_path: Path) -> dict[str, str]:
    """Reuse the review-package source-hashing convention for stale-case detection."""
    return source_hashes(case_path)


def build_manifest(
    *,
    case_id: str,
    review_manifest_sha256: str,
    record_path: Path,
    record_sha256: str,
    record: dict[str, object],
    review_manifest: dict[str, object],
    validator_ruleset_version: str,
    current_board_sha256: str,
    source_case_sha256: dict[str, str],
    artifact_sha256: dict[str, str],
) -> dict[str, object]:
    return {
        "proposal_format_version": "canonical-decision-proposal-1.0",
        "case_id": case_id,
        "review_manifest_file": "review_manifest.json",
        "review_manifest_sha256": review_manifest_sha256,
        "human_decision_record_file": record_path.name,
        "human_decision_record_sha256": record_sha256,
        "record_format_version": record.get("record_format_version", ""),
        "record_status": record.get("record_status", ""),
        "review_outcome": record.get("review_outcome", ""),
        "validator_ruleset_version": validator_ruleset_version,
        "current_decision_board_file": f"cases/{case_id}/02_decision_board.md",
        "current_decision_board_sha256": current_board_sha256,
        "proposed_decision_board_file": "proposed_02_decision_board.md",
        "proposed_decision_board_sha256": artifact_sha256["proposed_02_decision_board.md"],
        "proposed_diff_file": "proposed_02_decision_board.diff",
        "proposed_diff_sha256": artifact_sha256["proposed_02_decision_board.diff"],
        "application_checklist_file": "canonical_application_checklist.md",
        "application_checklist_sha256": artifact_sha256["canonical_application_checklist.md"],
        "source_case_sha256": source_case_sha256,
        "approved_route_ids": list(record.get("approved_route_ids", [])),
        "rejected_route_ids": list(record.get("rejected_route_ids", [])),
        "deferred_route_ids": list(record.get("deferred_route_ids", [])),
        "customer_release_status": record.get("customer_release_status", ""),
        "validation_note": "This proposal has not been applied to the canonical case.",
    }
