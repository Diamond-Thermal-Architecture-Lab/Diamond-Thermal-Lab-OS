from __future__ import annotations

import re
from pathlib import Path

from .case_file_checker import iter_canonical_case_files, read_text
from .pattern_reference_checker import has_validation_evidence, parse_claim_ledger
from .report import CaseCheckReport


INTERFACE_RISK_TERMS = (
    "interface thermal resistance",
    "thermal boundary resistance",
    "interface risk",
    "bonding quality",
    "contact resistance",
)

MANUFACTURABILITY_RISK_TERMS = (
    "manufacturability risk",
    "manufacturability",
    "manufacturing risk",
    "manufacturing route",
    "process risk",
    "integration risk",
    "qualification risk",
    "process compatibility",
)


def _combined_case_text(case_path: Path) -> str:
    return "\n".join(read_text(path) for path in iter_canonical_case_files(case_path)).lower()


def _has_interface_risk_evidence(text: str) -> bool:
    return any(term in text for term in INTERFACE_RISK_TERMS) or re.search(r"\btbr\b", text) is not None


def _has_validation_basis(text: str) -> bool:
    empty_values = {"", "none", "pending", "tbd", "todo", "n/a", "not available"}
    for line in text.splitlines():
        stripped = line.strip().lower()
        for field in ("validation_evidence", "validation_basis", "evidence_reference", "measurement_reference"):
            prefix = f"{field}:"
            if stripped.startswith(prefix):
                value = stripped.removeprefix(prefix).strip().strip("'\"")
                if value not in empty_values and not value.startswith(("no ", "not ", "without ")):
                    return True
        if re.search(r"(?:supported by|based on) (?:measurement|test data|reviewed case evidence)", stripped):
            if not stripped.startswith(("no ", "not ", "without ")):
                return True
    return False


def _is_customer_facing(path: Path) -> bool:
    return path.name == "09_customer_memo.md" or "customer_memo" in path.name.lower()


def _direct_first_step_lines(path: Path) -> list[int]:
    matches: list[int] = []
    section = ""
    for line_number, line in enumerate(read_text(path).splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            section = stripped.lstrip("#").strip().lower()
            continue
        if section == "claims not allowed":
            continue

        lower = line.lower()
        if "direct gan-on-diamond" not in lower:
            continue
        if any(
            term in lower
            for term in (
                "do not",
                "should not",
                "not the",
                "not be",
                "not recommend",
                "not recommended",
                "not as",
                "hold",
                "later candidate",
                "only if",
            )
        ):
            continue
        first_step_language = any(
            term in lower
            for term in ("first step", "immediate", "immediately", "default", "best", "primary recommendation")
        )
        direct_recommendation = re.search(r"\brecommend(?:ed|s|ing)?\b[^.\n]{0,80}\bdirect gan-on-diamond\b", lower)
        if first_step_language or direct_recommendation:
            matches.append(line_number)
    return matches


def _direct_claim_confidence_is_guarded(case_path: Path) -> bool:
    claims = [
        claim
        for claim in parse_claim_ledger(case_path / "10_claim_ledger.yml")
        if "direct gan-on-diamond" in claim.raw_text.lower()
    ]
    if not claims:
        return False
    for claim in claims:
        confidence = claim.value("confidence")
        if confidence in {"low", "medium"}:
            continue
        if confidence == "high" and has_validation_evidence(claim):
            continue
        return False
    return True


def _check_direct_gan_on_diamond_guardrails(case_path: Path, text: str, report: CaseCheckReport) -> None:
    interface_guardrail = _has_interface_risk_evidence(text)
    manufacturing_guardrail = any(term in text for term in MANUFACTURABILITY_RISK_TERMS)
    validation_guardrail = _has_validation_basis(text) or any(
        has_validation_evidence(claim)
        for claim in parse_claim_ledger(case_path / "10_claim_ledger.yml")
        if "direct gan-on-diamond" in claim.raw_text.lower()
    )
    confidence_guardrail = _direct_claim_confidence_is_guarded(case_path)

    for path in iter_canonical_case_files(case_path):
        for line_number in _direct_first_step_lines(path):
            missing: list[str] = []
            if not validation_guardrail:
                missing.append("validation basis")
            if not interface_guardrail:
                missing.append("interface-risk discussion")
            if not manufacturing_guardrail:
                missing.append("manufacturability-risk discussion")
            if not confidence_guardrail:
                missing.append("claim-ledger confidence at medium or lower")
            if not missing:
                continue
            severity = "FAIL" if _is_customer_facing(path) else "WARN"
            report.add(
                severity,
                "Red flags",
                "Direct GaN-on-Diamond first-step recommendation lacks " + ", ".join(missing) + ".",
                f"{path.name}:{line_number}",
            )


def check_thermal_red_flags(case_path: Path, report: CaseCheckReport) -> None:
    text = _combined_case_text(case_path)

    if "thermal conductivity" in text and not _has_interface_risk_evidence(text):
        report.add(
            "WARN",
            "Red flags",
            "Bulk thermal conductivity is discussed without interface thermal resistance discussion.",
            "case folder",
        )

    if "diamond" in text and not _has_interface_risk_evidence(text):
        report.add(
            "WARN",
            "Red flags",
            "Diamond is referenced without interface-risk discussion anywhere in the case.",
            "case folder",
        )

    _check_direct_gan_on_diamond_guardrails(case_path, text, report)

    simulation_recommendation = re.search(r"\b(recommend|launch|start|run)\b[^.\n]{0,80}\bsimulation\b", text)
    missing_boundary = "cooling boundary" in text and any(term in text for term in ["cooling boundary is uncertain", "cooling boundary: uncertain"])
    missing_geometry = "heat source geometry" in text and any(term in text for term in ["heat source geometry is incomplete", "heat source geometry: incomplete"])
    if simulation_recommendation and (missing_boundary or missing_geometry):
        report.add(
            "WARN",
            "Red flags",
            "Simulation is mentioned while geometry or boundary conditions remain undefined.",
            "case folder",
        )

    customer_memo = case_path / "09_customer_memo.md"
    if customer_memo.is_file():
        memo_text = customer_memo.read_text(encoding="utf-8").lower()
        if any(phrase in memo_text for phrase in ["will reduce", "will solve", "best solution"]) and "validation" not in memo_text:
            report.add(
                "FAIL",
                "Red flags",
                "Customer-facing claim appears without a validation path.",
                customer_memo.name,
            )
