from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class TriggeredRule:
    rule_id: str
    severity: str
    finding: str
    evidence: str
    action_enabled: str
    title: str = ""
    triggering_inputs: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    engineering_rationale: str = ""
    evidence_boundary: str = ""

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "finding": self.finding,
            "evidence": self.evidence,
            "action_enabled": self.action_enabled,
        }
        optional = {
            "title": self.title,
            "triggering_inputs": self.triggering_inputs,
            "missing_evidence": self.missing_evidence,
            "engineering_rationale": self.engineering_rationale,
            "evidence_boundary": self.evidence_boundary,
        }
        data.update({key: value for key, value in optional.items() if value})
        return data


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
    ruleset_version: str = "1.1"
    thermomechanical_screening: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["triggered_rules"] = [rule.to_dict() for rule in self.triggered_rules]
        return data
