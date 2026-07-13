from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from labos.decision_record.package import sha256_file
from labos.decision_record.report import exit_code, render_validation
from labos.decision_record.template import create_decision_record_template
from labos.decision_record.validator import validate_decision_record
from labos.review_package.exporter import export_decision_review_package


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_CASE = REPO_ROOT / "cases" / "example-incomplete-gan-rf-pa"
SCRIPT = REPO_ROOT / "scripts" / "labos_case.py"
CANONICAL_ROUTE = "PAT-DIA-SUBMOUNT-001"
ROUTE_ALIAS = "PAT-DIAMOND-SUBMOUNT"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, data: dict[str, object]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def numbered_case_hashes(case_path: Path) -> dict[str, str]:
    return {
        path.name: sha256(path)
        for path in sorted(case_path.iterdir())
        if path.is_file() and path.name[:2].isdigit() and path.name[2] == "_"
    }


def tree_hashes(path: Path) -> dict[str, str]:
    return {item.name: sha256(item) for item in sorted(path.iterdir()) if item.is_file()}


class HumanDecisionRecordTests(unittest.TestCase):
    def export_package(self, root: Path) -> Path:
        package = root / "review"
        export_decision_review_package(EXAMPLE_CASE, package, REPO_ROOT)
        return package

    def create_record(self, package: Path, root: Path) -> Path:
        record = root / "decision.json"
        create_decision_record_template(package, record, REPO_ROOT)
        return record

    def load_record(self, path: Path) -> dict[str, object]:
        return json.loads(path.read_text(encoding="utf-8"))

    def save_record(self, path: Path, record: dict[str, object]) -> None:
        write_json(path, record)

    def complete_common_final_fields(self, record: dict[str, object]) -> None:
        record["record_status"] = "final"
        record["reviewer"] = {"name": "Reviewer", "role": "thermal reviewer", "organization": ""}
        record["decision_owner"] = {"name": "Owner", "role": "decision owner", "organization": ""}
        record["decision_rationale"] = "Human review requires this outcome based on the bound package."
        record["evidence_references"] = ["decision_board_preview.json"]
        record["risk_acceptance"] = {"accepted": False, "accepted_risks": [], "rationale": "No risk is accepted by default."}
        record["acknowledgements"] = {
            "review_package_is_not_an_approved_decision": True,
            "pattern_selection_is_not_validation": True,
            "measured_simulated_supplier_and_pattern_evidence_are_distinct": True,
            "canonical_case_is_not_modified_automatically": True,
        }
        record["human_attestation"] = {
            "reviewer_attested": True,
            "decision_owner_attested": True,
            "attestation_note": "Human attestation only; not a cryptographic or digital signature.",
        }

    def test_template_generation_is_draft_pending_blank_and_bound(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = self.export_package(root)
            record_path = self.create_record(package, root)
            record = self.load_record(record_path)
            self.assertEqual(record["record_status"], "draft")
            self.assertEqual(record["review_outcome"], "pending")
            self.assertEqual(record["customer_release_status"], "blocked")
            self.assertEqual(record["reviewer"]["name"], "")
            self.assertEqual(record["decision_owner"]["name"], "")
            self.assertEqual(record["approved_route_ids"], [])
            self.assertFalse(record["acknowledgements"]["review_package_is_not_an_approved_decision"])
            self.assertFalse(record["human_attestation"]["reviewer_attested"])
            self.assertEqual(
                record["review_package_binding"]["review_manifest_sha256"],
                sha256_file(package / "review_manifest.json"),
            )

    def test_template_contains_no_run_specific_metadata_and_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = self.export_package(root)
            first = root / "first.json"
            second = root / "second.json"
            create_decision_record_template(package, first, REPO_ROOT)
            create_decision_record_template(package, second, REPO_ROOT)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            text = first.read_text(encoding="utf-8")
            self.assertNotIn(str(REPO_ROOT), text)
            self.assertNotRegex(text, r"\d{4}-\d{2}-\d{2}")
            self.assertNotRegex(text, r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
            self.assertNotIn("username", text.lower())
            self.assertNotIn("hostname", text.lower())

    def test_template_overwrite_and_file_safety(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = self.export_package(root)
            record_path = self.create_record(package, root)
            record_path.write_text("old\n", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                create_decision_record_template(package, record_path, REPO_ROOT)
            self.assertEqual(record_path.read_text(encoding="utf-8"), "old\n")
            create_decision_record_template(package, record_path, REPO_ROOT, force=True)
            self.assertNotEqual(record_path.read_text(encoding="utf-8"), "old\n")

            for protected in (
                EXAMPLE_CASE / "decision.json",
                REPO_ROOT / "patterns" / "decision.json",
                REPO_ROOT / "memory" / "decision.json",
                REPO_ROOT / ".git" / "decision.json",
                REPO_ROOT,
            ):
                with self.subTest(protected=protected):
                    with self.assertRaises(ValueError):
                        create_decision_record_template(package, protected, REPO_ROOT, force=True)

    def test_symlink_to_protected_output_is_rejected_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = self.export_package(root)
            target = EXAMPLE_CASE / "02_decision_board.md"
            link = root / "decision-link.json"
            try:
                link.symlink_to(target)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"file symlink unavailable: {exc}")
            with self.assertRaises(ValueError):
                create_decision_record_template(package, link, REPO_ROOT, force=True)
            self.assertTrue(target.exists())

    def test_generated_pending_template_validates_warn_and_exit_code_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = self.export_package(root)
            record = self.create_record(package, root)
            result = validate_decision_record(package, record)
            self.assertEqual(result.status, "WARN")
            self.assertTrue(result.manifest_binding_valid)
            self.assertEqual(result.record_status, "draft")
            self.assertEqual(result.review_outcome, "pending")
            self.assertEqual(exit_code(result), 1)

    def test_cli_template_and_validation_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = self.export_package(root)
            record = root / "decision.json"
            created = subprocess.run(
                [sys.executable, str(SCRIPT), "new-decision-record", str(package), "--output", str(record)],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            self.assertIn("Human Decision Record template created", created.stdout)

            validated = subprocess.run(
                [sys.executable, str(SCRIPT), "validate-decision-record", str(package), str(record), "--json"],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(validated.returncode, 1)
            payload = json.loads(validated.stdout)
            self.assertEqual(payload["status"], "WARN")
            self.assertEqual(payload["manifest_binding_valid"], True)
            self.assertEqual(validated.stdout, render_validation(validate_decision_record(package, record), as_json=True) + "\n")

    def test_binding_mismatches_and_tampered_package_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = self.export_package(root)
            record_path = self.create_record(package, root)

            record = self.load_record(record_path)
            record["case_id"] = "different-case"
            self.save_record(record_path, record)
            self.assertEqual(validate_decision_record(package, record_path).status, "FAIL")

            record = self.load_record(record_path)
            record["case_id"] = "example-incomplete-gan-rf-pa"
            record["review_package_binding"]["source_case_sha256"] = {"00_problem_intake.yml": "bad"}
            self.save_record(record_path, record)
            self.assertEqual(validate_decision_record(package, record_path).status, "FAIL")

            (package / "decision_board_preview.md").write_text("tampered\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_decision_record(package, record_path)

    def test_route_validation_unknown_alias_overlap_duplicate_and_out_of_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = self.export_package(root)
            record_path = self.create_record(package, root)

            record = self.load_record(record_path)
            record["deferred_route_ids"] = [ROUTE_ALIAS, CANONICAL_ROUTE]
            self.save_record(record_path, record)
            result = validate_decision_record(package, record_path)
            self.assertEqual(result.status, "WARN")
            self.assertTrue(any("Recognized alias" in warning for warning in result.warnings))
            self.assertTrue(any("Duplicate route IDs after canonical resolution" in warning for warning in result.warnings))

            record["approved_route_ids"] = [CANONICAL_ROUTE]
            record["rejected_route_ids"] = [CANONICAL_ROUTE]
            record["deferred_route_ids"] = []
            self.save_record(record_path, record)
            self.assertEqual(validate_decision_record(package, record_path).status, "FAIL")

            record["approved_route_ids"] = []
            record["deferred_route_ids"] = ["PAT-UNKNOWN-999"]
            record["rejected_route_ids"] = []
            self.save_record(record_path, record)
            self.assertEqual(validate_decision_record(package, record_path).status, "FAIL")

            record["deferred_route_ids"] = ["PAT-VAPOR-PKG-001"]
            self.save_record(record_path, record)
            self.assertEqual(validate_decision_record(package, record_path).status, "FAIL")

    def test_approved_outcome_on_hold_for_data_fails_and_customer_release_guardrails_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = self.export_package(root)
            record_path = self.create_record(package, root)
            record = self.load_record(record_path)
            self.complete_common_final_fields(record)
            record["review_outcome"] = "approved"
            record["approved_route_ids"] = [CANONICAL_ROUTE]
            record["customer_release_status"] = "approved"
            record["customer_release_basis"] = []
            self.save_record(record_path, record)
            result = validate_decision_record(package, record_path)
            self.assertEqual(result.status, "FAIL")
            self.assertTrue(any("READY_FOR_HUMAN_DECISION" in error for error in result.errors))
            self.assertTrue(any("Customer release approval requires release basis" in error for error in result.errors))

    def test_approved_outcome_cannot_rely_only_on_bulk_thermal_conductivity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = self.export_package(root)
            manifest_path = package / "review_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["board_status"] = "READY_FOR_HUMAN_DECISION"
            manifest["decision_state"] = "human_review_required"
            write_json(manifest_path, manifest)

            record_path = self.create_record(package, root)
            record = self.load_record(record_path)
            self.complete_common_final_fields(record)
            record["review_outcome"] = "approved"
            record["approved_route_ids"] = [CANONICAL_ROUTE]
            record["decision_rationale"] = "Approve this route because it has higher bulk thermal conductivity."
            self.save_record(record_path, record)
            result = validate_decision_record(package, record_path)
            self.assertEqual(result.status, "FAIL")
            self.assertTrue(any("bulk thermal conductivity" in error for error in result.errors))

    def test_deferred_more_evidence_and_rejected_outcome_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = self.export_package(root)
            record_path = self.create_record(package, root)

            record = self.load_record(record_path)
            self.complete_common_final_fields(record)
            record["review_outcome"] = "deferred"
            record["required_additional_evidence"] = []
            self.save_record(record_path, record)
            self.assertEqual(validate_decision_record(package, record_path).status, "FAIL")

            record["required_additional_evidence"] = ["bounded heat source geometry"]
            record["review_outcome"] = "more_evidence_required"
            record["approved_route_ids"] = [CANONICAL_ROUTE]
            self.save_record(record_path, record)
            self.assertEqual(validate_decision_record(package, record_path).status, "FAIL")

            record["review_outcome"] = "rejected"
            record["approved_route_ids"] = []
            record["rejected_route_ids"] = []
            self.save_record(record_path, record)
            self.assertEqual(validate_decision_record(package, record_path).status, "FAIL")

    def test_attestation_note_is_not_cryptographic_signature_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = self.export_package(root)
            record = self.load_record(self.create_record(package, root))
            note = record["human_attestation"]["attestation_note"]
            self.assertIn("not a cryptographic or digital signature", note)
            self.assertNotIn("non-repudiation", json.dumps(record).lower())

    def test_validation_is_read_only_for_record_package_case_patterns_and_memory(self) -> None:
        case_before = numbered_case_hashes(EXAMPLE_CASE)
        patterns_before = tree_hashes(REPO_ROOT / "patterns")
        memory_before = tree_hashes(REPO_ROOT / "memory")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = self.export_package(root)
            record = self.create_record(package, root)
            record_before = sha256(record)
            package_before = {path.name: sha256(path) for path in package.iterdir() if path.is_file()}
            validate_decision_record(package, record)
            self.assertEqual(record_before, sha256(record))
            self.assertEqual(package_before, {path.name: sha256(path) for path in package.iterdir() if path.is_file()})
        self.assertEqual(case_before, numbered_case_hashes(EXAMPLE_CASE))
        self.assertEqual(case_before["02_decision_board.md"], sha256(EXAMPLE_CASE / "02_decision_board.md"))
        self.assertEqual(patterns_before, tree_hashes(REPO_ROOT / "patterns"))
        self.assertEqual(memory_before, tree_hashes(REPO_ROOT / "memory"))


if __name__ == "__main__":
    unittest.main()
