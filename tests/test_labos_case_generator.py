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

PAT_CONVENTIONAL = "PAT-CONV-PKG-001"
PAT_DIAMOND_SUBMOUNT = "PAT-DIA-SUBMOUNT-001"
PAT_GAN_ON_DIAMOND = "PAT-GAN-DIA-001"
ALIAS_CONVENTIONAL = "PAT-CONVENTIONAL-PACKAGE-UPGRADE"
ALIAS_DIAMOND_SUBMOUNT = "PAT-DIAMOND-SUBMOUNT"


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

    def test_new_case_with_one_known_pattern_seeds_canonical_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cases_root = Path(tmp) / "cases"
            result = run_case_cli(
                "new",
                "--cases-root",
                str(cases_root),
                "--case-id",
                "submount-screening",
                "--title",
                "Submount screening",
                "--pattern",
                PAT_DIAMOND_SUBMOUNT,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            case_path = cases_root / "submount-screening"
            passport = (case_path / "01_thermal_design_passport.yml").read_text(encoding="utf-8")
            genomes = (case_path / "03_architecture_genomes.yml").read_text(encoding="utf-8")
            claims = (case_path / "10_claim_ledger.yml").read_text(encoding="utf-8")
            self.assertIn(f"pattern_id: {PAT_DIAMOND_SUBMOUNT}", passport)
            self.assertIn("selected_patterns:", passport)
            self.assertIn("route_status: candidate", genomes)
            self.assertIn("validation_status: unvalidated", genomes)
            self.assertIn("decision_status: screening_only", genomes)
            self.assertIn("claim_type: pattern_based", claims)
            self.assertIn("confidence: low", claims)
            self.assertIn("status: draft", claims)

    def test_alias_input_resolves_and_generated_files_store_canonical_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cases_root = Path(tmp) / "cases"
            result = run_case_cli(
                "new",
                "--cases-root",
                str(cases_root),
                "--case-id",
                "alias-submount",
                "--title",
                "Alias submount",
                "--pattern",
                ALIAS_DIAMOND_SUBMOUNT,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"Resolved {ALIAS_DIAMOND_SUBMOUNT} -> {PAT_DIAMOND_SUBMOUNT}", result.stdout)
            genomes = (cases_root / "alias-submount" / "03_architecture_genomes.yml").read_text(encoding="utf-8")
            self.assertIn(f"pattern_id: {PAT_DIAMOND_SUBMOUNT}", genomes)
            self.assertNotIn(ALIAS_DIAMOND_SUBMOUNT, genomes)

    def test_new_case_with_multiple_known_patterns_preserves_selection_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cases_root = Path(tmp) / "cases"
            result = run_case_cli(
                "new",
                "--cases-root",
                str(cases_root),
                "--case-id",
                "route-comparison",
                "--title",
                "Route comparison",
                "--pattern",
                PAT_CONVENTIONAL,
                "--pattern",
                PAT_DIAMOND_SUBMOUNT,
                "--pattern",
                PAT_GAN_ON_DIAMOND,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            passport = (cases_root / "route-comparison" / "01_thermal_design_passport.yml").read_text(encoding="utf-8")
            positions = [passport.index(pattern_id) for pattern_id in (PAT_CONVENTIONAL, PAT_DIAMOND_SUBMOUNT, PAT_GAN_ON_DIAMOND)]
            self.assertEqual(positions, sorted(positions))

    def test_new_case_without_patterns_keeps_existing_generator_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cases_root = Path(tmp) / "cases"
            result = run_case_cli(
                "new",
                "--cases-root",
                str(cases_root),
                "--case-id",
                "no-patterns",
                "--title",
                "No patterns",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            passport = (cases_root / "no-patterns" / "01_thermal_design_passport.yml").read_text(encoding="utf-8")
            self.assertNotIn("selected_patterns:", passport)

    def test_unknown_pattern_is_rejected_without_partial_case_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cases_root = Path(tmp) / "cases"
            case_path = cases_root / "unknown-pattern"
            result = run_case_cli(
                "new",
                "--cases-root",
                str(cases_root),
                "--case-id",
                "unknown-pattern",
                "--title",
                "Unknown pattern",
                "--pattern",
                "PAT-UNKNOWN-999",
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("Unknown pattern ID", result.stderr)
            self.assertIn("list-patterns", result.stderr)
            self.assertFalse(case_path.exists())

    def test_pattern_ids_are_case_sensitive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cases_root = Path(tmp) / "cases"
            result = run_case_cli(
                "new",
                "--cases-root",
                str(cases_root),
                "--case-id",
                "lowercase-pattern",
                "--title",
                "Lowercase pattern",
                "--pattern",
                PAT_CONVENTIONAL.lower(),
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("Unknown pattern ID", result.stderr)
            self.assertFalse((cases_root / "lowercase-pattern").exists())

    def test_more_than_five_patterns_is_rejected_without_partial_case_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cases_root = Path(tmp) / "cases"
            selected = [
                PAT_CONVENTIONAL,
                "PAT-DIA-SPREADER-001",
                PAT_DIAMOND_SUBMOUNT,
                PAT_GAN_ON_DIAMOND,
                "PAT-CUDIA-001",
                "PAT-DOUBLE-COOL-001",
            ]
            args = ["new", "--cases-root", str(cases_root), "--case-id", "too-many", "--title", "Too many"]
            for pattern_id in selected:
                args.extend(["--pattern", pattern_id])
            result = run_case_cli(*args)
            self.assertEqual(result.returncode, 2)
            self.assertIn("limits one case creation command to 5", result.stderr)
            self.assertFalse((cases_root / "too-many").exists())

    def test_duplicate_patterns_are_deduplicated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cases_root = Path(tmp) / "cases"
            result = run_case_cli(
                "new",
                "--cases-root",
                str(cases_root),
                "--case-id",
                "deduplicated",
                "--title",
                "Deduplicated patterns",
                "--pattern",
                PAT_DIAMOND_SUBMOUNT,
                "--pattern",
                PAT_DIAMOND_SUBMOUNT,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            genomes = (cases_root / "deduplicated" / "03_architecture_genomes.yml").read_text(encoding="utf-8")
            self.assertEqual(genomes.count(f"pattern_id: {PAT_DIAMOND_SUBMOUNT}"), 1)

    def test_canonical_and_alias_selection_are_deduplicated_after_normalization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cases_root = Path(tmp) / "cases"
            result = run_case_cli(
                "new",
                "--cases-root",
                str(cases_root),
                "--case-id",
                "canonical-alias-duplicate",
                "--title",
                "Canonical alias duplicate",
                "--pattern",
                PAT_DIAMOND_SUBMOUNT,
                "--pattern",
                ALIAS_DIAMOND_SUBMOUNT,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            genomes = (cases_root / "canonical-alias-duplicate" / "03_architecture_genomes.yml").read_text(encoding="utf-8")
            self.assertEqual(genomes.count(f"pattern_id: {PAT_DIAMOND_SUBMOUNT}"), 1)

    def test_five_pattern_limit_is_applied_after_alias_normalization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cases_root = Path(tmp) / "cases"
            selected = [
                PAT_CONVENTIONAL,
                ALIAS_CONVENTIONAL,
                "PAT-DIA-SPREADER-001",
                PAT_DIAMOND_SUBMOUNT,
                PAT_GAN_ON_DIAMOND,
                "PAT-CUDIA-001",
            ]
            args = ["new", "--cases-root", str(cases_root), "--case-id", "normalized-five", "--title", "Normalized five"]
            for pattern_id in selected:
                args.extend(["--pattern", pattern_id])
            result = run_case_cli(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((cases_root / "normalized-five").is_dir())

    def test_list_patterns_shows_known_pattern_ids(self) -> None:
        result = run_case_cli("list-patterns")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("pattern_id\taliases\troute_type", result.stdout)
        self.assertIn(PAT_CONVENTIONAL, result.stdout)
        self.assertIn(PAT_DIAMOND_SUBMOUNT, result.stdout)
        self.assertIn(ALIAS_CONVENTIONAL, result.stdout)
        self.assertIn(ALIAS_DIAMOND_SUBMOUNT, result.stdout)

    def test_diamond_pattern_adds_interface_and_bonding_todos(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cases_root = Path(tmp) / "cases"
            result = run_case_cli(
                "new", "--cases-root", str(cases_root), "--case-id", "diamond-todos", "--title", "Diamond TODOs",
                "--pattern", PAT_DIAMOND_SUBMOUNT,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            red_flags = (cases_root / "diamond-todos" / "05_red_flags.md").read_text(encoding="utf-8").lower()
            validation = (cases_root / "diamond-todos" / "07_validation_plan.md").read_text(encoding="utf-8").lower()
            self.assertIn("interface thermal resistance", red_flags)
            self.assertIn("bonding or contact", validation)

    def test_gan_on_diamond_remains_a_non_immediate_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cases_root = Path(tmp) / "cases"
            result = run_case_cli(
                "new", "--cases-root", str(cases_root), "--case-id", "gan-dia", "--title", "GaN on diamond",
                "--pattern", PAT_GAN_ON_DIAMOND,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            genomes = (cases_root / "gan-dia" / "03_architecture_genomes.yml").read_text(encoding="utf-8").lower()
            self.assertIn("higher-integration-risk candidate", genomes)
            self.assertIn("do not treat as an immediate recommendation", genomes)

    def test_conventional_package_upgrade_is_neutral_and_pattern_case_checks_without_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cases_root = Path(tmp) / "cases"
            result = run_case_cli(
                "new", "--cases-root", str(cases_root), "--case-id", "conventional", "--title", "Conventional package",
                "--pattern", PAT_CONVENTIONAL,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            genomes = (cases_root / "conventional" / "03_architecture_genomes.yml").read_text(encoding="utf-8").lower()
            self.assertIn("legitimate neutral package-level candidate", genomes)
            check_result = run_case_cli("check", str(cases_root / "conventional"))
            self.assertIn(check_result.returncode, {0, 1})
            self.assertNotIn("Status:\nFAIL", check_result.stdout)
            self.assertNotIn("Claim safety warnings\n  - WARN", check_result.stdout)

    def test_script_uses_standard_library_only(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        forbidden_imports = ["requests", "httpx", "openai", "yaml"]
        for name in forbidden_imports:
            self.assertNotIn(f"import {name}", text)
            self.assertNotIn(f"from {name}", text)


if __name__ == "__main__":
    unittest.main()
