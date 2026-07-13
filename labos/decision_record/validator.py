from __future__ import annotations

import json
from pathlib import Path

from labos.patterns.index import get_known_pattern_ids, resolve_pattern_id

from .models import (
    ALLOWED_CUSTOMER_RELEASE,
    ALLOWED_OUTCOMES,
    ALLOWED_RECORD_STATUS,
    VALIDATOR_RULESET_VERSION,
    RecordRule,
    ValidationResult,
)
from .package import load_json, load_verified_review_package


VALIDATION_NOTE = "This validator checks structure and decision guardrails. It does not verify human identity or create a cryptographic signature."
REQUIRED_TOP_LEVEL = (
    "record_format_version",
    "record_status",
    "case_id",
    "review_package_binding",
    "reviewer",
    "decision_owner",
    "review_outcome",
    "approved_route_ids",
    "rejected_route_ids",
    "deferred_route_ids",
    "decision_rationale",
    "approval_conditions",
    "required_additional_evidence",
    "evidence_references",
    "customer_release_status",
    "customer_release_basis",
    "risk_acceptance",
    "acknowledgements",
    "human_attestation",
    "validation_note",
)
ACK_FIELDS = (
    "review_package_is_not_an_approved_decision",
    "pattern_selection_is_not_validation",
    "measured_simulated_supplier_and_pattern_evidence_are_distinct",
    "canonical_case_is_not_modified_automatically",
)
ATTEST_FIELDS = ("reviewer_attested", "decision_owner_attested")


class _Collector:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.rules: list[RecordRule] = []

    def error(self, rule_id: str, finding: str, evidence: str, action: str) -> None:
        self.errors.append(finding)
        self.rules.append(RecordRule(rule_id, "FAIL", finding, evidence, action))

    def warn(self, rule_id: str, finding: str, evidence: str, action: str) -> None:
        self.warnings.append(finding)
        self.rules.append(RecordRule(rule_id, "WARN", finding, evidence, action))

    def info(self, rule_id: str, finding: str, evidence: str, action: str) -> None:
        self.rules.append(RecordRule(rule_id, "INFO", finding, evidence, action))


def validate_decision_record(review_package_dir: Path, record_path: Path) -> ValidationResult:
    context = load_verified_review_package(review_package_dir)
    record = load_json(record_path)
    collector = _Collector()
    _validate_schema(record, collector)

    record_status = _str(record.get("record_status"))
    review_outcome = _str(record.get("review_outcome"))
    release_status = _str(record.get("customer_release_status"))
    approved = _list_of_str(record.get("approved_route_ids"))
    rejected = _list_of_str(record.get("rejected_route_ids"))
    deferred = _list_of_str(record.get("deferred_route_ids"))

    binding_valid = _validate_binding(record, context.manifest, context.manifest_sha256, collector)
    _validate_routes(record, context, collector)
    _validate_outcome(record, context.manifest, collector)
    _validate_customer_release(record, context.manifest, collector)

    if review_outcome == "pending":
        collector.warn(
            "RECORD-OUTCOME-001",
            "Pending draft records require human completion before approval.",
            "review_outcome: pending",
            "Complete and validate a final human decision record when ready.",
        )

    status = "FAIL" if collector.errors else "WARN" if collector.warnings else "PASS"
    return ValidationResult(
        status=status,
        record_path=record_path.name,
        case_id=_str(record.get("case_id")),
        record_status=record_status,
        review_outcome=review_outcome,
        manifest_binding_valid=binding_valid,
        errors=collector.errors,
        warnings=collector.warnings,
        approved_route_ids=approved,
        rejected_route_ids=rejected,
        deferred_route_ids=deferred,
        customer_release_status=release_status,
        validation_note=VALIDATION_NOTE,
        validator_ruleset_version=VALIDATOR_RULESET_VERSION,
        triggered_rules=collector.rules,
    )


def _validate_schema(record: dict[str, object], collector: _Collector) -> None:
    for field in REQUIRED_TOP_LEVEL:
        if field not in record:
            collector.error("RECORD-SCHEMA-001", f"Missing required field: {field}", field, "Add the required field.")
    if _str(record.get("record_status")) not in ALLOWED_RECORD_STATUS:
        collector.error("RECORD-SCHEMA-002", "Invalid record_status.", _str(record.get("record_status")), "Use draft or final.")
    if _str(record.get("review_outcome")) not in ALLOWED_OUTCOMES:
        collector.error("RECORD-SCHEMA-003", "Invalid review_outcome.", _str(record.get("review_outcome")), "Use an allowed review outcome.")
    if _str(record.get("customer_release_status")) not in ALLOWED_CUSTOMER_RELEASE:
        collector.error("RECORD-SCHEMA-004", "Invalid customer_release_status.", _str(record.get("customer_release_status")), "Use not_requested, blocked, or approved.")
    for field in ("approved_route_ids", "rejected_route_ids", "deferred_route_ids", "approval_conditions", "required_additional_evidence", "evidence_references", "customer_release_basis"):
        if not isinstance(record.get(field), list):
            collector.error("RECORD-SCHEMA-005", f"Field must be a list: {field}", field, "Use a JSON array.")
    for field in ("review_package_binding", "reviewer", "decision_owner", "risk_acceptance", "acknowledgements", "human_attestation"):
        if not isinstance(record.get(field), dict):
            collector.error("RECORD-SCHEMA-006", f"Field must be an object: {field}", field, "Use a JSON object.")


def _validate_binding(record: dict[str, object], manifest: dict[str, object], manifest_sha256: str, collector: _Collector) -> bool:
    binding = record.get("review_package_binding") if isinstance(record.get("review_package_binding"), dict) else {}
    checks = {
        "review_manifest_sha256": manifest_sha256,
        "package_format_version": manifest.get("package_format_version", ""),
        "board_status": manifest.get("board_status", ""),
        "decision_state": manifest.get("decision_state", ""),
        "decision_board_ruleset_version": manifest.get("decision_board_ruleset_version", ""),
        "triage_ruleset_version": manifest.get("triage_ruleset_version", ""),
    }
    valid = True
    if _str(record.get("case_id")) != _str(manifest.get("case_id")):
        collector.error("RECORD-BINDING-001", "Record case_id does not match review manifest.", _str(record.get("case_id")), "Bind the record to the correct review package.")
        valid = False
    for field, expected in checks.items():
        if binding.get(field) != expected:
            collector.error("RECORD-BINDING-002", f"Review package binding mismatch: {field}", field, "Regenerate or correct the decision record binding.")
            valid = False
    if binding.get("source_case_sha256") != manifest.get("source_case_sha256"):
        collector.error("RECORD-BINDING-003", "Source case hash mapping does not match review manifest.", "source_case_sha256", "Use a record bound to this exact review manifest.")
        valid = False
    if valid:
        collector.info("RECORD-BINDING-000", "Review manifest binding is valid.", "review_manifest_sha256", "No binding action required.")
    return valid


def _validate_routes(record: dict[str, object], context, collector: _Collector) -> None:
    relevant = set(_list_of_str(context.manifest.get("relevant_pattern_ids")))
    board_routes = {
        route.get("pattern_id")
        for route in context.decision_board.get("candidate_routes", [])
        if isinstance(route, dict) and isinstance(route.get("pattern_id"), str)
    }
    board_routes.update(
        route.get("pattern_id")
        for route in context.decision_board.get("deferred_routes", [])
        if isinstance(route, dict) and isinstance(route.get("pattern_id"), str)
    )
    allowed_routes = relevant | {route for route in board_routes if route}
    known_ids = get_known_pattern_ids()
    route_sets = {
        "approved_route_ids": _list_of_str(record.get("approved_route_ids")),
        "rejected_route_ids": _list_of_str(record.get("rejected_route_ids")),
        "deferred_route_ids": _list_of_str(record.get("deferred_route_ids")),
    }
    for field, values in route_sets.items():
        if len(values) != len(set(values)):
            collector.warn("RECORD-ROUTE-001", f"Duplicate route IDs in {field}.", field, "Remove duplicate route IDs.")
        for route_id in values:
            canonical = resolve_pattern_id(route_id)
            if canonical is None:
                collector.error("RECORD-ROUTE-002", f"Unknown route or pattern ID: {route_id}", route_id, "Use a canonical route ID from the review package.")
                continue
            if route_id not in known_ids and canonical != route_id:
                collector.warn("RECORD-ROUTE-003", f"Recognized alias used in decision record: {route_id}; use canonical ID {canonical}.", route_id, f"Replace with {canonical}.")
            if canonical not in allowed_routes:
                collector.error("RECORD-ROUTE-004", f"Route is not present in the bound review package: {route_id}", route_id, "Use only routes from the bound review package.")
    canonical_sets = {
        field: [resolve_pattern_id(route_id) or route_id for route_id in values]
        for field, values in route_sets.items()
    }
    for field, values in canonical_sets.items():
        if len(values) != len(set(values)):
            collector.warn("RECORD-ROUTE-006", f"Duplicate route IDs after canonical resolution in {field}.", field, "Keep each canonical route ID only once.")
    approved, rejected, deferred = (
        set(canonical_sets["approved_route_ids"]),
        set(canonical_sets["rejected_route_ids"]),
        set(canonical_sets["deferred_route_ids"]),
    )
    if approved & rejected or approved & deferred or rejected & deferred:
        collector.error("RECORD-ROUTE-005", "Approved, rejected, and deferred route sets must be mutually disjoint.", "route lists", "Move each route ID to only one decision list.")


def _validate_outcome(record: dict[str, object], manifest: dict[str, object], collector: _Collector) -> None:
    outcome = _str(record.get("review_outcome"))
    status = _str(record.get("record_status"))
    board_status = _str(manifest.get("board_status"))
    release = _str(record.get("customer_release_status"))
    approved = _list_of_str(record.get("approved_route_ids"))
    rejected = _list_of_str(record.get("rejected_route_ids"))
    rationale = _str(record.get("decision_rationale"))
    evidence = _list_of_str(record.get("evidence_references"))
    required = _list_of_str(record.get("required_additional_evidence"))
    if outcome == "pending":
        if status != "draft":
            collector.warn("RECORD-OUTCOME-002", "Pending records should remain draft.", status, "Use record_status draft for pending records.")
        if approved:
            collector.error("RECORD-OUTCOME-003", "Pending records must not approve routes.", "approved_route_ids", "Leave approved_route_ids empty until final approval.")
        if release == "approved":
            collector.error("RECORD-RELEASE-001", "Pending records must not approve customer release.", release, "Keep customer release blocked or not requested.")
        return
    if status != "final":
        collector.error("RECORD-OUTCOME-004", "Final review outcomes require record_status final.", status, "Set record_status to final after human completion.")
    _require_identity(record, collector)
    if outcome == "approved":
        if board_status != "READY_FOR_HUMAN_DECISION":
            collector.error("RECORD-OUTCOME-005", f"Approved outcome requires READY_FOR_HUMAN_DECISION, not {board_status}.", board_status, "Do not approve HOLD or screening-only review packages.")
        _require_acknowledgements(record, collector)
        if not rationale:
            collector.error("RECORD-OUTCOME-006", "Approved outcome requires decision rationale.", "decision_rationale", "Add human decision rationale.")
        if not approved:
            collector.error("RECORD-OUTCOME-007", "Approved outcome requires at least one approved route.", "approved_route_ids", "Add the approved canonical route ID.")
        if not evidence:
            collector.error("RECORD-OUTCOME-008", "Approved outcome requires evidence references.", "evidence_references", "Add evidence references.")
        if _rationale_is_bulk_conductivity_only(rationale):
            collector.error(
                "RECORD-OUTCOME-019",
                "Approved outcome must not rely only on bulk thermal conductivity.",
                "decision_rationale",
                "Address system-level evidence, interfaces, package path, boundary conditions, and validation basis.",
            )
        _require_risk_addressed(record, collector)
    elif outcome == "deferred":
        _require_acknowledgements(record, collector)
        if not rationale:
            collector.error("RECORD-OUTCOME-009", "Deferred outcome requires decision rationale.", "decision_rationale", "Explain why the decision is deferred.")
        if not required:
            collector.error("RECORD-OUTCOME-010", "Deferred outcome requires additional evidence.", "required_additional_evidence", "List required additional evidence.")
        if release not in {"blocked", "not_requested"}:
            collector.error("RECORD-RELEASE-002", "Deferred outcome must not approve customer release.", release, "Keep customer release blocked or not requested.")
    elif outcome == "rejected":
        if not rejected:
            collector.error("RECORD-OUTCOME-011", "Rejected outcome requires rejected_route_ids.", "rejected_route_ids", "List rejected canonical route IDs.")
        if not rationale:
            collector.error("RECORD-OUTCOME-012", "Rejected outcome requires rationale.", "decision_rationale", "Add rejection rationale.")
        if not evidence:
            collector.warn("RECORD-OUTCOME-013", "Rejected outcome should cite evidence references.", "evidence_references", "Add evidence or explicit decision basis.")
    elif outcome == "more_evidence_required":
        _require_acknowledgements(record, collector)
        if approved:
            collector.error("RECORD-OUTCOME-014", "More-evidence-required outcome cannot approve a route.", "approved_route_ids", "Leave approved_route_ids empty.")
        if not required:
            collector.error("RECORD-OUTCOME-015", "More-evidence-required outcome requires additional evidence.", "required_additional_evidence", "List required additional evidence.")
        if not rationale:
            collector.error("RECORD-OUTCOME-016", "More-evidence-required outcome requires rationale.", "decision_rationale", "Add rationale.")
        if release not in {"blocked", "not_requested"}:
            collector.error("RECORD-RELEASE-003", "More-evidence-required outcome must not approve customer release.", release, "Keep customer release blocked or not requested.")


def _validate_customer_release(record: dict[str, object], manifest: dict[str, object], collector: _Collector) -> None:
    if _str(record.get("customer_release_status")) != "approved":
        return
    if _str(record.get("review_outcome")) != "approved":
        collector.error("RECORD-RELEASE-004", "Customer release approval requires approved review_outcome.", _str(record.get("review_outcome")), "Approve customer release only after technical approval.")
    if _str(record.get("record_status")) != "final":
        collector.error("RECORD-RELEASE-005", "Customer release approval requires final record status.", _str(record.get("record_status")), "Use record_status final.")
    if _str(manifest.get("board_status")) != "READY_FOR_HUMAN_DECISION":
        collector.error("RECORD-RELEASE-006", "Customer release approval requires READY_FOR_HUMAN_DECISION board status.", _str(manifest.get("board_status")), "Do not release customer claims from HOLD or screening-only packages.")
    if not _list_of_str(record.get("customer_release_basis")):
        collector.error("RECORD-RELEASE-007", "Customer release approval requires release basis.", "customer_release_basis", "Add customer release basis.")
    if not _list_of_str(record.get("evidence_references")):
        collector.error("RECORD-RELEASE-008", "Customer release approval requires evidence references.", "evidence_references", "Add evidence references.")
    _require_acknowledgements(record, collector)


def _require_identity(record: dict[str, object], collector: _Collector) -> None:
    reviewer = record.get("reviewer") if isinstance(record.get("reviewer"), dict) else {}
    owner = record.get("decision_owner") if isinstance(record.get("decision_owner"), dict) else {}
    if not _str(reviewer.get("name")) or not _str(reviewer.get("role")):
        collector.error("RECORD-IDENTITY-001", "Final approval requires reviewer name and role.", "reviewer", "Enter human-controlled reviewer name and role.")
    if not _str(owner.get("name")) or not _str(owner.get("role")):
        collector.error("RECORD-IDENTITY-002", "Final approval requires decision owner name and role.", "decision_owner", "Enter human-controlled decision owner name and role.")


def _require_acknowledgements(record: dict[str, object], collector: _Collector) -> None:
    ack = record.get("acknowledgements") if isinstance(record.get("acknowledgements"), dict) else {}
    attest = record.get("human_attestation") if isinstance(record.get("human_attestation"), dict) else {}
    for field in ACK_FIELDS:
        if ack.get(field) is not True:
            collector.error("RECORD-ATTEST-001", f"Acknowledgement must be true: {field}", field, "Complete all human acknowledgements.")
    for field in ATTEST_FIELDS:
        if attest.get(field) is not True:
            collector.error("RECORD-ATTEST-002", f"Human attestation must be true: {field}", field, "Complete human attestations.")
    note = _str(attest.get("attestation_note"))
    if "cryptographic or digital signature" not in note:
        collector.warn("RECORD-ATTEST-003", "Attestation note should state it is not a cryptographic or digital signature.", "attestation_note", "Use the standard attestation note.")


def _require_risk_addressed(record: dict[str, object], collector: _Collector) -> None:
    risk = record.get("risk_acceptance") if isinstance(record.get("risk_acceptance"), dict) else {}
    if not isinstance(risk.get("accepted"), bool):
        collector.error("RECORD-OUTCOME-017", "Risk acceptance must explicitly set accepted true or false.", "risk_acceptance.accepted", "Set accepted to true or false.")
    if not _str(risk.get("rationale")):
        collector.error("RECORD-OUTCOME-018", "Risk acceptance requires rationale.", "risk_acceptance.rationale", "Describe risk acceptance or rejection rationale.")


def _list_of_str(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _str(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _rationale_is_bulk_conductivity_only(rationale: str) -> bool:
    text = rationale.lower()
    if "bulk thermal conductivity" not in text and "higher thermal conductivity" not in text:
        return False
    system_terms = (
        "interface",
        "boundary",
        "package",
        "measurement",
        "measured",
        "validation",
        "validated",
        "comparison",
        "system",
        "thermal resistance",
        "tbr",
    )
    return not any(term in text for term in system_terms)
