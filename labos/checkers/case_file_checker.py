from __future__ import annotations

from pathlib import Path

from .report import CaseCheckReport


REQUIRED_CASE_FILES = [
    "00_problem_intake.yml",
    "01_thermal_design_passport.yml",
    "02_decision_board.md",
    "03_architecture_genomes.yml",
    "04_design_space_scorecard.md",
    "05_red_flags.md",
    "06_next_best_action.md",
    "07_validation_plan.md",
    "08_supplier_specification.md",
    "09_customer_memo.md",
    "10_claim_ledger.yml",
    "11_engineering_memory_entry.md",
]


def check_required_files(case_path: Path, report: CaseCheckReport) -> None:
    if not case_path.exists() or not case_path.is_dir():
        report.add("FAIL", "Required files", "Case path does not exist or is not a directory.", str(case_path))
        return

    for filename in REQUIRED_CASE_FILES:
        if not (case_path / filename).is_file():
            report.add("FAIL", "Required files", f"Missing required case file: {filename}", filename)


def iter_case_files(case_path: Path) -> list[Path]:
    if not case_path.exists():
        return []
    return sorted(path for path in case_path.iterdir() if path.is_file() and path.suffix.lower() in {".md", ".yml", ".yaml"})


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")

