from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from dataclasses import fields
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import labos.engineering.prediction_reality_adapter as adapter_module
from labos.engineering import (
    PREDICTION_REALITY_ADAPTER_VERSION,
    PersistedEngineeringEvaluationResult,
    PredictionRealityProjectionError,
    QuantityKind,
    canonical_json_bytes,
    convert_canonical_to_unit,
    convert_quantity,
    load_engineering_evaluation_result,
    project_eer_prediction_to_measurement,
)
from labos.evidence import validate_measurement_reference
from labos.evidence.template import create_evidence_template, create_measurement_template
from tests.test_m16a_evaluation_schema import evaluated_eer, stamp_eer


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ID = "EER-001-OUT-001"
MEASUREMENT_ID = "MSR-001"


class PredictionRealityAdapterCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.case = self.root / "synthetic-i3b2-case"
        self.case.mkdir()
        (self.case / "00_problem_intake.yml").write_text(
            f"case_id: {self.case.name}\n", encoding="utf-8"
        )
        self._write_evidence()
        self._write_measurement()
        self.eer = self._write_eer()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @property
    def measurement_path(self) -> Path:
        return self.case / "measurements" / f"{MEASUREMENT_ID}.json"

    @property
    def eer_path(self) -> Path:
        return self.case / "engineering" / "evaluations" / "EER-001.json"

    def _write_evidence(self) -> None:
        path = self.case / "evidence" / "EVD-001.json"
        create_evidence_template(self.case, "EVD-001", "measurement", path)
        data = json.loads(path.read_text(encoding="utf-8"))
        data.update(
            {
                "title": "SYNTHETIC TEST DATA - NOT AN ENGINEERING RESULT",
                "status": "reviewed",
                "evidence_level": "independently_measured",
                "source": {"reference": "controlled-synthetic-source", "sha256": "a" * 64},
                "method_summary": "Synthetic fixture method.",
                "applicability": "Synthetic fixture only.",
                "uncertainty_summary": "Synthetic fixture uncertainty.",
                "public_summary": "Synthetic metadata only.",
                "reviewed_by": "Synthetic reviewer declaration",
            }
        )
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _write_measurement(
        self,
        *,
        unit: str = "degC",
        quantity: str = "junction_temperature",
        case_id: str | None = None,
        measurement_id: str = MEASUREMENT_ID,
        raw_hash: str | None = "b" * 64,
    ) -> None:
        path = self.measurement_path
        if not path.exists():
            create_measurement_template(self.case, MEASUREMENT_ID, "EVD-001", path)
        data = json.loads(path.read_text(encoding="utf-8"))
        data.update(
            {
                "measurement_id": measurement_id,
                "case_id": case_id or self.case.name,
                "status": "reviewed",
                "quantity": quantity,
                "value": 50,
                "unit": unit,
                "sample_id": "ANON-SYN-001",
                "method": "Synthetic fixture method.",
                "operating_conditions": "Synthetic fixture conditions.",
                "uncertainty": {
                    "numeric_value": 2,
                    "unit": unit,
                    "basis": "Synthetic fixture uncertainty basis.",
                },
                "raw_data_reference": "controlled-synthetic-raw-reference",
                "raw_data_sha256": raw_hash,
                "reviewed_by": "Synthetic reviewer declaration",
            }
        )
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _write_eer(
        self,
        *,
        value: str = "323.15",
        lower: str | None = "320",
        upper: str | None = "325",
        model_id: str = "synthetic-model",
        model_version: str = "1.0",
    ) -> PersistedEngineeringEvaluationResult:
        data = evaluated_eer()
        data["case_id"] = self.case.name
        data["evaluation_plan"]["case_id"] = self.case.name
        data["model_manifest"]["model_id"] = model_id
        data["model_manifest"]["model_version"] = model_version
        data["evaluation_plan"]["model_request"] = {
            "model_id": model_id,
            "model_version": model_version,
        }
        output = data["prediction_outputs"][0]
        output["value"] = value
        output["lower_bound"] = lower
        output["upper_bound"] = upper
        data["result_payload"]["content"]["candidate_results"][0][
            "junction_temperature"
        ] = value
        stamp_eer(data)
        self.eer_path.parent.mkdir(parents=True, exist_ok=True)
        self.eer_path.write_bytes(canonical_json_bytes(data))
        return load_engineering_evaluation_result(self.case, "EER-001")

    def project(self):
        return project_eer_prediction_to_measurement(self.eer, OUTPUT_ID, MEASUREMENT_ID)

    def snapshot(self) -> dict[str, bytes]:
        return {
            path.relative_to(self.case).as_posix(): path.read_bytes()
            for path in self.case.rglob("*")
            if path.is_file()
        }


class ProjectionSuccessTests(PredictionRealityAdapterCase):
    def test_prj_01_absolute_temperature_projects_to_matching_degc(self) -> None:
        projection = self.project()
        self.assertEqual(projection.quantity, "junction_temperature")
        self.assertEqual(projection.prediction["value"], 50)
        self.assertIs(type(projection.prediction["value"]), int)
        self.assertEqual(projection.prediction["unit"], "degC")

    def test_prj_02_equivalent_units_preserve_m16a_identity_before_legacy(self) -> None:
        reverse = convert_canonical_to_unit(
            QuantityKind.ABSOLUTE_TEMPERATURE, Decimal("323.15"), "degC"
        )
        round_trip = convert_quantity(
            QuantityKind.ABSOLUTE_TEMPERATURE,
            reverse.conversion.original_value,
            reverse.conversion.original_unit,
        )
        self.assertEqual(round_trip.canonical_value, Decimal("323.15"))
        self.assertEqual(self.project().prediction["value"], 50)

    def test_adp_05_warn_is_usable_without_review_semantics(self) -> None:
        self._write_measurement(raw_hash=None)
        self.assertEqual(
            validate_measurement_reference(self.case, self.measurement_path).status, "WARN"
        )
        projection = self.project()
        serialized = projection.to_dict()
        self.assertEqual(projection.prediction["value"], 50)
        for forbidden in ("status", "reviewed_by", "review_notes", "learning_disposition"):
            self.assertNotIn(forbidden, serialized)
            self.assertNotIn(forbidden, serialized["prediction"])

    def test_adp_06_exact_measurement_unit_token_is_preserved(self) -> None:
        for token in ("degC", "°C"):
            with self.subTest(token=token):
                self._write_measurement(unit=token)
                projection = self.project()
                self.assertEqual(projection.prediction["unit"], token)
                self.assertEqual(projection.prediction["value"], 50)

    def test_adp_07_bounds_are_independently_projected(self) -> None:
        projection = self.project()
        self.assertEqual(projection.prediction["lower_bound"], 46.85)
        self.assertEqual(projection.prediction["upper_bound"], 51.85)

        self.eer = self._write_eer(lower=None, upper=None)
        projection = self.project()
        self.assertIsNone(projection.prediction["lower_bound"])
        self.assertIsNone(projection.prediction["upper_bound"])

    def test_adp_09_through_14_traceability_and_exact_legacy_shape(self) -> None:
        self.eer = self._write_eer(model_id="public-synthetic-model", model_version="2.3")
        projection = self.project()
        full = projection.to_dict()
        legacy = projection.legacy_fields()
        self.assertEqual(
            projection.prediction["input_reference"],
            "engineering/evaluations/EER-001.json",
        )
        self.assertEqual(projection.prediction["input_sha256"], self.eer.eer_file_sha256)
        self.assertNotEqual(
            projection.prediction["input_sha256"], self.eer.evaluation_result.content_sha256
        )
        self.assertEqual(projection.prediction["model_name"], "public-synthetic-model")
        self.assertEqual(projection.prediction["model_version"], "2.3")
        self.assertEqual(
            set(full),
            {
                "prediction_reality_adapter_version",
                "source_evaluation_id",
                "source_eer_content_sha256",
                "source_eer_file_sha256",
                "source_output_id",
                "source_candidate_id",
                "measurement_id",
                "quantity",
                "prediction",
            },
        )
        self.assertEqual(full["prediction_reality_adapter_version"], PREDICTION_REALITY_ADAPTER_VERSION)
        self.assertEqual(full["source_evaluation_id"], "EER-001")
        self.assertEqual(full["source_eer_content_sha256"], self.eer.evaluation_result.content_sha256)
        self.assertEqual(full["source_eer_file_sha256"], self.eer.eer_file_sha256)
        self.assertEqual(full["source_output_id"], OUTPUT_ID)
        self.assertEqual(full["source_candidate_id"], "CND-001")
        self.assertEqual(full["measurement_id"], MEASUREMENT_ID)
        self.assertEqual(set(legacy), {"quantity", "prediction"})
        self.assertEqual(set(legacy["prediction"]), adapter_module._LEGACY_PREDICTION_FIELDS)
        self.assertFalse(set(full) - {"quantity", "prediction"} & set(legacy))

    def test_adp_15_projection_writes_no_artifact(self) -> None:
        before = self.snapshot()
        self.project()
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.case / "prediction_reality").exists())


class ProjectionRejectionTests(PredictionRealityAdapterCase):
    def test_prj_03_different_quantity_label_rejects_without_alias(self) -> None:
        self._write_measurement(quantity="source_temperature")
        with self.assertRaises(PredictionRealityProjectionError):
            self.project()

    def test_prj_04a_unknown_target_unit_rejects(self) -> None:
        self._write_measurement(unit="C")
        with self.assertRaises(PredictionRealityProjectionError):
            self.project()

    def test_prj_04b_unit_for_different_kind_rejects(self) -> None:
        self._write_measurement(unit="mW")
        with self.assertRaises(PredictionRealityProjectionError):
            self.project()

    def test_prj_05_high_precision_legacy_number_loss_rejects(self) -> None:
        self.eer = self._write_eer(
            value="273.27345678901234567890123456789", lower=None, upper=None
        )
        with self.assertRaisesRegex(PredictionRealityProjectionError, "loses numeric identity"):
            self.project()

    def test_adp_01_unknown_or_malformed_output_id_rejects(self) -> None:
        for output_id in ("EER-001-OUT-999", "EER-1-OUT-1", " EER-001-OUT-001"):
            with self.subTest(output_id=output_id), self.assertRaises(
                PredictionRealityProjectionError
            ):
                project_eer_prediction_to_measurement(self.eer, output_id, MEASUREMENT_ID)

    def test_adp_02_measurement_id_and_filename_mismatch_rejects(self) -> None:
        self._write_measurement(measurement_id="MSR-002")
        with patch.object(
            adapter_module, "validate_measurement_reference", return_value=SimpleNamespace(status="PASS")
        ):
            with self.assertRaisesRegex(PredictionRealityProjectionError, "identity"):
                self.project()

    def test_adp_03_measurement_case_mismatch_rejects(self) -> None:
        self._write_measurement(case_id="different-case")
        with patch.object(
            adapter_module, "validate_measurement_reference", return_value=SimpleNamespace(status="PASS")
        ):
            with self.assertRaisesRegex(PredictionRealityProjectionError, "case_id"):
                self.project()

    def test_adp_04_repository_measurement_validation_fail_rejects(self) -> None:
        with patch.object(
            adapter_module, "validate_measurement_reference", return_value=SimpleNamespace(status="FAIL")
        ):
            with self.assertRaisesRegex(PredictionRealityProjectionError, "returned FAIL"):
                self.project()

    def test_adp_08_one_unrepresentable_bound_rejects_entire_projection(self) -> None:
        self.eer = self._write_eer(lower="273.27345678901234567890123456789")
        with self.assertRaisesRegex(PredictionRealityProjectionError, "loses numeric identity"):
            self.project()

    def test_adp_16_stale_or_changed_persisted_snapshot_rejects(self) -> None:
        stale = self.eer
        self._write_eer(model_version="1.1")
        with self.assertRaisesRegex(PredictionRealityProjectionError, "differs"):
            project_eer_prediction_to_measurement(stale, OUTPUT_ID, MEASUREMENT_ID)

    def test_adp_17_low_level_forged_wrapper_cannot_bypass_reload(self) -> None:
        forged = object.__new__(PersistedEngineeringEvaluationResult)
        for field in fields(PersistedEngineeringEvaluationResult):
            object.__setattr__(forged, field.name, getattr(self.eer, field.name))
        object.__setattr__(forged, "_eer_bytes", self.eer.eer_bytes + b"forged")
        with self.assertRaisesRegex(PredictionRealityProjectionError, "differs"):
            project_eer_prediction_to_measurement(forged, OUTPUT_ID, MEASUREMENT_ID)

    def test_adp_18_measurement_change_during_validation_rejects(self) -> None:
        def mutate(_case: Path, path: Path) -> SimpleNamespace:
            path.write_bytes(path.read_bytes() + b" ")
            return SimpleNamespace(status="PASS")

        with patch.object(adapter_module, "validate_measurement_reference", side_effect=mutate):
            with self.assertRaisesRegex(PredictionRealityProjectionError, "bytes changed"):
                self.project()


class HistoricalSeparationTests(PredictionRealityAdapterCase):
    def test_prj_06_historical_prediction_reality_sources_remain_untouched(self) -> None:
        historical = (
            REPO_ROOT / "labos" / "prediction_reality" / "comparison.py",
            REPO_ROOT / "labos" / "prediction_reality" / "validator.py",
            REPO_ROOT / "labos" / "prediction_reality" / "__init__.py",
            REPO_ROOT / "labos" / "schemas" / "prediction_reality_record.schema.json",
            REPO_ROOT / "tests" / "test_evidence_reality.py",
        )
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in historical}
        self.project()
        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in historical}
        self.assertEqual(after, before)

    def test_adapter_imports_no_private_quantity_registry_helpers(self) -> None:
        source = Path(adapter_module.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "_lookup_unit",
            "_UNIT_DEFINITIONS",
            "_CANONICAL_UNITS",
            "_DECIMAL_CONTEXT",
            "_converted_decimal",
            "_coerce_kind",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
