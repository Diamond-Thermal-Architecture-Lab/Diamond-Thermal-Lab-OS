from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from labos.canonical_proposal.builder import build_canonical_decision_proposal
from labos.canonical_proposal.models import PROPOSAL_FILES
from labos.decision_record.package import sha256_file
from labos.decision_record.template import create_decision_record_template
from labos.decision_record.validator import validate_decision_record
from labos.review_package.exporter import export_decision_review_package


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_CASE = REPO_ROOT / "cases" / "example-incomplete-gan-rf-pa"
ROUTE = "PAT-DIA-SUBMOUNT-001"
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


def write_json(path: Path, data: dict[str, object]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


class CanonicalDecisionProposalTests(unittest.TestCase):
    def export_package(self, root: Path) -> Path:
        package = root / "review"
        export_decision_review_package(EXAMPLE_CASE, package, REPO_ROOT)
        return package

    def final_record(self, package: Path, root: Path, outcome: str = "deferred") -> Path:
        record_path = root / f"{outcome}.json"
        create_decision_record_template(package, record_path, REPO_ROOT)
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record.update(
            {
                "record_status": "final",
                "review_outcome": outcome,
                "reviewer": {"name": "Human reviewer", "role": "thermal reviewer", "organization": ""},
                "decision_owner": {"name": "Human owner", "role": "decision owner", "organization": ""},
                "decision_rationale": "Human review records this outcome against the bound review package.",
                "evidence_references": ["decision_board_preview.json"],
                "risk_acceptance": {"accepted": False, "accepted_risks": [], "rationale": "No risk is accepted automatically."},
                "acknowledgements": {
                    "review_package_is_not_an_approved_decision": True,
                    "pattern_selection_is_not_validation": True,
                    "measured_simulated_supplier_and_pattern_evidence_are_distinct": True,
                    "canonical_case_is_not_modified_automatically": True,
                },
                "human_attestation": {
                    "reviewer_attested": True,
                    "decision_owner_attested": True,
                    "attestation_note": "Human attestation only; not a cryptographic or digital signature.",
                },
            }
        )
        if outcome == "approved":
            record["approved_route_ids"] = [ROUTE]
        elif outcome == "deferred":
            record["deferred_route_ids"] = [ROUTE]
            record["required_additional_evidence"] = ["Bound interface thermal resistance and package boundary conditions."]
        elif outcome == "rejected":
            record["rejected_route_ids"] = [ROUTE]
        elif outcome == "more_evidence_required":
            record["required_additional_evidence"] = ["Review measured thermal evidence before route selection."]
        write_json(record_path, record)
        self.assertEqual(validate_decision_record(package, record_path).status, "PASS")
        return record_path

    def test_final_pass_outcomes_generate_exact_four_files_and_preserve_sources(self) -> None:
        case_before = numbered_case_hashes(EXAMPLE_CASE)
        board_before = sha256(EXAMPLE_CASE / "02_decision_board.md")
        for outcome in ("deferred", "rejected", "more_evidence_required"):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                package = self.export_package(root)
                record = self.final_record(package, root, outcome)
                result = build_canonical_decision_proposal(EXAMPLE_CASE, package, record, root / "proposal", REPO_ROOT)
                self.assertEqual(result.review_outcome, outcome)
                self.assertEqual({path.name for path in (root / "proposal").iterdir()}, set(PROPOSAL_FILES))
                proposed = (root / "proposal" / "proposed_02_decision_board.md").read_text(encoding="utf-8")
                self.assertIn("It has not been applied to the canonical case.", proposed)
                if outcome == "deferred":
                    self.assertIn("Deferral is not rejection.", proposed)
                if outcome == "rejected":
                    self.assertIn("does not establish physical impossibility", proposed)
                if outcome == "more_evidence_required":
                    self.assertIn("No route is approved.", proposed)
        self.assertEqual(case_before, numbered_case_hashes(EXAMPLE_CASE))
        self.assertEqual(board_before, sha256(EXAMPLE_CASE / "02_decision_board.md"))

    def test_approved_final_pass_record_can_generate_when_bound_package_is_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = self.export_package(root)
            manifest_path = package / "review_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["board_status"] = "READY_FOR_HUMAN_DECISION"
            manifest["decision_state"] = "human_review_required"
            write_json(manifest_path, manifest)
            record = self.final_record(package, root, "approved")
            result = build_canonical_decision_proposal(EXAMPLE_CASE, package, record, root / "proposal", REPO_ROOT)
            proposed = (result.output_dir / "proposed_02_decision_board.md").read_text(encoding="utf-8")
            self.assertIn(ROUTE, proposed)
            self.assertIn("approved by human record", proposed)

    def test_warn_draft_and_stale_case_inputs_create_no_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = self.export_package(root)
            draft = root / "draft.json"
            create_decision_record_template(package, draft, REPO_ROOT)
            output = root / "proposal"
            with self.assertRaises(ValueError):
                build_canonical_decision_proposal(EXAMPLE_CASE, package, draft, output, REPO_ROOT)
            self.assertFalse(output.exists())

            manifest_path = package / "review_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["source_case_sha256"] = {"00_problem_intake.yml": "stale"}
            write_json(manifest_path, manifest)
            stale = self.final_record(package, root, "deferred")
            with self.assertRaises(ValueError):
                build_canonical_decision_proposal(EXAMPLE_CASE, package, stale, output, REPO_ROOT)
            self.assertFalse(output.exists())

    def test_manifest_hashes_diff_determinism_and_read_only_behavior(self) -> None:
        case_before = numbered_case_hashes(EXAMPLE_CASE)
        patterns_before = tree_hashes(REPO_ROOT / "patterns")
        memory_before = tree_hashes(REPO_ROOT / "memory")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = self.export_package(root)
            record = self.final_record(package, root)
            package_before = {path.name: sha256(path) for path in package.iterdir()}
            record_before = sha256(record)
            first = root / "first"
            second = root / "second"
            build_canonical_decision_proposal(EXAMPLE_CASE, package, record, first, REPO_ROOT)
            build_canonical_decision_proposal(EXAMPLE_CASE, package, record, second, REPO_ROOT)
            for name in PROPOSAL_FILES:
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes(), name)
            manifest = json.loads((first / "canonical_proposal_manifest.json").read_text(encoding="utf-8"))
            for field in (
                "proposal_format_version",
                "case_id",
                "review_manifest_sha256",
                "human_decision_record_sha256",
                "source_case_sha256",
                "approved_route_ids",
                "rejected_route_ids",
                "deferred_route_ids",
                "validation_note",
            ):
                self.assertIn(field, manifest)
            self.assertEqual(manifest["source_case_sha256"], case_before)
            self.assertNotIn("canonical_proposal_manifest.json", json.dumps(manifest))
            manifest_text = (first / "canonical_proposal_manifest.json").read_text(encoding="utf-8")
            self.assertNotIn(str(REPO_ROOT), manifest_text)
            self.assertNotRegex(manifest_text, r"\d{4}-\d{2}-\d{2}")
            self.assertNotRegex(manifest_text, r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
            self.assertEqual(manifest["current_decision_board_sha256"], sha256(EXAMPLE_CASE / "02_decision_board.md"))
            for key, name in (
                ("proposed_decision_board_sha256", "proposed_02_decision_board.md"),
                ("proposed_diff_sha256", "proposed_02_decision_board.diff"),
                ("application_checklist_sha256", "canonical_application_checklist.md"),
            ):
                self.assertEqual(manifest[key], sha256(first / name))
            diff = (first / "proposed_02_decision_board.diff").read_text(encoding="utf-8")
            self.assertIn("--- a/cases/example-incomplete-gan-rf-pa/02_decision_board.md", diff)
            self.assertIn("+++ b/cases/example-incomplete-gan-rf-pa/02_decision_board.md", diff)
            self.assertNotIn(str(REPO_ROOT), diff)
            self.assertEqual(package_before, {path.name: sha256(path) for path in package.iterdir()})
            self.assertEqual(record_before, sha256(record))
        self.assertEqual(case_before, numbered_case_hashes(EXAMPLE_CASE))
        self.assertEqual(patterns_before, tree_hashes(REPO_ROOT / "patterns"))
        self.assertEqual(memory_before, tree_hashes(REPO_ROOT / "memory"))

    def test_path_safety_and_force_preserves_unrelated_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = self.export_package(root)
            record = self.final_record(package, root)
            protected = (EXAMPLE_CASE / "proposal", package / "proposal", REPO_ROOT / "patterns" / "proposal", REPO_ROOT / "memory" / "proposal", REPO_ROOT / ".git" / "proposal", REPO_ROOT)
            for output in protected:
                with self.subTest(output=output):
                    with self.assertRaises(ValueError):
                        build_canonical_decision_proposal(EXAMPLE_CASE, package, record, output, REPO_ROOT)
            output = root / "proposal"
            build_canonical_decision_proposal(EXAMPLE_CASE, package, record, output, REPO_ROOT)
            unrelated = output / "keep.txt"
            unrelated.write_text("keep\n", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                build_canonical_decision_proposal(EXAMPLE_CASE, package, record, output, REPO_ROOT)
            build_canonical_decision_proposal(EXAMPLE_CASE, package, record, output, REPO_ROOT, force=True)
            self.assertEqual(unrelated.read_text(encoding="utf-8"), "keep\n")

    def test_symlink_to_protected_output_is_rejected_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = self.export_package(root)
            record = self.final_record(package, root)
            link = root / "case-link"
            try:
                link.symlink_to(EXAMPLE_CASE, target_is_directory=True)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"directory symlink unavailable: {exc}")
            with self.assertRaises(ValueError):
                build_canonical_decision_proposal(EXAMPLE_CASE, package, record, link, REPO_ROOT)

    def test_cli_generates_proposal_only_for_final_pass_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = self.export_package(root)
            record = self.final_record(package, root)
            output = root / "proposal"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "propose-canonical-decision",
                    str(EXAMPLE_CASE),
                    str(package),
                    str(record),
                    "--output-dir",
                    str(output),
                ],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("Canonical Decision Proposal generated", completed.stdout)
            self.assertEqual({path.name for path in output.iterdir()}, set(PROPOSAL_FILES))


if __name__ == "__main__":
    unittest.main()
