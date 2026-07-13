from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from labos.review_package.exporter import export_decision_review_package
from labos.review_package.models import PACKAGE_FILES


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_CASE = REPO_ROOT / "cases" / "example-incomplete-gan-rf-pa"
SCRIPT = REPO_ROOT / "scripts" / "labos_case.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def numbered_case_hashes(case_path: Path) -> dict[str, str]:
    return {
        path.name: sha256(path)
        for path in sorted(case_path.iterdir())
        if path.is_file() and path.name[:2].isdigit() and path.name[2] == "_"
    }


def tree_hashes(path: Path) -> dict[str, str]:
    return {item.name: sha256(item) for item in sorted(path.iterdir()) if item.is_file()}


def export_to(path: Path, force: bool = False):
    return export_decision_review_package(EXAMPLE_CASE, path, REPO_ROOT, force=force)


class DecisionReviewPackageTests(unittest.TestCase):
    def test_successful_export_creates_exactly_four_package_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "review"
            result = export_to(output)
            self.assertEqual(set(item.name for item in output.iterdir()), set(PACKAGE_FILES))
            self.assertEqual(result.board_status, "HOLD_FOR_DATA")
            self.assertEqual(result.decision_state, "deferred")

    def test_exported_json_parses_and_keeps_screening_posture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "review"
            export_to(output)
            data = json.loads((output / "decision_board_preview.json").read_text(encoding="utf-8"))
            self.assertEqual(data["board_status"], "HOLD_FOR_DATA")
            self.assertEqual(data["decision_state"], "deferred")
            self.assertIn("Defer architecture selection", data["current_decision"])
            self.assertNotIn("winning", json.dumps(data).lower())
            self.assertTrue(all(route["pattern_id"].startswith("PAT-") for route in data["candidate_routes"]))
            self.assertFalse(any("PAT-DIAMOND-SUBMOUNT" in json.dumps(route) for route in data["candidate_routes"]))

    def test_human_checklist_remains_pending_and_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "review"
            export_to(output)
            checklist = (output / "human_review_checklist.md").read_text(encoding="utf-8")
            self.assertIn("Review status: pending", checklist)
            for field in ("Reviewer:", "Review date:", "Approved architecture:", "Customer-release approval:"):
                self.assertIn(field + "\n", checklist)
            self.assertIn("does not approve architectures", checklist)

    def test_manifest_contains_source_and_artifact_hashes_without_self_hash_or_local_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "review"
            export_to(output)
            manifest_text = (output / "review_manifest.json").read_text(encoding="utf-8")
            manifest = json.loads(manifest_text)
            self.assertEqual(manifest["case_id"], "example-incomplete-gan-rf-pa")
            self.assertIn("00_problem_intake.yml", manifest["source_case_sha256"])
            self.assertIn("decision_board_preview.md", manifest["generated_artifact_sha256"])
            self.assertIn("decision_board_preview.json", manifest["generated_artifact_sha256"])
            self.assertIn("human_review_checklist.md", manifest["generated_artifact_sha256"])
            self.assertNotIn("review_manifest.json", manifest["generated_artifact_sha256"])
            self.assertNotIn(str(REPO_ROOT), manifest_text)
            self.assertNotRegex(manifest_text, r"\d{4}-\d{2}-\d{2}")
            self.assertNotRegex(manifest_text, r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")

    def test_repeated_exports_are_byte_for_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first"
            second = Path(tmp) / "second"
            export_to(first)
            export_to(second)
            for name in PACKAGE_FILES:
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes(), name)

    def test_protected_output_paths_are_rejected(self) -> None:
        protected = [
            EXAMPLE_CASE / "review",
            REPO_ROOT / "patterns" / "review",
            REPO_ROOT / "memory" / "review",
            REPO_ROOT / ".git" / "review",
            REPO_ROOT,
        ]
        for output in protected:
            with self.subTest(output=output):
                with self.assertRaises(ValueError):
                    export_to(output)
                if output != REPO_ROOT:
                    self.assertFalse(output.exists())

    def test_symlink_to_protected_path_is_rejected_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            link = Path(tmp) / "case-link"
            try:
                link.symlink_to(EXAMPLE_CASE, target_is_directory=True)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"directory symlink unavailable: {exc}")
            with self.assertRaises(ValueError):
                export_to(link)

    def test_existing_package_files_are_not_overwritten_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "review"
            output.mkdir()
            target = output / "decision_board_preview.md"
            target.write_text("existing\n", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                export_to(output)
            self.assertEqual(target.read_text(encoding="utf-8"), "existing\n")

    def test_force_overwrites_known_files_and_preserves_unrelated_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "review"
            export_to(output)
            unrelated = output / "notes.txt"
            unrelated.write_text("keep me\n", encoding="utf-8")
            (output / "decision_board_preview.md").write_text("old\n", encoding="utf-8")
            export_to(output, force=True)
            self.assertTrue(unrelated.is_file())
            self.assertEqual(unrelated.read_text(encoding="utf-8"), "keep me\n")
            self.assertNotEqual((output / "decision_board_preview.md").read_text(encoding="utf-8"), "old\n")

    def test_invalid_case_path_creates_no_partial_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "review"
            with self.assertRaises(ValueError):
                export_decision_review_package(Path(tmp) / "missing-case", output, REPO_ROOT)
            self.assertFalse(output.exists())

    def test_cli_success_and_invalid_case_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "review"
            success = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "export-decision-review",
                    str(EXAMPLE_CASE),
                    "--output-dir",
                    str(output),
                ],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(success.returncode, 0, success.stderr)
            self.assertIn("Decision Review Package exported", success.stdout)

            invalid_output = Path(tmp) / "invalid"
            invalid = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "export-decision-review",
                    str(Path(tmp) / "missing-case"),
                    "--output-dir",
                    str(invalid_output),
                ],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(invalid.returncode, 2)
            self.assertFalse(invalid_output.exists())

    def test_canonical_case_patterns_and_memory_remain_unchanged(self) -> None:
        case_before = numbered_case_hashes(EXAMPLE_CASE)
        patterns_before = tree_hashes(REPO_ROOT / "patterns")
        memory_before = tree_hashes(REPO_ROOT / "memory")
        with tempfile.TemporaryDirectory() as tmp:
            export_to(Path(tmp) / "review")
        self.assertEqual(case_before, numbered_case_hashes(EXAMPLE_CASE))
        self.assertEqual(case_before["02_decision_board.md"], sha256(EXAMPLE_CASE / "02_decision_board.md"))
        self.assertEqual(patterns_before, tree_hashes(REPO_ROOT / "patterns"))
        self.assertEqual(memory_before, tree_hashes(REPO_ROOT / "memory"))


if __name__ == "__main__":
    unittest.main()
