from __future__ import annotations

import json

from .models import ValidationResult


def render_validation(result: ValidationResult, as_json: bool = False) -> str:
    if as_json:
        return json.dumps(result.to_dict(), indent=2, sort_keys=True)
    return "\n\n".join(
        (
            "Human Decision Record Validation",
            f"Status:\n{result.status}",
            f"Case:\n{result.case_id}",
            f"Record status:\n{result.record_status}",
            f"Review outcome:\n{result.review_outcome}",
            f"Manifest binding:\n{'valid' if result.manifest_binding_valid else 'invalid'}",
            f"Approved routes:\n{_lines(result.approved_route_ids)}",
            f"Rejected routes:\n{_lines(result.rejected_route_ids)}",
            f"Deferred routes:\n{_lines(result.deferred_route_ids)}",
            f"Customer release:\n{result.customer_release_status}",
            f"Errors:\n{_lines(result.errors)}",
            f"Warnings:\n{_lines(result.warnings)}",
            f"Triggered rules:\n{_lines([rule.rule_id for rule in result.triggered_rules])}",
            f"Validation note:\n{result.validation_note}",
        )
    )


def exit_code(result: ValidationResult, strict: bool = False) -> int:
    if result.status == "PASS":
        return 0
    if result.status == "WARN":
        return 1
    return 2


def _lines(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- none"
