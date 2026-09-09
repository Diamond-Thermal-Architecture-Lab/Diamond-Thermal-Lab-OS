from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from labos.engineering import (
    CompilationFailure,
    QuantityKind,
    compile_engineering_problem,
    write_engineering_problem,
)
from tests.test_m16a_epr_schema import base_problem, envelope, missing_envelope


def authoring(case_id: str) -> dict:
    persisted = base_problem()
    persisted["case_id"] = case_id
    return {
        "problem_id": persisted["problem_id"],
        "case_id": case_id,
        "title": persisted["title"],
        "purpose": persisted["purpose"],
        "selected_source_filenames": [],
        "requirements": copy.deepcopy(persisted["requirements"]),
        "heat_sources": copy.deepcopy(persisted["heat_sources"]),
        "baseline": {
            field: copy.deepcopy(persisted[field])
            for field in ("geometry", "materials", "interfaces", "boundary_conditions")
        },
        "constraints": copy.deepcopy(persisted["constraints"]),
        "candidates": [
            {
                "candidate_id": "CND-001",
                "label": "Normalized baseline",
                "parent_requirement_id": "REQ-001",
                "overrides": [],
            },
            {
                "candidate_id": "CND-002",
                "label": "Thicker spreader variant",
                "parent_requirement_id": "REQ-001",
                "overrides": [{
                    "path": "/geometry/layers/1/thickness",
                    "value": envelope(QuantityKind.LENGTH, "0.2", "mm"),
                }],
            },
        ],
        "confidentiality_level": "public",
    }


def evidence_object(case_id: str, *, evidence_id: str = "EVD-001", status: str = "reviewed", measurements: list[str] | None = None) -> dict:
    return {
        "evidence_format_version": "1.0", "evidence_id": evidence_id,
        "case_id": case_id, "title": "Synthetic public evidence",
        "evidence_type": "measurement" if measurements else "literature",
        "status": status, "evidence_level": "source_documented",
        "source": {"reference": "controlled-public-source", "sha256": None},
        "method_summary": "Public synthetic method and input basis.",
        "applicability": "Compiler validation only.",
        "uncertainty_summary": "No quantitative claim is made.",
        "supports_claim_ids": [], "contradicts_claim_ids": [],
        "measurement_reference_ids": measurements or [],
        "public_summary": "Synthetic public-safe sidecar.",
        "confidentiality_level": "public",
        "reviewed_by": "Independent reviewer" if status == "reviewed" else "",
        "review_notes": "Synthetic validation fixture.",
    }


def measurement_reference(
    case_id: str,
    *,
    evidence_id: str = "EVD-001",
    status: str = "reviewed",
    quantity: str = "power",
    value: int | float | None = 10,
    unit: str | None = "W",
) -> dict:
    return {
        "measurement_format_version": "1.0", "measurement_id": "MSR-001",
        "case_id": case_id, "evidence_id": evidence_id, "status": status,
        "quantity": quantity, "value": value, "unit": unit,
        "sample_id": "ANON-COMPILER-001", "method": "Synthetic measurement method.",
        "operating_conditions": "Synthetic ambient conditions.",
        "uncertainty": {"numeric_value": 0.1, "unit": "W", "basis": "Synthetic bound."},
        "raw_data_reference": "controlled-public-data", "raw_data_sha256": None,
        "confidentiality_level": "public",
        "reviewed_by": "Independent reviewer" if status == "reviewed" else "",
        "review_notes": "Synthetic validation fixture.",
    }


class CompilerCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.case = self.root / "compiler-case"
        self.case.mkdir()
        self.intake = self.case / "00_problem_intake.yml"
        self.intake.write_bytes(b"case_id: compiler-case\n")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def compile(self, value: dict | None = None):
        return compile_engineering_problem(self.case, value or authoring(self.case.name))

    def write_json(self, relative: str, value: dict) -> tuple[Path, str]:
        path = self.case / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
        path.write_bytes(data)
        return path, hashlib.sha256(data).hexdigest()


class SourceAcceptanceTests(CompilerCase):
    def test_src_01_mandatory_intake_exact_bytes_are_recorded(self) -> None:
        result = self.compile()
        self.assertEqual(
            result.source_case_sha256,
            {"00_problem_intake.yml": hashlib.sha256(self.intake.read_bytes()).hexdigest()},
        )

    def test_src_02_selected_additional_source_changes_identity(self) -> None:
        extra = self.case / "05_red_flags.md"
        extra.write_bytes(b"# Public red flags\n")
        raw = authoring(self.case.name)
        raw["selected_source_filenames"] = ["05_red_flags.md"]
        first = self.compile(raw)
        extra.write_bytes(b"# Changed public red flags\n")
        second = self.compile(raw)
        self.assertNotEqual(first.source_case_sha256["05_red_flags.md"], second.source_case_sha256["05_red_flags.md"])
        self.assertNotEqual(first.engineering_problem.content_sha256, second.engineering_problem.content_sha256)

    def test_src_03_unselected_file_has_no_source_authority(self) -> None:
        unrelated = self.case / "notes.txt"
        unrelated.write_text("one", encoding="utf-8")
        first = self.compile()
        unrelated.write_text("two", encoding="utf-8")
        second = self.compile()
        self.assertEqual(first.source_case_sha256, second.source_case_sha256)
        self.assertEqual(first.canonical_bytes, second.canonical_bytes)

    def test_src_04_unsafe_references_are_rejected(self) -> None:
        for reference in (str(self.intake.resolve()), ".. /bad".replace(" ", ""), "folder\\file", "not-canonical.md"):
            raw = authoring(self.case.name)
            raw["selected_source_filenames"] = [reference]
            with self.subTest(reference=reference), self.assertRaises(CompilationFailure):
                self.compile(raw)
        link = self.case / "05_red_flags.md"
        try:
            link.symlink_to(self.intake)
        except OSError:
            return
        raw = authoring(self.case.name)
        raw["selected_source_filenames"] = [link.name]
        with self.assertRaises(CompilationFailure):
            self.compile(raw)

    def test_src_05_missing_intake_and_case_mismatches_do_not_emit(self) -> None:
        self.intake.unlink()
        with self.assertRaises(CompilationFailure):
            self.compile()
        self.intake.write_text("case_id: other-case\n", encoding="utf-8")
        with self.assertRaises(CompilationFailure):
            self.compile()
        self.intake.write_text("case_id: compiler-case\n", encoding="utf-8")
        raw = authoring("other-case")
        with self.assertRaises(CompilationFailure):
            self.compile(raw)
        self.assertFalse((self.case / "engineering").exists())

    def test_source_change_after_compile_aborts_writer_without_epr(self) -> None:
        result = self.compile()
        self.intake.write_bytes(b"case_id: compiler-case\n# changed\n")
        with self.assertRaisesRegex(CompilationFailure, "M16A-EPR-SOURCE-004"):
            write_engineering_problem(result)
        self.assertFalse((self.case / "engineering").exists())


class OutcomeAcceptanceTests(CompilerCase):
    def test_cmp_01_required_missing_holds_with_deterministic_unknown(self) -> None:
        raw = authoring(self.case.name)
        raw["heat_sources"][0]["total_power"] = missing_envelope(QuantityKind.POWER, "W")
        raw["heat_sources"][0]["heat_flux"] = missing_envelope(QuantityKind.HEAT_FLUX, "W/m^2")
        result = self.compile(raw).engineering_problem.to_dict()
        self.assertEqual(result["compilation"]["outcome"], "HOLD_FOR_INPUT")
        paths = [(item["unknown_id"], item["field_path"]) for item in result["unknowns"]]
        self.assertIn(("UNK-001", "/heat_sources/0/heat_flux"), paths)

    def test_cmp_02_heat_conflict_fails_with_stable_rule(self) -> None:
        raw = authoring(self.case.name)
        raw["heat_sources"][0]["total_power"] = envelope(QuantityKind.POWER, "11", "W")
        result = self.compile(raw).engineering_problem.to_dict()
        self.assertEqual(result["compilation"]["outcome"], "FAIL")
        self.assertIn("M16A-EPR-HEAT-001", [item["rule_id"] for item in result["compilation"]["blocking_findings"]])

    def test_heat_consistency_uses_inclusive_exact_decimal_tolerance(self) -> None:
        raw = authoring(self.case.name)
        raw["heat_sources"][0]["total_power"] = envelope(QuantityKind.POWER, "9.99", "W")
        self.assertEqual(self.compile(raw).engineering_problem.to_dict()["compilation"]["outcome"], "READY")
        raw["heat_sources"][0]["total_power"] = envelope(QuantityKind.POWER, "9.989", "W")
        self.assertEqual(self.compile(raw).engineering_problem.to_dict()["compilation"]["outcome"], "FAIL")

    def test_cmp_03_complete_assumption_is_explicit(self) -> None:
        raw = authoring(self.case.name)
        raw["baseline"]["materials"][0]["thermal_properties"][0]["thermal_conductivity"] = envelope(
            QuantityKind.THERMAL_CONDUCTIVITY, "100", "W/(m*K)", status="assumed", source_type="assumption"
        )
        result = self.compile(raw).engineering_problem.to_dict()
        path = "/materials/0/thermal_properties/0/thermal_conductivity"
        self.assertEqual(result["compilation"]["outcome"], "READY_WITH_ASSUMPTIONS")
        self.assertIn(path, result["compilation"]["assumptions_present"])

    def test_cmp_04_complete_evidence_disposed_problem_is_ready_and_warnings_do_not_hold(self) -> None:
        result = self.compile().engineering_problem.to_dict()
        self.assertEqual(result["compilation"]["outcome"], "READY")
        self.assertTrue(result["compilation"]["warnings"])


class CandidateAcceptanceTests(CompilerCase):
    def test_cnd_01_and_02_complete_deterministic_baseline_and_variant(self) -> None:
        first = self.compile().engineering_problem.to_dict()
        second = self.compile().engineering_problem.to_dict()
        baseline, variant = first["candidates"]
        self.assertEqual(baseline["candidate_role"], "baseline")
        self.assertEqual(baseline["changed_field_paths"], [])
        for field in ("geometry", "materials", "interfaces", "boundary_conditions"):
            self.assertEqual(baseline[field], first[field])
        self.assertEqual(variant["changed_field_paths"], ["/geometry/layers/1/thickness"])
        self.assertEqual(variant["resolved_content_sha256"], second["candidates"][1]["resolved_content_sha256"])

    def test_cnd_03_missing_duplicate_and_overlapping_targets_fail(self) -> None:
        sets = (
            [{"path": "/geometry/missing", "value": "x"}],
            [{"path": "/geometry/~2invalid", "value": "x"}],
            [{"path": "/geometry/source_to_sink_direction", "value": "+x"}] * 2,
            [{"path": "/geometry", "value": "not-a-geometry-object"}],
            [
                {"path": "/geometry", "value": authoring(self.case.name)["baseline"]["geometry"]},
                {"path": "/geometry/source_to_sink_direction", "value": "+x"},
            ],
        )
        for overrides in sets:
            raw = authoring(self.case.name)
            raw["candidates"][1]["overrides"] = overrides
            with self.subTest(overrides=overrides), self.assertRaisesRegex(CompilationFailure, "M16A-EPR-CND-003"):
                self.compile(raw)
            self.assertFalse((self.case / "engineering").exists())

    def test_cnd_04_authoring_mutation_after_compile_is_detached(self) -> None:
        raw = authoring(self.case.name)
        result = self.compile(raw)
        before = result.canonical_bytes
        raw["baseline"]["geometry"]["layers"][0]["role"] = "mutated"
        self.assertEqual(result.canonical_bytes, before)

    def test_cnd_05_inherited_states_are_explicit(self) -> None:
        raw = authoring(self.case.name)
        raw["baseline"]["materials"][0]["thermal_properties"][0]["thermal_conductivity"] = envelope(
            QuantityKind.THERMAL_CONDUCTIVITY, "100", "W/(m*K)", status="assumed", source_type="assumption"
        )
        result = self.compile(raw).engineering_problem.to_dict()
        path = "/materials/0/thermal_properties/0/thermal_conductivity"
        self.assertEqual(result["candidates"][0]["assumption_paths"], [path])
        self.assertEqual(result["candidates"][1]["assumption_paths"], [path])

    def test_cnd_06_raw_collection_order_has_no_pointer_authority(self) -> None:
        one = authoring(self.case.name)
        one["candidates"][1]["overrides"] = [{
            "path": "/materials/1/thermal_properties/0/thermal_conductivity",
            "value": envelope(QuantityKind.THERMAL_CONDUCTIVITY, "120", "W/(m*K)"),
        }]
        two = copy.deepcopy(one)
        two["baseline"]["materials"].reverse()
        first = self.compile(one).engineering_problem.to_dict()["candidates"][1]
        second = self.compile(two).engineering_problem.to_dict()["candidates"][1]
        self.assertEqual(first, second)

    def test_membership_change_requires_whole_array_replacement(self) -> None:
        raw = authoring(self.case.name)
        extra = copy.deepcopy(raw["baseline"]["materials"][1])
        extra["material_id"] = "MAT-003"
        extra["thermal_properties"][0]["property_id"] = "PRP-003"
        raw["candidates"][1]["overrides"] = [{"path": "/materials", "value": raw["baseline"]["materials"] + [extra]}]
        candidate = self.compile(raw).engineering_problem.to_dict()["candidates"][1]
        self.assertEqual(candidate["changed_field_paths"], ["/materials"])
        self.assertEqual(len(candidate["materials"]), 3)


class SeparationAndWriterAcceptanceTests(CompilerCase):
    def test_sep_01_unequal_footprints_compile(self) -> None:
        self.assertEqual(self.compile().engineering_problem.to_dict()["compilation"]["outcome"], "READY")

    def test_sep_02_multiple_volumetric_sources_compile(self) -> None:
        raw = authoring(self.case.name)
        second = copy.deepcopy(raw["heat_sources"][0])
        second["source_id"] = "HSR-002"
        second["source_location"] = {"layer_id": "LYR-002", "location_type": "named_region", "region_name": "public synthetic region"}
        second["spatial_profile"] = "volumetric"
        raw["heat_sources"].append(second)
        self.assertEqual(self.compile(raw).engineering_problem.to_dict()["compilation"]["outcome"], "READY")

    def test_sep_03_rotated_anisotropy_direct_convection_area_mismatch_compile(self) -> None:
        raw = authoring(self.case.name)
        raw["baseline"]["materials"][0]["anisotropy_representation"] = "rotated_tensor"
        raw["baseline"]["materials"][0]["thermal_properties"][0]["component"] = "other"
        raw["baseline"]["boundary_conditions"]["downstream"] = {
            "representation_type": "direct_convection",
            "heat_transfer_coefficient": envelope(QuantityKind.AREA_THERMAL_CONDUCTANCE, "100", "W/(m^2*K)"),
            "boundary_area": envelope(QuantityKind.AREA, "99", "mm^2"),
            "ambient_temperature": envelope(QuantityKind.ABSOLUTE_TEMPERATURE, "300", "K"),
            "operating_basis": "Synthetic direct convection boundary.",
        }
        self.assertEqual(self.compile(raw).engineering_problem.to_dict()["compilation"]["outcome"], "READY")

    def test_safe_01_free_text_does_not_create_numeric_defaults(self) -> None:
        raw = authoring(self.case.name)
        raw["baseline"]["materials"][0]["label"] = "diamond conductivity 2000 W/mK"
        raw["baseline"]["materials"][0]["thermal_properties"][0]["thermal_conductivity"] = missing_envelope(QuantityKind.THERMAL_CONDUCTIVITY, "W/(m*K)")
        result = self.compile(raw).engineering_problem.to_dict()
        quantity = result["materials"][0]["thermal_properties"][0]["thermal_conductivity"]
        self.assertIsNone(quantity["value"])
        self.assertEqual(result["compilation"]["outcome"], "HOLD_FOR_INPUT")

    def test_safe_02_different_existing_bytes_are_refused_and_identical_is_idempotent(self) -> None:
        result = self.compile()
        target = write_engineering_problem(result)
        self.assertEqual(write_engineering_problem(result), target)
        target.write_bytes(b"different\n")
        with self.assertRaises(CompilationFailure):
            write_engineering_problem(result)
        self.assertEqual(target.read_bytes(), b"different\n")

    def test_safe_03_writer_changes_no_canonical_file(self) -> None:
        before = self.intake.read_bytes()
        target = write_engineering_problem(self.compile())
        self.assertEqual(target, self.case / "engineering" / "problems" / "EPR-001.json")
        self.assertEqual(self.intake.read_bytes(), before)
        self.assertEqual({path.name for path in self.case.iterdir()}, {"00_problem_intake.yml", "engineering"})

    def test_target_and_parent_symlinks_are_rejected(self) -> None:
        result = self.compile()
        outside = self.root / "outside"
        outside.mkdir()
        engineering = self.case / "engineering"
        try:
            engineering.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("symlink creation is unavailable")
        with self.assertRaises(CompilationFailure):
            write_engineering_problem(result)

    def test_target_symlink_is_rejected(self) -> None:
        result = self.compile()
        problems = self.case / "engineering" / "problems"
        problems.mkdir(parents=True)
        outside = self.root / "outside.json"
        outside.write_bytes(b"outside\n")
        target = problems / "EPR-001.json"
        try:
            target.symlink_to(outside)
        except OSError:
            self.skipTest("symlink creation is unavailable")
        with self.assertRaises(CompilationFailure):
            write_engineering_problem(result)
        self.assertEqual(outside.read_bytes(), b"outside\n")


class StructuralPolicyAcceptanceTests(CompilerCase):
    def test_constraint_length_target_and_length_threshold_are_compatible(self) -> None:
        raw = authoring(self.case.name)
        raw["constraints"][0]["operator"] = "le"
        raw["constraints"][0]["threshold"] = envelope(QuantityKind.LENGTH, "0.2", "mm")
        result = self.compile(raw).engineering_problem.to_dict()
        self.assertEqual(result["compilation"]["outcome"], "READY")
        self.assertNotIn("M16A-EPR-QTY-004", [item["rule_id"] for item in result["compilation"]["blocking_findings"]])

    def test_constraint_length_target_and_power_threshold_fail_dimensionally(self) -> None:
        raw = authoring(self.case.name)
        raw["constraints"][0]["operator"] = "le"
        raw["constraints"][0]["threshold"] = envelope(QuantityKind.POWER, "1", "W")
        result = self.compile(raw).engineering_problem.to_dict()
        self.assertEqual(result["compilation"]["outcome"], "FAIL")
        self.assertIn("M16A-EPR-QTY-004", [item["rule_id"] for item in result["compilation"]["blocking_findings"]])

    def test_review_only_null_threshold_remains_valid(self) -> None:
        result = self.compile().engineering_problem.to_dict()
        self.assertEqual(result["constraints"][0]["operator"], "review_only")
        self.assertIsNone(result["constraints"][0]["threshold"])
        self.assertNotIn("M16A-EPR-QTY-004", [item["rule_id"] for item in result["compilation"]["blocking_findings"]])

    def test_generic_dimensionless_value_above_one_is_not_globally_clamped(self) -> None:
        raw = authoring(self.case.name)
        raw["requirements"][0]["target"] = envelope(QuantityKind.PHYSICAL_DIMENSIONLESS, "1.5", "1")
        raw["constraints"][0]["target_path"] = "/boundary_conditions/source_side/heat_flow_fraction"
        raw["constraints"][0]["operator"] = "le"
        raw["constraints"][0]["threshold"] = envelope(QuantityKind.PHYSICAL_DIMENSIONLESS, "1.5", "1")
        self.assertEqual(self.compile(raw).engineering_problem.to_dict()["compilation"]["outcome"], "READY")

    def test_generic_dimensionless_negative_value_is_not_globally_rejected(self) -> None:
        raw = authoring(self.case.name)
        raw["requirements"][0]["target"] = envelope(QuantityKind.PHYSICAL_DIMENSIONLESS, "-0.5", "1")
        raw["constraints"][0]["target_path"] = "/boundary_conditions/source_side/heat_flow_fraction"
        raw["constraints"][0]["operator"] = "ge"
        raw["constraints"][0]["threshold"] = envelope(QuantityKind.PHYSICAL_DIMENSIONLESS, "-0.5", "1")
        self.assertEqual(self.compile(raw).engineering_problem.to_dict()["compilation"]["outcome"], "READY")

    def test_heat_flow_fraction_range_applies_to_provided_and_assumed(self) -> None:
        for value in ("-0.1", "1.1"):
            for status in ("provided", "assumed"):
                raw = authoring(self.case.name)
                raw["baseline"]["boundary_conditions"]["source_side"]["heat_flow_fraction"] = envelope(
                    QuantityKind.PHYSICAL_DIMENSIONLESS, value, "1", status=status,
                    source_type="assumption" if status == "assumed" else "synthetic_fixture",
                )
                with self.subTest(value=value, status=status):
                    result = self.compile(raw).engineering_problem.to_dict()
                    self.assertEqual(result["compilation"]["outcome"], "FAIL")
                    self.assertIn("M16A-EPR-QTY-003", [item["rule_id"] for item in result["compilation"]["blocking_findings"]])

    def test_duty_cycle_range_applies_to_provided_and_assumed(self) -> None:
        for value in ("-0.1", "1.1"):
            for status in ("provided", "assumed"):
                raw = authoring(self.case.name)
                raw["heat_sources"][0]["duty_cycle"] = envelope(
                    QuantityKind.PHYSICAL_DIMENSIONLESS, value, "1", status=status,
                    source_type="assumption" if status == "assumed" else "synthetic_fixture",
                )
                with self.subTest(value=value, status=status):
                    result = self.compile(raw).engineering_problem.to_dict()
                    self.assertEqual(result["compilation"]["outcome"], "FAIL")
                    self.assertIn("M16A-EPR-QTY-003", [item["rule_id"] for item in result["compilation"]["blocking_findings"]])


class EvidenceRealityAcceptanceTests(CompilerCase):
    def set_provenance(self, raw: dict, source_type: str, reference: str, digest: str, *, evd: str = "EVD-001", review: str = "reviewed") -> None:
        provenance = {
            "source_type": source_type, "reference": reference,
            "evidence_object_ids": [evd],
            "measurement_reference_ids": ["MSR-001"] if source_type == "measurement_reference" else [],
            "source_sha256": digest, "review_status": review, "rationale": None,
        }
        raw["heat_sources"][0]["total_power"]["provenance"] = provenance

    def test_valid_evd_provenance(self) -> None:
        _, digest = self.write_json("evidence/EVD-001.json", evidence_object(self.case.name))
        raw = authoring(self.case.name)
        self.set_provenance(raw, "evidence_object", "evidence/EVD-001.json", digest)
        self.assertEqual(self.compile(raw).engineering_problem.to_dict()["compilation"]["outcome"], "READY")

    def test_valid_msr_and_owning_evd_provenance(self) -> None:
        self.write_json("evidence/EVD-001.json", evidence_object(self.case.name, measurements=["MSR-001"]))
        _, digest = self.write_json("measurements/MSR-001.json", measurement_reference(self.case.name))
        raw = authoring(self.case.name)
        self.set_provenance(raw, "measurement_reference", "measurements/MSR-001.json", digest)
        self.assertEqual(self.compile(raw).engineering_problem.to_dict()["compilation"]["outcome"], "READY")

    def test_msr_equivalent_units_bind_through_i1_numeric_identity(self) -> None:
        self.write_json("evidence/EVD-001.json", evidence_object(self.case.name, measurements=["MSR-001"]))
        _, digest = self.write_json(
            "measurements/MSR-001.json",
            measurement_reference(self.case.name, value=10000, unit="mW"),
        )
        raw = authoring(self.case.name)
        self.set_provenance(raw, "measurement_reference", "measurements/MSR-001.json", digest)
        self.assertEqual(self.compile(raw).engineering_problem.to_dict()["compilation"]["outcome"], "READY")

    def test_msr_numeric_mismatch_cannot_be_ready(self) -> None:
        self.write_json("evidence/EVD-001.json", evidence_object(self.case.name, measurements=["MSR-001"]))
        _, digest = self.write_json("measurements/MSR-001.json", measurement_reference(self.case.name, value=11))
        raw = authoring(self.case.name)
        self.set_provenance(raw, "measurement_reference", "measurements/MSR-001.json", digest)
        self.assert_provenance_failure(raw)

    def test_msr_quantity_kind_mismatch_cannot_be_ready(self) -> None:
        self.write_json("evidence/EVD-001.json", evidence_object(self.case.name, measurements=["MSR-001"]))
        _, digest = self.write_json(
            "measurements/MSR-001.json",
            measurement_reference(self.case.name, quantity="length", value=10, unit="mm"),
        )
        raw = authoring(self.case.name)
        self.set_provenance(raw, "measurement_reference", "measurements/MSR-001.json", digest)
        self.assert_provenance_failure(raw)

    def test_reviewed_msr_with_draft_owning_evd_cannot_be_reviewed(self) -> None:
        self.write_json(
            "evidence/EVD-001.json",
            evidence_object(self.case.name, status="draft", measurements=["MSR-001"]),
        )
        _, digest = self.write_json("measurements/MSR-001.json", measurement_reference(self.case.name))
        raw = authoring(self.case.name)
        self.set_provenance(raw, "measurement_reference", "measurements/MSR-001.json", digest)
        self.assert_provenance_failure(raw)

    def test_deprecated_owning_evd_cannot_support_provided_ready_value(self) -> None:
        self.write_json(
            "evidence/EVD-001.json",
            evidence_object(self.case.name, status="deprecated", measurements=["MSR-001"]),
        )
        _, digest = self.write_json("measurements/MSR-001.json", measurement_reference(self.case.name))
        raw = authoring(self.case.name)
        self.set_provenance(raw, "measurement_reference", "measurements/MSR-001.json", digest, review="unverified")
        self.assert_provenance_failure(raw)

    def test_direct_deprecated_evd_cannot_support_provided_ready_value(self) -> None:
        _, digest = self.write_json(
            "evidence/EVD-001.json",
            evidence_object(self.case.name, status="deprecated"),
        )
        raw = authoring(self.case.name)
        self.set_provenance(raw, "evidence_object", "evidence/EVD-001.json", digest, review="unverified")
        self.assert_provenance_failure(raw)

    def test_planned_msr_without_numeric_value_cannot_substantiate_provided_value(self) -> None:
        self.write_json("evidence/EVD-001.json", evidence_object(self.case.name, measurements=["MSR-001"]))
        _, digest = self.write_json(
            "measurements/MSR-001.json",
            measurement_reference(self.case.name, status="planned", value=None, unit=None),
        )
        raw = authoring(self.case.name)
        self.set_provenance(raw, "measurement_reference", "measurements/MSR-001.json", digest, review="unverified")
        self.assert_provenance_failure(raw)

    def test_stale_evidence_parent_symlink_is_rejected_even_with_same_bytes(self) -> None:
        _, digest = self.write_json("evidence/EVD-001.json", evidence_object(self.case.name))
        raw = authoring(self.case.name)
        self.set_provenance(raw, "evidence_object", "evidence/EVD-001.json", digest)
        result = self.compile(raw)
        evidence = self.case / "evidence"
        relocated = self.case / "relocated-evidence"
        evidence.rename(relocated)
        try:
            evidence.symlink_to(relocated, target_is_directory=True)
        except OSError:
            self.skipTest("symlink creation is unavailable")
        with self.assertRaisesRegex(CompilationFailure, "M16A-EPR-SOURCE-004"):
            write_engineering_problem(result)
        self.assertFalse((self.case / "engineering" / "problems" / "EPR-001.json").exists())

    def test_stale_measurement_parent_symlink_is_rejected_even_with_same_bytes(self) -> None:
        self.write_json("evidence/EVD-001.json", evidence_object(self.case.name, measurements=["MSR-001"]))
        _, digest = self.write_json("measurements/MSR-001.json", measurement_reference(self.case.name))
        raw = authoring(self.case.name)
        self.set_provenance(raw, "measurement_reference", "measurements/MSR-001.json", digest)
        result = self.compile(raw)
        measurements = self.case / "measurements"
        relocated = self.case / "relocated-measurements"
        measurements.rename(relocated)
        try:
            measurements.symlink_to(relocated, target_is_directory=True)
        except OSError:
            self.skipTest("symlink creation is unavailable")
        with self.assertRaisesRegex(CompilationFailure, "M16A-EPR-SOURCE-004"):
            write_engineering_problem(result)
        self.assertFalse((self.case / "engineering" / "problems" / "EPR-001.json").exists())

    def assert_provenance_failure(self, raw: dict) -> None:
        result = self.compile(raw).engineering_problem.to_dict()
        self.assertEqual(result["compilation"]["outcome"], "FAIL")
        self.assertIn("M16A-EPR-PROV-001", [item["rule_id"] for item in result["compilation"]["blocking_findings"]])

    def test_evd_wrong_case_fails(self) -> None:
        _, digest = self.write_json("evidence/EVD-001.json", evidence_object("wrong-case"))
        raw = authoring(self.case.name)
        self.set_provenance(raw, "evidence_object", "evidence/EVD-001.json", digest)
        self.assert_provenance_failure(raw)

    def test_evd_missing_source_fails(self) -> None:
        raw = authoring(self.case.name)
        self.set_provenance(raw, "evidence_object", "evidence/EVD-001.json", "0" * 64)
        self.assert_provenance_failure(raw)

    def test_evd_bad_exact_byte_hash_fails(self) -> None:
        self.write_json("evidence/EVD-001.json", evidence_object(self.case.name))
        raw = authoring(self.case.name)
        self.set_provenance(raw, "evidence_object", "evidence/EVD-001.json", "0" * 64)
        self.assert_provenance_failure(raw)

    def test_msr_wrong_evd_linkage_fails(self) -> None:
        self.write_json("evidence/EVD-001.json", evidence_object(self.case.name, measurements=["MSR-001"]))
        _, digest = self.write_json("measurements/MSR-001.json", measurement_reference(self.case.name, evidence_id="EVD-002"))
        raw = authoring(self.case.name)
        self.set_provenance(raw, "measurement_reference", "measurements/MSR-001.json", digest)
        self.assert_provenance_failure(raw)

    def test_msr_review_status_overclaim_fails(self) -> None:
        self.write_json("evidence/EVD-001.json", evidence_object(self.case.name, measurements=["MSR-001"]))
        _, digest = self.write_json("measurements/MSR-001.json", measurement_reference(self.case.name, status="completed"))
        raw = authoring(self.case.name)
        self.set_provenance(raw, "measurement_reference", "measurements/MSR-001.json", digest)
        self.assert_provenance_failure(raw)


if __name__ == "__main__":
    unittest.main()
