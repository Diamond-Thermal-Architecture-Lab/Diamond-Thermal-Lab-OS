from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .models import RECORD_FORMAT_VERSION
from .package import load_verified_review_package


def build_decision_record_template(review_package_dir: Path) -> dict[str, object]:
    context = load_verified_review_package(review_package_dir)
    manifest = context.manifest
    return {
        "record_format_version": RECORD_FORMAT_VERSION,
        "record_status": "draft",
        "case_id": manifest["case_id"],
        "review_package_binding": {
            "review_manifest_file": "review_manifest.json",
            "review_manifest_sha256": context.manifest_sha256,
            "package_format_version": manifest.get("package_format_version", ""),
            "board_status": manifest.get("board_status", ""),
            "decision_state": manifest.get("decision_state", ""),
            "decision_board_ruleset_version": manifest.get("decision_board_ruleset_version", ""),
            "triage_ruleset_version": manifest.get("triage_ruleset_version", ""),
            "source_case_sha256": manifest.get("source_case_sha256", {}),
        },
        "reviewer": {"name": "", "role": "", "organization": ""},
        "decision_owner": {"name": "", "role": "", "organization": ""},
        "review_outcome": "pending",
        "approved_route_ids": [],
        "rejected_route_ids": [],
        "deferred_route_ids": [],
        "decision_rationale": "",
        "approval_conditions": [],
        "required_additional_evidence": [],
        "evidence_references": [],
        "customer_release_status": "blocked",
        "customer_release_basis": [],
        "risk_acceptance": {"accepted": False, "accepted_risks": [], "rationale": ""},
        "acknowledgements": {
            "review_package_is_not_an_approved_decision": False,
            "pattern_selection_is_not_validation": False,
            "measured_simulated_supplier_and_pattern_evidence_are_distinct": False,
            "canonical_case_is_not_modified_automatically": False,
        },
        "human_attestation": {
            "reviewer_attested": False,
            "decision_owner_attested": False,
            "attestation_note": "Human attestation only; not a cryptographic or digital signature.",
        },
        "validation_note": "This record captures a human decision against a specific review package. It does not automatically modify the canonical case.",
    }


def create_decision_record_template(
    review_package_dir: Path, output_path: Path, repo_root: Path, force: bool = False
) -> dict[str, object]:
    record = build_decision_record_template(review_package_dir)
    output_resolved = resolve_output_file(output_path)
    validate_output_file_path(output_resolved, repo_root)
    if output_resolved.exists() and not force:
        raise FileExistsError(f"Decision record already exists: {output_resolved}")
    output_resolved.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(output_resolved, record)
    return record


def record_json(record: dict[str, object]) -> str:
    return json.dumps(record, indent=2, sort_keys=True) + "\n"


def write_json_atomic(path: Path, record: dict[str, object]) -> None:
    data = record_json(record)
    temp_name = ""
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as handle:
        temp_name = handle.name
        handle.write(data)
    os.replace(temp_name, path)


def resolve_output_file(output_path: Path) -> Path:
    candidate = output_path if output_path.is_absolute() else Path.cwd() / output_path
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


def validate_output_file_path(output_path: Path, repo_root: Path) -> None:
    repo_root = repo_root.resolve(strict=True)
    if output_path == repo_root or output_path.exists() and output_path.is_dir():
        raise ValueError("Decision record output must be an explicit file path.")
    protected = (repo_root / "cases", repo_root / "patterns", repo_root / "memory", repo_root / ".git")
    for protected_path in protected:
        protected_resolved = protected_path.resolve(strict=False)
        if _is_same_or_inside(output_path, protected_resolved):
            raise ValueError(f"Unsafe decision record output path: {output_path}")


def _is_same_or_inside(candidate: Path, parent: Path) -> bool:
    return candidate == parent or parent in candidate.parents
