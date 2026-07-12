from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class TriggeredRule:
    rule_id: str
    severity: str
    finding: str
    evidence: str
    action_enabled: str


@dataclass(frozen=True)
class TriageResult:
    case_id: str
    status: str
    primary_classification: str
    secondary_classifications: list[str]
    confidence: str
    rationale: str
    critical_missing_data: list[str]
    top_uncertainty: str
    next_best_action: str
    do_not_do_first: list[str]
    relevant_pattern_ids: list[str]
    triggered_rules: list[TriggeredRule]
    validation_note: str
    ruleset_version: str = "1.0"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

