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
            self.assertEqual(validate_evidence(case, malformed).status, "FAIL")


class EvidenceRealityHardeningTests(unittest.TestCase):
    def test_all_template_bytes_are_deterministic_for_identical_logical_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as first_tmp, tempfile.TemporaryDirectory() as second_tmp:
            first, second = copy_case(first_tmp), copy_case(second_tmp)
            first_paths = (
                first / "evidence" / "EVD-001.json",
                first / "measurements" / "MSR-001.json",
                first / "prediction_reality" / "PRL-001.json",
            )
            second_paths = (
                second / "evidence" / "EVD-001.json",
                second / "measurements" / "MSR-001.json",
                second / "prediction_reality" / "PRL-001.json",
            )
            create_evidence_template(first, "EVD-001", "measurement", first_paths[0])
            create_measurement_template(first, "MSR-001", "EVD-001", first_paths[1])
            create_prediction_reality_template(first, "PRL-001", "MSR-001", first_paths[2])
            create_evidence_template(second, "EVD-001", "measurement", second_paths[0])
            create_measurement_template(second, "MSR-001", "EVD-001", second_paths[1])
            create_prediction_reality_template(second, "PRL-001", "MSR-001", second_paths[2])
            for first_path, second_path in zip(first_paths, second_paths, strict=True):
                self.assertEqual(first_path.read_bytes(), second_path.read_bytes())

    def test_schema_contracts_are_complete_and_explicit(self) -> None:
        schemas = {
            "evidence_object.schema.json": ("source", "evidence_id", "EVD-"),
            "measurement_reference.schema.json": ("uncertainty", "measurement_id", "MSR-"),
            "prediction_reality_record.schema.json": ("prediction", "record_id", "PRL-"),
        }
        for filename, (nested, identifier, prefix) in schemas.items():
            with self.subTest(filename=filename):
                data = json.loads((REPO_ROOT / "labos" / "schemas" / filename).read_text(encoding="utf-8"))
                self.assertEqual(data["$schema"], "https://json-schema.org/draft/2020-12/schema")
                self.assertFalse(data["additionalProperties"])
                self.assertTrue(set(data["required"]).issubset(data["properties"]))
                self.assertEqual(data["properties"][identifier]["pattern"], f"^{prefix}[0-9]{{3}}$")
                self.assertEqual(data["properties"][nested]["type"], "object")
                self.assertIn("additionalProperties", data["properties"][nested])

    def test_evidence_user_file_problems_return_fail_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = copy_case(tmp)
            path = make_reviewed_evidence(case)
            cases: list[tuple[str, object]] = [
                ("array-root", []),
                ("wrong-case", {"case_id": "wrong-case"}),
                ("bad-id", {"evidence_id": "EVD-1"}),
                ("bad-type", {"evidence_type": "unknown"}),
                ("bad-status", {"status": "unknown"}),
                ("bad-level", {"evidence_level": "unknown"}),
                ("bad-confidentiality", {"confidentiality_level": "secret"}),
                ("missing-reviewer", {"reviewed_by": ""}),
                ("bad-source-hash", {"source": {"reference": "controlled", "sha256": "ABC"}}),
                ("windows-path", {"source": {"reference": "C:\\restricted\\raw.csv", "sha256": None}}),
                ("posix-path", {"source": {"reference": "/restricted/raw.csv", "sha256": None}}),
                ("credential", {"source": {"reference": "token=not-allowed", "sha256": None}}),
            ]
            valid = json.loads(path.read_text(encoding="utf-8"))
            for name, change in cases:
                with self.subTest(name=name):
                    if name == "array-root":
                        path.write_text(json.dumps(change), encoding="utf-8")
                    else:
                        data = dict(valid)
                        data.update(change)  # type: ignore[arg-type]
                        path.write_text(json.dumps(data), encoding="utf-8")
                    self.assertEqual(validate_evidence(case, path).status, "FAIL")
            path.write_text(json.dumps(valid), encoding="utf-8")
            data = json.loads(path.read_text(encoding="utf-8"))
            data["evidence_type"], data["evidence_level"] = "supplier_claim", "production_validated"
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(validate_evidence(case, path).status, "FAIL")

    def test_evidence_arrays_and_measurement_reference_ids_are_checked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = copy_case(tmp)
            path = make_reviewed_evidence(case)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["supports_claim_ids"] = "CLM-001"
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(validate_evidence(case, path).status, "FAIL")
            data["supports_claim_ids"] = ["CLM-001"]
            data["measurement_reference_ids"] = ["MSR-1"]
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(validate_evidence(case, path).status, "FAIL")
            data["measurement_reference_ids"] = ["MSR-001"]
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(validate_evidence(case, path).status, "FAIL")

    def test_measurement_contract_edge_cases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = copy_case(tmp)
            make_reviewed_evidence(case)
            path = make_reviewed_measurement(case)
            valid = json.loads(path.read_text(encoding="utf-8"))
            cases = {
                "wrong-case": {"case_id": "wrong-case"},
                "bad-id": {"measurement_id": "MSR-X"},
                "bad-evidence-id": {"evidence_id": "EVD-1"},
                "bool-value": {"value": True},
                "no-unit": {"unit": ""},
                "missing-reviewer": {"reviewed_by": ""},
                "bad-raw-hash": {"raw_data_sha256": "bad"},
                "unsafe-reference": {"raw_data_reference": "/restricted/raw.csv"},
                "bad-uncertainty": {"uncertainty": {"numeric_value": True, "unit": 3, "basis": ""}},
            }
            for name, change in cases.items():
                with self.subTest(name=name):
                    data = dict(valid)
                    data.update(change)
                    path.write_text(json.dumps(data), encoding="utf-8")
                    self.assertEqual(validate_measurement_reference(case, path).status, "FAIL")
            data = dict(valid)
            data["status"] = "completed"
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(validate_measurement_reference(case, path).status, "PASS")
            data = dict(valid)
            data["status"], data["value"], data["unit"] = "planned", None, None
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(validate_measurement_reference(case, path).status, "WARN")

    def test_prediction_contract_edge_cases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = copy_case(tmp)
            make_reviewed_evidence(case)
            make_reviewed_measurement(case)
            path = make_prediction(case)
            valid = json.loads(path.read_text(encoding="utf-8"))
            cases = {
                "wrong-case": {"case_id": "wrong-case"},
                "bad-record-id": {"record_id": "PRL-X"},
                "bad-measurement-id": {"reality_measurement_id": "MSR-X"},
                "unknown-measurement": {"reality_measurement_id": "MSR-999"},
                "unknown-evidence": {"prediction_evidence_ids": ["EVD-999"]},
                "bad-evidence-id": {"prediction_evidence_ids": ["EVD-X"]},
                "missing-comparable-prediction": {"prediction": {**valid["prediction"], "value": None}},
                "rejected-bounds": {"prediction": {**valid["prediction"], "lower_bound": 110, "upper_bound": 100}},
                "reviewed-without-reviewer": {"status": "reviewed", "reviewed_by": ""},
                "accepted-without-review": {"learning_disposition": "accepted_for_calibration"},
                "bool-prediction": {"prediction": {**valid["prediction"], "value": True}},
            }
            for name, change in cases.items():
                with self.subTest(name=name):
                    data = dict(valid)
                    data.update(change)
                    path.write_text(json.dumps(data), encoding="utf-8")
                    self.assertEqual(validate_prediction_reality_record(case, path).status, "FAIL")
            data = dict(valid)
            data["status"] = "draft"
            data["prediction"] = {**valid["prediction"], "value": None}
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(validate_prediction_reality_record(case, path).status, "WARN")

    def test_prediction_interval_miss_and_malformed_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = copy_case(tmp)
            make_reviewed_evidence(case)
            make_reviewed_measurement(case)
            path = make_prediction(case)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["prediction"]["upper_bound"] = 95
            path.write_text(json.dumps(data), encoding="utf-8")
            result = validate_prediction_reality_record(case, path)
            self.assertEqual(result.status, "PASS")
            self.assertFalse(result.comparison["reality_within_prediction_interval"])
            for validator, folder, name in (
                (validate_evidence, "evidence", "EVD-099.json"),
                (validate_measurement_reference, "measurements", "MSR-099.json"),
                (validate_prediction_reality_record, "prediction_reality", "PRL-099.json"),
            ):
                malformed = case / folder / name
                malformed.parent.mkdir(exist_ok=True)
                malformed.write_text("{bad", encoding="utf-8")
                with self.subTest(name=name):
                    self.assertEqual(validator(case, malformed).status, "FAIL")
                malformed.write_text("[]", encoding="utf-8")
                with self.subTest(name=f"array-{name}"):
                    self.assertEqual(validator(case, malformed).status, "FAIL")

    def test_cli_malformed_json_is_structured_fail_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = copy_case(tmp)
            commands = (
                ("validate-evidence", case / "evidence" / "EVD-001.json"),
                ("validate-measurement-reference", case / "measurements" / "MSR-001.json"),
                ("validate-prediction-reality-record", case / "prediction_reality" / "PRL-001.json"),
            )
            for command, path in commands:
                path.parent.mkdir(exist_ok=True)
                path.write_text("{bad", encoding="utf-8")
                completed = subprocess.run([sys.executable, str(SCRIPT), command, str(case), str(path), "--json"], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
                with self.subTest(command=command):
                    self.assertEqual(completed.returncode, 2)
                    self.assertNotIn("Traceback", completed.stderr)
                    self.assertEqual(json.loads(completed.stdout)["status"], "FAIL")

    def test_summary_and_general_checker_fail_on_malformed_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = copy_case(tmp)
            malformed = case / "evidence" / "EVD-001.json"
            malformed.parent.mkdir()
            malformed.write_text("{bad", encoding="utf-8")
            self.assertEqual(summarize_case(case).status, "FAIL")
            checked = subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "labos_check_case.py"), str(case)], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertEqual(checked.returncode, 2)
            self.assertIn("Status:\nFAIL", checked.stdout)

    def test_force_preserves_unrelated_files_and_symlink_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = copy_case(tmp)
            output = case / "evidence" / "EVD-001.json"
            create_evidence_template(case, "EVD-001", "measurement", output)
            unrelated = case / "evidence" / "notes.txt"
            unrelated.write_text("preserve\n", encoding="utf-8")
            create_evidence_template(case, "EVD-001", "measurement", output, force=True)
            self.assertEqual(unrelated.read_text(encoding="utf-8"), "preserve\n")
            escape = Path(tmp) / "escape"
            try:
                escape.symlink_to(Path(tmp), target_is_directory=True)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"directory symlink unavailable: {exc}")
            with self.assertRaises(ValueError):
                create_evidence_template(case, "EVD-002", "measurement", escape / "EVD-002.json")


if __name__ == "__main__":
    unittest.main()
