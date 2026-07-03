from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "labos_check_case.py"


REQUIRED_FILES = [
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


BASE_INTAKE = """case_id: unit-case
title: Unit Test Thermal Case
application: RF module
device_type: GaN RF PA
customer_question: Which thermal route should be evaluated first?
heat_source_geometry: bounded heat source dimensions are available
power_or_power_density: bounded power density range is available
current_material_stack: GaN device in conventional package
cooling_boundary: heat sink boundary is defined for screening
target_temperature_or_margin: increase thermal margin
known_data:
  - interface thermal resistance is included in the assumptions
missing_data:
  - validation data is not yet available
confidentiality_level: public
"""


BASE_CLAIMS = """claims:
  - claim_id: CLM-001
    claim: The case is ready for preliminary screening.
    claim_type: assumption
    basis: Unit test fixture
    assumptions:
      - Interface thermal resistance is represented.
    confidence: low
    validation_required: Review assumptions before customer use.
    status: proposed
    public_release: yes
    confidentiality_level: public
    reviewer: pending
"""


def run_checker(case_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(case_path), *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def write_complete_case(case_path: Path, intake: str = BASE_INTAKE, customer_memo: str | None = None) -> None:
    case_path.mkdir(parents=True)
    content_by_name = {
        "00_problem_intake.yml": intake,
        "01_thermal_design_passport.yml": "case_id: unit-case\nnext_best_action: review assumptions\nconfidentiality_level: public\n",
        "02_decision_board.md": "# Decision Board\n\nInterface thermal resistance is discussed.\n",
        "03_architecture_genomes.yml": "architectures: []\n",
        "04_design_space_scorecard.md": "# Scorecard\n\nQualitative screening only.\n",
        "05_red_flags.md": "# Red Flags\n\nNo high-confidence validation claims.\n",
        "06_next_best_action.md": "# Next Best Action\n\nBound assumptions before simulation.\n",
        "07_validation_plan.md": "# Validation Plan\n\nValidation required before stronger claims.\n",
        "08_supplier_specification.md": "# Supplier Specification\n\nConfidentiality level: public\n",
        "09_customer_memo.md": customer_memo or "# Customer Memo\n\nConfidentiality level: public\nConclusions are preliminary and validation is needed.\n",
        "10_claim_ledger.yml": BASE_CLAIMS,
        "11_engineering_memory_entry.md": "# Engineering Memory\n\nConfidentiality level: public\n",
    }
    for filename in REQUIRED_FILES:
        (case_path / filename).write_text(content_by_name[filename], encoding="utf-8")


class LabOsCaseCheckerTests(unittest.TestCase):
    def test_complete_example_case_returns_pass_or_warn_not_fail(self) -> None:
        result = run_checker(REPO_ROOT / "cases" / "example-incomplete-gan-rf-pa")
        self.assertIn(result.returncode, {0, 1})
        self.assertNotIn("Status:\nFAIL", result.stdout)

    def test_missing_required_file_causes_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case_path = Path(tmp) / "case"
            write_complete_case(case_path)
            (case_path / "07_validation_plan.md").unlink()
            result = run_checker(case_path)
            self.assertEqual(result.returncode, 2)
            self.assertIn("Missing required case file", result.stdout)

    def test_missing_critical_thermal_field_causes_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case_path = Path(tmp) / "case"
            intake = BASE_INTAKE.replace("title: Unit Test Thermal Case\n", "")
            write_complete_case(case_path, intake=intake)
            result = run_checker(case_path)
            self.assertEqual(result.returncode, 2)
            self.assertIn("Missing critical field", result.stdout)

    def test_unsafe_customer_claim_causes_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case_path = Path(tmp) / "case"
            write_complete_case(
                case_path,
                customer_memo="# Customer Memo\n\nConfidentiality level: public\nThis package is guaranteed and will solve overheating.\n",
            )
            result = run_checker(case_path)
            self.assertEqual(result.returncode, 2)
            self.assertIn("Potentially unsafe claim language", result.stdout)

    def test_interface_thermal_resistance_missing_causes_warn(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case_path = Path(tmp) / "case"
            write_complete_case(case_path)
            for path in case_path.iterdir():
                path.write_text(
                    path.read_text(encoding="utf-8")
                    .replace("interface thermal resistance", "thermal path")
                    .replace("Interface thermal resistance", "Thermal path"),
                    encoding="utf-8",
                )
            result = run_checker(case_path, "--strict")
            self.assertEqual(result.returncode, 1)
            self.assertIn("Interface thermal resistance is not clearly discussed", result.stdout)

    def test_direct_gan_on_diamond_first_step_without_validation_basis_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case_path = Path(tmp) / "case"
            write_complete_case(case_path)
            (case_path / "02_decision_board.md").write_text(
                "# Decision Board\n\nDirect GaN-on-Diamond is recommended as the first step.\n",
                encoding="utf-8",
            )
            result = run_checker(case_path, "--strict")
            self.assertEqual(result.returncode, 1)
            self.assertIn("Direct GaN-on-Diamond", result.stdout)

    def test_restricted_marker_in_customer_memo_causes_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case_path = Path(tmp) / "case"
            write_complete_case(
                case_path,
                customer_memo="# Customer Memo\n\nConfidentiality level: public\nThis contains a restricted process recipe.\n",
            )
            result = run_checker(case_path)
            self.assertEqual(result.returncode, 2)
            self.assertIn("Restricted marker found", result.stdout)


if __name__ == "__main__":
    unittest.main()
