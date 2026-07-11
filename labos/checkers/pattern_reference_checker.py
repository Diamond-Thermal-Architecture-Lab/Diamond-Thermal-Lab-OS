from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .case_file_checker import iter_case_files
from .report import CaseCheckReport


REPO_ROOT = Path(__file__).resolve().parents[2]
PATTERN_INDEX = REPO_ROOT / "patterns" / "pattern_index.yml"
PATTERN_ID_RE = re.compile(r"\bPAT-[A-Z0-9]+(?:-[A-Z0-9]+)+\b", re.IGNORECASE)
INDEX_ID_RE = re.compile(r"^\s*(?:-\s*)?pattern_id:\s*['\"]?([A-Z0-9_-]+)", re.IGNORECASE | re.MULTILINE)
CLAIM_START_RE = re.compile(r"^\s*-\s*claim_id:\s*(.*?)\s*$", re.IGNORECASE)
CLAIM_FIELD_RE = re.compile(r"^\s{2,}([A-Za-z_][A-Za-z0-9_]*):\s*(.*?)\s*$")

PATTERN_CLAIM_TYPES = {"pattern_based", "screening", "architecture_screening"}
VALIDATED_STATUSES = {"validated", "validated_for_case"}
PUBLIC_RELEASE_ALLOWED = {"yes", "true", "allowed", "approved", "public"}
EMPTY_OR_PENDING = {"", "none", "null", "n/a", "na", "pending", "tbd", "todo", "unassigned"}
EVIDENCE_FIELDS = {
    "validation_evidence",
    "evidence",
    "evidence_reference",
    "measurement_reference",
    "validation_basis",
}
VALIDATION_EVIDENCE_TERMS = (
    "measurement",
    "measured",
    "test data",
    "reviewed case evidence",
    "validated evidence",
    "supplier data review",
)
PATTERN_ONLY_EVIDENCE_TERMS = (
    "pattern library",
    "pattern reference",
    "architecture pattern",
    "screening only",
)


@dataclass(frozen=True)
class ClaimRecord:
    fields: dict[str, str]
    raw_text: str
    line_number: int

    def value(self, field: str) -> str:
        return self.fields.get(field, "").strip().strip("'\"").lower()


def load_known_pattern_ids(index_path: Path = PATTERN_INDEX) -> set[str]:
    if not index_path.is_file():
        return set()
    text = index_path.read_text(encoding="utf-8")
    return {match.group(1).upper() for match in INDEX_ID_RE.finditer(text)}


def find_pattern_references(case_path: Path) -> dict[str, set[str]]:
    references: dict[str, set[str]] = {}
    for path in iter_case_files(case_path):
        for match in PATTERN_ID_RE.finditer(path.read_text(encoding="utf-8")):
            references.setdefault(match.group(0).upper(), set()).add(path.name)
    return references


def parse_claim_ledger(path: Path) -> list[ClaimRecord]:
    if not path.is_file():
        return []

    claims: list[ClaimRecord] = []
    current_fields: dict[str, str] | None = None
    current_lines: list[str] = []
    start_line = 0

    def finish_claim() -> None:
        if current_fields is not None:
            claims.append(ClaimRecord(dict(current_fields), "\n".join(current_lines), start_line))

    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        start = CLAIM_START_RE.match(line)
        if start:
            finish_claim()
            current_fields = {"claim_id": start.group(1).strip()}
            current_lines = [line]
            start_line = line_number
            continue
        if current_fields is None:
            continue
        current_lines.append(line)
        field = CLAIM_FIELD_RE.match(line)
        if field:
            current_fields[field.group(1).lower()] = field.group(2).strip()

    finish_claim()
    return claims


def _is_false_validation_requirement(value: str) -> bool:
    return value in {"false", "no", "none", "not_required", "not required"}


def has_validation_evidence(claim: ClaimRecord) -> bool:
    for field in EVIDENCE_FIELDS:
        value = claim.value(field)
        if value in EMPTY_OR_PENDING or value.startswith(("no ", "not ", "without ")):
            continue
        pattern_only = any(term in value for term in PATTERN_ONLY_EVIDENCE_TERMS)
        includes_validation_evidence = any(term in value for term in VALIDATION_EVIDENCE_TERMS)
        if not pattern_only or includes_validation_evidence:
            return True

    basis = claim.value("basis")
    return any(term in basis for term in VALIDATION_EVIDENCE_TERMS) and not basis.startswith(
        ("no ", "not ", "without ")
    )


def _has_completed_review(claim: ClaimRecord) -> bool:
    reviewer = claim.value("reviewer")
    status = claim.value("status")
    reviewer_records_completion = any(term in reviewer for term in ("reviewed", "approved"))
    return reviewer_records_completion or status in {"reviewed", "approved", *VALIDATED_STATUSES}


def _check_pattern_claims(claim_ledger: Path, report: CaseCheckReport) -> None:
    for claim in parse_claim_ledger(claim_ledger):
        if claim.value("claim_type") not in PATTERN_CLAIM_TYPES:
            continue

        claim_id = claim.value("claim_id") or f"line {claim.line_number}"
        status = claim.value("status")
        validation_required = claim.value("validation_required")
        has_evidence = has_validation_evidence(claim)
        validation_complete = has_evidence or (
            status in VALIDATED_STATUSES and _is_false_validation_requirement(validation_required)
        )

        if claim.value("confidence") == "high" and not validation_complete:
            report.add(
                "WARN",
                "Pattern references",
                f"Pattern-based claim {claim_id} has high confidence without validation support.",
                f"{claim_ledger.name}:{claim.line_number}",
            )

        if status in VALIDATED_STATUSES and not (
            has_evidence or _is_false_validation_requirement(validation_required)
        ):
            report.add(
                "FAIL",
                "Pattern references",
                f"Pattern-based claim {claim_id} is marked validated without evidence or a closed validation requirement.",
                f"{claim_ledger.name}:{claim.line_number}",
            )

        if (
            claim.value("public_release") in PUBLIC_RELEASE_ALLOWED
            and not has_evidence
            and not _has_completed_review(claim)
        ):
            report.add(
                "WARN",
                "Pattern references",
                f"Pattern-based claim {claim_id} allows public release without evidence or completed review.",
                f"{claim_ledger.name}:{claim.line_number}",
            )


def check_pattern_references(case_path: Path, report: CaseCheckReport) -> None:
    known_ids = load_known_pattern_ids()
    references = find_pattern_references(case_path)

    if not PATTERN_INDEX.is_file():
        report.add("WARN", "Pattern references", "Pattern index is unavailable.", str(PATTERN_INDEX))
    elif not known_ids:
        report.add("WARN", "Pattern references", "Pattern index contains no recognized pattern IDs.", str(PATTERN_INDEX))

    for pattern_id, filenames in sorted(references.items()):
        locations = ", ".join(sorted(filenames))
        if pattern_id in known_ids:
            report.add("INFO", "Pattern references", f"Known pattern reference: {pattern_id}", locations)
            continue

        customer_facing = any("customer_memo" in filename.lower() for filename in filenames)
        severity = "FAIL" if customer_facing else "WARN"
        report.add(
            severity,
            "Pattern references",
            f"Unknown pattern reference: {pattern_id}",
            locations,
        )

    _check_pattern_claims(case_path / "10_claim_ledger.yml", report)
