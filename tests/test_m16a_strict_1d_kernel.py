from __future__ import annotations

import copy
import json
import unittest
from decimal import Decimal, getcontext
from pathlib import Path

from labos.engineering import (
    DETERMINISTIC_RUNTIME_POLICY_VERSION,
    ENGINEERING_EVALUATION_RESULT_FORMAT_VERSION,
    UNIT_REGISTRY_VERSION,
    EngineeringEvaluationResult,
    EngineeringProblem,
    EvaluationPlan,
    QuantityKind,
    canonical_json_bytes,
    canonical_sha256,
    candidate_content_sha256,
    convert_quantity,
    engineering_evaluation_result_content_sha256,
    engineering_problem_content_sha256,
    evaluation_input_sha256,
    evaluation_plan_sha256,
    model_manifest_sha256,
    result_payload_content_sha256,
)
from labos.thermal import (
    ACCEPTED_QUANTITY_KINDS,
    APPLICABILITY_RULE_IDS,
    CANONICAL_UNITS,
    CONSTRAINT_POLICY_VERSION,
    MODEL_ID,
    MODEL_VERSION,
    OAT_POLICY_VERSION,
    RANKING_POLICY_VERSION,
    RESULT_PAYLOAD_SCHEMA_ID,
    RESULT_PAYLOAD_SCHEMA_VERSION,
    SCENARIO_POLICY_VERSION,
    Strict1DResultValidationError,
    bind_strict_1d_inputs,
    build_strict_1d_model_manifest,
    build_strict_1d_result_payload,
    evaluate_strict_1d_baseline,
    validate_strict_1d_result_content,
)
from tests.test_m16a_epr_schema import (
    base_problem,
    envelope,
    missing_envelope,
)


ZERO_HASH = "0" * 64
EPR_FILE_HASH = "f" * 64


def _restamp(problem: dict) -> dict:
    for field in ("geometry", "materials", "interfaces", "boundary_conditions"):
        problem[field] = copy.deepcopy(problem["candidates"][0][field])
    for candidate in problem["candidates"]:
        candidate["resolved_content_sha256"] = candidate_content_sha256(candidate)
    problem["compiled_content_sha256"] = engineering_problem_content_sha256(problem)
    return problem


def _replace_envelope(candidate: dict, path: tuple[object, ...], value: dict) -> None:
    current = candidate
    for token in path[:-1]:
        current = current[token]
    current[path[-1]] = value


def baseline_problem() -> dict:
    problem = base_problem()
    geometry = problem["geometry"]
    for index, layer in enumerate(geometry["layers"]):
        layer["footprint_dimensions"] = [
            envelope(QuantityKind.LENGTH, "2", "mm"),
            envelope(QuantityKind.LENGTH, "2", "mm"),
        ]
        layer["footprint_area"] = envelope(QuantityKind.AREA, "4", "mm^2")
        layer["thickness"] = envelope(
            QuantityKind.LENGTH, "100" if index == 0 else "300", "um"
        )
    problem["materials"][0]["thermal_properties"][0]["thermal_conductivity"] = envelope(
        QuantityKind.THERMAL_CONDUCTIVITY, "160", "W/(m*K)"
    )
    problem["materials"][1]["thermal_properties"][0]["thermal_conductivity"] = envelope(
        QuantityKind.THERMAL_CONDUCTIVITY, "1000", "W/(m*K)"
    )
    problem["interfaces"][0]["value"] = envelope(
        QuantityKind.AREA_THERMAL_RESISTANCE, "5e-9", "m^2*K/W"
    )
    problem["interfaces"][0]["effective_area"] = envelope(
        QuantityKind.AREA, "4", "mm^2"
    )
    problem["boundary_conditions"] = {
        "source_side": {
            "heat_flow_fraction": envelope(QuantityKind.PHYSICAL_DIMENSIONLESS, "1", "1"),
            "path_disposition": "adiabatic_other_paths",
        },
        "downstream": {
            "representation_type": "absolute_resistance",
            "resistance": envelope(QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "1.5", "K/W"),
            "reference_temperature": envelope(QuantityKind.ABSOLUTE_TEMPERATURE, "50", "degC"),
            "operating_basis": "Public-safe synthetic boundary fixture.",
        },
    }
    problem["heat_sources"][0]["total_power"] = envelope(QuantityKind.POWER, "10", "W")
    problem["heat_sources"][0]["heated_area"] = envelope(QuantityKind.AREA, "4", "mm^2")
    problem["heat_sources"][0]["footprint"]["dimensions"] = [
        envelope(QuantityKind.LENGTH, "2", "mm"),
        envelope(QuantityKind.LENGTH, "2", "mm"),
    ]
    problem["heat_sources"][0]["heat_flux"] = envelope(
        QuantityKind.HEAT_FLUX, "2.5", "W/mm^2"
    )
    for field in ("geometry", "materials", "interfaces", "boundary_conditions"):
        problem["candidates"][0][field] = copy.deepcopy(problem[field])
        problem["candidates"][1][field] = copy.deepcopy(problem[field])
    problem["candidates"][1]["changed_field_paths"] = [
        "/materials/1/thermal_properties/0/thermal_conductivity"
    ]
    problem["candidates"][1]["materials"][1]["thermal_properties"][0][
        "thermal_conductivity"
    ] = envelope(QuantityKind.THERMAL_CONDUCTIVITY, "400", "W/(m*K)")
    for candidate in problem["candidates"]:
        candidate["applicable_constraint_ids"] = []
        candidate["assumption_paths"] = []
        candidate["evidence_required_paths"] = []
    problem["constraints"] = []
    return _restamp(problem)


def model_options() -> dict:
    return {
        "strict_1d_validity_assertions": {
            "constant_layer_properties_over_evaluated_range": True,
            "no_coupled_physics": True,
            "no_fluid_or_radiation_model": True,
            "no_temperature_dependent_material_law": True,
            "no_unrepresented_parallel_paths_or_power_splits": True,
        }
    }


def plan_for(problem: dict, *, candidate_ids: list[str] | None = None, acknowledgements: list[dict] | None = None) -> dict:
    return {
        "evaluation_plan_format_version": "m16a-evaluation-plan-1.0",
        "case_id": problem["case_id"],
        "problem_id": problem["problem_id"],
        "epr_compiled_content_sha256": problem["compiled_content_sha256"],
        "model_request": {"model_id": MODEL_ID, "model_version": MODEL_VERSION},
        "selected_candidate_ids": candidate_ids or ["CND-001"],
        "objective": {
            "metric": "source_temperature",
            "direction": "minimize",
            "reference_requirement_id": None,
        },
        "constraint_handling": "report_only",
        "parameter_sweeps": [],
        "sensitivity_request": None,
        "assumption_acknowledgements": copy.deepcopy(acknowledgements or []),
        "model_options": model_options(),
        "maximum_requested_combination_count": len(candidate_ids or ["CND-001"]),
    }


def build_bound(problem: dict | None = None, plan: dict | None = None):
    problem = baseline_problem() if problem is None else problem
    plan = plan_for(problem) if plan is None else plan
    return bind_strict_1d_inputs(
        EngineeringProblem.from_dict(problem),
        EvaluationPlan.from_dict(plan),
    )


def baseline_result(problem: dict | None = None, plan: dict | None = None, candidate_id: str = "CND-001") -> dict:
    return evaluate_strict_1d_baseline(build_bound(problem, plan), candidate_id).to_dict()


def content_for(scenario: dict, objective: dict | None = None) -> dict:
    disposition = scenario["disposition"]
    counts = {
        "evaluated_core_scenarios": int(disposition == "evaluated"),
        "blocked_core_scenarios": int(disposition == "blocked"),
        "invalid_core_scenarios": int(disposition == "invalid"),
        "not_applicable_core_scenarios": int(disposition == "not_applicable"),
    }
    return {
        "scenario_policy_version": SCENARIO_POLICY_VERSION,
        "constraint_policy_version": CONSTRAINT_POLICY_VERSION,
        "ranking_policy_version": RANKING_POLICY_VERSION,
        "oat_policy_version": OAT_POLICY_VERSION,
        "candidate_results": [{
            "candidate_id": scenario["candidate_id"],
            "coverage_summary": {
                "requested_core_scenarios": 1,
                **counts,
                "oat_coverage": None,
            },
            "core_scenarios": [copy.deepcopy(scenario)],
            "sweep_result": None,
            "oat_result": None,
            "findings": copy.deepcopy(scenario["applicability_findings"]),
            "warnings": copy.deepcopy(scenario["execution_findings"]),
        }],
        "candidate_comparison": {
            "objective": objective or {
                "metric": "source_temperature",
                "direction": "minimize",
                "reference_requirement_id": None,
            },
            "comparison_basis_rule": "sole_unswept_baseline_only",
            "constraint_handling": "report_only",
            "ranking_status": "not_performed",
            "candidate_eligibility": [{
                "candidate_id": scenario["candidate_id"],
                "eligible": disposition == "evaluated",
                "basis_scenario_id": scenario["scenario_id"] if disposition == "evaluated" else None,
                "reason_ids": [] if disposition == "evaluated" else ["I4-RANK-INELIGIBLE-BASIS"],
            }],
            "ranked_entries": [],
            "tie_rule": "objective_value_then_candidate_id",
            "calculation_notice": "Ranking is a conditional calculation, not a recommendation or approval.",
        },
        "findings": copy.deepcopy(scenario["applicability_findings"]),
        "warnings": copy.deepcopy(scenario["execution_findings"]),
    }


def _stamp_eer(value: dict) -> dict:
    value["evaluation_plan_sha256"] = evaluation_plan_sha256(value["evaluation_plan"])
    value["model_manifest_sha256"] = model_manifest_sha256(value["model_manifest"])
    value["evaluation_input_sha256"] = evaluation_input_sha256(
        epr_compiled_content_sha256=value["epr_compiled_content_sha256"],
        evaluation_plan_sha256=value["evaluation_plan_sha256"],
        model_manifest_sha256=value["model_manifest_sha256"],
        unit_registry_version=value["unit_registry_version"],
        deterministic_runtime_policy_version=value["deterministic_runtime_policy_version"],
    )
    value["eer_content_sha256"] = engineering_evaluation_result_content_sha256(value)
    return value


def valid_eer(problem: dict, plan: dict, scenario: dict, payload: dict) -> dict:
    manifest = build_strict_1d_model_manifest().to_dict()
    value = {
        "engineering_evaluation_result_format_version": ENGINEERING_EVALUATION_RESULT_FORMAT_VERSION,
        "evaluation_id": "EER-001",
        "case_id": problem["case_id"],
        "problem_id": problem["problem_id"],
        "epr_reference": "engineering/problems/EPR-001.json",
        "epr_compiled_content_sha256": problem["compiled_content_sha256"],
        "epr_file_sha256": EPR_FILE_HASH,
        "evaluation_plan": copy.deepcopy(plan),
        "evaluation_plan_sha256": ZERO_HASH,
        "model_manifest": manifest,
        "model_manifest_sha256": ZERO_HASH,
        "unit_registry_version": UNIT_REGISTRY_VERSION,
        "deterministic_runtime_policy_version": DETERMINISTIC_RUNTIME_POLICY_VERSION,
        "evaluation_input_sha256": ZERO_HASH,
        "execution_outcome": "completed",
        "candidate_execution": [{
            "candidate_id": "CND-001",
            "execution_status": "evaluated",
            "applicability_status": scenario["applicability_status"],
            "applicability_findings": copy.deepcopy(scenario["applicability_findings"]),
            "assumption_acknowledgements_used": copy.deepcopy(scenario["assumption_acknowledgements_used"]),
            "result_presence": True,
        }],
        "assumptions_used": copy.deepcopy(scenario["assumption_acknowledgements_used"]),
        "result_payload": copy.deepcopy(payload),
        "prediction_outputs": [],
        "findings": [],
        "warnings": [],
        "confidentiality_level": "public",
        "calculation_not_approval_notice": "This is a model result, not validation, approval, or a canonical engineering decision.",
        "eer_content_sha256": ZERO_HASH,
    }
    return _stamp_eer(value)


class ManifestAndSchemaTests(unittest.TestCase):
    def test_manifest_exact_identity_and_commit_validation(self) -> None:
        manifest = build_strict_1d_model_manifest().to_dict()
        self.assertEqual(manifest["model_id"], "m16a-strict-1d-thermal")
        self.assertEqual(manifest["model_version"], "1.0.0")
        self.assertEqual(manifest["applicability_rule_ids"], list(APPLICABILITY_RULE_IDS))
        self.assertEqual(manifest["accepted_quantity_kinds"], list(ACCEPTED_QUANTITY_KINDS))
        self.assertEqual(manifest["canonical_units"], CANONICAL_UNITS)
        self.assertIsNone(manifest["implementation_git_commit"])
        supplied = build_strict_1d_model_manifest("a" * 40).to_dict()
        self.assertEqual(supplied["implementation_git_commit"], "a" * 40)
        with self.assertRaises(ValueError):
            build_strict_1d_model_manifest("A" * 40)

    def test_closed_schema_and_runtime_reject_unknown_and_float(self) -> None:
        schema = json.loads(Path("labos/schemas/m16a_strict_1d_result.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["$id"], "labos/m16a_strict_1d_result.schema.json")
        self.assertFalse(schema["additionalProperties"])
        self.assertIn("scenario_record", schema["$defs"])
        content = content_for(baseline_result())
        validate_strict_1d_result_content(content)
        unknown = copy.deepcopy(content)
        unknown["approval"] = True
        with self.assertRaises(Strict1DResultValidationError):
            validate_strict_1d_result_content(unknown)
        bare_float = copy.deepcopy(content)
        bare_float["candidate_results"][0]["core_scenarios"][0]["numerical_result"][
            "common_area"
        ]["value"] = 0.000004
        with self.assertRaises(Strict1DResultValidationError):
            validate_strict_1d_result_content(bare_float)


class KernelAcceptanceTests(unittest.TestCase):
    def test_kern_01_exact_baseline_budget_and_nodes(self) -> None:
        result = baseline_result()
        self.assertEqual(result["disposition"], "evaluated")
        numerical = result["numerical_result"]
        self.assertEqual(
            [item["resistance"]["value"] for item in numerical["layer_resistance_contributions"]],
            ["0.15625", "0.075"],
        )
        self.assertEqual(
            numerical["interface_resistance_contributions"][0]["resistance"]["value"],
            "0.00125",
        )
        self.assertEqual(numerical["total_thermal_resistance"]["value"], "1.7325")
        self.assertEqual(numerical["temperature_rise"]["value"], "17.325")
        self.assertEqual(numerical["source_temperature"]["value"], "340.475")
        self.assertEqual(
            [node["temperature"]["value"] for node in numerical["node_temperatures"]],
            ["340.475", "338.9125", "338.9", "338.15", "323.15"],
        )
        temperatures = [Decimal(node["temperature"]["value"]) for node in numerical["node_temperatures"]]
        self.assertTrue(all(left >= right for left, right in zip(temperatures, temperatures[1:])))
        self.assertEqual(numerical["node_temperatures"][-1]["node_role"], "reference")
        self.assertEqual(numerical["node_temperatures"][-1]["temperature"], numerical["reference_temperature"])

    def test_kern_02_all_supported_boundaries(self) -> None:
        absolute = baseline_result()["numerical_result"]["boundary_resistance_contribution"]
        self.assertEqual(absolute["resistance"]["value"], "1.5")
        fixed_problem = baseline_problem()
        fixed_problem["boundary_conditions"]["downstream"] = {
            "representation_type": "fixed_temperature",
            "terminal_plane": "Explicit reference plane.",
            "reference_temperature": envelope(QuantityKind.ABSOLUTE_TEMPERATURE, "323.15", "K"),
        }
        fixed_problem["candidates"][0]["boundary_conditions"] = copy.deepcopy(fixed_problem["boundary_conditions"])
        _restamp(fixed_problem)
        fixed = baseline_result(fixed_problem)["numerical_result"]["boundary_resistance_contribution"]
        self.assertEqual(fixed["resistance"]["value"], "0")
        self.assertIsNone(fixed["supplied_resistance"])
        convection_problem = baseline_problem()
        convection_problem["boundary_conditions"]["downstream"] = {
            "representation_type": "direct_convection",
            "heat_transfer_coefficient": envelope(
                QuantityKind.AREA_THERMAL_CONDUCTANCE, "100000", "W/(m^2*K)"
            ),
            "boundary_area": envelope(QuantityKind.AREA, "4", "mm^2"),
            "ambient_temperature": envelope(QuantityKind.ABSOLUTE_TEMPERATURE, "323.15", "K"),
            "operating_basis": "Synthetic direct-convection fixture.",
        }
        convection_problem["candidates"][0]["boundary_conditions"] = copy.deepcopy(
            convection_problem["boundary_conditions"]
        )
        _restamp(convection_problem)
        convection = baseline_result(convection_problem)["numerical_result"]["boundary_resistance_contribution"]
        self.assertEqual(convection["resistance"]["value"], "2.5")
        self.assertIsNotNone(convection["heat_transfer_coefficient"])

    def test_kern_03_reorder_preserves_total_and_changes_nodes(self) -> None:
        original = baseline_result()["numerical_result"]
        problem = baseline_problem()
        for root in (problem, problem["candidates"][0]):
            layers = root["geometry"]["layers"]
            layers.reverse()
            for index, layer in enumerate(layers):
                layer["order"] = index
            root["interfaces"][0]["upstream_layer_id"] = layers[0]["layer_id"]
            root["interfaces"][0]["downstream_layer_id"] = layers[1]["layer_id"]
        problem["heat_sources"][0]["source_location"]["layer_id"] = problem["geometry"]["layers"][0]["layer_id"]
        _restamp(problem)
        reordered = baseline_result(problem)["numerical_result"]
        self.assertEqual(reordered["total_thermal_resistance"], original["total_thermal_resistance"])
        self.assertNotEqual(reordered["node_temperatures"], original["node_temperatures"])

    def test_kern_04_explicit_zero_tbr_is_retained(self) -> None:
        problem = baseline_problem()
        zero = envelope(QuantityKind.AREA_THERMAL_RESISTANCE, "0", "m^2*K/W")
        for root in (problem, problem["candidates"][0]):
            root["interfaces"][0]["representation_type"] = "ideal_zero"
            root["interfaces"][0]["value"] = copy.deepcopy(zero)
        _restamp(problem)
        result = baseline_result(problem)
        self.assertEqual(result["disposition"], "evaluated")
        self.assertEqual(
            result["numerical_result"]["interface_resistance_contributions"][0]["resistance"]["value"],
            "0",
        )

    def test_invariants_thickness_area_and_conductivity(self) -> None:
        base = baseline_result()["numerical_result"]
        thick = baseline_problem()
        doubled = envelope(QuantityKind.LENGTH, "200", "um")
        for root in (thick, thick["candidates"][0]):
            root["geometry"]["layers"][0]["thickness"] = copy.deepcopy(doubled)
        _restamp(thick)
        thick_result = baseline_result(thick)["numerical_result"]
        self.assertEqual(thick_result["layer_resistance_contributions"][0]["resistance"]["value"], "0.3125")

        high_k = baseline_problem()
        conductivity = envelope(QuantityKind.THERMAL_CONDUCTIVITY, "320", "W/(m*K)")
        for root in (high_k, high_k["candidates"][0]):
            root["materials"][0]["thermal_properties"][0]["thermal_conductivity"] = copy.deepcopy(conductivity)
        _restamp(high_k)
        high_k_result = baseline_result(high_k)["numerical_result"]
        self.assertLessEqual(
            Decimal(high_k_result["layer_resistance_contributions"][0]["resistance"]["value"]),
            Decimal(base["layer_resistance_contributions"][0]["resistance"]["value"]),
        )

        large = baseline_problem()
        for root in (large, large["candidates"][0]):
            for layer in root["geometry"]["layers"]:
                layer["footprint_area"] = envelope(QuantityKind.AREA, "8", "mm^2")
                layer["footprint_dimensions"] = [
                    envelope(QuantityKind.LENGTH, "4", "mm"),
                    envelope(QuantityKind.LENGTH, "2", "mm"),
                ]
            root["interfaces"][0]["effective_area"] = envelope(QuantityKind.AREA, "8", "mm^2")
        large["heat_sources"][0]["heated_area"] = envelope(QuantityKind.AREA, "8", "mm^2")
        large["heat_sources"][0]["footprint"]["dimensions"] = [
            envelope(QuantityKind.LENGTH, "4", "mm"),
            envelope(QuantityKind.LENGTH, "2", "mm"),
        ]
        _restamp(large)
        large_result = baseline_result(large)["numerical_result"]
        self.assertEqual(large_result["layer_resistance_contributions"][0]["resistance"]["value"], "0.078125")
        self.assertEqual(large_result["interface_resistance_contributions"][0]["resistance"]["value"], "0.000625")


class ApplicabilityAcceptanceTests(unittest.TestCase):
    def assert_not_applicable(self, problem: dict, expected_rule: str) -> None:
        _restamp(problem)
        result = baseline_result(problem)
        self.assertEqual(result["disposition"], "not_applicable")
        self.assertIsNone(result["numerical_result"])
        self.assertIn(expected_rule, {item["rule_id"] for item in result["applicability_findings"]})

    def test_app_01_common_area_and_footprint_mismatch(self) -> None:
        area = baseline_problem()
        area["candidates"][0]["geometry"]["layers"][1]["footprint_area"] = envelope(
            QuantityKind.AREA, "9", "mm^2"
        )
        self.assert_not_applicable(area, "I4-APP-CONSTANT-AREA")
        footprint = baseline_problem()
        footprint["candidates"][0]["geometry"]["layers"][1]["footprint_dimensions"] = [
            envelope(QuantityKind.LENGTH, "1", "mm"),
            envelope(QuantityKind.LENGTH, "4", "mm"),
        ]
        self.assert_not_applicable(footprint, "I4-APP-NO-LATERAL-MISMATCH")

    def test_app_02_direct_convection_area_mismatch(self) -> None:
        problem = baseline_problem()
        problem["candidates"][0]["boundary_conditions"]["downstream"] = {
            "representation_type": "direct_convection",
            "heat_transfer_coefficient": envelope(
                QuantityKind.AREA_THERMAL_CONDUCTANCE, "1000", "W/(m^2*K)"
            ),
            "boundary_area": envelope(QuantityKind.AREA, "9", "mm^2"),
            "ambient_temperature": envelope(QuantityKind.ABSOLUTE_TEMPERATURE, "323.15", "K"),
            "operating_basis": "Synthetic mismatch.",
        }
        self.assert_not_applicable(problem, "I4-APP-CONVECTION-COMMON-AREA")

    def test_app_03_multiple_source_and_parallel_path(self) -> None:
        multiple = baseline_problem()
        second = copy.deepcopy(multiple["heat_sources"][0])
        second["source_id"] = "HSR-002"
        multiple["heat_sources"].append(second)
        self.assert_not_applicable(multiple, "I4-APP-SINGLE-HEAT-SOURCE")
        parallel = baseline_problem()
        parallel["candidates"][0]["boundary_conditions"]["source_side"]["path_disposition"] = "declared_parallel_paths"
        self.assert_not_applicable(parallel, "I4-APP-SINGLE-SERIES-PATH")
        distributed = baseline_problem()
        distributed["heat_sources"][0]["spatial_profile"] = "volumetric"
        self.assert_not_applicable(distributed, "I4-APP-NO-DISTRIBUTED-GENERATION")

    def test_app_04_rotated_and_temperature_law(self) -> None:
        rotated = baseline_problem()
        rotated["candidates"][0]["materials"][0]["anisotropy_representation"] = "rotated_tensor"
        self.assert_not_applicable(rotated, "I4-APP-NORMAL-CONDUCTIVITY")
        law = baseline_problem()
        law["candidates"][0]["materials"][0]["thermal_properties"][0][
            "temperature_basis"
        ] = "A temperature-dependent law is required."
        self.assert_not_applicable(law, "I4-APP-NO-TEMPERATURE-LAW")

    def test_app_05_unsupported_interface_and_boundary(self) -> None:
        interface = baseline_problem()
        interface["candidates"][0]["interfaces"][0]["representation_type"] = "absolute_resistance"
        interface["candidates"][0]["interfaces"][0]["value"] = envelope(
            QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "0.1", "K/W"
        )
        self.assert_not_applicable(interface, "I4-APP-SUPPORTED-INTERFACE")
        boundary = baseline_problem()
        boundary["candidates"][0]["boundary_conditions"]["downstream"] = {
            "representation_type": "other",
            "description": "Public-safe unsupported boundary.",
        }
        self.assert_not_applicable(boundary, "I4-APP-SUPPORTED-BOUNDARY")

    def test_nonphysical_base_values_block_before_arithmetic(self) -> None:
        cases = [
            ("area", ("heat_sources", 0, "heated_area"), envelope(QuantityKind.AREA, "0", "m^2")),
            ("negative_area", ("heat_sources", 0, "heated_area"), envelope(QuantityKind.AREA, "-1", "m^2")),
            ("thickness", ("candidates", 0, "geometry", "layers", 0, "thickness"), envelope(QuantityKind.LENGTH, "0", "m")),
            ("conductivity", ("candidates", 0, "materials", 0, "thermal_properties", 0, "thermal_conductivity"), envelope(QuantityKind.THERMAL_CONDUCTIVITY, "-1", "W/(m*K)")),
            ("tbr", ("candidates", 0, "interfaces", 0, "value"), envelope(QuantityKind.AREA_THERMAL_RESISTANCE, "-1e-9", "m^2*K/W")),
        ]
        for label, path, replacement in cases:
            with self.subTest(label=label):
                problem = baseline_problem()
                current = problem
                for token in path[:-1]:
                    current = current[token]
                current[path[-1]] = replacement
                if path[:2] == ("heat_sources", 0):
                    problem["candidates"][0]["geometry"]["layers"][0]["footprint_area"] = copy.deepcopy(replacement)
                _restamp(problem)
                result = baseline_result(problem)
                self.assertEqual(result["disposition"], "blocked")
                self.assertIn(
                    "I4-NUM-NONPHYSICAL-BASE-INPUT",
                    {item["rule_id"] for item in result["execution_findings"]},
                )

    def test_supported_boundary_missing_numeric_value_blocks(self) -> None:
        problem = baseline_problem()
        problem["candidates"][0]["boundary_conditions"]["downstream"]["resistance"] = (
            missing_envelope(QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "K/W")
        )
        problem["compilation"]["outcome"] = "HOLD_FOR_INPUT"
        _restamp(problem)
        result = baseline_result(problem)
        self.assertEqual(result["disposition"], "blocked")
        self.assertIsNone(result["numerical_result"])
        self.assertIn("I4-BIND-MISSING-INPUT", {item["rule_id"] for item in result["execution_findings"]})


class BindingAcceptanceTests(unittest.TestCase):
    def test_bind_01_consumed_paths_are_exact_and_deterministic(self) -> None:
        first = build_bound().consumed_input_paths("CND-001")
        second = build_bound().consumed_input_paths("CND-001")
        self.assertEqual(first, second)
        self.assertEqual(first, sorted(first, key=lambda item: (0 if item["scope"] == "global" else 1, item["candidate_id"] or "", item["field_path"])))
        paths = {(item["scope"], item["field_path"]) for item in first}
        self.assertIn(("global", "/heat_sources"), paths)
        self.assertIn(("global", "/heat_sources/0/total_power"), paths)
        self.assertIn(("candidate", "/geometry/layers"), paths)
        self.assertIn(("candidate", "/interfaces/0/value"), paths)
        self.assertIn(("candidate", "/boundary_conditions/downstream/resistance"), paths)

    def test_bind_02_missing_consumed_assumption_acknowledgement(self) -> None:
        problem = baseline_problem()
        assumed = envelope(QuantityKind.THERMAL_CONDUCTIVITY, "160", "W/(m*K)", status="assumed")
        path = "/materials/0/thermal_properties/0/thermal_conductivity"
        problem["materials"][0]["thermal_properties"][0]["thermal_conductivity"] = copy.deepcopy(assumed)
        problem["candidates"][0]["materials"][0]["thermal_properties"][0]["thermal_conductivity"] = copy.deepcopy(assumed)
        problem["candidates"][0]["assumption_paths"] = [path]
        problem["compilation"]["outcome"] = "READY_WITH_ASSUMPTIONS"
        _restamp(problem)
        result = baseline_result(problem)
        self.assertEqual(result["disposition"], "blocked")
        self.assertEqual(result["assumption_acknowledgements_used"], [])

    def test_bind_03_extra_candidate_and_global_acknowledgements(self) -> None:
        problem = baseline_problem()
        candidate_path = "/materials/1/thermal_properties/0/thermal_conductivity"
        assumed = envelope(QuantityKind.THERMAL_CONDUCTIVITY, "2000", "W/(m*K)", status="assumed")
        problem["candidates"][0]["materials"].append({
            "material_id": "MAT-003",
            "label": "Unused synthetic material",
            "material_class": "synthetic solid",
            "anisotropy_representation": "isotropic",
            "thermal_properties": [{
                "property_id": "PRP-003",
                "component": "isotropic",
                "thermal_conductivity": copy.deepcopy(assumed),
                "temperature_basis": "Synthetic constant basis.",
                "condition_basis": "Synthetic fixture.",
            }],
        })
        candidate_path = "/materials/2/thermal_properties/0/thermal_conductivity"
        problem["candidates"][0]["assumption_paths"] = [candidate_path]
        _restamp(problem)
        candidate_ack = {"scope": "candidate", "candidate_id": "CND-001", "field_path": candidate_path}
        result = baseline_result(problem, plan_for(problem, acknowledgements=[candidate_ack]))
        self.assertEqual(result["disposition"], "blocked")
        self.assertEqual(result["assumption_acknowledgements_used"], [])

        global_problem = baseline_problem()
        global_problem["requirements"][0]["target"] = envelope(
            QuantityKind.LENGTH, "0.1", "mm", status="assumed"
        )
        _restamp(global_problem)
        global_ack = {
            "scope": "global",
            "candidate_id": None,
            "field_path": "/requirements/0/target",
        }
        global_result = baseline_result(
            global_problem,
            plan_for(global_problem, acknowledgements=[global_ack]),
        )
        self.assertEqual(global_result["disposition"], "blocked")

    def test_bind_04_status_semantics(self) -> None:
        global_path = "/heat_sources/0/total_power"
        assumed_problem = baseline_problem()
        assumed = envelope(QuantityKind.POWER, "10", "W", status="assumed")
        assumed_problem["heat_sources"][0]["total_power"] = assumed
        assumed_problem["compilation"]["outcome"] = "READY_WITH_ASSUMPTIONS"
        _restamp(assumed_problem)
        acknowledgement = {"scope": "global", "candidate_id": None, "field_path": global_path}
        assumed_result = baseline_result(
            assumed_problem,
            plan_for(assumed_problem, acknowledgements=[acknowledgement]),
        )
        self.assertEqual(assumed_result["disposition"], "evaluated")
        self.assertEqual(assumed_result["assumption_acknowledgements_used"], [acknowledgement])

        evidence_problem = baseline_problem()
        evidence_problem["heat_sources"][0]["total_power"] = envelope(
            QuantityKind.POWER, "10", "W", status="evidence_required"
        )
        evidence_problem["compilation"]["outcome"] = "HOLD_FOR_INPUT"
        _restamp(evidence_problem)
        evidence_result = baseline_result(evidence_problem)
        self.assertEqual(evidence_result["disposition"], "evaluated")
        self.assertEqual(evidence_result["applicability_status"], "applicable_with_warnings")
        self.assertIn("I4-BIND-EVIDENCE-REQUIRED", {item["rule_id"] for item in evidence_result["execution_findings"]})

        missing_problem = baseline_problem()
        missing_problem["heat_sources"][0]["total_power"] = missing_envelope(QuantityKind.POWER, "W")
        missing_problem["compilation"]["outcome"] = "HOLD_FOR_INPUT"
        _restamp(missing_problem)
        missing_result = baseline_result(missing_problem)
        self.assertEqual(missing_result["disposition"], "blocked")
        self.assertIsNone(missing_result["numerical_result"])

    def test_global_acknowledgement_required_by_one_candidate_is_not_extra_for_another(self) -> None:
        problem = baseline_problem()
        problem["constraints"] = [{
            "constraint_id": "CON-001",
            "target_path": "/heat_sources/0/source_location",
            "operator": "le",
            "threshold": envelope(
                QuantityKind.ABSOLUTE_TEMPERATURE, "75", "degC", status="assumed"
            ),
            "severity": "blocking",
            "provenance": copy.deepcopy(problem["requirements"][0]["provenance"]),
            "evaluation_disposition": "machine_evaluable",
        }]
        problem["candidates"][0]["applicable_constraint_ids"] = ["CON-001"]
        problem["candidates"][1]["applicable_constraint_ids"] = []
        problem["compilation"]["outcome"] = "READY_WITH_ASSUMPTIONS"
        _restamp(problem)
        acknowledgement = {
            "scope": "global",
            "candidate_id": None,
            "field_path": "/constraints/0/threshold",
        }
        plan = plan_for(
            problem,
            candidate_ids=["CND-001", "CND-002"],
            acknowledgements=[acknowledgement],
        )
        bound = build_bound(problem, plan)
        first = evaluate_strict_1d_baseline(bound, "CND-001").to_dict()
        second = evaluate_strict_1d_baseline(bound, "CND-002").to_dict()
        self.assertEqual(first["disposition"], "evaluated")
        self.assertEqual(second["disposition"], "evaluated")
        self.assertEqual(first["assumption_acknowledgements_used"], [acknowledgement])
        self.assertEqual(second["assumption_acknowledgements_used"], [])

    def test_model_options_missing_false_non_boolean_and_extra_block(self) -> None:
        variants = []
        missing = model_options()
        del missing["strict_1d_validity_assertions"]["no_coupled_physics"]
        variants.append(missing)
        false_value = model_options()
        false_value["strict_1d_validity_assertions"]["no_coupled_physics"] = False
        variants.append(false_value)
        non_boolean = model_options()
        non_boolean["strict_1d_validity_assertions"]["no_coupled_physics"] = 1
        variants.append(non_boolean)
        extra = model_options()
        extra["strict_1d_validity_assertions"]["extra"] = True
        variants.append(extra)
        for options in variants:
            with self.subTest(options=options):
                problem = baseline_problem()
                plan = plan_for(problem)
                plan["model_options"] = options
                result = baseline_result(problem, plan)
                self.assertEqual(result["disposition"], "blocked")
                self.assertIsNone(result["numerical_result"])


class DeterminismAndCompatibilityTests(unittest.TestCase):
    def test_det_01_repeated_content_and_hash_are_identical(self) -> None:
        first_content = content_for(baseline_result())
        second_content = content_for(baseline_result())
        first = build_strict_1d_result_payload(first_content)
        second = build_strict_1d_result_payload(second_content)
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))
        self.assertEqual(first["content_sha256"], second["content_sha256"])

    def test_det_02_mapping_insertion_order_does_not_change_output(self) -> None:
        def reverse_mappings(value):
            if isinstance(value, dict):
                return {key: reverse_mappings(value[key]) for key in reversed(list(value))}
            if isinstance(value, list):
                return [reverse_mappings(item) for item in value]
            return value

        problem = baseline_problem()
        first = baseline_result(problem)
        second_problem = reverse_mappings(problem)
        second = evaluate_strict_1d_baseline(
            bind_strict_1d_inputs(
                EngineeringProblem.from_dict(second_problem),
                EvaluationPlan.from_dict(reverse_mappings(plan_for(problem))),
            ),
            "CND-001",
        ).to_dict()
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))

    def test_det_03_context_rounding_is_local_and_reproducible(self) -> None:
        before = getcontext().copy()
        first = baseline_result()["numerical_result"]
        second = baseline_result()["numerical_result"]
        self.assertEqual(first["numerical_exactness"], "context_rounded")
        self.assertEqual(first, second)
        after = getcontext()
        self.assertEqual(before.prec, after.prec)
        self.assertEqual(before.rounding, after.rounding)
        self.assertEqual(before.Emin, after.Emin)
        self.assertEqual(before.Emax, after.Emax)

    def test_det_04_frozen_i3_payload_hash_and_eer_compatibility(self) -> None:
        problem = baseline_problem()
        plan = plan_for(problem)
        scenario = baseline_result(problem, plan)
        content = content_for(scenario, plan["objective"])
        payload = dict(build_strict_1d_result_payload(content))
        self.assertEqual(payload["content_sha256"], result_payload_content_sha256(payload))
        eer = valid_eer(problem, plan, scenario, payload)
        EngineeringEvaluationResult.from_dict(eer)

        wrong = copy.deepcopy(eer)
        wrong["result_payload"]["content_sha256"] = canonical_sha256({
            "result_payload_content_identity_version": "unapproved-extra-domain",
            "schema_id": payload["schema_id"],
            "schema_version": payload["schema_version"],
            "content": payload["content"],
        })
        wrong["eer_content_sha256"] = engineering_evaluation_result_content_sha256(wrong)
        with self.assertRaises(ValueError):
            EngineeringEvaluationResult.from_dict(wrong)


class SeparationAcceptanceTests(unittest.TestCase):
    def test_sep_01_only_frozen_equations_and_no_hidden_correction_fields(self) -> None:
        numerical = baseline_result()["numerical_result"]
        forbidden = {
            "spreading_resistance",
            "constriction_resistance",
            "fin_efficiency",
            "radiation",
            "transient",
            "fluid_solver",
        }
        self.assertFalse(forbidden & set(json.dumps(numerical, sort_keys=True).split('"')))

    def test_sep_02_no_approval_identity_or_local_context_in_result(self) -> None:
        content = content_for(baseline_result())
        text = canonical_json_bytes(content).decode("utf-8")
        for forbidden in (
            "reviewed_by",
            "approval_status",
            "canonical_decision",
            "memory_action",
            "timestamp",
            "hostname",
            "username",
            "C:\\\\",
        ):
            self.assertNotIn(forbidden, text)

    def test_sep_03_i4a_exposes_no_orchestration_or_governance_api(self) -> None:
        import labos.thermal as thermal

        for forbidden in (
            "execute_parameter_sweeps",
            "aggregate_candidates",
            "rank_candidates",
            "evaluate_constraints",
            "execute_oat",
            "build_engineering_evaluation_result",
            "create_evidence_object",
        ):
            self.assertFalse(hasattr(thermal, forbidden))


if __name__ == "__main__":
    unittest.main()
