from __future__ import annotations

import json

from .models import SummaryResult, ValidationResult


def render_validation(result: ValidationResult, as_json: bool = False) -> str:
    if as_json:
        return json.dumps(result.to_dict(), indent=2, sort_keys=True, ensure_ascii=True)
    lines = [
        f"{result.object_type.replace('_', ' ').title()} Validation",
        "",
        "Status:", result.status,
        "Case:", result.case_id,
        "Object:", result.object_id or "unknown",
        "Errors:",
    ]
    lines.extend(f"- {item}" for item in result.errors) or lines.append("- none")
    lines.append("Warnings:")
    lines.extend(f"- {item}" for item in result.warnings) or lines.append("- none")
    if result.comparison is not None:
        lines.append("Comparison:")
        lines.append(json.dumps(result.comparison, sort_keys=True, ensure_ascii=True))
    lines.append("Validation note:")
    lines.append("PASS indicates structural and traceability quality only; it is not technical validation or approval.")
    return "\n".join(lines)


def render_summary(result: SummaryResult, as_json: bool = False) -> str:
    if as_json:
        return json.dumps(result.to_dict(), indent=2, sort_keys=True, ensure_ascii=True)
    lines = [
        f"Evidence and Reality Summary: {result.case_id}", "", "Status:", result.status,
        "Reality loop status:", result.reality_loop_status, "", "Object counts:",
    ]
    lines.extend(f"- {key}: {value}" for key, value in result.counts_by_object_type.items())
    lines.append("Validation counts:")
    lines.extend(f"- {key}: {value}" for key, value in result.validation_counts.items())
    lines.append("Unresolved evidence gaps:")
    lines.extend(f"- {item}" for item in result.unresolved_evidence_gaps) or lines.append("- none")
    lines.append("Validation note:")
    lines.append("This read-only summary does not validate a model, approve an architecture, or change a claim.")
    return "\n".join(lines)
