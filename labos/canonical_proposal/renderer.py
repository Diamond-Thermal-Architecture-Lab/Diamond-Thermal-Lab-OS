from __future__ import annotations

import difflib
import json


PROPOSAL_WARNING = (
    "This is a proposed canonical Decision Board generated from a validated Human Decision Record. "
    "It has not been applied to the canonical case."
)


def render_proposed_board(record: dict[str, object], decision_board: dict[str, object]) -> str:
    case_id = _text(record.get("case_id"))
    outcome = _text(record.get("review_outcome"))
    binding = _mapping(record.get("review_package_binding"))
    reviewer = _mapping(record.get("reviewer"))
    owner = _mapping(record.get("decision_owner"))
    attestation = _mapping(record.get("human_attestation"))
    risk = _mapping(record.get("risk_acceptance"))
    claim_guardrails = _strings(decision_board.get("claim_guardrails"))
    if not claim_guardrails:
        claim_guardrails = ["Customer-facing claims remain limited to the validated Human Decision Record and its evidence references."]
    residual = _unique(_strings(decision_board.get("top_uncertainties")) + _strings(record.get("required_additional_evidence")))
    lines = [
        "# Proposed Canonical Decision Board",
        "",
        PROPOSAL_WARNING,
        "",
        f"Case ID: {case_id}",
        f"Decision status: {_decision_status(outcome)}",
        f"Human review outcome: {outcome}",
        "",
        "## Source Review-Package Binding",
        "",
        f"- Review manifest: {binding.get('review_manifest_file', 'review_manifest.json')}",
        f"- Review manifest SHA256: {binding.get('review_manifest_sha256', '')}",
        f"- Board status at review: {binding.get('board_status', '')}",
        f"- Decision state at review: {binding.get('decision_state', '')}",
        "",
        "## Current Decision",
        "",
        _current_decision(outcome, decision_board),
        "",
        "## Approved Routes",
        "",
        _markdown_list(_strings(record.get("approved_route_ids"))),
        "",
        "## Rejected Routes",
        "",
        _markdown_list(_strings(record.get("rejected_route_ids"))),
        "",
        "## Deferred Routes",
        "",
        _markdown_list(_strings(record.get("deferred_route_ids"))),
        "",
        "## Decision Rationale",
        "",
        _text(record.get("decision_rationale")) or "No additional rationale was recorded.",
        "",
        "## Approval Conditions",
        "",
        _markdown_list(_strings(record.get("approval_conditions"))),
        "",
        "## Required Additional Evidence",
        "",
        _markdown_list(_strings(record.get("required_additional_evidence"))),
        "",
        "## Evidence References",
        "",
        _markdown_list(_strings(record.get("evidence_references"))),
        "",
        "## Key Residual Uncertainties",
        "",
        _markdown_list(residual),
        "",
        "## Risk Acceptance Summary",
        "",
        f"- Accepted: {risk.get('accepted', False)}",
        f"- Accepted risks: {', '.join(_strings(risk.get('accepted_risks'))) or 'none recorded'}",
        f"- Rationale: {_text(risk.get('rationale')) or 'No additional rationale was recorded.'}",
        "",
        "## Customer-Release Status",
        "",
        f"- Status: {_text(record.get('customer_release_status'))}",
        "- This record does not establish complete technical validation, legal approval, regulatory approval, quality approval, or automatic customer-release authorization.",
        "",
        "## Claim Guardrails",
        "",
        _markdown_list(claim_guardrails),
        "",
        "## Human Review Fields",
        "",
        f"- Reviewer: {_human_field(reviewer, 'name')} ({_human_field(reviewer, 'role')})",
        f"- Reviewer organization: {_human_field(reviewer, 'organization')}",
        f"- Decision owner: {_human_field(owner, 'name')} ({_human_field(owner, 'role')})",
        f"- Decision owner organization: {_human_field(owner, 'organization')}",
        f"- Reviewer attested: {attestation.get('reviewer_attested', False)}",
        f"- Decision owner attested: {attestation.get('decision_owner_attested', False)}",
        f"- Attestation note: {_text(attestation.get('attestation_note'))}",
        "",
        "## Validation Note",
        "",
        "Human-entered identities and attestations are not cryptographically verified. This proposal is a review artifact only and requires a separate explicit PR-based canonical application workflow.",
        "",
        "## Canonical-Write Warning",
        "",
        "Do not copy, apply, or merge this proposal automatically. Review the accompanying diff, current case hashes, confidentiality implications, claim ledger implications, and human approval conditions before any explicit canonical-file change.",
        "",
    ]
    return "\n".join(lines)


def render_diff(current: str, proposed: str, case_id: str) -> str:
    label = f"cases/{case_id}/02_decision_board.md"
    return "".join(
        difflib.unified_diff(
            current.splitlines(keepends=True),
            proposed.splitlines(keepends=True),
            fromfile=f"a/{label}",
            tofile=f"b/{label}",
            lineterm="\n",
        )
    )


def render_application_checklist() -> str:
    return """# Canonical Application Checklist

Application status: pending
Applied by:
Application reviewer:
Application date:
Target branch:
Target commit before application:
Target commit after application:
PR number:
Independent reviewer:
Comments:

## Required Checks

- [ ] Human Decision Record validation status is PASS.
- [ ] Manifest binding is unchanged.
- [ ] Current canonical case hashes still match the proposal manifest.
- [ ] Proposed diff has been reviewed.
- [ ] Route IDs are canonical.
- [ ] No unsupported claims were added.
- [ ] Customer-release status has not been overstated.
- [ ] Reviewer and decision-owner identity have not been represented as cryptographically verified.
- [ ] Confidentiality review is complete.
- [ ] Claim ledger implications have been reviewed.
- [ ] Final application will occur through a separate explicit PR.

## Boundary

This checklist is controlled by humans. A Canonical Decision Proposal is not applied automatically and does not itself authorize a canonical Decision Board change.
"""


def manifest_json(manifest: dict[str, object]) -> str:
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"


def _decision_status(outcome: str) -> str:
    return {"approved": "approved by human record", "deferred": "deferred", "rejected": "rejected", "more_evidence_required": "more evidence required"}.get(outcome, outcome)


def _current_decision(outcome: str, decision_board: dict[str, object]) -> str:
    if outcome == "approved":
        return "The listed approved routes are recorded as the human decision, subject to the stated approval conditions and evidence references."
    if outcome == "deferred":
        return "Architecture selection remains deferred pending the listed additional evidence. Deferral is not rejection."
    if outcome == "rejected":
        return "The listed routes are recorded as rejected for this decision context; this does not establish physical impossibility without supporting evidence."
    if outcome == "more_evidence_required":
        return "No route is approved. The architecture decision remains open until the listed additional evidence is reviewed."
    return _text(decision_board.get("current_decision")) or "No current decision was recorded."


def _mapping(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _strings(value: object) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _human_field(values: dict[str, object], field: str) -> str:
    return _text(values.get(field)) or "not provided"


def _markdown_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- none recorded"


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))
