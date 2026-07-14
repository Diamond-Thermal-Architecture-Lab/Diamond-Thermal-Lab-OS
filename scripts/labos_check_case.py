from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from labos.checkers.case_file_checker import check_required_files
from labos.checkers.claim_safety_checker import check_claim_safety
from labos.checkers.confidentiality_checker import check_confidentiality
from labos.checkers.evidence_sidecar_checker import check_evidence_sidecars
from labos.checkers.pattern_reference_checker import check_pattern_references
from labos.checkers.red_flag_checker import check_thermal_red_flags
from labos.checkers.report import CaseCheckReport
from labos.checkers.required_fields_checker import check_required_thermal_problem_fields
from labos.checkers.thermal_input_checker import check_critical_thermal_inputs


def run_case_check(case_path: Path, strict: bool = False) -> CaseCheckReport:
    report = CaseCheckReport(case_path=case_path)
    check_required_files(case_path, report)
    check_required_thermal_problem_fields(case_path, report)
    check_critical_thermal_inputs(case_path, report)
    check_thermal_red_flags(case_path, report)
    check_pattern_references(case_path, report)
    check_evidence_sidecars(case_path, report)
    check_claim_safety(case_path, report)
    check_confidentiality(case_path, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run local no-API Diamond Thermal Lab OS case checks.",
    )
    parser.add_argument("case_path", type=Path, help="Path to a Lab OS case folder.")
    parser.add_argument("--strict", action="store_true", help="Return exit code 1 for WARN.")
    args = parser.parse_args(argv)

    report = run_case_check(args.case_path, strict=args.strict)
    print(report.render())
    return report.exit_code(strict=args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
