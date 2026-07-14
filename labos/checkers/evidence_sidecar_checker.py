from __future__ import annotations

from pathlib import Path

from labos.evidence.summary import summarize_case

from .report import CaseCheckReport


def check_evidence_sidecars(case_path: Path, report: CaseCheckReport) -> None:
    """Inspect optional evidence sidecars without requiring them for draft cases."""
    if not any((case_path / name).exists() for name in ("evidence", "measurements", "prediction_reality")):
        return
    try:
        summary = summarize_case(case_path)
    except (OSError, ValueError) as exc:
        report.add("FAIL", "Evidence and reality", f"Unable to inspect sidecars: {exc}", "sidecars")
        return
    for object_id in summary.duplicate_ids:
        report.add("FAIL", "Evidence and reality", f"Duplicate sidecar ID: {object_id}", "sidecars")
    for finding in sorted(set(summary.broken_references + summary.unknown_claim_ids)):
        report.add("FAIL", "Evidence and reality", finding, "sidecars")
    if summary.validation_counts.get("FAIL", 0) and not (summary.duplicate_ids or summary.broken_references or summary.unknown_claim_ids):
        report.add("FAIL", "Evidence and reality", "One or more evidence sidecars failed structural validation.", "sidecars")
    for item in summary.unresolved_evidence_gaps:
        report.add("WARN", "Evidence and reality", item, "sidecars")
