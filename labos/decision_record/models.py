from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


RECORD_FORMAT_VERSION = "1.0"
VALIDATOR_RULESET_VERSION = "human-decision-record-1.0"
ALLOWED_RECORD_STATUS = {"draft", "final"}
ALLOWED_OUTCOMES = {"pending", "approved", "deferred", "rejected", "more_evidence_required"}
ALLOWED_CUSTOMER_RELEASE = {"not_requested", "blocked", "approved"}


@dataclass(frozen=True)
class ReviewPackageContext:
    path: Path
    manifest: dict[str, object]
    manifest_sha256: str
    decision_board: dict[str, object]


@dataclass(frozen=True)
class RecordRule:
    rule_id: str
    severity: str
    finding: str
    evidence: str
    action_required: str


@dataclass(frozen=True)
class ValidationResult:
    status: str
    record_path: str
    case_id: str
    record_status: str
    review_outcome: str
    manifest_binding_valid: bool
    errors: list[str]
    warnings: list[str]
    approved_route_ids: list[str]
    rejected_route_ids: list[str]
    deferred_route_ids: list[str]
    customer_release_status: str
    validation_note: str
    validator_ruleset_version: str
    triggered_rules: list[RecordRule]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
