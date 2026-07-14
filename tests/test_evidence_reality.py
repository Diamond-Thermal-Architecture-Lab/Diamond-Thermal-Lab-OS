from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from labos.evidence.summary import summarize_case
from labos.evidence.template import create_evidence_template, create_measurement_template, create_prediction_reality_template
from labos.evidence.validator import validate_evidence, validate_measurement_reference, validate_prediction_reality_record


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_CASE = REPO_ROOT / "cases" / "example-incomplete-gan-rf-pa"
SCRIPT = REPO_ROOT / "scripts" / "labos_case.py"


def copy_case(tmp: str) -> Path:
    destination = Path(tmp) / "synthetic-case"
    shutil.copytree(EXAMPLE_CASE, destination)
    intake = destination / "00_problem_intake.yml"
    intake.write_text(intake.read_text(encoding="utf-8").replace("example-incomplete-gan-rf-pa", "synthetic-case"), encoding="utf-8")
    return destination


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_reviewed_evidence(case: Path, evidence_id: str = "EVD-001") -> Path:
    path = case / "evidence" / f"{evidence_id}.json"
    create_evidence_template(case, evidence_id, "measurement", path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update({
        "title": "SYNTHETIC TEST DATA - NOT A MEASURED ENGINEERING RESULT",
        "status": "reviewed",
        "evidence_level": "independently_measured",
        "source": {"reference": "controlled-synthetic-test-source", "sha256": "a" * 64},
        "method_summary": "Synthetic test measurement method and collection basis.",
        "applicability": "Synthetic fixture only.",
        "uncertainty_summary": "Synthetic uncertainty statement.",
        "public_summary": "Synthetic test metadata only; no engineering result.",
        "reviewed_by": "Test reviewer declaration",
    })
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def make_reviewed_measurement(case: Path, evidence_id: str = "EVD-001", measurement_id: str = "MSR-001", value: object = 100) -> Path:
    path = case / "measurements" / f"{measurement_id}.json"
    create_measurement_template(case, measurement_id, evidence_id, path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update({
        "status": "reviewed",
        "quantity": "junction_temperature",
        "value": value,
        "unit": "K",
        "sample_id": "ANON-SYN-001",
        "method": "Synthetic fixture method.",
        "operating_conditions": "Synthetic fixture conditions.",
        "uncertainty": {"numeric_value": 2, "unit": "K", "basis": "Synthetic fixture uncertainty basis."},
        "raw_data_reference": "controlled-synthetic-raw-reference",
        "raw_data_sha256": "b" * 64,
        "reviewed_by": "Test reviewer declaration",
    })
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def make_prediction(case: Path, measurement_id: str = "MSR-001", record_id: str = "PRL-001", unit: str = "K", reality_quantity: str = "junction_temperature") -> Path:
    path = case / "prediction_reality" / f"{record_id}.json"
    create_prediction_reality_template(case, record_id, measurement_id, path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update({
        "status": "comparable",
        "quantity": reality_quantity,
        "comparison_context": "Synthetic fixture comparison context.",
        "decision_impact": "Synthetic test only; no decision change.",
        "prediction": {
            "value": 90,
            "unit": unit,
            "lower_bound": 80,
            "upper_bound": 105,
            "model_name": "synthetic-test-model",
            "model_version": "0.0",
            "input_reference": "controlled-synthetic-input-reference",
            "input_sha256": "c" * 64,
        },
    })
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


class EvidenceRealityTests(unittest.TestCase):
    def test_deterministic_evidence_template_and_draft_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = copy_case(tmp)
            first = case / "evidence" / "EVD-001.json"
            second = case / "evidence" / "EVD-002.json"
            create_evidence_template(case, "EVD-001", "measurement", first)
            create_evidence_template(case, "EVD-002", "measurement", second)
            first_data = json.loads(first.read_text(encoding="utf-8"))
            second_data = json.loads(second.read_text(encoding="utf-8"))
            self.assertEqual(first_data["status"], "draft")
            self.assertEqual(validate_evidence(case, first).status, "WARN")
            self.assertEqual(set(first_data), set(second_data))

    def test_reviewed_evidence_claim_links_and_confidentiality_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = copy_case(tmp)
            evidence = make_reviewed_evidence(case)
            self.assertEqual(validate_evidence(case, evidence).status, "PASS")
            data = json.loads(evidence.read_text(encoding="utf-8"))
            data["supports_claim_ids"] = ["CLM-001"]
            data["contradicts_claim_ids"] = ["CLM-001"]
            evidence.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(validate_evidence(case, evidence).status, "FAIL")
            data["contradicts_claim_ids"] = ["CLM-999"]
            evidence.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(validate_evidence(case, evidence).status, "FAIL")
            data["contradicts_claim_ids"] = []
            data["source"] = {"reference": "C:\\restricted\\raw.csv", "sha256": "not-a-hash"}
            evidence.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(validate_evidence(case, evidence).status, "FAIL")

    def test_measurement_reference_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = copy_case(tmp)
            make_reviewed_evidence(case)
            measurement = make_reviewed_measurement(case)
            self.assertEqual(validate_measurement_reference(case, measurement).status, "PASS")
            data = json.loads(measurement.read_text(encoding="utf-8"))
            data["status"], data["value"] = "completed", None
            measurement.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(validate_measurement_reference(case, measurement).status, "FAIL")
            data["status"], data["value"], data["evidence_id"] = "planned", None, "EVD-999"
            measurement.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(validate_measurement_reference(case, measurement).status, "FAIL")

    def test_prediction_comparison_and_conservative_edge_cases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = copy_case(tmp)
            make_reviewed_evidence(case)
            make_reviewed_measurement(case)
            record = make_prediction(case)
            result = validate_prediction_reality_record(case, record)
            self.assertEqual(result.status, "PASS")
            self.assertEqual(result.comparison["signed_error"], "10")
            self.assertEqual(result.comparison["absolute_error"], "10")
            self.assertEqual(result.comparison["relative_error_percent"], "10.0")
            self.assertTrue(result.comparison["reality_within_prediction_interval"])
            data = json.loads(record.read_text(encoding="utf-8"))
            data["prediction"]["unit"] = "C"
            record.write_text(json.dumps(data), encoding="utf-8")
            mismatch = validate_prediction_reality_record(case, record)
            self.assertEqual(mismatch.status, "WARN")
            self.assertFalse(mismatch.comparison["comparable"])
            data["prediction"]["unit"] = "K"
            data["quantity"] = "different_quantity"
            record.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(validate_prediction_reality_record(case, record).status, "FAIL")

    def test_zero_reality_value_and_calibration_guardrail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = copy_case(tmp)
            make_reviewed_evidence(case)
            make_reviewed_measurement(case, value=0)
            record = make_prediction(case)
            data = json.loads(record.read_text(encoding="utf-8"))
            data["learning_disposition"] = "accepted_for_calibration"
            record.write_text(json.dumps(data), encoding="utf-8")
            result = validate_prediction_reality_record(case, record)
            self.assertEqual(result.status, "FAIL")
            self.assertIsNone(result.comparison["relative_error_percent"])

    def test_summary_duplicates_cli_json_and_no_sidecars(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = copy_case(tmp)
            no_sidecars = summarize_case(case)
            self.assertEqual(no_sidecars.reality_loop_status, "NO_EVIDENCE")
            make_reviewed_evidence(case)
            duplicate = case / "evidence" / "copy.json"
            duplicate.write_bytes((case / "evidence" / "EVD-001.json").read_bytes())
            summary = summarize_case(case)
            self.assertEqual(summary.status, "FAIL")
            self.assertIn("EVD-001", summary.duplicate_ids)
            completed = subprocess.run([sys.executable, str(SCRIPT), "evidence-summary", str(case), "--json"], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertEqual(completed.returncode, 2)
            self.assertEqual(json.loads(completed.stdout)["status"], "FAIL")

    def test_cli_exit_codes_overwrite_and_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = copy_case(tmp)
            baseline = {path.name: sha256(path) for path in case.iterdir() if path.is_file() and path.name[:2].isdigit()}
            output = case / "evidence" / "EVD-001.json"
            created = subprocess.run([sys.executable, str(SCRIPT), "new-evidence", str(case), "--evidence-id", "EVD-001", "--type", "measurement", "--output", str(output)], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertEqual(created.returncode, 0, created.stderr)
            refused = subprocess.run([sys.executable, str(SCRIPT), "new-evidence", str(case), "--evidence-id", "EVD-001", "--type", "measurement", "--output", str(output)], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertEqual(refused.returncode, 2)
            checked = subprocess.run([sys.executable, str(SCRIPT), "validate-evidence", str(case), str(output)], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertEqual(checked.returncode, 1)
            self.assertEqual(baseline, {path.name: sha256(path) for path in case.iterdir() if path.is_file() and path.name[:2].isdigit()})

    def test_path_traversal_and_malformed_json_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = copy_case(tmp)
            with self.assertRaises(ValueError):
                create_evidence_template(case, "EVD-001", "measurement", case / ".." / "outside.json")
            malformed = case / "evidence" / "EVD-001.json"
            malformed.parent.mkdir()
            malformed.write_text("{bad", encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_evidence(case, malformed)


if __name__ == "__main__":
    unittest.main()
