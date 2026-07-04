from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "labos_case.py"


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


def run_case_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class LabOsCaseGeneratorTests(unittest.TestCase):
    def test_creating_new_case_writes_canonical_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cases_root = Path(tmp) / "cases"
            result = run_case_cli(
                "new",
                "--cases-root",
                str(cases_root),
                "--case-id",
                "example-new-case",
                "--title",
                "Example new thermal case",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            case_path = cases_root / "example-new-case"
            for filename in REQUIRED_FILES:
                self.assertTrue((case_path / filename).is_file(), filename)

    def test_unsafe_case_id_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cases_root = Path(tmp) / "cases"
            for unsafe_case_id in ["Bad Case", "../escape", "case/name", "case$name"]:
                result = run_case_cli(
                    "new",
                    "--cases-root",
                    str(cases_root),
                    "--case-id",
                    unsafe_case_id,
                    "--title",
                    "Unsafe case",
                )
                self.assertEqual(result.returncode, 2, unsafe_case_id)
                self.assertIn("case_id", result.stderr)

    def test_existing_case_is_not_overwritten_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cases_root = Path(tmp) / "cases"
            first = run_case_cli(
                "new",
                "--cases-root",
                str(cases_root),
                "--case-id",
                "existing-case",
                "--title",
                "Original title",
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            intake_path = cases_root / "existing-case" / "00_problem_intake.yml"
            original = intake_path.read_text(encoding="utf-8")

            second = run_case_cli(
                "new",
                "--cases-root",
                str(cases_root),
                "--case-id",
                "existing-case",
                "--title",
                "Replacement title",
            )
            self.assertEqual(second.returncode, 2)
            self.assertEqual(intake_path.read_text(encoding="utf-8"), original)

    def test_force_overwrites_canonical_files_inside_target_case(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cases_root = Path(tmp) / "cases"
            run_case_cli(
                "new",
                "--cases-root",
                str(cases_root),
                "--case-id",
                "force-case",
                "--title",
                "Original title",
            )
            extra_path = cases_root / "force-case" / "notes.md"
            extra_path.write_text("keep me", encoding="utf-8")

            result = run_case_cli(
                "new",
                "--cases-root",
                str(cases_root),
                "--case-id",
                "force-case",
                "--title",
                "Replacement title",
                "--force",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(extra_path.is_file())
            self.assertIn("Replacement title", (cases_root / "force-case" / "00_problem_intake.yml").read_text(encoding="utf-8"))

    def test_generated_case_can_be_checked_without_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cases_root = Path(tmp) / "cases"
            create_result = run_case_cli(
                "new",
                "--cases-root",
                str(cases_root),
                "--case-id",
                "checkable-case",
                "--title",
                "Checkable thermal case",
                "--application",
                "high-power RF",
                "--device-type",
                "GaN RF PA",
                "--confidentiality-level",
                "internal",
                "--owner",
                "thermal architect",
            )
            self.assertEqual(create_result.returncode, 0, create_result.stderr)
            check_result = run_case_cli("check", str(cases_root / "checkable-case"))
            self.assertIn(check_result.returncode, {0, 1})
            self.assertNotIn("Status:\nFAIL", check_result.stdout)

    def test_list_command_includes_created_case(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cases_root = Path(tmp) / "cases"
            run_case_cli(
                "new",
                "--cases-root",
                str(cases_root),
                "--case-id",
                "listed-case",
                "--title",
                "Listed thermal case",
            )
            result = run_case_cli("list", "--cases-root", str(cases_root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("listed-case", result.stdout)
            self.assertIn("canonical", result.stdout)

    def test_script_uses_standard_library_only(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        forbidden_imports = ["requests", "httpx", "openai", "yaml"]
        for name in forbidden_imports:
            self.assertNotIn(f"import {name}", text)
            self.assertNotIn(f"from {name}", text)


if __name__ == "__main__":
    unittest.main()
