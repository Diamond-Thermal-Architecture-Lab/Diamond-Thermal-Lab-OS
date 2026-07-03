from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Finding:
    severity: str
    section: str
    message: str
    path: str | None = None

    def format(self) -> str:
        location = f" [{self.path}]" if self.path else ""
        return f"- {self.severity}: {self.message}{location}"


@dataclass
class CaseCheckReport:
    case_path: Path
    findings: list[Finding] = field(default_factory=list)

    def add(self, severity: str, section: str, message: str, path: str | None = None) -> None:
        self.findings.append(Finding(severity=severity, section=section, message=message, path=path))

    @property
    def status(self) -> str:
        if any(f.severity == "FAIL" for f in self.findings):
            return "FAIL"
        if any(f.severity == "WARN" for f in self.findings):
            return "WARN"
        return "PASS"

    def exit_code(self, strict: bool = False) -> int:
        if self.status == "FAIL":
            return 2
        if self.status == "WARN":
            return 1 if strict else 0
        return 0

    def section_findings(self, section: str) -> list[Finding]:
        return [finding for finding in self.findings if finding.section == section]

    def recommended_actions(self) -> list[str]:
        if self.status == "PASS":
            return ["Proceed with normal engineering review."]

        actions: list[str] = []
        if self.section_findings("Required files"):
            actions.append("Add missing canonical case files before review.")
        if self.section_findings("Required fields"):
            actions.append("Complete missing critical thermal intake fields.")
        if self.section_findings("Thermal input warnings") or self.section_findings("Red flags"):
            actions.append("Resolve or explicitly justify thermal assumptions before stronger decisions.")
        if self.section_findings("Claim safety warnings"):
            actions.append("Rewrite overconfident claims and connect customer-facing statements to validation paths.")
        if self.section_findings("Confidentiality warnings"):
            actions.append("Remove restricted markers or move sensitive content to approved private handling.")
        return actions

    def render(self) -> str:
        sections = [
            "Required files",
            "Required fields",
            "Thermal input warnings",
            "Red flags",
            "Claim safety warnings",
            "Confidentiality warnings",
        ]
        lines = [
            f"Case Check Report: {self.case_path}",
            "",
            "Status:",
            self.status,
            "",
            "Sections:",
        ]
        for section in sections:
            lines.append(f"- {section}")
            findings = self.section_findings(section)
            if findings:
                lines.extend(f"  {finding.format()}" for finding in findings)
            else:
                lines.append("  - OK")

        lines.append("- Recommended next actions")
        for action in self.recommended_actions():
            lines.append(f"  - {action}")
        return "\n".join(lines)

