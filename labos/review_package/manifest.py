from __future__ import annotations

import hashlib
from pathlib import Path

from labos.decision_board.models import DecisionBoardResult

from .models import PACKAGE_FILES


PACKAGE_FORMAT_VERSION = "decision-review-package-1.0"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def numbered_case_files(case_path: Path) -> list[Path]:
    return sorted(path for path in case_path.iterdir() if path.is_file() and path.name[:2].isdigit() and path.name[2] == "_")


def source_hashes(case_path: Path) -> dict[str, str]:
    return {path.name: sha256_bytes(path.read_bytes()) for path in numbered_case_files(case_path)}


def artifact_hashes(artifacts: dict[str, str]) -> dict[str, str]:
    return {
        name: sha256_text(artifacts[name])
        for name in PACKAGE_FILES
        if name != "review_manifest.json" and name in artifacts
    }


def build_manifest(case_path: Path, result: DecisionBoardResult, artifacts: dict[str, str]) -> dict[str, object]:
    source_case_sha256 = source_hashes(case_path)
    return {
        "package_format_version": PACKAGE_FORMAT_VERSION,
        "case_id": result.case_id,
        "board_status": result.board_status,
        "decision_state": result.decision_state,
        "decision_board_ruleset_version": result.ruleset_version,
        "triage_ruleset_version": _triage_ruleset_version(result),
        "source_case_files": sorted(source_case_sha256),
        "source_case_sha256": source_case_sha256,
        "generated_artifacts": list(PACKAGE_FILES),
        "generated_artifact_sha256": artifact_hashes(artifacts),
        "relevant_pattern_ids": list(result.relevant_pattern_ids),
        "triggered_rule_ids": [rule.rule_id for rule in result.triggered_rules],
        "validation_note": "This package is for human review and is not an approved engineering decision.",
    }


def _triage_ruleset_version(result: DecisionBoardResult) -> str:
    return next((rule.rule_id.split("-", 2)[0].lower() + "-1.0" for rule in result.triggered_rules if rule.rule_id.startswith("TRIAGE-")), "triage-1.0")
