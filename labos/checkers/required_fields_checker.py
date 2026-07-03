from __future__ import annotations

import re
from pathlib import Path

from .report import CaseCheckReport


REQUIRED_THERMAL_PROBLEM_FIELDS = [
    "case_id",
    "title",
    "application",
    "device_type",
    "customer_question",
    "heat_source_geometry",
    "power_or_power_density",
    "current_material_stack",
    "cooling_boundary",
    "target_temperature_or_margin",
    "known_data",
    "missing_data",
    "confidentiality_level",
]


TOP_LEVEL_FIELD_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")


def top_level_fields(text: str) -> set[str]:
    fields: set[str] = set()
    for line in text.splitlines():
        if not line or line.startswith((" ", "\t", "#", "-")):
            continue
        match = TOP_LEVEL_FIELD_RE.match(line)
        if match:
            fields.add(match.group(1))
    return fields


def check_required_thermal_problem_fields(case_path: Path, report: CaseCheckReport) -> None:
    intake_path = case_path / "00_problem_intake.yml"
    if not intake_path.is_file():
        return
    fields = top_level_fields(intake_path.read_text(encoding="utf-8"))
    for field in REQUIRED_THERMAL_PROBLEM_FIELDS:
        if field not in fields:
            report.add("FAIL", "Required fields", f"Missing critical field in problem intake: {field}", intake_path.name)

