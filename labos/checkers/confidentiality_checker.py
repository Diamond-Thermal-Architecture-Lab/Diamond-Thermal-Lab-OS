from __future__ import annotations

from pathlib import Path

from .case_file_checker import iter_case_files
from .report import CaseCheckReport


KEY_CONFIDENTIALITY_FILES = [
    "00_problem_intake.yml",
    "08_supplier_specification.md",
    "09_customer_memo.md",
    "10_claim_ledger.yml",
    "11_engineering_memory_entry.md",
]

RESTRICTED_MARKERS = [
    "restricted process recipe",
    "proprietary growth recipe",
    "confidential customer name",
    "exact internal cost",
    "undisclosed supplier price",
    "trade secret",
]


def check_confidentiality(case_path: Path, report: CaseCheckReport) -> None:
    for filename in KEY_CONFIDENTIALITY_FILES:
        path = case_path / filename
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8").lower()
        if "confidentiality_level" not in text and "confidentiality level" not in text:
            report.add("WARN", "Confidentiality warnings", "Missing confidentiality level marker.", filename)

    for path in iter_case_files(case_path):
        text = path.read_text(encoding="utf-8").lower()
        for marker in RESTRICTED_MARKERS:
            if marker in text:
                report.add(
                    "FAIL",
                    "Confidentiality warnings",
                    f"Restricted marker found: {marker}",
                    path.name,
                )

    customer_memo = case_path / "09_customer_memo.md"
    if customer_memo.is_file() and "restricted" in customer_memo.read_text(encoding="utf-8").lower():
        report.add(
            "FAIL",
            "Confidentiality warnings",
            "Customer memo contains content labeled restricted.",
            customer_memo.name,
        )

    claim_ledger = case_path / "10_claim_ledger.yml"
    if claim_ledger.is_file() and "public_release:" not in claim_ledger.read_text(encoding="utf-8").lower():
        report.add(
            "FAIL",
            "Confidentiality warnings",
            "Claim ledger is missing public_release fields.",
            claim_ledger.name,
        )

