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

    def test_known_pattern_reference_is_reported_without_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case_path = Path(tmp) / "case"
            write_complete_case(case_path)
            (case_path / "03_architecture_genomes.yml").write_text(
                "architectures:\n  - pattern_id: PAT-DIA-SPREADER-001\n",
                encoding="utf-8",
            )
            result = run_checker(case_path, "--strict")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Known pattern reference: PAT-DIA-SPREADER-001", result.stdout)

    def test_unknown_pattern_reference_causes_warn(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case_path = Path(tmp) / "case"
            write_complete_case(case_path)
            (case_path / "03_architecture_genomes.yml").write_text(
                "architectures:\n  - pattern_id: PAT-NOT-IN-INDEX\n",
                encoding="utf-8",
            )
            result = run_checker(case_path, "--strict")
            self.assertEqual(result.returncode, 1)
            self.assertIn("Unknown pattern reference: PAT-NOT-IN-INDEX", result.stdout)

    def test_recognized_persisted_alias_causes_warn_with_canonical_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case_path = Path(tmp) / "case"
            write_complete_case(case_path)
            (case_path / "03_architecture_genomes.yml").write_text(
                "architectures:\n  - pattern_id: PAT-DIAMOND-SUBMOUNT\n",
                encoding="utf-8",
            )
            result = run_checker(case_path, "--strict")
            self.assertEqual(result.returncode, 1)
            self.assertIn("Recognized pattern alias used in persisted case", result.stdout)
            self.assertIn("PAT-DIA-SUBMOUNT-001", result.stdout)
            self.assertNotIn("Unknown pattern reference", result.stdout)

    def test_unknown_pattern_reference_in_customer_memo_causes_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case_path = Path(tmp) / "case"
            write_complete_case(
                case_path,
                customer_memo=(
                    "# Customer Memo\n\nConfidentiality level: public\n"
                    "The recommendation relies on PAT-NOT-IN-INDEX.\n"
                ),
            )
            result = run_checker(case_path)
            self.assertEqual(result.returncode, 2)
            self.assertIn("Unknown pattern reference: PAT-NOT-IN-INDEX", result.stdout)

    def test_pattern_based_claim_with_high_confidence_without_validation_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case_path = Path(tmp) / "case"
            write_complete_case(case_path)
            (case_path / "10_claim_ledger.yml").write_text(
                """claims:
  - claim_id: CLM-PAT-001
    claim: A referenced pattern is suitable for screening.
    claim_type: pattern_based
    basis: Pattern library
    assumptions:
      - Case inputs remain incomplete.
    confidence: high
    validation_required: true
    status: proposed
    public_release: not_allowed_until_review
    confidentiality_level: public
    reviewer: pending
""",
                encoding="utf-8",
            )
            result = run_checker(case_path, "--strict")
            self.assertEqual(result.returncode, 1)
            self.assertIn("has high confidence without validation support", result.stdout)

    def test_pattern_based_claim_marked_validated_without_evidence_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case_path = Path(tmp) / "case"
            write_complete_case(case_path)
            (case_path / "10_claim_ledger.yml").write_text(
                """claims:
  - claim_id: CLM-PAT-002
    claim: A pattern proves the selected architecture.
    claim_type: architecture_screening
    basis: Pattern library
    evidence: Pattern library reference only
    assumptions:
      - No case measurement is available.
    confidence: medium
    validation_required: true
    status: validated
    public_release: no
    confidentiality_level: public
    reviewer: pending
""",
                encoding="utf-8",
            )
            result = run_checker(case_path)
            self.assertEqual(result.returncode, 2)
            self.assertIn("is marked validated without evidence", result.stdout)

    def test_pattern_based_claim_public_release_without_review_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case_path = Path(tmp) / "case"
            write_complete_case(case_path)
            (case_path / "10_claim_ledger.yml").write_text(
                """claims:
  - claim_id: CLM-PAT-003
    claim: A referenced pattern is a screening candidate.
    claim_type: screening
    basis: Pattern library
    assumptions:
      - Case evidence is not yet available.
    confidence: low
    validation_required: true
    status: proposed
    public_release: yes
    confidentiality_level: public
    reviewer: thermal lead
""",
                encoding="utf-8",
            )
            result = run_checker(case_path, "--strict")
            self.assertEqual(result.returncode, 1)
            self.assertIn("allows public release without evidence or completed review", result.stdout)

    def test_diamond_with_interface_risk_elsewhere_avoids_generic_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case_path = Path(tmp) / "case"
            write_complete_case(case_path)
            (case_path / "02_decision_board.md").write_text(
                "# Decision Board\n\nA diamond heat spreader is recommended for screening.\n",
                encoding="utf-8",
            )
            result = run_checker(case_path, "--strict")
            self.assertEqual(result.returncode, 0)
            self.assertNotIn("Diamond is referenced without interface-risk discussion", result.stdout)

    def test_diamond_with_tbr_discussed_elsewhere_avoids_generic_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case_path = Path(tmp) / "case"
            write_complete_case(case_path)
            for path in case_path.iterdir():
                path.write_text(
                    path.read_text(encoding="utf-8")
                    .replace("interface thermal resistance", "TBR")
                    .replace("Interface thermal resistance", "TBR"),
                    encoding="utf-8",
                )
            (case_path / "02_decision_board.md").write_text(
                "# Decision Board\n\nA diamond heat spreader is recommended for screening.\n",
                encoding="utf-8",
            )
            result = run_checker(case_path, "--strict")
            self.assertEqual(result.returncode, 0)
            self.assertNotIn("Diamond is referenced without interface-risk discussion", result.stdout)

    def test_diamond_without_interface_discussion_causes_warn(self) -> None:
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
            (case_path / "02_decision_board.md").write_text(
                "# Decision Board\n\nA diamond heat spreader is recommended for screening.\n",
                encoding="utf-8",
            )
            result = run_checker(case_path, "--strict")
            self.assertEqual(result.returncode, 1)
            self.assertIn("Diamond is referenced without interface-risk discussion", result.stdout)

    def test_direct_gan_on_diamond_first_step_in_customer_memo_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case_path = Path(tmp) / "case"
            write_complete_case(
                case_path,
                customer_memo=(
                    "# Customer Memo\n\nConfidentiality level: public\n"
                    "We recommend direct GaN-on-Diamond as the immediate first step.\n"
                ),
            )
            result = run_checker(case_path)
            self.assertEqual(result.returncode, 2)
            self.assertIn("Direct GaN-on-Diamond first-step recommendation lacks", result.stdout)


if __name__ == "__main__":
    unittest.main()
