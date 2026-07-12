from __future__ import annotations

import json

from .models import DecisionBoardResult


def _lines(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- none"


def render(result: DecisionBoardResult, as_json: bool = False) -> str:
    if as_json:
        return json.dumps(result.to_dict(), indent=2)

    candidates = (
        "\n".join(
            f"- {route.pattern_id}: {route.decision_status}; {route.note}" for route in result.candidate_routes
        )
        or "- none; no approved pattern candidate has been selected."
    )
    deferred = (
        "\n".join(f"- {route.pattern_id}: {route.reason}" for route in result.deferred_routes) or "- none"
    )
    actions = "\n".join(f"{action.priority}. {action.action}" for action in result.next_actions) or "- none"
    rules = ", ".join(rule.rule_id for rule in result.triggered_rules) or "none"
    return "\n\n".join(
        (
            f"Decision Board Preview: {result.case_id}",
            f"Board status:\n{result.board_status}",
            f"Decision state:\n{result.decision_state}",
            f"Current decision:\n{result.current_decision}",
            f"Decision basis:\n{_lines(result.decision_basis)}",
            f"Critical missing data:\n{_lines(result.critical_missing_data)}",
            f"Top uncertainties:\n{_lines(result.top_uncertainties)}",
            f"Candidate routes:\n{candidates}",
            f"Deferred routes:\n{deferred}",
            f"Next actions:\n{actions}",
            f"Hold points:\n{_lines(result.hold_points)}",
            f"Claim guardrails:\n{_lines(result.claim_guardrails)}",
            f"Triggered rules:\n{rules}",
            f"Validation note:\n{result.validation_note}",
        )
    )
