from __future__ import annotations

import re
from pathlib import Path

from .case_file_checker import iter_case_files, read_text
from .report import CaseCheckReport


def _combined_case_text(case_path: Path) -> str:
    return "\n".join(read_text(path) for path in iter_case_files(case_path)).lower()


def _has_negated_direct_diamond(text: str) -> bool:
    guarded_patterns = [
        r"do not (?:immediately )?recommend direct gan-on-diamond",
        r"direct gan-on-diamond should not",
        r"not .*direct gan-on-diamond.*first",
        r"direct gan-on-diamond.*hold",
        r"direct gan-on-diamond.*later candidate",
    ]
    return any(re.search(pattern, text, re.IGNORECASE | re.DOTALL) for pattern in guarded_patterns)


def check_thermal_red_flags(case_path: Path, report: CaseCheckReport) -> None:
    text = _combined_case_text(case_path)

    if "thermal conductivity" in text and "interface thermal resistance" not in text and "interface resistance" not in text:
        report.add(
            "WARN",
            "Red flags",
            "Bulk thermal conductivity is discussed without interface thermal resistance discussion.",
            "case folder",
        )

    diamond_recommendation = re.search(r"\brecommend(?:ed|s|ing)?\b[^.\n]{0,120}\bdiamond\b", text)
    if diamond_recommendation and "interface" not in diamond_recommendation.group(0):
        report.add(
            "WARN",
            "Red flags",
            "Diamond appears to be recommended without local explanation of interface risk.",
            "case folder",
        )

    direct_first_step = re.search(
        r"direct gan-on-diamond[^.\n]{0,160}(first step|default|best|recommend)",
        text,
        re.IGNORECASE,
    )
    if direct_first_step and not _has_negated_direct_diamond(text):
        report.add(
            "WARN",
            "Red flags",
            "Direct GaN-on-Diamond appears to be a first-step recommendation without adequate guardrails.",
            "case folder",
        )

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
