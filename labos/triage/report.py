from __future__ import annotations

import json

from .models import TriageResult


def render(result: TriageResult, as_json: bool = False) -> str:
    if as_json:
        return json.dumps(result.to_dict(), indent=2)
    rules = ", ".join(rule.rule_id for rule in result.triggered_rules) or "none"
    patterns = ", ".join(result.relevant_pattern_ids) or "none"
    secondary = ", ".join(result.secondary_classifications) or "none"
    return "\n".join((f"Thermal Triage Report: {result.case_id}", "", f"Status:\n{result.status}", f"Primary classification:\n{result.primary_classification}", f"Secondary classifications:\n{secondary}", f"Confidence:\n{result.confidence}", f"Top uncertainty:\n{result.top_uncertainty}", f"Next best action:\n{result.next_best_action}", f"Do not do first:\n{'; '.join(result.do_not_do_first)}", f"Relevant patterns:\n{patterns}", f"Triggered rules:\n{rules}", f"Validation note:\n{result.validation_note}"))
