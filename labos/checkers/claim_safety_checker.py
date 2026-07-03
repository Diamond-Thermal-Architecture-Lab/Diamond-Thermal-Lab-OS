from __future__ import annotations

import re
from pathlib import Path

from .case_file_checker import iter_case_files
from .report import CaseCheckReport


UNSAFE_PATTERNS = [
    ("guaranteed", re.compile(r"\bguaranteed\b", re.IGNORECASE)),
    ("proven", re.compile(r"\bproven\b", re.IGNORECASE)),
    ("will solve", re.compile(r"\bwill solve\b", re.IGNORECASE)),
    ("eliminates overheating", re.compile(r"\beliminates overheating\b", re.IGNORECASE)),
    ("best solution", re.compile(r"\bbest solution\b", re.IGNORECASE)),
    ("validated", re.compile(r"\bvalidated\b", re.IGNORECASE)),
    ("breakthrough performance", re.compile(r"\bbreakthrough performance\b", re.IGNORECASE)),
    ("certain to reduce temperature", re.compile(r"\bcertain to reduce temperature\b", re.IGNORECASE)),
]


SAFE_VALIDATED_CONTEXTS = [
    "not validated",
    "unvalidated",
    "validation required",
    "validated results are not yet available",
    "not yet validated",
    "no validation",
    "no validated",
    "no technical assumption has been validated",
    "validated performance claims",
    "validated thermal performance claims",
    "treated as validated",
    "will be validated",
    "has been validated",
]


def _is_safe_validated_context(line: str) -> bool:
    lower = line.lower()
    if "validated" not in lower:
        return False
    if lower.lstrip().startswith(("status:", "validation_required:", "- status:")):
        return True
    return any(context in lower for context in SAFE_VALIDATED_CONTEXTS)


def _is_customer_facing(path: Path) -> bool:
    return path.name == "09_customer_memo.md" or "customer" in path.name.lower()


def _is_safe_proven_context(line: str) -> bool:
    lower = line.lower()
    return "if " in lower and "proven" in lower


def check_claim_safety(case_path: Path, report: CaseCheckReport) -> None:
    for path in iter_case_files(case_path):
        section = ""
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                section = stripped.lstrip("#").strip().lower()
                continue
            if section == "claims not allowed":
                continue

            for label, pattern in UNSAFE_PATTERNS:
                if not pattern.search(line):
                    continue
                if label == "validated" and _is_safe_validated_context(line):
                    continue
                if label == "proven" and _is_safe_proven_context(line):
                    continue
                severity = "FAIL" if _is_customer_facing(path) else "WARN"
                report.add(
                    severity,
                    "Claim safety warnings",
                    f"Potentially unsafe claim language found: {label}",
                    f"{path.name}:{line_number}",
                )

            lower = line.lower()
            if (
                "direct gan-on-diamond" in lower
                and any(term in lower for term in ["first step", "best", "recommended", "default"])
                and not any(term in lower for term in ["not", "do not", "should not"])
            ):
                severity = "FAIL" if _is_customer_facing(path) else "WARN"
                report.add(
                    severity,
                    "Claim safety warnings",
                    "Direct GaN-on-Diamond first-step language lacks safety guardrails.",
                    f"{path.name}:{line_number}",
                )
