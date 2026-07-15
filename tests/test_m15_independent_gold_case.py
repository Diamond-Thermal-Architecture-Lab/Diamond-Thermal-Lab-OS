from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from labos.checkers.case_file_checker import iter_canonical_case_files, iter_public_case_text_files
from labos.checkers.claim_safety_checker import check_claim_safety
from labos.checkers.confidentiality_checker import check_confidentiality
from labos.checkers.pattern_reference_checker import check_pattern_references
from labos.checkers.report import CaseCheckReport
from labos.evidence.summary import summarize_case
from labos.evidence.validator import (
    validate_evidence,
    validate_measurement_reference,
    validate_prediction_reality_record,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CASE_ID = "literature-arxiv-2305-thermal-sio2-released-membrane"
CASE = REPO_ROOT / "cases" / CASE_ID
BASELINE = REPO_ROOT / "exports" / f"{CASE_ID}-baseline"
M14_BASELINE = REPO_ROOT / "exports" / "literature-2021-diamond-on-gan-membrane-stress-baseline"
SCRIPT = REPO_ROOT / "scripts" / "labos_case.py"
M14_THERMOMECHANICAL_SOURCE = REPO_ROOT / "labos" / "triage" / "thermomechanical.py"
SCHEMAS = REPO_ROOT / "labos" / "schemas"
RECOGNIZED_DEPENDENCY_MANIFESTS = [
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "Pipfile",
    "poetry.lock",
]

EXPECTED_BASELINE_HASHES = {
    "decision_board_preview.json": "6a18fadcbdef0295a0cfd9ddbe43f4e99e11ea9bb6a4e9112e9f610ff718bc2e",
    "decision_board_preview.md": "80912cdd40b32c5a8d2f8159c9d9c1c55cd7719c15e6c38c4c6625f766c9f488",
    "human_review_checklist.md": "6ee1ac064f30208361f5d445581b853515505f7d46fb9e230d04137815a2d58c",
    "review_manifest.json": "f00ce5370270c0984bd0023acb886014ccb72ce89028b61c9315b2069cbcdcfb",
    "triage_report.md": "a8f35bc5765f03807da8f0074e533086f034edf407861fd60f8f6db7cc53f248",
    "triage_result.json": "d99a8d6490d64c37736aae8426adeb72b896a009b9f65cc4b6444d3c5dca2b64",
}
EXPECTED_BASELINE_MANIFEST_HASH = "4f3bfa78c50bbfaa65d47ded5d25c6de5dff683bc8b8dc6f7222c49115d6690c"
EXPECTED_CANONICAL_HASHES = {
    "00_problem_intake.yml": "8c795eab010653d3fc0441d19ddd44afb8a26368c333267be2a357380047e65e",
    "01_thermal_design_passport.yml": "36701af4ba7ad3b96aba60e79c4c6b136170cfa27be314b9412a19df670845c1",
    "02_decision_board.md": "95f3d4131949fa9abca00e7adc99960cc508bb13ccc45c41c889e89e6162dbe5",
    "03_architecture_genomes.yml": "1533f6a0d06e8f94a2d2f9fac166df7da40060523123c0262543c56b62356fc2",
    "04_design_space_scorecard.md": "9e66bb52186e7e970f9552f21dd804d9b5fd31a396c24a6f8a10c08e1bdb9ddc",
    "05_red_flags.md": "4311c1f82d61418253644d3937703c06b3b72b4ddcbf43f2fc3924bb2c66c4e5",
    "06_next_best_action.md": "28c19ca664faaf5c1a57566d89aaad106c3c3738563e0d2e5ed72f88663e0034",
    "07_validation_plan.md": "5ae90168f5f119ed68687cadee2465959e18a2e97d73a0cf8667a06ebc74ccb0",
    "08_supplier_specification.md": "5d0b8e946f048ec327d9fe35c5fca8d4d02dd8ebb4eafe4a4af175abda1882ef",
    "09_customer_memo.md": "60fbe28188592e1b10eec0b1682fe6eb4e41566984d40b0a5a38595787a015a4",
    "10_claim_ledger.yml": "248cd39bda0a31e80170a9eaee3e5cc77c9c8b399b2d4d661d7d18acc5545971",
    "11_engineering_memory_entry.md": "e00a1190410114cc14f63c66c29dda57bc500be2e3277dcdb15d019767843453",
}
EXPECTED_M14_BASELINE_HASHES = {
    "decision_board_preview.json": "cbe9fff37b0628e91bfebc0f4e22fe2df687596702174ac135dff061c8759430",
    "decision_board_preview.md": "e38d0651e2a612b08558a35e81181bb76161330054e2f3714a0a81cf21bb5833",
    "human_review_checklist.md": "6ee1ac064f30208361f5d445581b853515505f7d46fb9e230d04137815a2d58c",
    "review_manifest.json": "975a7dd162886b4b3932dbdb6be234071b5be013e51b05eac7c323fb512e81fe",
}
EXPECTED_M14_THERMOMECHANICAL_SHA256 = "d9e6e1fbd36c96fa83e88676ac30760449639bb2e40161fd63ba1e05e262618f"
EXPECTED_SCHEMA_TREE_SHA256 = "e62fc8c9545c4d212da3eb20074e8568a9855a7b092c4e6b889edd0580f2459e"
EXPECTED_DEPENDENCY_MANIFEST_HASHES: dict[str, str] = {}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _triage_json(case_path: Path) -> str:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "triage", str(case_path), "--json"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)
    return completed.stdout


def _tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


class M15BlindBaselineTests(unittest.TestCase):
    def test_blind_case_contains_the_twelve_canonical_files(self) -> None:
        numbered = sorted(path.name for path in CASE.iterdir() if path.is_file() and path.name[:2].isdigit())
        self.assertEqual(numbered, [
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
        ])

    def test_frozen_baseline_hashes_match_the_manifest(self) -> None:
        manifest = json.loads((BASELINE / "baseline_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["frozen_artifact_sha256"], EXPECTED_BASELINE_HASHES)
        actual = {
            name: _sha256(BASELINE / name)
            for name in manifest["frozen_artifacts"]
        }
        self.assertEqual(actual, EXPECTED_BASELINE_HASHES)
        self.assertNotIn("baseline_manifest.json", manifest["frozen_artifacts"])
        self.assertEqual(_sha256(BASELINE / "baseline_manifest.json"), EXPECTED_BASELINE_MANIFEST_HASH)

    def test_phase_one_canonical_case_hashes_are_unchanged(self) -> None:
        actual = {name: _sha256(CASE / name) for name in EXPECTED_CANONICAL_HASHES}
        self.assertEqual(actual, EXPECTED_CANONICAL_HASHES)

    def test_blind_triage_is_deterministic_and_outcome_free(self) -> None:
        first = _triage_json(CASE)
        second = _triage_json(CASE)
        self.assertEqual(first, second)
        self.assertEqual(first, (BASELINE / "triage_result.json").read_text(encoding="utf-8"))
        result = json.loads(first)
        self.assertEqual(result["thermomechanical_screening"]["status"], "not_applicable")
        canonical_text = "\n".join(
            path.read_text(encoding="utf-8").lower()
            for path in CASE.iterdir()
            if path.is_file() and path.name[:2].isdigit()
        )
        for restricted_term in (
            "malhaire",
            "arxiv:2305.15794",
            "determination of compressive stress",
            "-11.3",
            "-14.2",
            "-20.9",
            "-319 mpa",
            "-320 mpa",
            "-321 mpa",
            "-323 mpa",
            "moderate buckling",
            "mainly to thermal-expansion mismatch",
        ):
            self.assertNotIn(restricted_term, canonical_text)

    def test_iterator_scopes_are_explicit(self) -> None:
        canonical_names = [path.name for path in iter_canonical_case_files(CASE)]
        public_names = [path.name for path in iter_public_case_text_files(CASE)]
        self.assertEqual(canonical_names, list(EXPECTED_CANONICAL_HASHES))
        self.assertIn("BLIND_INPUT_MANIFEST.md", public_names)
        self.assertIn("GOLD_CASE_ASSESSMENT.md", public_names)
        self.assertIn("BENCHMARK_AUDIT_QUALIFICATION.md", public_names)
        self.assertNotIn("GOLD_CASE_ASSESSMENT.md", canonical_names)

    def test_metadata_files_cannot_alter_triage_output(self) -> None:
        expected = _triage_json(CASE)
        with tempfile.TemporaryDirectory() as tmp:
            copied = Path(tmp) / CASE_ID
            shutil.copytree(CASE, copied)
            for name in ("BLIND_INPUT_MANIFEST.md", "GOLD_CASE_ASSESSMENT.md", "BENCHMARK_AUDIT_QUALIFICATION.md"):
                (copied / name).write_text(
                    "PAT-UNKNOWN-REVIEW-ONLY\n"
                    "This review-only file says diamond thickness should not matter here.\n"
                    "The canonical triage corpus must ignore this text.\n",
                    encoding="utf-8",
                )
            self.assertEqual(_triage_json(copied), expected)

    def test_public_review_files_remain_in_claim_and_confidentiality_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            copied = Path(tmp) / CASE_ID
            shutil.copytree(CASE, copied)
            (copied / "GOLD_CASE_ASSESSMENT.md").write_text(
                "This benchmark is guaranteed to be the best solution.\n",
                encoding="utf-8",
            )
            claim_report = CaseCheckReport(copied)
            check_claim_safety(copied, claim_report)
            self.assertTrue(claim_report.section_findings("Claim safety warnings"))

            (copied / "BENCHMARK_AUDIT_QUALIFICATION.md").write_text(
                "restricted process recipe\n",
                encoding="utf-8",
            )
            confidentiality_report = CaseCheckReport(copied)
            check_confidentiality(copied, confidentiality_report)
            findings = confidentiality_report.section_findings("Confidentiality warnings")
            self.assertTrue(any("restricted process recipe" in finding.message for finding in findings))

    def test_pattern_references_use_canonical_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            copied = Path(tmp) / CASE_ID
            shutil.copytree(CASE, copied)
            (copied / "GOLD_CASE_ASSESSMENT.md").write_text(
                "Review-only text mentioning PAT-UNKNOWN-REVIEW-ONLY.\n",
                encoding="utf-8",
            )
            report = CaseCheckReport(copied)
            check_pattern_references(copied, report)
            messages = "\n".join(finding.message for finding in report.section_findings("Pattern references"))
            self.assertNotIn("PAT-UNKNOWN-REVIEW-ONLY", messages)

            with (copied / "04_design_space_scorecard.md").open("a", encoding="utf-8") as handle:
                handle.write("\nPAT-UNKNOWN-CANONICAL-ONLY\n")
            report = CaseCheckReport(copied)
            check_pattern_references(copied, report)
            messages = "\n".join(finding.message for finding in report.section_findings("Pattern references"))
            self.assertIn("PAT-UNKNOWN-CANONICAL-ONLY", messages)


class M15EvidenceRevealTests(unittest.TestCase):
    def test_evidence_reveal_does_not_change_frozen_baseline_artifacts(self) -> None:
        actual = {
            name: _sha256(BASELINE / name)
            for name in EXPECTED_BASELINE_HASHES
        }
        self.assertEqual(actual, EXPECTED_BASELINE_HASHES)
        m14_actual = {name: _sha256(M14_BASELINE / name) for name in EXPECTED_M14_BASELINE_HASHES}
        self.assertEqual(m14_actual, EXPECTED_M14_BASELINE_HASHES)

    def test_source_documented_sidecars_have_reciprocal_links_and_pending_review(self) -> None:
        evidence = CASE / "evidence"
        measurements = CASE / "measurements"
        self.assertEqual(validate_evidence(CASE, evidence / "EVD-001.json").status, "WARN")
        self.assertEqual(validate_evidence(CASE, evidence / "EVD-002.json").status, "WARN")
        parent = json.loads((evidence / "EVD-002.json").read_text(encoding="utf-8"))
        self.assertEqual(parent["status"], "draft")
        self.assertEqual(parent["reviewed_by"], "")
        self.assertEqual(parent["measurement_reference_ids"], [f"MSR-{index:03d}" for index in range(1, 7)])
        for index in range(1, 7):
            path = measurements / f"MSR-{index:03d}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["evidence_id"], "EVD-002")
            self.assertEqual(data["status"], "completed")
            self.assertIn(validate_measurement_reference(CASE, path).status, {"PASS", "WARN"})
        summary = summarize_case(CASE)
        self.assertIn("EVD-002.json", summary.unreviewed_evidence)

    def test_prediction_reality_binds_to_phase_one_without_fabricated_prediction(self) -> None:
        record_path = CASE / "prediction_reality" / "PRL-001.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        self.assertEqual(record["prediction"]["value"], None)
        self.assertEqual(record["prediction"]["lower_bound"], None)
        self.assertEqual(record["prediction"]["upper_bound"], None)
        self.assertEqual(record["status"], "draft")
        self.assertEqual(record["learning_disposition"], "pending_review")
        self.assertIn("9a9f3af3001b947226484f48b8db99f428556428", record["prediction"]["input_reference"])
        self.assertIn("baseline_manifest.json", record["prediction"]["input_reference"])
        self.assertIn("generalization is not evaluable", record["comparison_context"])
        self.assertIn("adjacent-scope transfer was not demonstrated", record["comparison_context"])
        self.assertEqual(validate_prediction_reality_record(CASE, record_path).status, "WARN")

    def test_assessment_reclassifies_scope_boundary_benchmark(self) -> None:
        assessment = (CASE / "GOLD_CASE_ASSESSMENT.md").read_text(encoding="utf-8")
        frozen = json.loads((BASELINE / "triage_result.json").read_text(encoding="utf-8"))
        for rule in frozen["triggered_rules"]:
            self.assertIn(rule["rule_id"], assessment)
        for rule_id in (f"TRIAGE-THERMOMECH-{index:03d}" for index in range(1, 8)):
            self.assertIn(rule_id, assessment)
        self.assertIn("artifact-separated retrospective, outcome-value-withheld, adjacent-scope boundary benchmark", assessment)
        self.assertIn("outside the strict M14 process-sequence contract", assessment)
        self.assertIn("generalization_not_evaluable", assessment)
        self.assertIn("adjacent_scope_transfer_not_supported", assessment)
        self.assertIn("construct-invalid and superseded", assessment)
        self.assertNotIn("Disposition: `generalization_not_supported`", assessment)
        self.assertNotIn("| Total | 10 | 0 |", assessment)
        self.assertIn("must not be rewritten", assessment)

    def test_assessment_records_frozen_decision_board_coherence_findings(self) -> None:
        assessment = (CASE / "GOLD_CASE_ASSESSMENT.md").read_text(encoding="utf-8")
        for phrase in (
            "candidate_routes` is empty",
            "two or three architectures",
            "TRIAGE-DESIGN-001",
            "Two diamond-thickness hold points",
            "duplicated in different wording",
            "Interface-limited classification is questionable",
            "generic architecture-comparison action displaced",
            "READY_FOR_ARCHITECTURE_SCREENING",
        ):
            self.assertIn(phrase, assessment)

    def test_post_freeze_audit_qualification_exists_and_is_non_frozen(self) -> None:
        qualification = (CASE / "BENCHMARK_AUDIT_QUALIFICATION.md").read_text(encoding="utf-8")
        self.assertIn("added after the frozen phase-one commit", qualification)
        self.assertIn("does not form part of the frozen baseline", qualification)
        self.assertIn("Agent knowledge isolation was not preserved", qualification)
        self.assertIn("not a prospective double-blind benchmark", qualification)

    def test_noncanonical_benchmark_notes_do_not_change_case_check_scope(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "check", str(CASE)],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("Diamond is referenced without interface-risk discussion", completed.stdout)

    def test_m14_rules_schemas_and_dependencies_are_unchanged(self) -> None:
        self.assertEqual(_sha256(M14_THERMOMECHANICAL_SOURCE), EXPECTED_M14_THERMOMECHANICAL_SHA256)
        self.assertEqual(_tree_sha256(SCHEMAS), EXPECTED_SCHEMA_TREE_SHA256)

        actual_manifests = {
            manifest: _sha256(REPO_ROOT / manifest)
            for manifest in RECOGNIZED_DEPENDENCY_MANIFESTS
            if (REPO_ROOT / manifest).is_file()
        }
        self.assertEqual(actual_manifests, EXPECTED_DEPENDENCY_MANIFEST_HASHES)


if __name__ == "__main__":
    unittest.main()
