from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Callable

from .loader import iter_sidecar_json, load_json, read_case_id, require_case
from .models import SummaryResult, ValidationResult
from .validator import validate_evidence, validate_measurement_reference, validate_prediction_reality_record


OBJECTS: tuple[tuple[str, str, str, Callable[[Path, Path], ValidationResult]], ...] = (
    ("evidence", "evidence", "evidence_id", validate_evidence),
    ("measurement_reference", "measurements", "measurement_id", validate_measurement_reference),
    ("prediction_reality", "prediction_reality", "record_id", validate_prediction_reality_record),
)


def summarize_case(case_path: Path) -> SummaryResult:
    case_path = require_case(case_path)
    object_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    validation_counts: Counter[str] = Counter()
    ids: Counter[str] = Counter()
    broken: list[str] = []
    unknown_claims: list[str] = []
    unreviewed: list[str] = []
    missing_values: list[str] = []
    mismatches: list[str] = []
    comparisons: list[dict[str, object]] = []
    for object_type, folder, id_field, validator in OBJECTS:
        for path in iter_sidecar_json(case_path, folder):
            object_counts[object_type] += 1
            try:
                data = load_json(path)
                object_id = data.get(id_field)
                if isinstance(object_id, str):
                    ids[object_id] += 1
                status = data.get("status")
                if isinstance(status, str):
                    status_counts[status] += 1
                result = validator(case_path, path)
            except (OSError, ValueError) as exc:
                validation_counts["FAIL"] += 1
                broken.append(f"{path.name}: {exc}")
                continue
            validation_counts[result.status] += 1
            for error in result.errors:
                if "Unknown Claim Ledger ID" in error:
                    unknown_claims.append(error)
                if "unknown" in error.lower() or "references" in error.lower() or "does not match" in error.lower():
                    broken.append(f"{path.name}: {error}")
            if object_type == "evidence" and data.get("status") != "reviewed":
                unreviewed.append(path.name)
            if object_type == "measurement_reference" and data.get("value") is None:
                missing_values.append(path.name)
            if result.comparison:
                if result.comparison.get("comparable"):
                    comparisons.append(result.comparison)
                elif result.comparison.get("reason") == "unit_mismatch":
                    mismatches.append(path.name)
    duplicate_ids = sorted(object_id for object_id, count in ids.items() if count > 1)
    if object_counts["prediction_reality"] == 0 and object_counts["evidence"] == 0:
        loop = "NO_EVIDENCE"
    elif object_counts["measurement_reference"] == 0:
        loop = "EVIDENCE_CAPTURED"
    elif comparisons:
        loop = "HUMAN_REVIEW_REQUIRED"
    elif missing_values:
        loop = "MEASUREMENT_LINKED"
    elif object_counts["prediction_reality"]:
        loop = "COMPARISON_READY"
    else:
        loop = "MEASUREMENT_LINKED"
    gaps: list[str] = []
    if unreviewed:
        gaps.append("Human evidence review remains incomplete.")
    if missing_values:
        gaps.append("Measurement values remain unavailable for one or more references.")
    if object_counts["prediction_reality"] and not comparisons:
        gaps.append("No completed comparable prediction-versus-reality record is available.")
    status = "FAIL" if validation_counts["FAIL"] or duplicate_ids else "WARN" if validation_counts["WARN"] else "PASS"
    return SummaryResult(
        case_id=read_case_id(case_path),
        status=status,
        counts_by_object_type={name: object_counts[name] for name, _, _, _ in OBJECTS},
        counts_by_status=dict(sorted(status_counts.items())),
        validation_counts={key: validation_counts[key] for key in ("PASS", "WARN", "FAIL")},
        duplicate_ids=duplicate_ids,
        broken_references=broken,
        unknown_claim_ids=unknown_claims,
        unreviewed_evidence=unreviewed,
        missing_measurement_values=missing_values,
        comparable_prediction_reality_records=len(comparisons),
        pending_comparisons=max(0, object_counts["prediction_reality"] - len(comparisons)),
        unit_mismatches=mismatches,
        comparison_results=comparisons,
        unresolved_evidence_gaps=gaps,
        reality_loop_status=loop,
    )
