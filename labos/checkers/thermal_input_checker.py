from __future__ import annotations

import re
from pathlib import Path

from .case_file_checker import iter_case_files, read_text
from .report import CaseCheckReport


UNCERTAIN_RE = re.compile(r"\b(incomplete|unknown|uncertain|missing|not specified|tbd|to be defined)\b", re.IGNORECASE)


def _field_value(text: str, field: str) -> str:
    pattern = re.compile(rf"^{re.escape(field)}:\s*(.*)$", re.MULTILINE)
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def _combined_case_text(case_path: Path) -> str:
    return "\n".join(read_text(path) for path in iter_case_files(case_path)).lower()


def check_critical_thermal_inputs(case_path: Path, report: CaseCheckReport) -> None:
    intake_path = case_path / "00_problem_intake.yml"
    if not intake_path.is_file():
        return

    intake = intake_path.read_text(encoding="utf-8")
    checks = {
        "heat_source_geometry": "Heat source geometry is missing, incomplete, or uncertain.",
        "power_or_power_density": "Power or power density is missing, incomplete, or uncertain.",
        "cooling_boundary": "Cooling boundary is missing, incomplete, or uncertain.",
    }
    for field, message in checks.items():
        value = _field_value(intake, field)
        if not value or UNCERTAIN_RE.search(value):
            report.add("WARN", "Thermal input warnings", message, intake_path.name)

    combined = _combined_case_text(case_path)
    interface_discussed = any(
        term in combined
        for term in (
            "interface thermal resistance",
            "interface resistance",
            "thermal boundary resistance",
            "contact resistance",
            "bonding quality",
        )
    ) or re.search(r"\btbr\b", combined) is not None
    if not interface_discussed:
        report.add(
            "WARN",
            "Thermal input warnings",
            "Interface thermal resistance is not clearly discussed.",
            "case folder",
        )
