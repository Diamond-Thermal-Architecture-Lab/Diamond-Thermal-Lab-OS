from __future__ import annotations

import re
from pathlib import Path

from labos.checkers.case_file_checker import iter_case_files
from labos.checkers.thermal_input_checker import combined_case_text, field_value
from labos.patterns.index import resolve_pattern_id

from .models import TriageResult, TriggeredRule
from .rules import CRITICAL_FIELDS, has_bounded_interface_evidence, has_measurement_evidence, has_package_uncertainty, is_missing


PATTERN_RE = re.compile(r"\bPAT-[A-Z0-9]+(?:-[A-Z0-9]+)+\b", re.IGNORECASE)


def _patterns(case_path: Path) -> list[str]:
    found: list[str] = []
    for path in iter_case_files(case_path):
        for match in PATTERN_RE.finditer(path.read_text(encoding="utf-8")):
            canonical = resolve_pattern_id(match.group(0))
            if canonical and canonical not in found:
                found.append(canonical)
    return found


def _rule(rules: list[TriggeredRule], rule_id: str, severity: str, finding: str, evidence: str, action: str) -> None:
    rules.append(TriggeredRule(rule_id, severity, finding, evidence, action))


def triage_case(case_path: Path) -> TriageResult:
    intake_path = case_path / "00_problem_intake.yml"
    if not case_path.is_dir() or not intake_path.is_file():
        raise ValueError("Case path is invalid or missing 00_problem_intake.yml.")

    intake_text = intake_path.read_text(encoding="utf-8")
    values = {field: field_value(intake_text, field) for field in (*CRITICAL_FIELDS, "case_id")}
    text = combined_case_text(case_path)
    patterns = _patterns(case_path)
    rules: list[TriggeredRule] = []
    missing = [field for field in CRITICAL_FIELDS if is_missing(values.get(field, ""))]
    interface_bounded = has_bounded_interface_evidence(text)
    package_uncertain = has_package_uncertainty(text)
    diamond_context = any("DIA" in pattern for pattern in patterns) or any(term in text for term in ("diamond", "bonding", "submount", "tim", "solder"))
    secondary: list[str] = []
    do_not: list[str] = []

    if missing:
        for field in missing:
            _rule(rules, f"TRIAGE-DATA-{field.upper()}", "WARN", f"Critical input is incomplete: {field}.", field, f"Define {field}.")
        if "cooling_boundary" in missing:
            secondary.append("cooling_boundary_limited")
            _rule(rules, "TRIAGE-BOUNDARY-001", "WARN", "Cooling boundary is not defined.", "cooling_boundary", "Define package-to-heat-sink boundary.")
        if diamond_context and not interface_bounded:
            secondary.append("interface_limited_candidate")
            _rule(rules, "TRIAGE-INTERFACE-001", "WARN", "Interface resistance remains unbounded in an interface-sensitive context.", "pattern or material context", "Bound interface thermal resistance.")
        do_not.append("Do not start detailed FEM before defining heat source geometry and cooling boundary.")
        return TriageResult(values.get("case_id", case_path.name), "NEEDS_DATA", "insufficient_data", secondary, "low", "Critical thermal inputs are incomplete; screening cannot rank architectures safely.", missing, missing[0], f"Define {missing[0]}.", do_not, patterns, rules, "This is a deterministic screening assessment, not a validated thermal conclusion.")

    if diamond_context and not interface_bounded:
        secondary.append("interface_limited_candidate")
        _rule(rules, "TRIAGE-INTERFACE-001", "WARN", "Interface resistance is not bounded for an interface-sensitive route.", "case text and pattern context", "Bound or measure interface thermal resistance.")
        do_not.append("Do not optimize diamond thickness before bounding interface resistance.")
    if "PAT-GAN-DIA-001" in patterns:
        _rule(
            rules,
            "TRIAGE-DESIGN-002",
            "WARN",
            "Direct GaN-on-Diamond remains a higher-integration-risk screening candidate.",
            "PAT-GAN-DIA-001",
            "Review interface and manufacturability risks before prioritizing this route.",
        )
        do_not.append("Do not treat direct GaN-on-Diamond as the first recommendation without interface and integration evidence.")
    if "PAT-CONV-PKG-001" in patterns:
        _rule(
            rules,
            "TRIAGE-PACKAGE-002",
            "INFO",
            "Conventional package improvement remains a legitimate screening candidate.",
            "PAT-CONV-PKG-001",
            "Compare package-path improvements against other candidates using case data.",
        )
    if package_uncertain:
        secondary.append("package_limited_candidate")
        _rule(rules, "TRIAGE-PACKAGE-001", "WARN", "Package or mounting path remains uncertain.", "package path context", "Define package-to-heat-sink path.")
    symptom_asserted = any(term in text for term in ("overheating", "hot spot", "thermal symptom"))
    if symptom_asserted and not has_measurement_evidence(text):
        secondary.append("measurement_limited")
        _rule(rules, "TRIAGE-MEASUREMENT-001", "WARN", "Thermal symptom lacks supporting measurement evidence.", "no thermal map or calibrated measurement found", "Obtain powered thermal mapping.")
    material_ready = not secondary and "package_path" in text and interface_bounded
    if material_ready:
        primary = "material_limited_candidate"
        status = "READY_FOR_SCREENING"
        confidence = "medium"
        action = "Compare two or three candidate architectures with a screening model."
        _rule(rules, "TRIAGE-MATERIAL-001", "INFO", "Core inputs and interface/package context are available for material screening.", "intake and case context", action)
    elif "measurement_limited" in secondary and len(secondary) == 1:
        primary = "measurement_limited"
        status = "NEEDS_MEASUREMENT"
        confidence = "low"
        action = "Obtain powered thermal mapping."
    else:
        primary = "design_space_unclear"
        status = "READY_FOR_SCREENING"
        confidence = "low"
        action = "Compare two or three candidate architectures with a screening model."
        _rule(rules, "TRIAGE-DESIGN-001", "INFO", "Multiple routes remain plausible without a validated winner.", "case inputs", action)
    do_not.append("Do not treat pattern selection as a validated recommendation.")
    return TriageResult(values.get("case_id", case_path.name), status, primary, secondary, confidence, "Classification is conservative and rule-based; candidates are not confirmed bottlenecks.", [], secondary[0] if secondary else "architecture comparison evidence", action, do_not, patterns, rules, "This is a deterministic screening assessment, not a validated thermal conclusion.")
