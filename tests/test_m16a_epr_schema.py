from __future__ import annotations

import copy
import json
import unittest
from unittest.mock import patch

from labos.engineering import (
    CANDIDATE_CONTENT_IDENTITY_VERSION,
    COMPILER_POLICY_VERSION,
    EPR_CONTENT_IDENTITY_VERSION,
    HEAT_SOURCE_CONSISTENCY_POLICY_VERSION,
    PROBLEM_FORMAT_VERSION,
    EngineeringProblem,
    EngineeringProblemValidationError,
    QuantityKind,
    candidate_content_sha256,
    canonical_json_bytes,
    convert_quantity,
    engineering_problem_content_sha256,
)


ZERO_HASH = "0" * 64
SOURCE_HASH = "1" * 64


def provenance(source_type: str = "synthetic_fixture") -> dict:
    return {
        "source_type": source_type,
        "reference": "fixtures/m16a-i2a-inline",
        "evidence_object_ids": [],
        "measurement_reference_ids": [],
        "source_sha256": None,
        "review_status": "not_applicable",
        "rationale": None,
    }


def helper(kind: QuantityKind, value: str, unit: str) -> dict:
    quantity = convert_quantity(kind, value, unit)
    data = quantity.to_dict()
    return {
        "value": data["canonical_value"],
        "unit": data["canonical_unit"],
        "quantity_kind": data["quantity_kind"],
        "conversion": data["conversion"],
    }


def envelope(
    kind: QuantityKind,
    value: str,
    unit: str,
    *,
    uncertainty: dict | None = None,
    status: str = "provided",
    source_type: str = "synthetic_fixture",
) -> dict:
    quantity = helper(kind, value, unit)
    result = {
        **quantity,
        "provenance": provenance(source_type),
        "uncertainty": uncertainty or {"kind": "not_provided", "basis": "No numeric uncertainty supplied."},
        "confidence": "high",
        "status": status,
    }
    if status == "assumed":
        result["provenance"]["rationale"] = "Public-safe synthetic assumption."
    return result


def missing_envelope(kind: QuantityKind, unit: str) -> dict:
    return {
        "value": None,
        "unit": unit,
        "quantity_kind": kind.value,
        "provenance": provenance(),
        "uncertainty": {"kind": "not_provided", "basis": "Value is missing."},
        "confidence": "unknown",
        "status": "missing",
        "conversion": None,
    }


def layer(layer_id: str, order: int, material_id: str, side_mm: str = "2") -> dict:
    return {
        "layer_id": layer_id,
        "order": order,
        "role": "device" if order == 0 else "heat spreader",
        "material_id": material_id,
        "thickness": envelope(QuantityKind.LENGTH, "0.1", "mm"),
        "footprint_dimensions": [
            envelope(QuantityKind.LENGTH, side_mm, "mm"),
            envelope(QuantityKind.LENGTH, side_mm, "mm"),
        ],
        "footprint_area": envelope(QuantityKind.AREA, str(int(side_mm) ** 2), "mm^2"),
        "orientation": {"stack_normal_axis": "z", "rotation_description": None},
    }


def material(material_id: str, property_id: str, label: str) -> dict:
    return {
        "material_id": material_id,
        "label": label,
        "material_class": "synthetic solid",
        "anisotropy_representation": "isotropic",
        "thermal_properties": [{
            "property_id": property_id,
            "component": "isotropic",
            "thermal_conductivity": envelope(QuantityKind.THERMAL_CONDUCTIVITY, "100", "W/(m*K)"),
            "temperature_basis": "Synthetic constant value over the intended range.",
            "condition_basis": "Synthetic fixture only.",
        }],
    }


def base_problem() -> dict:
    geometry = {
        "stack_id": "STK-001",
        "source_to_sink_direction": "+z",
        "layers": [
            layer("LYR-001", 0, "MAT-001", "2"),
            layer("LYR-002", 1, "MAT-002", "3"),
        ],
    }
    materials = [
        material("MAT-001", "PRP-001", "Synthetic device layer"),
        material("MAT-002", "PRP-002", "Synthetic spreader layer"),
    ]
    interfaces = [{
        "interface_id": "IFC-001",
        "upstream_layer_id": "LYR-001",
        "downstream_layer_id": "LYR-002",
        "representation_type": "area_normalized_resistance",
        "value": envelope(QuantityKind.AREA_THERMAL_RESISTANCE, "0.001", "mm^2*K/W"),
        "effective_area": envelope(QuantityKind.AREA, "4", "mm^2"),
        "condition_basis": "Synthetic fixture only.",
    }]
    boundary = {
        "source_side": {
            "heat_flow_fraction": envelope(QuantityKind.PHYSICAL_DIMENSIONLESS, "1", "1"),
            "path_disposition": "adiabatic_other_paths",
        },
        "downstream": {
            "representation_type": "fixed_temperature",
            "terminal_plane": "sink-side face of LYR-002",
            "reference_temperature": envelope(QuantityKind.ABSOLUTE_TEMPERATURE, "300", "K"),
        },
    }
    problem = {
        "problem_format_version": PROBLEM_FORMAT_VERSION,
        "problem_id": "EPR-001",
        "case_id": "synthetic-i2a-case",
        "title": "Synthetic persisted EPR",
        "purpose": "Exercise the public-safe I2A persisted contract.",
        "source_case_sha256": {"00_problem_intake.yml": SOURCE_HASH},
        "requirements": [{
            "requirement_id": "REQ-001",
            "description": "Represent the first layer thickness explicitly.",
            "target_path": "/geometry/layers/0/thickness",
            "target": envelope(QuantityKind.LENGTH, "0.1", "mm"),
            "provenance": provenance("requirement"),
        }],
        "heat_sources": [{
            "source_id": "HSR-001",
            "source_location": {"layer_id": "LYR-001", "location_type": "source_side", "region_name": None},
            "total_power": envelope(QuantityKind.POWER, "10", "W"),
            "heat_flux": envelope(QuantityKind.HEAT_FLUX, "2.5", "W/mm^2"),
            "footprint": {
                "shape": "rectangle",
                "dimensions": [envelope(QuantityKind.LENGTH, "2", "mm"), envelope(QuantityKind.LENGTH, "2", "mm")],
                "profile_reference": None,
            },
            "heated_area": envelope(QuantityKind.AREA, "4", "mm^2"),
            "spatial_profile": "uniform_surface",
            "operating_mode": "steady_state",
            "duty_cycle": None,
        }],
        "geometry": geometry,
        "materials": materials,
        "interfaces": interfaces,
        "boundary_conditions": boundary,
        "constraints": [{
            "constraint_id": "CON-001",
            "target_path": "/geometry/layers/0/thickness",
            "operator": "review_only",
            "threshold": None,
            "severity": "advisory",
            "provenance": provenance("requirement"),
            "evaluation_disposition": "review_required",
        }],
        "candidates": [],
        "unknowns": [],
        "compilation": {
            "compiler_policy_version": COMPILER_POLICY_VERSION,
            "unit_registry_version": "m16a-unit-registry-1.0",
            "canonical_json_version": "m16a-canonical-json-1.0",
            "heat_source_consistency_policy_version": HEAT_SOURCE_CONSISTENCY_POLICY_VERSION,
            "outcome": "READY",
            "blocking_findings": [],
            "non_blocking_findings": [],
            "warnings": [],
            "assumptions_present": [],
            "assumptions_requiring_later_acknowledgement": [],
        },
        "confidentiality_level": "public",
        "compiled_content_sha256": ZERO_HASH,
    }
    baseline = {
        "candidate_id": "CND-001",
        "candidate_role": "baseline",
        "label": "Normalized baseline",
        "parent_requirement_id": "REQ-001",
        "geometry": copy.deepcopy(geometry),
        "materials": copy.deepcopy(materials),
        "interfaces": copy.deepcopy(interfaces),
        "boundary_conditions": copy.deepcopy(boundary),
        "changed_field_paths": [],
        "applicable_constraint_ids": ["CON-001"],
        "assumption_paths": [],
        "evidence_required_paths": [],
        "resolved_content_sha256": ZERO_HASH,
    }
    variant = copy.deepcopy(baseline)
    variant.update({
        "candidate_id": "CND-002",
        "candidate_role": "variant",
        "label": "Thicker spreader variant",
        "changed_field_paths": ["/geometry/layers/1/thickness"],
    })
    variant["geometry"]["layers"][1]["thickness"] = envelope(QuantityKind.LENGTH, "0.2", "mm")
    for candidate in (baseline, variant):
        candidate["resolved_content_sha256"] = candidate_content_sha256(candidate)
    problem["candidates"] = [baseline, variant]
    problem["compiled_content_sha256"] = engineering_problem_content_sha256(problem)
    return problem


def restamp(problem: dict) -> dict:
    for candidate in problem["candidates"]:
        candidate["resolved_content_sha256"] = candidate_content_sha256(candidate)
    problem["compiled_content_sha256"] = engineering_problem_content_sha256(problem)
    return problem


class M16AEPRSchemaTests(unittest.TestCase):
    def test_sch_01_valid_minimal_complete_epr_and_schema_identity(self) -> None:
        with open("labos/schemas/engineering_problem.schema.json", encoding="utf-8") as stream:
            schema = json.load(stream)
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["$id"], "labos/engineering_problem.schema.json")
        self.assertEqual(schema["properties"]["problem_format_version"]["const"], PROBLEM_FORMAT_VERSION)
        self.assertIn("quantified_value_envelope", schema["$defs"])
        self.assertEqual(set(schema["properties"]), {
            "problem_format_version", "problem_id", "case_id", "title", "purpose",
            "source_case_sha256", "requirements", "heat_sources", "geometry",
            "materials", "interfaces", "boundary_conditions", "constraints",
            "candidates", "unknowns", "compilation", "confidentiality_level",
            "compiled_content_sha256",
        })
        reconstructed = EngineeringProblem.from_dict(base_problem())
        self.assertEqual(reconstructed.problem_id, "EPR-001")
        self.assertEqual(reconstructed.to_dict(), base_problem())

    def test_sch_02_exact_version_and_ids(self) -> None:
        for field, invalid in (("problem_format_version", "1.0"), ("problem_id", "EPR-1"), ("case_id", "../case")):
            value = base_problem()
            value[field] = invalid
            restamp(value)
            with self.subTest(field=field), self.assertRaises(EngineeringProblemValidationError):
                EngineeringProblem.from_dict(value)

    def test_sch_03_missing_and_unknown_fields_are_rejected(self) -> None:
        missing = base_problem()
        del missing["purpose"]
        with self.assertRaises(EngineeringProblemValidationError):
            EngineeringProblem.from_dict(missing)
        nested = base_problem()
        nested["geometry"]["unexpected"] = True
        restamp(nested)
        with self.assertRaises(EngineeringProblemValidationError):
            EngineeringProblem.from_dict(nested)


class M16AEPRQuantityAndUncertaintyTests(unittest.TestCase):
    def test_qty_01_json_number_invalid_unit_kind_and_forged_conversion(self) -> None:
        mutators = (
            lambda q: q.update(value=1.0),
            lambda q: q.update(unit="mm"),
            lambda q: q.update(quantity_kind="area"),
            lambda q: q["conversion"].update(conversion_rule_id="M16A-UNIT-FORGED"),
        )
        for mutate in mutators:
            value = base_problem()
            mutate(value["geometry"]["layers"][0]["thickness"])
            value["candidates"][0]["geometry"] = copy.deepcopy(value["geometry"])
            with self.subTest(mutate=mutate), self.assertRaises(EngineeringProblemValidationError):
                EngineeringProblem.from_dict(value)

    def test_qty_02_missing_status_exact_rules(self) -> None:
        value = base_problem()
        missing = missing_envelope(QuantityKind.POWER, "W")
        value["heat_sources"][0]["total_power"] = missing
        restamp(value)
        EngineeringProblem.from_dict(value)
        for field, invalid in (("value", "0"), ("confidence", "low"), ("conversion", helper(QuantityKind.POWER, "0", "W")["conversion"])):
            broken = copy.deepcopy(value)
            broken["heat_sources"][0]["total_power"][field] = invalid
            restamp(broken)
            with self.subTest(field=field), self.assertRaises(EngineeringProblemValidationError):
                EngineeringProblem.from_dict(broken)

    def test_qty_03_assumed_source_and_rationale_rules(self) -> None:
        value = base_problem()
        assumed = envelope(QuantityKind.POWER, "10", "W", status="assumed", source_type="assumption")
        value["heat_sources"][0]["total_power"] = assumed
        restamp(value)
        EngineeringProblem.from_dict(value)
        for change in ("missing_rationale", "wrong_status"):
            broken = copy.deepcopy(value)
            target = broken["heat_sources"][0]["total_power"]
            if change == "missing_rationale":
                target["provenance"]["rationale"] = None
            else:
                target["status"] = "provided"
            restamp(broken)
            with self.subTest(change=change), self.assertRaises(EngineeringProblemValidationError):
                EngineeringProblem.from_dict(broken)

    def test_unc_01_all_five_forms(self) -> None:
        forms = (
            {"kind": "not_provided", "basis": "Not measured."},
            {"kind": "not_applicable", "basis": "Exact synthetic definition."},
            {"kind": "absolute", "basis": "Bound.", "amount": helper(QuantityKind.LENGTH, "0.01", "mm")},
            {"kind": "relative", "basis": "Fraction.", "fraction": helper(QuantityKind.PHYSICAL_DIMENSIONLESS, "0.1", "1")},
            {"kind": "interval", "basis": "Range.", "lower": helper(QuantityKind.LENGTH, "0.09", "mm"), "upper": helper(QuantityKind.LENGTH, "0.11", "mm")},
        )
        for form in forms:
            value = base_problem()
            value["geometry"]["layers"][0]["thickness"]["uncertainty"] = form
            value["candidates"][0]["geometry"] = copy.deepcopy(value["geometry"])
            restamp(value)
            with self.subTest(kind=form["kind"]):
                EngineeringProblem.from_dict(value)

    def test_unc_02_temperature_difference_and_invalid_bounds(self) -> None:
        value = base_problem()
        temperature = value["boundary_conditions"]["downstream"]["reference_temperature"]
        temperature["uncertainty"] = {
            "kind": "absolute", "basis": "Instrument bound.",
            "amount": helper(QuantityKind.TEMPERATURE_DIFFERENCE, "2", "K"),
        }
        value["candidates"][0]["boundary_conditions"] = copy.deepcopy(value["boundary_conditions"])
        restamp(value)
        EngineeringProblem.from_dict(value)

        invalid_forms = (
            {"kind": "absolute", "basis": "Bad.", "amount": helper(QuantityKind.LENGTH, "-0.01", "mm")},
            {"kind": "relative", "basis": "Bad.", "fraction": helper(QuantityKind.PHYSICAL_DIMENSIONLESS, "-0.1", "1")},
            {"kind": "interval", "basis": "Bad.", "lower": helper(QuantityKind.LENGTH, "0.11", "mm"), "upper": helper(QuantityKind.LENGTH, "0.09", "mm")},
            {"kind": "interval", "basis": "Bad.", "lower": helper(QuantityKind.LENGTH, "0.2", "mm"), "upper": helper(QuantityKind.LENGTH, "0.3", "mm")},
        )
        for form in invalid_forms:
            broken = base_problem()
            broken["geometry"]["layers"][0]["thickness"]["uncertainty"] = form
            broken["candidates"][0]["geometry"] = copy.deepcopy(broken["geometry"])
            restamp(broken)
            with self.subTest(kind=form["kind"]), self.assertRaises(EngineeringProblemValidationError):
                EngineeringProblem.from_dict(broken)


class M16AEPRProvenanceTests(unittest.TestCase):
    def test_prov_01_structural_evd_and_msr_combinations(self) -> None:
        valid_evd = provenance("evidence_object")
        valid_evd.update(evidence_object_ids=["EVD-001"], source_sha256="2" * 64)
        valid_msr = provenance("measurement_reference")
        valid_msr.update(evidence_object_ids=["EVD-001"], measurement_reference_ids=["MSR-001"], source_sha256="3" * 64)
        for source in (valid_evd, valid_msr):
            value = base_problem()
            value["heat_sources"][0]["total_power"]["provenance"] = source
            restamp(value)
            EngineeringProblem.from_dict(value)

        invalid = (copy.deepcopy(valid_evd), copy.deepcopy(valid_msr), provenance("literature"))
        invalid[0]["measurement_reference_ids"] = ["MSR-001"]
        invalid[1]["evidence_object_ids"] = []
        invalid[2]["evidence_object_ids"] = ["EVD-001"]
        for source in invalid:
            value = base_problem()
            value["heat_sources"][0]["total_power"]["provenance"] = source
            restamp(value)
            with self.assertRaises(EngineeringProblemValidationError):
                EngineeringProblem.from_dict(value)

    def test_prov_02_reconstruction_does_not_resolve_filesystem_evidence(self) -> None:
        value = base_problem()
        source = provenance("measurement_reference")
        source.update(
            reference="cases/nonexistent/evidence/measurements/MSR-001.json",
            evidence_object_ids=["EVD-999"],
            measurement_reference_ids=["MSR-001"],
            source_sha256="4" * 64,
        )
        value["heat_sources"][0]["total_power"]["provenance"] = source
        restamp(value)
        with patch("pathlib.Path.exists", side_effect=AssertionError("filesystem lookup forbidden")):
            EngineeringProblem.from_dict(value)


class M16AEPRIdentityAndAuthorityTests(unittest.TestCase):
    def test_hash_01_versions_determinism_and_mapping_key_order(self) -> None:
        self.assertEqual(EPR_CONTENT_IDENTITY_VERSION, "m16a-epr-content-identity-1.0")
        self.assertEqual(CANDIDATE_CONTENT_IDENTITY_VERSION, "m16a-candidate-content-identity-1.0")
        first = base_problem()
        second = {key: first[key] for key in reversed(first)}
        one = EngineeringProblem.from_dict(first)
        two = EngineeringProblem.from_dict(second)
        self.assertEqual(one.content_sha256, two.content_sha256)
        self.assertEqual(one.canonical_bytes(), two.canonical_bytes())
        self.assertEqual(candidate_content_sha256(first["candidates"][1]), candidate_content_sha256(second["candidates"][1]))

    def test_hash_02_self_hash_exclusion_and_semantic_changes(self) -> None:
        value = base_problem()
        original_epr = engineering_problem_content_sha256(value)
        value["compiled_content_sha256"] = "f" * 64
        self.assertEqual(engineering_problem_content_sha256(value), original_epr)
        original_candidate = candidate_content_sha256(value["candidates"][1])
        value["candidates"][1]["resolved_content_sha256"] = "e" * 64
        self.assertEqual(candidate_content_sha256(value["candidates"][1]), original_candidate)
        value["title"] = "Semantically changed title"
        self.assertNotEqual(engineering_problem_content_sha256(value), original_epr)
        value["candidates"][1]["label"] = "Semantically changed candidate"
        self.assertNotEqual(candidate_content_sha256(value["candidates"][1]), original_candidate)

    def test_hash_03_forged_supplied_hashes_are_rejected(self) -> None:
        candidate = base_problem()
        candidate["candidates"][1]["resolved_content_sha256"] = "a" * 64
        candidate["compiled_content_sha256"] = engineering_problem_content_sha256(candidate)
        with self.assertRaises(EngineeringProblemValidationError):
            EngineeringProblem.from_dict(candidate)
        problem = base_problem()
        problem["compiled_content_sha256"] = "b" * 64
        with self.assertRaises(EngineeringProblemValidationError):
            EngineeringProblem.from_dict(problem)

    def test_cnd_01_role_count_baseline_mirror_and_changed_paths(self) -> None:
        mutations = (
            lambda p: p["candidates"][1].update(candidate_role="baseline"),
            lambda p: p["candidates"][0]["geometry"]["layers"][0].update(role="different"),
            lambda p: p["candidates"][0].update(changed_field_paths=["/geometry/layers/0/thickness"]),
        )
        for mutate in mutations:
            value = base_problem()
            mutate(value)
            restamp(value)
            with self.subTest(mutate=mutate), self.assertRaises(EngineeringProblemValidationError):
                EngineeringProblem.from_dict(value)

    def test_order_01_noncanonical_persisted_collections_fail(self) -> None:
        mutations = (
            lambda p: p["geometry"]["layers"].reverse(),
            lambda p: p["materials"].reverse(),
            lambda p: p["candidates"].reverse(),
            lambda p: p["candidates"][1].update(changed_field_paths=["/materials", "/geometry"]),
            lambda p: p.update(source_case_sha256={"01_thermal_design_passport.yml": "2" * 64, "00_problem_intake.yml": SOURCE_HASH}),
        )
        for mutate in mutations:
            value = base_problem()
            mutate(value)
            # A reversed top-level baseline is mirrored so the failure is ordering, not equivalence.
            value["candidates"][0]["geometry"] = copy.deepcopy(value["geometry"])
            value["candidates"][0]["materials"] = copy.deepcopy(value["materials"])
            restamp(value)
            with self.subTest(mutate=mutate), self.assertRaises(EngineeringProblemValidationError):
                EngineeringProblem.from_dict(value)

    def test_order_02_requirements_sources_constraints_unknowns_and_findings(self) -> None:
        cases: list[tuple[str, dict]] = []

        requirements = base_problem()
        second_requirement = copy.deepcopy(requirements["requirements"][0])
        second_requirement.update(requirement_id="REQ-002", description="Second synthetic requirement.")
        requirements["requirements"].append(second_requirement)
        requirements["requirements"].reverse()
        cases.append(("requirements", requirements))

        sources = base_problem()
        second_source = copy.deepcopy(sources["heat_sources"][0])
        second_source["source_id"] = "HSR-002"
        sources["heat_sources"].append(second_source)
        sources["heat_sources"].reverse()
        cases.append(("heat_sources", sources))

        constraints = base_problem()
        second_constraint = copy.deepcopy(constraints["constraints"][0])
        second_constraint["constraint_id"] = "CON-002"
        constraints["constraints"].append(second_constraint)
        constraints["constraints"].reverse()
        cases.append(("constraints", constraints))

        unknowns = base_problem()
        unknowns["unknowns"] = [
            {
                "unknown_id": "UNK-001", "field_path": "/geometry/layers/0/thickness",
                "state": "assumed", "reason": "Synthetic assumption.",
                "consequence": "Requires later review.",
                "readiness_impact": "requires_later_acknowledgement",
                "next_evidence_action": "Review the synthetic assumption.",
            },
            {
                "unknown_id": "UNK-002", "field_path": "/materials/0/thermal_properties/0/thermal_conductivity",
                "state": "missing", "reason": "Synthetic gap.",
                "consequence": "Blocks evaluation.", "readiness_impact": "blocking",
                "next_evidence_action": "Supply public-safe evidence.",
            },
        ]
        unknowns["unknowns"].reverse()
        cases.append(("unknowns", unknowns))

        findings = base_problem()
        findings["compilation"]["warnings"] = [
            {
                "rule_id": "M16A-EPR-UNC-001", "classification": "STRUCTURAL_MODEL_INDEPENDENT",
                "field_paths": ["/geometry/layers/0/thickness/uncertainty"],
                "message": "First warning.", "required_action": "Document uncertainty.",
            },
            {
                "rule_id": "M16A-EPR-UNC-002", "classification": "STRUCTURAL_MODEL_INDEPENDENT",
                "field_paths": ["/geometry/layers/1/thickness/uncertainty"],
                "message": "Second warning.", "required_action": "Document uncertainty.",
            },
        ]
        findings["compilation"]["warnings"].reverse()
        cases.append(("findings", findings))

        for name, value in cases:
            restamp(value)
            with self.subTest(collection=name), self.assertRaises(EngineeringProblemValidationError):
                EngineeringProblem.from_dict(value)

    def test_order_03_interfaces_use_upstream_layer_then_id(self) -> None:
        value = base_problem()
        value["geometry"]["layers"].append(layer("LYR-003", 2, "MAT-003", "4"))
        value["materials"].append(material("MAT-003", "PRP-003", "Synthetic sink layer"))
        value["interfaces"].append({
            "interface_id": "IFC-002", "upstream_layer_id": "LYR-002",
            "downstream_layer_id": "LYR-003",
            "representation_type": "area_normalized_resistance",
            "value": envelope(QuantityKind.AREA_THERMAL_RESISTANCE, "0.001", "mm^2*K/W"),
            "effective_area": envelope(QuantityKind.AREA, "9", "mm^2"),
            "condition_basis": "Synthetic fixture only.",
        })
        value["candidates"][0]["geometry"] = copy.deepcopy(value["geometry"])
        value["candidates"][0]["materials"] = copy.deepcopy(value["materials"])
        value["candidates"][0]["interfaces"] = copy.deepcopy(value["interfaces"])
        restamp(value)
        EngineeringProblem.from_dict(value)
        value["interfaces"].reverse()
        value["candidates"][0]["interfaces"] = copy.deepcopy(value["interfaces"])
        restamp(value)
        with self.assertRaises(EngineeringProblemValidationError):
            EngineeringProblem.from_dict(value)

    def test_src_01_source_hash_map_shape(self) -> None:
        for source_map in ({}, {"01_thermal_design_passport.yml": "2" * 64}, {"00_problem_intake.yml": "ABC"}, {"00_problem_intake.yml": SOURCE_HASH, "12_other.yml": "2" * 64}):
            value = base_problem()
            value["source_case_sha256"] = source_map
            restamp(value)
            with self.subTest(source_map=source_map), self.assertRaises(EngineeringProblemValidationError):
                EngineeringProblem.from_dict(value)

    def test_immutability_detaches_authoring_mapping(self) -> None:
        source = base_problem()
        reconstructed = EngineeringProblem.from_dict(source)
        source["title"] = "Mutated authoring data"
        self.assertEqual(reconstructed.to_dict()["title"], "Synthetic persisted EPR")
        with self.assertRaises(TypeError):
            reconstructed._content["title"] = "no"  # type: ignore[index]


class M16AEPRModelSeparationTests(unittest.TestCase):
    def test_sep_01_unequal_footprints_are_valid(self) -> None:
        EngineeringProblem.from_dict(base_problem())

    def test_sep_02_multiple_and_volumetric_sources_are_valid(self) -> None:
        value = base_problem()
        second = copy.deepcopy(value["heat_sources"][0])
        second.update(
            source_id="HSR-002",
            source_location={"layer_id": "LYR-001", "location_type": "named_region", "region_name": "active volume"},
            spatial_profile="volumetric",
            operating_mode="pulsed",
            duty_cycle=envelope(QuantityKind.PHYSICAL_DIMENSIONLESS, "0.5", "1"),
        )
        value["heat_sources"].append(second)
        restamp(value)
        EngineeringProblem.from_dict(value)

    def test_sep_03_rotated_anisotropy_is_valid(self) -> None:
        value = base_problem()
        value["materials"][1]["anisotropy_representation"] = "rotated_tensor"
        value["materials"][1]["thermal_properties"][0]["temperature_basis"] = "Temperature-dependent source table reference."
        value["geometry"]["layers"][1]["orientation"] = {"stack_normal_axis": "other", "rotation_description": "Synthetic 30 degree rotation about x."}
        value["candidates"][0]["materials"] = copy.deepcopy(value["materials"])
        value["candidates"][0]["geometry"] = copy.deepcopy(value["geometry"])
        restamp(value)
        EngineeringProblem.from_dict(value)

    def test_sep_04_parallel_paths_fraction_and_convection_area_mismatch_are_valid(self) -> None:
        value = base_problem()
        value["boundary_conditions"] = {
            "source_side": {
                "heat_flow_fraction": envelope(QuantityKind.PHYSICAL_DIMENSIONLESS, "0.8", "1"),
                "path_disposition": "declared_parallel_paths",
            },
            "downstream": {
                "representation_type": "direct_convection",
                "heat_transfer_coefficient": envelope(QuantityKind.AREA_THERMAL_CONDUCTANCE, "1000", "W/(m^2*K)"),
                "boundary_area": envelope(QuantityKind.AREA, "100", "mm^2"),
                "ambient_temperature": envelope(QuantityKind.ABSOLUTE_TEMPERATURE, "300", "K"),
                "operating_basis": "Synthetic steady environment.",
            },
        }
        value["candidates"][0]["boundary_conditions"] = copy.deepcopy(value["boundary_conditions"])
        restamp(value)
        EngineeringProblem.from_dict(value)


if __name__ == "__main__":
    unittest.main()
