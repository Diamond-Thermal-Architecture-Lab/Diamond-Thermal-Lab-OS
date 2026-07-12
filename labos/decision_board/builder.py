from __future__ import annotations

from pathlib import Path

from labos.checkers.thermal_input_checker import field_value
from labos.patterns.index import patterns_by_id
from labos.triage.engine import triage_case
from labos.triage.models import TriggeredRule

from .models import CandidateRoute, DecisionBoardResult, DeferredRoute, NextAction


RULESET_VERSION = "decision-board-1.0"


def _board_rule(
    rules: list[TriggeredRule], rule_id: str, severity: str, finding: str, evidence: str, action: str
) -> None:
    rules.append(TriggeredRule(rule_id, severity, finding, evidence, action))


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def _plain(value: str) -> str:
    return value.strip().strip("'\"")


def _problem_summary(case_path: Path) -> str:
    intake = (case_path / "00_problem_intake.yml").read_text(encoding="utf-8")
    device_type = _plain(field_value(intake, "device_type")) or "thermal system"
    application = _plain(field_value(intake, "application")) or "unspecified application"
    question = _plain(field_value(intake, "customer_question"))
    if question in {"|", ">"}:
        lines = intake.splitlines()
        start = next((index + 1 for index, line in enumerate(lines) if line.startswith("customer_question:")), 0)
        block: list[str] = []
        for line in lines[start:]:
            if line and not line[0].isspace():
                break
            if line.strip():
                block.append(line.strip())
        question = " ".join(block)
    question = question or "thermal architecture question"
    return f"{device_type} in {application}: {question}"


def _is_diamond_pattern(pattern_id: str) -> bool:
    return "DIA" in pattern_id


def _has_comparison_evidence(case_path: Path) -> bool:
    """Require an explicit review marker; pattern selection alone is not evidence."""
    scorecard_path = case_path / "04_design_space_scorecard.md"
    if not scorecard_path.is_file():
        return False
    scorecard = scorecard_path.read_text(encoding="utf-8").lower()
    markers = (
        "comparison_evidence: reviewed",
        "comparison evidence: reviewed",
        "reviewed comparison evidence",
        "architecture comparison approved for human review",
    )
    return any(marker in scorecard for marker in markers)


def _board_state(
    triage_status: str, comparison_evidence: bool, unresolved_candidates: list[str], rules: list[TriggeredRule]
) -> tuple[str, str, str]:
    if triage_status == "NEEDS_DATA":
        _board_rule(
            rules,
            "BOARD-STATUS-001",
            "WARN",
            "Decision Board is held because critical thermal inputs are incomplete.",
            "triage status NEEDS_DATA",
            "Complete the highest-impact intake gap before architecture selection.",
        )
        return "HOLD_FOR_DATA", "deferred", "Defer architecture selection until critical thermal inputs are defined."
    if triage_status == "NEEDS_MEASUREMENT":
        _board_rule(
            rules,
            "BOARD-STATUS-002",
            "WARN",
            "Decision Board is held because measurement evidence is the primary gap.",
            "triage status NEEDS_MEASUREMENT",
            "Obtain the required measurement evidence before route selection.",
        )
        return "HOLD_FOR_MEASUREMENT", "deferred", "Defer route selection until measurement evidence is available."
    if comparison_evidence and not unresolved_candidates:
        _board_rule(
            rules,
            "BOARD-STATUS-004",
            "INFO",
            "Explicit comparison evidence is available for human decision review.",
            "review marker in 04_design_space_scorecard.md",
            "Submit the reviewed comparison to the responsible human decision owner.",
        )
        return "READY_FOR_HUMAN_DECISION", "human_review_required", "Present the reviewed comparison for human decision approval."
    evidence_note = "no explicit reviewed comparison evidence" if not comparison_evidence else "unresolved screening candidates remain"
    _board_rule(
        rules,
        "BOARD-STATUS-003",
        "INFO",
        "Core inputs support comparative screening but not an approved architecture decision.",
        f"triage status READY_FOR_SCREENING; {evidence_note}",
        "Proceed with comparative screening of the identified candidate routes.",
    )
    return "READY_FOR_ARCHITECTURE_SCREENING", "screening", "Proceed with comparative screening of the identified candidate routes."


def _route(
    pattern_id: str, triage_status: str, secondary: list[str], rules: list[TriggeredRule]
) -> CandidateRoute:
    entries = patterns_by_id()
    entry = entries.get(pattern_id)
    uncertainties: list[str] = []
    validation: list[str] = ["Compare the route against case-specific geometry, boundary, package, and cost constraints."]
    decision_status = "screening_only"
    note = "Pattern reference is screening context only; it is not a final recommendation."
    evidence_status = "pattern reference only; no case-specific validation evidence"
    confidence = "low"

    if triage_status == "NEEDS_DATA":
        decision_status = "needs_data"
        evidence_status = "critical thermal inputs are incomplete"
        uncertainties.append("Critical thermal inputs remain incomplete.")
    if "interface_limited_candidate" in secondary and _is_diamond_pattern(pattern_id):
        decision_status = "needs_validation"
        uncertainties.append("Interface thermal resistance is unbounded or unresolved.")
        validation.append("Bound or measure interface thermal resistance and review bonding or contact quality.")
    if _is_diamond_pattern(pattern_id) and not any("interface thermal resistance" in item.lower() for item in uncertainties):
        uncertainties.append("Interface thermal resistance and bonding/contact quality require review.")
        validation.append("Review interface thermal resistance and bonding or contact quality.")
    if pattern_id == "PAT-GAN-DIA-001":
        decision_status = "human_review_required" if triage_status != "NEEDS_DATA" else "needs_data"
        uncertainties.extend(("Higher integration and manufacturability risk.", "GaN/diamond interface evidence requires review."))
        validation.append("Review manufacturability, integration risk, and interface evidence before prioritization.")
        note = "Higher-integration-risk screening candidate; do not treat as an immediate recommendation."
        _board_rule(
            rules,
            "BOARD-ROUTE-003",
            "WARN",
            "Direct GaN-on-Diamond remains a higher-integration-risk screening candidate.",
            pattern_id,
            "Require interface and manufacturability review before any prioritization.",
        )
    elif pattern_id == "PAT-CONV-PKG-001":
        note = "Legitimate neutral package-level screening candidate; it is not inferior by default."
    elif entry is not None:
        note = f"{entry.route_type} is a screening candidate only; case-specific evidence and validation remain required."

    return CandidateRoute(
        pattern_id=pattern_id,
        route_role="screening_candidate",
        confidence=confidence,
        evidence_status=evidence_status,
        key_uncertainties=_unique(uncertainties),
        required_validation=_unique(validation),
        decision_status=decision_status,
        note=note,
    )


def _deferred_routes(pattern_ids: list[str], triage_status: str, secondary: list[str]) -> list[DeferredRoute]:
    deferred: list[DeferredRoute] = []
    if triage_status == "NEEDS_DATA" and "PAT-GAN-DIA-001" in pattern_ids:
        deferred.append(
            DeferredRoute(
                "PAT-GAN-DIA-001",
                "Critical inputs are incomplete and the route has higher integration risk at this decision stage.",
                "Defined geometry, power, cooling boundary, interface evidence, and manufacturability review.",
            )
        )
    if "interface_limited_candidate" in secondary:
        for pattern_id in pattern_ids:
            if _is_diamond_pattern(pattern_id) and pattern_id != "PAT-GAN-DIA-001":
                deferred.append(
                    DeferredRoute(
                        pattern_id,
                        "Interface risk is not yet bounded for this interface-sensitive candidate.",
                        "Bounded interface thermal resistance and bonding/contact quality evidence.",
                    )
                )
    return deferred


def _next_actions(triage_action: str, secondary: list[str], pattern_ids: list[str], rules: list[TriggeredRule]) -> list[NextAction]:
    actions = [
        NextAction(
            1,
            triage_action,
            "The deterministic triage result identifies this as the highest-impact immediate uncertainty reduction.",
            "thermal engineer",
            "A documented input, bounded range, or measurement record that resolves the stated gap.",
        )
    ]
    if "interface_limited_candidate" in secondary:
        actions.append(
            NextAction(
                len(actions) + 1,
                "Bound interface thermal resistance for the relevant thermal stack.",
                "Interface uncertainty can change the relative value of material and package routes.",
                "thermal engineer",
                "A documented sensitivity range, measurement basis, or reviewed interface assumption.",
            )
        )
    if "measurement_limited" in secondary:
        actions.append(
            NextAction(
                len(actions) + 1,
                "Obtain powered thermal mapping or a calibrated junction-temperature estimate.",
                "The thermal symptom lacks a supporting measurement basis.",
                "test engineer",
                "A traceable measurement record with operating conditions and uncertainty.",
            )
        )
    if pattern_ids:
        actions.append(
            NextAction(
                len(actions) + 1,
                "Prepare a neutral comparison basis for the selected screening candidates.",
                "Pattern references organize options but do not rank or validate them.",
                "thermal engineer",
                "A reviewed scorecard with common assumptions, uncertainties, and validation needs.",
            )
        )
    actions.append(
        NextAction(
            len(actions) + 1,
            "Define supplier or test acceptance criteria before external engagement.",
            "Evidence requests need clear decision and inspection criteria.",
            "project owner",
            "A public-safe data request or validation plan with acceptance criteria.",
        )
    )
    _board_rule(
        rules,
        "BOARD-ACTION-001",
        "INFO",
        "The first Decision Board action is inherited from triage.",
        triage_action,
        triage_action,
    )
    return actions[:5]


def build_decision_board(case_path: Path) -> DecisionBoardResult:
    """Build a deterministic preview without modifying any case artifact."""
    triage = triage_case(case_path)
    rules = list(triage.triggered_rules)
    comparison_evidence = _has_comparison_evidence(case_path)
    board_status, decision_state, current_decision = _board_state(
        triage.status, comparison_evidence, triage.secondary_classifications, rules
    )
    patterns = list(triage.relevant_pattern_ids)
    candidates = [_route(pattern_id, triage.status, triage.secondary_classifications, rules) for pattern_id in patterns]
    if patterns:
        _board_rule(
            rules,
            "BOARD-ROUTE-001",
            "INFO",
            "Referenced patterns are retained as screening candidates only.",
            ", ".join(patterns),
            "Compare candidates with case-specific evidence before a human decision.",
        )
    else:
        _board_rule(
            rules,
            "BOARD-ROUTE-002",
            "INFO",
            "No approved pattern candidate is selected in the case.",
            "no known pattern references",
            "Select legitimate screening candidates only after critical inputs are complete.",
        )

    top_uncertainties = list(triage.critical_missing_data)
    if triage.top_uncertainty:
        top_uncertainties.append(triage.top_uncertainty)
    if "interface_limited_candidate" in triage.secondary_classifications:
        top_uncertainties.append("interface thermal resistance")
    if "package_limited_candidate" in triage.secondary_classifications:
        top_uncertainties.append("package-to-heat-sink path")

    hold_points = list(triage.do_not_do_first)
    if "interface_limited_candidate" in triage.secondary_classifications:
        hold_points.append("Do not optimize diamond thickness before interface resistance is bounded.")
    if patterns:
        hold_points.append("Do not treat pattern selection as a validated recommendation.")
    hold_points.append("Do not make customer-facing thermal claims before measurement or validation.")
    _board_rule(
        rules,
        "BOARD-HOLD-001",
        "WARN",
        "Decision hold points preserve traceability while case evidence remains incomplete or unvalidated.",
        triage.status,
        "Close the applicable data, evidence, and validation gaps before strengthening the decision.",
    )

    claim_guardrails = [
        "Screening output is not a validated thermal conclusion.",
        "Pattern selection is not a final recommendation.",
        "Measured and simulated evidence must be clearly distinguished.",
        "Supplier-stated properties must not be treated as system-level performance.",
    ]
    if triage.status != "READY_FOR_SCREENING":
        claim_guardrails.append("Customer-facing performance claims remain blocked until the stated evidence gap is closed.")
    _board_rule(
        rules,
        "BOARD-CLAIM-001",
        "WARN",
        "Claim guardrails remain active until case-specific evidence and review support stronger statements.",
        "triage state and unvalidated pattern context",
        "Keep external language aligned with the claim ledger and validation state.",
    )

    decision_basis = [rule.finding for rule in triage.triggered_rules]
    if not decision_basis:
        decision_basis.append("Core intake data supports conservative architecture screening.")
    if comparison_evidence:
        decision_basis.append("The scorecard contains an explicit reviewed comparison-evidence marker.")

    return DecisionBoardResult(
        case_id=triage.case_id,
        board_status=board_status,
        decision_state=decision_state,
        problem_summary=_problem_summary(case_path),
        triage_status=triage.status,
        primary_classification=triage.primary_classification,
        secondary_classifications=list(triage.secondary_classifications),
        confidence=triage.confidence,
        current_decision=current_decision,
        decision_basis=decision_basis,
        critical_missing_data=list(triage.critical_missing_data),
        top_uncertainties=_unique(top_uncertainties),
        candidate_routes=candidates,
        deferred_routes=_deferred_routes(patterns, triage.status, triage.secondary_classifications),
        next_actions=_next_actions(triage.next_best_action, triage.secondary_classifications, patterns, rules),
        hold_points=_unique(hold_points),
        claim_guardrails=_unique(claim_guardrails),
        relevant_pattern_ids=patterns,
        triggered_rules=rules,
        validation_note="This is a deterministic decision preview, not an approved engineering decision.",
        ruleset_version=RULESET_VERSION,
    )
