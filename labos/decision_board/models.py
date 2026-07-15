from __future__ import annotations

from dataclasses import asdict, dataclass

from labos.triage.models import TriggeredRule


@dataclass(frozen=True)
class CandidateRoute:
    pattern_id: str
    route_role: str
    confidence: str
    evidence_status: str
    key_uncertainties: list[str]
    required_validation: list[str]
    decision_status: str
    note: str


@dataclass(frozen=True)
class DeferredRoute:
    pattern_id: str
    reason: str
    evidence_needed_to_reconsider: str


@dataclass(frozen=True)
class NextAction:
    priority: int
    action: str
    rationale: str
    owner_role: str
    completion_evidence: str


@dataclass(frozen=True)
class DecisionBoardResult:
    case_id: str
    board_status: str
    decision_state: str
    problem_summary: str
    triage_status: str
    primary_classification: str
    secondary_classifications: list[str]
    confidence: str
    current_decision: str
    decision_basis: list[str]
    critical_missing_data: list[str]
    top_uncertainties: list[str]
    candidate_routes: list[CandidateRoute]
    deferred_routes: list[DeferredRoute]
    next_actions: list[NextAction]
    hold_points: list[str]
    claim_guardrails: list[str]
    relevant_pattern_ids: list[str]
    triggered_rules: list[TriggeredRule]
    validation_note: str
    ruleset_version: str = "decision-board-1.0"

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["triggered_rules"] = [rule.to_dict() for rule in self.triggered_rules]
        return data
