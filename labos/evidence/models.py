from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class EvidenceRule:
    rule_id: str
    severity: str
    finding: str
    evidence: str
    action_required: str


@dataclass
class ValidationResult:
    object_type: str
    object_id: str
    case_id: str
    status: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    triggered_rules: list[EvidenceRule] = field(default_factory=list)
    comparison: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "object_type": self.object_type,
            "object_id": self.object_id,
            "case_id": self.case_id,
            "status": self.status,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "triggered_rules": [asdict(rule) for rule in self.triggered_rules],
        }
        if self.comparison is not None:
            result["comparison"] = self.comparison
        return result


@dataclass
class SummaryResult:
    case_id: str
    status: str
    counts_by_object_type: dict[str, int]
    counts_by_status: dict[str, int]
    validation_counts: dict[str, int]
    duplicate_ids: list[str]
    broken_references: list[str]
    unknown_claim_ids: list[str]
    unreviewed_evidence: list[str]
    missing_measurement_values: list[str]
    comparable_prediction_reality_records: int
    pending_comparisons: int
    unit_mismatches: list[str]
    comparison_results: list[dict[str, Any]]
    unresolved_evidence_gaps: list[str]
    reality_loop_status: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("duplicate_ids", "broken_references", "unknown_claim_ids", "unreviewed_evidence", "missing_measurement_values", "unit_mismatches", "unresolved_evidence_gaps"):
            data[key] = sorted(data[key])
        data["comparison_results"] = sorted(data["comparison_results"], key=lambda item: str(item.get("record_id", "")))
        return data


def decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")
