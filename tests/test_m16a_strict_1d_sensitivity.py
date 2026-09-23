"""Public-safe I4C OAT, output identity, and synthetic projection acceptance."""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from decimal import Decimal, localcontext
from pathlib import Path

from labos.engineering import (
    EngineeringProblem,
    EvaluationPlan,
    QuantityKind,
    bind_evaluation_plan,
    canonical_json_bytes,
    load_engineering_evaluation_result,
    project_eer_prediction_to_measurement,
    write_engineering_evaluation_result,
)
from labos.evidence.template import create_evidence_template, create_measurement_template
from labos.thermal import (
    Strict1DValidationError,
    build_strict_1d_engineering_evaluation_result,
    orchestrate_strict_1d,
)
from labos.thermal.strict_1d_sensitivity import _sensitivity_ranking
from tests.test_m16a_strict_1d_kernel import _restamp, baseline_problem, envelope
from tests.test_m16a_strict_1d_orchestration import (
    add_constraint,
    grid,
    make_plan,
    quantity,
    set_temperature_margin,
)
from tests.test_m16a_epr_schema import missing_envelope


BOUNDARY = "/boundary_conditions/downstream/resistance"
THICKNESS = "/geometry/layers/1/thickness"
OAT_ONLY_PROPERTY = "/materials/2/thermal_properties/0/thermal_conductivity"


def oat_parameter(path: str, kind: QuantityKind, minus: str, plus: str, unit: str) -> dict:
    return {
        "candidate_id": "CND-001",
        "field_path": path,
        "minus_value": quantity(kind, minus, unit),
        "plus_value": quantity(kind, plus, unit),
    }


def oat_plan(problem: dict, metric: str, parameters: list[dict], *, sweeps: list[dict] | None = None) -> dict:
    plan = make_plan(problem, sweeps=sweeps)
    plan["sensitivity_request"] = {
        "method": "oat",
        "baseline_candidate_id": "CND-001",
        "output_metric": metric,
        "parameters": parameters,
    }
    return plan


def run(problem: dict, plan: dict) -> dict:
    return orchestrate_strict_1d(
        EngineeringProblem.from_dict(problem), EvaluationPlan.from_dict(plan)
    ).to_dict()


def first_candidate(result: dict) -> dict:
    return result["result_payload"]["content"]["candidate_results"][0]


def ids(items: list[dict]) -> set[str]:
    return {item["rule_id"] for item in items}


def add_unused_oat_property(problem: dict, status: str) -> dict:
    """Add a public-safe numeric candidate envelope unused by every thermal layer."""
    candidate = problem["candidates"][0]
    candidate["materials"].append({
        "material_id": "MAT-003",
        "label": "Unused synthetic OAT material",
        "material_class": "synthetic solid",
        "anisotropy_representation": "isotropic",
        "thermal_properties": [{
            "property_id": "PRP-003",
            "component": "isotropic",
            "thermal_conductivity": envelope(
                QuantityKind.THERMAL_CONDUCTIVITY, "1200", "W/(m*K)", status=status
            ),
            "temperature_basis": "Public-safe constant synthetic property.",
            "condition_basis": "Synthetic OAT-only binding fixture.",
        }],
    })
    if status == "assumed":
        candidate["assumption_paths"] = [OAT_ONLY_PROPERTY]
        problem["compilation"]["outcome"] = "READY_WITH_ASSUMPTIONS"
    elif status == "evidence_required":
        candidate["evidence_required_paths"] = [OAT_ONLY_PROPERTY]
        problem["compilation"]["outcome"] = "HOLD_FOR_INPUT"
    _restamp(problem)
    return problem


class OATAcceptanceTests(unittest.TestCase):
    def test_normalized_ranking_exact_tie_uses_lexical_field_path(self) -> None:
        status, ranking = _sensitivity_ranking([
            {"field_path": THICKNESS, "disposition": "complete",
             "normalized_sensitivity": {"value": "-2", "quantity_kind": "physical_dimensionless", "unit": "1"}},
            {"field_path": BOUNDARY, "disposition": "complete",
             "normalized_sensitivity": {"value": "2", "quantity_kind": "physical_dimensionless", "unit": "1"}},
        ])
        self.assertEqual(status, "performed")
        self.assertEqual([item["field_path"] for item in ranking], [BOUNDARY, THICKNESS])

    def test_oat_01_exact_central_derivative_reuse_coverage_and_ranking(self) -> None:
        problem = baseline_problem()
        plan = oat_plan(problem, "total_thermal_resistance", [
            oat_parameter(BOUNDARY, QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "0.5", "2.5", "K/W"),
            oat_parameter(THICKNESS, QuantityKind.LENGTH, "200", "500", "um"),
        ])
        result = run(problem, plan)
        candidate = first_candidate(result)
        oat = candidate["oat_result"]
        reference = oat["reference_scenario"]
        self.assertEqual(reference["scenario_id"], "SCN-C001-O000-REF")
        self.assertEqual(reference["reused_core_scenario_id"], "SCN-C001-K000001")
        self.assertEqual(
            canonical_json_bytes(reference["numerical_result"]),
            canonical_json_bytes(candidate["core_scenarios"][0]["numerical_result"]),
        )
        self.assertEqual(reference["input_overrides"], [])
        self.assertEqual(reference["oat_coordinate"], {
            "parameter_ordinal": 0, "field_path": None, "side": "reference",
        })
        self.assertEqual(candidate["coverage_summary"]["oat_coverage"], {
            "requested_oat_points": 5,
            "evaluated_oat_points": 5,
            "blocked_oat_points": 0,
            "invalid_oat_points": 0,
            "not_applicable_oat_points": 0,
        })
        boundary = oat["parameters"][0]
        self.assertEqual(
            [boundary[side]["scenario_id"] for side in ("minus_scenario", "plus_scenario")],
            ["SCN-C001-O001-MINUS", "SCN-C001-O001-PLUS"],
        )
        self.assertEqual(boundary["minus_scenario"]["scenario_kind"], "oat_minus")
        self.assertEqual(boundary["plus_scenario"]["scenario_kind"], "oat_plus")
        self.assertEqual(boundary["minus_scenario"]["sweep_coordinates"], [])
        self.assertEqual(boundary["minus_scenario"]["input_overrides"], [{
            "source_kind": "oat", "source_id": None, "field_path": BOUNDARY,
            "point_ordinal": 1, "side": "minus",
            "value": {"value": "0.5", "unit": "K/W", "quantity_kind": "absolute_thermal_resistance"},
        }])
        self.assertEqual(
            [boundary[side]["numerical_result"]["total_thermal_resistance"]["value"]
             for side in ("minus_scenario", "plus_scenario")],
            ["0.7325", "2.7325"],
        )
        self.assertEqual(reference["numerical_result"]["total_thermal_resistance"]["value"], "1.7325")
        self.assertEqual(boundary["dimensional_derivative"]["value"], "1")
        self.assertEqual(boundary["dimensional_derivative"], {
            "value": "1", "output_quantity_kind": "absolute_thermal_resistance",
            "output_unit": "K/W", "input_quantity_kind": "absolute_thermal_resistance",
            "input_unit": "K/W",
        })
        with localcontext() as context:
            context.prec = 50
            expected = context.divide(Decimal("1.5"), Decimal("1.7325"))
        self.assertEqual(Decimal(boundary["normalized_sensitivity"]["value"]), expected)
        self.assertEqual(oat["ranking_status"], "performed")
        self.assertEqual(oat["sensitivity_ranking"][0]["field_path"], BOUNDARY)
        self.assertEqual(candidate["warnings"], [])

    def test_oat_02_and_05_failed_side_retains_core_and_outputs(self) -> None:
        problem = baseline_problem()
        plan = oat_plan(problem, "total_thermal_resistance", [
            oat_parameter(THICKNESS, QuantityKind.LENGTH, "-100", "500", "um"),
        ])
        result = run(problem, plan)
        candidate = first_candidate(result)
        parameter = candidate["oat_result"]["parameters"][0]
        self.assertEqual(parameter["minus_scenario"]["disposition"], "invalid")
        self.assertEqual(parameter["plus_scenario"]["disposition"], "evaluated")
        self.assertEqual(parameter["disposition"], "incomplete")
        self.assertIsNone(parameter["dimensional_derivative"])
        self.assertIsNone(parameter["normalized_sensitivity"])
        self.assertEqual(parameter["finding_ids"], ["I4-OAT-INCOMPLETE"])
        self.assertEqual(result["candidate_execution"][0]["execution_status"], "evaluated")
        self.assertTrue(result["candidate_execution"][0]["result_presence"])
        self.assertEqual(result["candidate_execution"][0]["applicability_status"], "applicable_with_warnings")
        self.assertEqual(result["execution_outcome"], "completed")
        self.assertEqual(candidate["core_scenarios"][0]["numerical_result"]["source_temperature"]["value"], "340.475")
        self.assertIn("I4-OAT-INCOMPLETE", ids(result["warnings"]))
        self.assertIn("I4-SCENARIO-PARTIAL-COVERAGE", ids(result["warnings"]))
        with tempfile.TemporaryDirectory() as temporary:
            case = Path(temporary) / problem["case_id"]
            epr_dir = case / "engineering" / "problems"
            epr_dir.mkdir(parents=True)
            (epr_dir / "EPR-001.json").write_bytes(canonical_json_bytes(problem))
            bound = bind_evaluation_plan(case, EvaluationPlan.from_dict(plan))
            eer = build_strict_1d_engineering_evaluation_result(bound, "EER-001")
            self.assertEqual(len(eer.to_dict()["prediction_outputs"]), 3)

    def test_oat_03_zero_x_and_zero_y_findings_only(self) -> None:
        zero_x = baseline_problem()
        zero_x["candidates"][0]["boundary_conditions"]["downstream"]["resistance"] = envelope(
            QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "0", "K/W"
        )
        _restamp(zero_x)
        plan = oat_plan(zero_x, "total_thermal_resistance", [
            oat_parameter(BOUNDARY, QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "0.5", "2.5", "K/W"),
        ])
        result = run(zero_x, plan)
        parameter = first_candidate(result)["oat_result"]["parameters"][0]
        self.assertEqual(parameter["disposition"], "complete")
        self.assertEqual(parameter["normalized_sensitivity_disposition"], "zero_x_reference")
        self.assertIsNotNone(parameter["dimensional_derivative"])
        self.assertIsNone(parameter["normalized_sensitivity"])
        self.assertIn("I4-OAT-NORMALIZED-NOT-DEFINED", ids(result["findings"]))
        self.assertNotIn("I4-OAT-NORMALIZED-NOT-DEFINED", ids(result["warnings"]))
        self.assertEqual(result["candidate_execution"][0]["applicability_status"], "applicable")

        zero_y = baseline_problem()
        set_temperature_margin(zero_y)
        zero_y["requirements"][0]["target"] = envelope(
            QuantityKind.ABSOLUTE_TEMPERATURE, "340.475", "K"
        )
        _restamp(zero_y)
        plan = oat_plan(zero_y, "temperature_margin", [
            oat_parameter(BOUNDARY, QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "0.5", "2.5", "K/W"),
        ])
        plan["objective"] = {
            "metric": "temperature_margin", "direction": "maximize", "reference_requirement_id": "REQ-001",
        }
        result = run(zero_y, plan)
        parameter = first_candidate(result)["oat_result"]["parameters"][0]
        self.assertEqual(parameter["disposition"], "complete")
        self.assertEqual(parameter["normalized_sensitivity_disposition"], "zero_y_reference")
        self.assertIsNotNone(parameter["dimensional_derivative"])
        self.assertIsNone(parameter["normalized_sensitivity"])
        self.assertEqual(result["candidate_execution"][0]["applicability_status"], "applicable")
        dual_zero = copy.deepcopy(zero_y)
        dual_zero["candidates"][0]["boundary_conditions"]["downstream"]["resistance"] = envelope(
            QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "0", "K/W"
        )
        dual_zero["requirements"][0]["target"] = envelope(
            QuantityKind.ABSOLUTE_TEMPERATURE, "325.475", "K"
        )
        _restamp(dual_zero)
        dual_plan = oat_plan(dual_zero, "temperature_margin", [
            oat_parameter(BOUNDARY, QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "0.5", "2.5", "K/W"),
        ])
        dual_plan["objective"] = {
            "metric": "temperature_margin", "direction": "maximize", "reference_requirement_id": "REQ-001",
        }
        dual = first_candidate(run(dual_zero, dual_plan))["oat_result"]["parameters"][0]
        self.assertEqual(dual["normalized_sensitivity_disposition"], "zero_x_reference")

    def test_oat_04_absolute_temperature_has_derivative_without_rank(self) -> None:
        problem = baseline_problem()
        result = run(problem, oat_plan(problem, "source_temperature", [
            oat_parameter(BOUNDARY, QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "0.5", "2.5", "K/W"),
        ]))
        oat = first_candidate(result)["oat_result"]
        parameter = oat["parameters"][0]
        self.assertEqual(parameter["disposition"], "complete")
        self.assertEqual(parameter["dimensional_derivative"]["value"], "10")
        self.assertIsNone(parameter["normalized_sensitivity"])
        self.assertEqual(parameter["normalized_sensitivity_disposition"], "absolute_temperature_not_normalized")
        self.assertEqual(oat["ranking_status"], "not_performed")
        self.assertEqual(oat["sensitivity_ranking"], [])
        self.assertEqual(result["candidate_execution"][0]["applicability_status"], "applicable")

    def test_swept_oat_reference_is_explicit_and_has_no_candidate_output(self) -> None:
        problem = baseline_problem()
        sweep = grid("SWP-001", "CND-001", THICKNESS, QuantityKind.LENGTH, ["200", "500"], "um")
        plan = oat_plan(problem, "total_thermal_resistance", [
            oat_parameter(BOUNDARY, QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "0.5", "2.5", "K/W"),
        ], sweeps=[sweep])
        result = run(problem, plan)
        candidate = first_candidate(result)
        self.assertEqual(candidate["coverage_summary"]["requested_core_scenarios"], 2)
        self.assertIsNone(candidate["oat_result"]["reference_scenario"]["reused_core_scenario_id"])
        self.assertEqual(candidate["oat_result"]["reference_scenario"]["numerical_result"]["source_temperature"]["value"], "340.475")
        self.assertEqual(result["result_payload"]["content"]["candidate_comparison"]["candidate_eligibility"][0]["reason_ids"], ["I4-RANK-INELIGIBLE-BASIS"])
        with tempfile.TemporaryDirectory() as temporary:
            case = Path(temporary) / problem["case_id"]
            epr_dir = case / "engineering" / "problems"
            epr_dir.mkdir(parents=True)
            (epr_dir / "EPR-001.json").write_bytes(canonical_json_bytes(problem))
            bound = bind_evaluation_plan(case, EvaluationPlan.from_dict(plan))
            self.assertEqual(build_strict_1d_engineering_evaluation_result(bound, "EER-001").to_dict()["prediction_outputs"], [])

    def test_auxiliary_oat_cannot_create_core_result_presence(self) -> None:
        problem = baseline_problem()
        sweep = grid("SWP-001", "CND-001", THICKNESS, QuantityKind.LENGTH, ["0"], "um")
        plan = oat_plan(problem, "total_thermal_resistance", [
            oat_parameter(BOUNDARY, QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "0.5", "2.5", "K/W"),
        ], sweeps=[sweep])
        result = run(problem, plan)
        self.assertEqual(first_candidate(result)["core_scenarios"][0]["disposition"], "invalid")
        self.assertEqual(first_candidate(result)["oat_result"]["reference_scenario"]["disposition"], "evaluated")
        self.assertEqual(result["candidate_execution"][0]["execution_status"], "blocked")
        self.assertFalse(result["candidate_execution"][0]["result_presence"])
        self.assertEqual(result["execution_outcome"], "not_evaluated")

    def test_evidence_required_oat_warning_and_missing_status_not_repaired(self) -> None:
        evidence = baseline_problem()
        evidence["candidates"][0]["boundary_conditions"]["downstream"]["resistance"] = envelope(
            QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "1.5", "K/W", status="evidence_required"
        )
        evidence["compilation"]["outcome"] = "HOLD_FOR_INPUT"
        _restamp(evidence)
        plan = oat_plan(evidence, "total_thermal_resistance", [
            oat_parameter(BOUNDARY, QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "0.5", "2.5", "K/W"),
        ])
        result = run(evidence, plan)
        oat = first_candidate(result)["oat_result"]
        self.assertEqual(result["candidate_execution"][0]["execution_status"], "evaluated")
        self.assertEqual(result["candidate_execution"][0]["applicability_status"], "applicable_with_warnings")
        self.assertTrue(all("I4-BIND-EVIDENCE-REQUIRED" in ids(item["execution_findings"])
                            for item in (oat["reference_scenario"], oat["parameters"][0]["minus_scenario"],
                                         oat["parameters"][0]["plus_scenario"])))
        missing = baseline_problem()
        missing["candidates"][0]["boundary_conditions"]["downstream"]["resistance"] = missing_envelope(
            QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "K/W"
        )
        missing["compilation"]["outcome"] = "HOLD_FOR_INPUT"
        _restamp(missing)
        # I3 binding rejects a nonnumeric OAT target before an override can masquerade as source data.
        with self.assertRaises(ValueError):
            with tempfile.TemporaryDirectory() as temporary:
                case = Path(temporary) / missing["case_id"]
                epr_dir = case / "engineering" / "problems"
                epr_dir.mkdir(parents=True)
                (epr_dir / "EPR-001.json").write_bytes(canonical_json_bytes(missing))
                bind_evaluation_plan(case, EvaluationPlan.from_dict(oat_plan(missing, "total_thermal_resistance", [
                    oat_parameter(BOUNDARY, QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "0.5", "2.5", "K/W"),
                ])))

    def test_temperature_margin_requires_exact_plan_objective_reference(self) -> None:
        problem = baseline_problem()
        plan = oat_plan(problem, "temperature_margin", [
            oat_parameter(BOUNDARY, QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "0.5", "2.5", "K/W"),
        ])
        with self.assertRaisesRegex(Strict1DValidationError, "exact Plan temperature-margin"):
            run(problem, plan)

    def test_oat_acknowledgement_status_is_preserved(self) -> None:
        problem = baseline_problem()
        problem["candidates"][0]["boundary_conditions"]["downstream"]["resistance"] = envelope(
            QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "1.5", "K/W", status="assumed"
        )
        problem["candidates"][0]["assumption_paths"] = [BOUNDARY]
        problem["compilation"]["outcome"] = "READY_WITH_ASSUMPTIONS"
        _restamp(problem)
        plan = oat_plan(problem, "total_thermal_resistance", [
            oat_parameter(BOUNDARY, QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "0.5", "2.5", "K/W"),
        ])
        missing_ack = run(problem, plan)
        self.assertEqual(missing_ack["candidate_execution"][0]["execution_status"], "blocked")
        ack = {"scope": "candidate", "candidate_id": "CND-001", "field_path": BOUNDARY}
        plan["assumption_acknowledgements"] = [ack]
        executed = run(problem, plan)
        oat = first_candidate(executed)["oat_result"]
        self.assertEqual(executed["candidate_execution"][0]["assumption_acknowledgements_used"], [ack])
        self.assertEqual(oat["reference_scenario"]["assumption_acknowledgements_used"], [ack])
        self.assertTrue(all(item["assumption_acknowledgements_used"] == [ack]
                            for parameter in oat["parameters"]
                            for item in (parameter["minus_scenario"], parameter["plus_scenario"])))
        self.assertEqual(problem["candidates"][0]["boundary_conditions"]["downstream"]["resistance"]["status"], "assumed")

    def test_oat_only_assumed_path_without_ack_blocks_oat_not_core(self) -> None:
        problem = add_unused_oat_property(baseline_problem(), "assumed")
        plan = oat_plan(problem, "total_thermal_resistance", [
            oat_parameter(
                OAT_ONLY_PROPERTY,
                QuantityKind.THERMAL_CONDUCTIVITY,
                "1000",
                "1400",
                "W/(m*K)",
            ),
        ])
        result = run(problem, plan)
        candidate = first_candidate(result)
        core = candidate["core_scenarios"][0]
        parameter = candidate["oat_result"]["parameters"][0]
        self.assertEqual(core["disposition"], "evaluated")
        self.assertEqual(core["assumption_acknowledgements_used"], [])
        self.assertNotIn(
            OAT_ONLY_PROPERTY,
            [item["field_path"] for item in core["consumed_input_paths"]],
        )
        self.assertEqual(parameter["disposition"], "incomplete")
        for scenario in (parameter["minus_scenario"], parameter["plus_scenario"]):
            self.assertEqual(scenario["disposition"], "blocked")
            self.assertIsNone(scenario["numerical_result"])
            self.assertIn("I4-BIND-ACKNOWLEDGEMENT-CLOSURE", ids(scenario["execution_findings"]))
            self.assertIn(
                OAT_ONLY_PROPERTY,
                [item["field_path"] for item in scenario["consumed_input_paths"]],
            )
        execution = result["candidate_execution"][0]
        self.assertEqual(
            (execution["execution_status"], execution["applicability_status"], execution["result_presence"]),
            ("evaluated", "applicable_with_warnings", True),
        )
        self.assertEqual(execution["assumption_acknowledgements_used"], [])
        self.assertEqual(result["assumptions_used"], [])
        self.assertIn("I4-OAT-INCOMPLETE", ids(result["warnings"]))
        self.assertIn("I4-SCENARIO-PARTIAL-COVERAGE", ids(result["warnings"]))
        with tempfile.TemporaryDirectory() as temporary:
            case = Path(temporary) / problem["case_id"]
            epr_dir = case / "engineering" / "problems"
            epr_dir.mkdir(parents=True)
            (epr_dir / "EPR-001.json").write_bytes(canonical_json_bytes(problem))
            bound = bind_evaluation_plan(case, EvaluationPlan.from_dict(plan))
            eer = build_strict_1d_engineering_evaluation_result(bound, "EER-001").to_dict()
            self.assertEqual(len(eer["prediction_outputs"]), 3)
            self.assertEqual(eer["assumptions_used"], [])

    def test_oat_only_assumed_path_exact_ack_is_scenario_local_and_used_once(self) -> None:
        problem = add_unused_oat_property(baseline_problem(), "assumed")
        original_envelope = copy.deepcopy(
            problem["candidates"][0]["materials"][2]["thermal_properties"][0]["thermal_conductivity"]
        )
        acknowledgement = {
            "scope": "candidate",
            "candidate_id": "CND-001",
            "field_path": OAT_ONLY_PROPERTY,
        }
        plan = oat_plan(problem, "total_thermal_resistance", [
            oat_parameter(
                OAT_ONLY_PROPERTY,
                QuantityKind.THERMAL_CONDUCTIVITY,
                "1000",
                "1400",
                "W/(m*K)",
            ),
        ])
        plan["assumption_acknowledgements"] = [acknowledgement]
        result = run(problem, plan)
        candidate = first_candidate(result)
        core = candidate["core_scenarios"][0]
        parameter = candidate["oat_result"]["parameters"][0]
        self.assertEqual(core["disposition"], "evaluated")
        self.assertEqual(core["assumption_acknowledgements_used"], [])
        self.assertNotIn("I4-BIND-ACKNOWLEDGEMENT-CLOSURE", ids(core["execution_findings"]))
        for scenario in (parameter["minus_scenario"], parameter["plus_scenario"]):
            self.assertEqual(scenario["disposition"], "evaluated")
            self.assertIn(
                OAT_ONLY_PROPERTY,
                [item["field_path"] for item in scenario["consumed_input_paths"]],
            )
            self.assertEqual(scenario["assumption_acknowledgements_used"], [acknowledgement])
            self.assertNotIn("I4-BIND-ACKNOWLEDGEMENT-CLOSURE", ids(scenario["execution_findings"]))
        self.assertEqual(parameter["disposition"], "complete")
        self.assertIsNotNone(parameter["dimensional_derivative"])
        self.assertEqual(result["candidate_execution"][0]["assumption_acknowledgements_used"], [acknowledgement])
        self.assertEqual(result["assumptions_used"], [acknowledgement])
        self.assertEqual(
            problem["candidates"][0]["materials"][2]["thermal_properties"][0]["thermal_conductivity"],
            original_envelope,
        )
        with tempfile.TemporaryDirectory() as temporary:
            case = Path(temporary) / problem["case_id"]
            epr_dir = case / "engineering" / "problems"
            epr_dir.mkdir(parents=True)
            (epr_dir / "EPR-001.json").write_bytes(canonical_json_bytes(problem))
            bound = bind_evaluation_plan(case, EvaluationPlan.from_dict(plan))
            eer = build_strict_1d_engineering_evaluation_result(bound, "EER-001").to_dict()
            self.assertEqual(eer["assumptions_used"], [acknowledgement])
            self.assertEqual(len(eer["prediction_outputs"]), 3)

    def test_oat_only_evidence_required_warns_only_affected_scenarios(self) -> None:
        problem = add_unused_oat_property(baseline_problem(), "evidence_required")
        plan = oat_plan(problem, "total_thermal_resistance", [
            oat_parameter(
                OAT_ONLY_PROPERTY,
                QuantityKind.THERMAL_CONDUCTIVITY,
                "1000",
                "1400",
                "W/(m*K)",
            ),
        ])
        result = run(problem, plan)
        candidate = first_candidate(result)
        core = candidate["core_scenarios"][0]
        parameter = candidate["oat_result"]["parameters"][0]
        self.assertEqual(core["disposition"], "evaluated")
        self.assertEqual(core["applicability_status"], "applicable")
        self.assertNotIn("I4-BIND-EVIDENCE-REQUIRED", ids(core["execution_findings"]))
        for scenario in (parameter["minus_scenario"], parameter["plus_scenario"]):
            self.assertEqual(scenario["disposition"], "evaluated")
            self.assertEqual(scenario["applicability_status"], "applicable_with_warnings")
            self.assertIn("I4-BIND-EVIDENCE-REQUIRED", ids(scenario["execution_findings"]))
            self.assertEqual(scenario["assumption_acknowledgements_used"], [])
        self.assertEqual(parameter["disposition"], "complete")
        self.assertIsNotNone(parameter["dimensional_derivative"])
        self.assertEqual(result["candidate_execution"][0]["execution_status"], "evaluated")
        self.assertEqual(result["candidate_execution"][0]["applicability_status"], "applicable_with_warnings")
        self.assertEqual(result["assumptions_used"], [])
        self.assertIn("I4-BIND-EVIDENCE-REQUIRED", ids(candidate["warnings"]))

    def test_oat_only_provided_executes_and_missing_cannot_be_repaired_by_points(self) -> None:
        provided = add_unused_oat_property(baseline_problem(), "provided")
        provided_plan = oat_plan(provided, "total_thermal_resistance", [
            oat_parameter(
                OAT_ONLY_PROPERTY,
                QuantityKind.THERMAL_CONDUCTIVITY,
                "1000",
                "1400",
                "W/(m*K)",
            ),
        ])
        provided_result = run(provided, provided_plan)
        provided_parameter = first_candidate(provided_result)["oat_result"]["parameters"][0]
        self.assertEqual(provided_parameter["disposition"], "complete")
        self.assertTrue(all(
            scenario["disposition"] == "evaluated"
            for scenario in (provided_parameter["minus_scenario"], provided_parameter["plus_scenario"])
        ))
        self.assertEqual(provided_result["candidate_execution"][0]["applicability_status"], "applicable")

        missing = add_unused_oat_property(baseline_problem(), "provided")
        missing["candidates"][0]["materials"][2]["thermal_properties"][0]["thermal_conductivity"] = (
            missing_envelope(QuantityKind.THERMAL_CONDUCTIVITY, "W/(m*K)")
        )
        missing["compilation"]["outcome"] = "HOLD_FOR_INPUT"
        _restamp(missing)
        missing_plan = oat_plan(missing, "total_thermal_resistance", [
            oat_parameter(
                OAT_ONLY_PROPERTY,
                QuantityKind.THERMAL_CONDUCTIVITY,
                "1000",
                "1400",
                "W/(m*K)",
            ),
        ])
        with tempfile.TemporaryDirectory() as temporary:
            case = Path(temporary) / missing["case_id"]
            epr_dir = case / "engineering" / "problems"
            epr_dir.mkdir(parents=True)
            (epr_dir / "EPR-001.json").write_bytes(canonical_json_bytes(missing))
            with self.assertRaisesRegex(ValueError, "non-null numeric physical value"):
                bind_evaluation_plan(case, EvaluationPlan.from_dict(missing_plan))

    def test_oat_only_nonphysical_conductivity_points_are_invalid(self) -> None:
        for minus_value in ("0", "-100"):
            with self.subTest(minus_value=minus_value):
                problem = add_unused_oat_property(baseline_problem(), "provided")
                plan = oat_plan(problem, "total_thermal_resistance", [
                    oat_parameter(
                        OAT_ONLY_PROPERTY,
                        QuantityKind.THERMAL_CONDUCTIVITY,
                        minus_value,
                        "1400",
                        "W/(m*K)",
                    ),
                ])
                result = run(problem, plan)
                candidate = first_candidate(result)
                parameter = candidate["oat_result"]["parameters"][0]
                minus = parameter["minus_scenario"]
                plus = parameter["plus_scenario"]

                self.assertEqual(candidate["core_scenarios"][0]["disposition"], "evaluated")
                self.assertEqual(minus["disposition"], "invalid")
                self.assertIsNone(minus["numerical_result"])
                self.assertEqual(plus["disposition"], "evaluated")
                self.assertEqual(parameter["disposition"], "incomplete")
                self.assertIsNone(parameter["dimensional_derivative"])
                self.assertIsNone(parameter["normalized_sensitivity"])
                self.assertEqual(parameter["finding_ids"], ["I4-OAT-INCOMPLETE"])
                self.assertIn(
                    "I4-SCENARIO-INVALID-OVERRIDE", ids(minus["execution_findings"])
                )
                self.assertEqual(minus["input_overrides"][0]["field_path"], OAT_ONLY_PROPERTY)
                self.assertEqual(minus["input_overrides"][0]["value"]["value"], minus_value)
                self.assertIn(
                    OAT_ONLY_PROPERTY,
                    [item["field_path"] for item in minus["consumed_input_paths"]],
                )
                execution = result["candidate_execution"][0]
                self.assertEqual(
                    (
                        execution["execution_status"],
                        execution["result_presence"],
                        execution["applicability_status"],
                    ),
                    ("evaluated", True, "applicable_with_warnings"),
                )
                self.assertIn("I4-OAT-INCOMPLETE", ids(result["warnings"]))
                self.assertIn("I4-SCENARIO-PARTIAL-COVERAGE", ids(result["warnings"]))
                with tempfile.TemporaryDirectory() as temporary:
                    case = Path(temporary) / problem["case_id"]
                    epr_dir = case / "engineering" / "problems"
                    epr_dir.mkdir(parents=True)
                    (epr_dir / "EPR-001.json").write_bytes(canonical_json_bytes(problem))
                    bound = bind_evaluation_plan(case, EvaluationPlan.from_dict(plan))
                    eer = build_strict_1d_engineering_evaluation_result(
                        bound, "EER-001"
                    ).to_dict()
                    self.assertEqual(len(eer["prediction_outputs"]), 3)

    def test_ideal_zero_positive_oat_and_sweep_points_are_invalid(self) -> None:
        problem = baseline_problem()
        interface = problem["candidates"][0]["interfaces"][0]
        interface["representation_type"] = "ideal_zero"
        interface["value"] = envelope(
            QuantityKind.AREA_THERMAL_RESISTANCE, "0", "m^2*K/W"
        )
        _restamp(problem)

        plan = oat_plan(problem, "total_thermal_resistance", [
            oat_parameter(
                "/interfaces/0/value",
                QuantityKind.AREA_THERMAL_RESISTANCE,
                "0",
                "1e-9",
                "m^2*K/W",
            ),
        ])
        result = run(problem, plan)
        candidate = first_candidate(result)
        core = candidate["core_scenarios"][0]
        parameter = candidate["oat_result"]["parameters"][0]
        minus = parameter["minus_scenario"]
        plus = parameter["plus_scenario"]

        self.assertEqual(core["disposition"], "evaluated")
        self.assertEqual(
            core["numerical_result"]["interface_resistance_contributions"][0]["resistance"]["value"],
            "0",
        )
        self.assertEqual(minus["disposition"], "evaluated")
        self.assertEqual(plus["disposition"], "invalid")
        self.assertIsNone(plus["numerical_result"])
        self.assertIn("I4-SCENARIO-INVALID-OVERRIDE", ids(plus["execution_findings"]))
        self.assertEqual(plus["input_overrides"][0]["field_path"], "/interfaces/0/value")
        self.assertEqual(plus["input_overrides"][0]["value"]["value"], "0.000000001")
        self.assertIn(
            "/interfaces/0/value",
            [item["field_path"] for item in plus["consumed_input_paths"]],
        )
        self.assertEqual(parameter["disposition"], "incomplete")
        self.assertIsNone(parameter["dimensional_derivative"])
        self.assertIsNone(parameter["normalized_sensitivity"])
        self.assertEqual(parameter["finding_ids"], ["I4-OAT-INCOMPLETE"])
        self.assertEqual(
            (
                result["candidate_execution"][0]["execution_status"],
                result["candidate_execution"][0]["result_presence"],
                result["candidate_execution"][0]["applicability_status"],
            ),
            ("evaluated", True, "applicable_with_warnings"),
        )
        self.assertIn("I4-OAT-INCOMPLETE", ids(result["warnings"]))
        self.assertIn("I4-SCENARIO-PARTIAL-COVERAGE", ids(result["warnings"]))

        sweep = grid(
            "SWP-001",
            "CND-001",
            "/interfaces/0/value",
            QuantityKind.AREA_THERMAL_RESISTANCE,
            ["1e-9"],
            "m^2*K/W",
        )
        sweep_scenario = first_candidate(
            run(problem, make_plan(problem, sweeps=[sweep]))
        )["core_scenarios"][0]
        self.assertEqual(sweep_scenario["disposition"], "invalid")
        self.assertIsNone(sweep_scenario["numerical_result"])
        self.assertIn(
            "I4-SCENARIO-INVALID-OVERRIDE",
            ids(sweep_scenario["execution_findings"]),
        )
        self.assertEqual(
            sweep_scenario["input_overrides"][0]["field_path"], "/interfaces/0/value"
        )
        self.assertEqual(
            sweep_scenario["input_overrides"][0]["value"]["value"], "0.000000001"
        )


class OutputIdentityTests(unittest.TestCase):
    def test_output_order_pointers_and_determinism(self) -> None:
        problem = baseline_problem()
        plan = oat_plan(problem, "total_thermal_resistance", [
            oat_parameter(BOUNDARY, QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "0.5", "2.5", "K/W"),
        ])
        plan["selected_candidate_ids"] = ["CND-001", "CND-002"]
        plan["maximum_requested_combination_count"] = 2
        with tempfile.TemporaryDirectory() as temporary:
            case = Path(temporary) / problem["case_id"]
            epr_dir = case / "engineering" / "problems"
            epr_dir.mkdir(parents=True)
            (epr_dir / "EPR-001.json").write_bytes(canonical_json_bytes(problem))
            bound = bind_evaluation_plan(case, EvaluationPlan.from_dict(plan))
            first = build_strict_1d_engineering_evaluation_result(bound, "EER-001")
            second = build_strict_1d_engineering_evaluation_result(bound, "EER-001")
            self.assertEqual(first.canonical_bytes(), second.canonical_bytes())
            data = first.to_dict()
            self.assertEqual(
                [item["output_id"] for item in data["prediction_outputs"]],
                [f"EER-001-OUT-{i:03d}" for i in range(1, 7)],
            )
            self.assertEqual(
                [item["candidate_id"] for item in data["prediction_outputs"]],
                ["CND-001"] * 3 + ["CND-002"] * 3,
            )
            self.assertEqual(
                [item["quantity_label"] for item in data["prediction_outputs"]],
                ["source_temperature", "temperature_rise", "total_thermal_resistance"] * 2,
            )
            content = data["result_payload"]["content"]
            self.assertIsNone(content["candidate_results"][1]["oat_result"])
            self.assertIsNone(content["candidate_results"][1]["coverage_summary"]["oat_coverage"])
            for output in data["prediction_outputs"]:
                resolved = content
                for token in output["result_pointer"].split("/")[1:]:
                    resolved = resolved[int(token)] if type(resolved) is list else resolved[token]
                self.assertEqual(resolved, output["value"])
                index = data["candidate_execution"].index(next(
                    item for item in data["candidate_execution"] if item["candidate_id"] == output["candidate_id"]
                ))
                quantity = content["candidate_results"][index]["core_scenarios"][0]["numerical_result"][output["quantity_label"]]
                self.assertEqual((output["value"], output["quantity_kind"], output["unit"]),
                                 (quantity["value"], quantity["quantity_kind"], quantity["unit"]))
                self.assertIsNone(output["lower_bound"])
                self.assertIsNone(output["upper_bound"])

    def test_epr_plan_eer_persistence_reload_and_prediction_reality_projection(self) -> None:
        problem = baseline_problem()
        plan = oat_plan(problem, "total_thermal_resistance", [
            oat_parameter(BOUNDARY, QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "0.5", "2.5", "K/W"),
        ])
        with tempfile.TemporaryDirectory() as temporary:
            case = Path(temporary) / problem["case_id"]
            epr_dir = case / "engineering" / "problems"
            epr_dir.mkdir(parents=True)
            (epr_dir / "EPR-001.json").write_bytes(canonical_json_bytes(problem))
            bound = bind_evaluation_plan(case, EvaluationPlan.from_dict(plan))
            eer = build_strict_1d_engineering_evaluation_result(bound, "EER-001")
            path = write_engineering_evaluation_result(bound, eer)
            loaded = load_engineering_evaluation_result(case, "EER-001")
            self.assertEqual(path.read_bytes(), eer.canonical_bytes())
            self.assertEqual(loaded.evaluation_result.canonical_bytes(), eer.canonical_bytes())
            self.assertEqual(loaded.eer_file_sha256, hashlib.sha256(path.read_bytes()).hexdigest())
            output = eer.to_dict()["prediction_outputs"][0]

            (case / "00_problem_intake.yml").write_text(
                f"case_id: {case.name}\n", encoding="utf-8"
            )
            evidence_path = case / "evidence" / "EVD-001.json"
            create_evidence_template(case, "EVD-001", "measurement", evidence_path)
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence.update({
                "title": "SYNTHETIC TEST DATA - NOT AN ENGINEERING RESULT",
                "status": "reviewed",
                "evidence_level": "independently_measured",
                "source": {"reference": "controlled-synthetic-source", "sha256": "a" * 64},
                "method_summary": "Synthetic fixture method.",
                "applicability": "Synthetic fixture only.",
                "uncertainty_summary": "Synthetic fixture uncertainty.",
                "public_summary": "Synthetic metadata only.",
                "reviewed_by": "Synthetic reviewer declaration",
            })
            evidence_path.write_text(json.dumps(evidence, sort_keys=True) + "\n", encoding="utf-8")
            measurement_path = case / "measurements" / "MSR-001.json"
            create_measurement_template(case, "MSR-001", "EVD-001", measurement_path)
            measurement = json.loads(measurement_path.read_text(encoding="utf-8"))
            measurement.update({
                "measurement_id": "MSR-001",
                "case_id": case.name,
                "status": "reviewed",
                "quantity": "source_temperature",
                "value": 67.325,
                "unit": "degC",
                "sample_id": "ANON-SYN-001",
                "method": "Synthetic fixture method.",
                "operating_conditions": "Synthetic fixture conditions.",
                "uncertainty": {"numeric_value": 2, "unit": "degC", "basis": "Synthetic fixture uncertainty basis."},
                "raw_data_reference": "controlled-synthetic-raw-reference",
                "raw_data_sha256": "b" * 64,
                "reviewed_by": "Synthetic reviewer declaration",
            })
            measurement_path.write_text(json.dumps(measurement, sort_keys=True) + "\n", encoding="utf-8")
            projection = project_eer_prediction_to_measurement(
                loaded, output["output_id"], "MSR-001"
            ).to_dict()
            self.assertEqual(projection["source_evaluation_id"], "EER-001")
            self.assertEqual(projection["source_eer_content_sha256"], eer.content_sha256)
            self.assertEqual(projection["source_eer_file_sha256"], loaded.eer_file_sha256)
            self.assertEqual(projection["source_output_id"], output["output_id"])
            self.assertEqual(projection["source_candidate_id"], "CND-001")
            self.assertEqual(projection["measurement_id"], "MSR-001")
            self.assertEqual(projection["prediction"]["value"], 67.325)
            self.assertEqual(projection["prediction"]["unit"], "degC")


class AnalyticAndNegativeFixtureTests(unittest.TestCase):
    def test_fix_01_complete_analytic_fixture(self) -> None:
        problem = baseline_problem()
        add_constraint(problem)
        baseline = run(problem, make_plan(problem, candidates=["CND-001", "CND-002"]))
        diamond = first_candidate(baseline)["core_scenarios"][0]
        copper = baseline["result_payload"]["content"]["candidate_results"][1]["core_scenarios"][0]
        numerical = diamond["numerical_result"]
        self.assertEqual(
            [item["resistance"]["value"] for item in numerical["layer_resistance_contributions"]],
            ["0.15625", "0.075"],
        )
        self.assertEqual(numerical["interface_resistance_contributions"][0]["resistance"]["value"], "0.00125")
        self.assertEqual(numerical["boundary_resistance_contribution"]["resistance"]["value"], "1.5")
        self.assertEqual(numerical["total_thermal_resistance"]["value"], "1.7325")
        self.assertEqual(numerical["temperature_rise"]["value"], "17.325")
        self.assertEqual(numerical["reference_temperature"]["value"], "323.15")
        self.assertEqual(numerical["source_temperature"]["value"], "340.475")
        self.assertEqual(diamond["constraint_results"][0]["limit"]["value"], "348.15")
        self.assertEqual(diamond["constraint_results"][0]["margin"]["value"], "7.675")
        self.assertEqual(copper["numerical_result"]["total_thermal_resistance"]["value"], "1.845")
        self.assertEqual(copper["numerical_result"]["source_temperature"]["value"], "341.6")
        self.assertEqual(
            Decimal(copper["numerical_result"]["source_temperature"]["value"])
            - Decimal(numerical["source_temperature"]["value"]), Decimal("1.125")
        )
        fixtures = (
            (THICKNESS, QuantityKind.LENGTH, ["200", "300", "500"], "um", ["340.225", "340.475", "340.975"]),
            ("/interfaces/0/value", QuantityKind.AREA_THERMAL_RESISTANCE,
             ["2e-9", "10e-9"], "m^2*K/W", ["340.4675", "340.4875"]),
            ("/materials/1/thermal_properties/0/thermal_conductivity", QuantityKind.THERMAL_CONDUCTIVITY,
             ["800", "1500"], "W/(m*K)", ["340.6625", "340.225"]),
            (BOUNDARY, QuantityKind.ABSOLUTE_THERMAL_RESISTANCE,
             ["0.5", "2.5"], "K/W", ["330.475", "350.475"]),
        )
        for path, kind, points, unit, expected in fixtures:
            with self.subTest(path=path):
                sweep = grid("SWP-001", "CND-001", path, kind, points, unit)
                scenarios = first_candidate(run(problem, make_plan(problem, sweeps=[sweep])))["core_scenarios"]
                self.assertEqual(
                    [item["numerical_result"]["source_temperature"]["value"] for item in scenarios],
                    expected,
                )
                if path == BOUNDARY:
                    self.assertEqual(scenarios[1]["constraint_results"][0]["margin"]["value"], "-2.325")

    def test_fix_02_negative_and_invariant_matrix(self) -> None:
        # Each row executes the public orchestration API against a stamped EPR.
        def checked(problem: dict, expected: str, rule: str | None = None) -> dict:
            _restamp(problem)
            result = run(problem, make_plan(problem))
            scenario = first_candidate(result)["core_scenarios"][0]
            self.assertEqual(scenario["disposition"], expected)
            if rule:
                self.assertIn(rule, ids(scenario["applicability_findings"] + scenario["execution_findings"]))
            return scenario

        area = baseline_problem()
        area["candidates"][0]["geometry"]["layers"][1]["footprint_area"] = envelope(QuantityKind.AREA, "9", "mm^2")
        checked(area, "not_applicable", "I4-APP-CONSTANT-AREA")
        convection = baseline_problem()
        convection["candidates"][0]["boundary_conditions"]["downstream"] = {
            "representation_type": "direct_convection",
            "heat_transfer_coefficient": envelope(QuantityKind.AREA_THERMAL_CONDUCTANCE, "1000", "W/(m^2*K)"),
            "boundary_area": envelope(QuantityKind.AREA, "9", "mm^2"),
            "ambient_temperature": envelope(QuantityKind.ABSOLUTE_TEMPERATURE, "323.15", "K"),
            "operating_basis": "Public-safe synthetic mismatch.",
        }
        checked(convection, "not_applicable", "I4-APP-CONVECTION-COMMON-AREA")
        base_variants = (
            ("area", ("heat_sources", 0, "heated_area"), QuantityKind.AREA, "0", "m^2"),
            ("thickness", ("candidates", 0, "geometry", "layers", 0, "thickness"), QuantityKind.LENGTH, "0", "m"),
            ("conductivity", ("candidates", 0, "materials", 0, "thermal_properties", 0, "thermal_conductivity"), QuantityKind.THERMAL_CONDUCTIVITY, "-1", "W/(m*K)"),
            ("tbr", ("candidates", 0, "interfaces", 0, "value"), QuantityKind.AREA_THERMAL_RESISTANCE, "-1e-9", "m^2*K/W"),
        )
        for label, path, kind, value, unit in base_variants:
            with self.subTest(bound=label):
                problem = baseline_problem()
                current = problem
                for token in path[:-1]:
                    current = current[token]
                current[path[-1]] = envelope(kind, value, unit)
                checked(problem, "blocked", "I4-NUM-NONPHYSICAL-BASE-INPUT")
        negative_area = baseline_problem()
        negative_area["heat_sources"][0]["heated_area"] = envelope(QuantityKind.AREA, "-1", "m^2")
        checked(negative_area, "blocked", "I4-NUM-NONPHYSICAL-BASE-INPUT")
        explicit = (
            ("area", "/geometry/layers/1/footprint_area", QuantityKind.AREA, "0", "mm^2"),
            ("thickness", THICKNESS, QuantityKind.LENGTH, "0", "um"),
            ("conductivity", "/materials/1/thermal_properties/0/thermal_conductivity", QuantityKind.THERMAL_CONDUCTIVITY, "0", "W/(m*K)"),
            ("tbr", "/interfaces/0/value", QuantityKind.AREA_THERMAL_RESISTANCE, "-1e-9", "m^2*K/W"),
        )
        for label, path, kind, value, unit in explicit:
            with self.subTest(explicit=label):
                problem = baseline_problem()
                sweep = grid("SWP-001", "CND-001", path, kind, [value], unit)
                scenario = first_candidate(run(problem, make_plan(problem, sweeps=[sweep])))["core_scenarios"][0]
                self.assertEqual(scenario["disposition"], "invalid")
        oat_area = baseline_problem()
        oat = oat_plan(oat_area, "total_thermal_resistance", [
            oat_parameter("/geometry/layers/1/footprint_area", QuantityKind.AREA, "0", "4", "mm^2")
        ])
        self.assertEqual(first_candidate(run(oat_area, oat))["oat_result"]["parameters"][0]["minus_scenario"]["disposition"], "invalid")
        zero_tbr = baseline_problem()
        zero_tbr["candidates"][0]["interfaces"][0]["value"] = envelope(
            QuantityKind.AREA_THERMAL_RESISTANCE, "0", "m^2*K/W"
        )
        checked(zero_tbr, "evaluated")
        missing = baseline_problem()
        missing["candidates"][0]["boundary_conditions"]["downstream"]["resistance"] = missing_envelope(
            QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "K/W"
        )
        missing["compilation"]["outcome"] = "HOLD_FOR_INPUT"
        checked(missing, "blocked", "I4-BIND-MISSING-INPUT")
        multiple = baseline_problem()
        second = copy.deepcopy(multiple["heat_sources"][0])
        second["source_id"] = "HSR-002"
        multiple["heat_sources"].append(second)
        checked(multiple, "not_applicable", "I4-APP-SINGLE-HEAT-SOURCE")
        parallel = baseline_problem()
        parallel["candidates"][0]["boundary_conditions"]["source_side"]["path_disposition"] = "declared_parallel_paths"
        checked(parallel, "not_applicable", "I4-APP-SINGLE-SERIES-PATH")
        distributed = baseline_problem()
        distributed["heat_sources"][0]["spatial_profile"] = "volumetric"
        checked(distributed, "not_applicable", "I4-APP-NO-DISTRIBUTED-GENERATION")
        rotated = baseline_problem()
        rotated["candidates"][0]["materials"][0]["anisotropy_representation"] = "rotated_tensor"
        checked(rotated, "not_applicable", "I4-APP-NORMAL-CONDUCTIVITY")
        prose = baseline_problem()
        prose["candidates"][0]["materials"][0]["thermal_properties"][0]["temperature_basis"] = "Synthetic constant property."
        checked(prose, "evaluated")
        unsupported_interface = baseline_problem()
        unsupported_interface["candidates"][0]["interfaces"][0]["representation_type"] = "absolute_resistance"
        unsupported_interface["candidates"][0]["interfaces"][0]["value"] = envelope(
            QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "0.1", "K/W"
        )
        checked(unsupported_interface, "not_applicable", "I4-APP-SUPPORTED-INTERFACE")
        unsupported_boundary = baseline_problem()
        unsupported_boundary["candidates"][0]["boundary_conditions"]["downstream"] = {
            "representation_type": "other", "description": "Synthetic unsupported boundary."
        }
        checked(unsupported_boundary, "not_applicable", "I4-APP-SUPPORTED-BOUNDARY")
        fixed = baseline_problem()
        fixed["candidates"][0]["boundary_conditions"]["downstream"] = {
            "representation_type": "fixed_temperature",
            "terminal_plane": "Explicit synthetic reference plane.",
            "reference_temperature": envelope(QuantityKind.ABSOLUTE_TEMPERATURE, "323.15", "K"),
        }
        fixed_numerical = checked(fixed, "evaluated")["numerical_result"]
        self.assertEqual(fixed_numerical["boundary_resistance_contribution"]["resistance"]["value"], "0")
        nodes = [Decimal(item["temperature"]["value"]) for item in fixed_numerical["node_temperatures"]]
        self.assertTrue(all(a >= b for a, b in zip(nodes, nodes[1:])))
        missing_boundary = baseline_problem()
        missing_boundary["candidates"][0]["boundary_conditions"]["downstream"]["resistance"] = missing_envelope(
            QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "K/W"
        )
        missing_boundary["compilation"]["outcome"] = "HOLD_FOR_INPUT"
        checked(missing_boundary, "blocked", "I4-BIND-MISSING-INPUT")
        assumed = baseline_problem()
        assumed["candidates"][0]["boundary_conditions"]["downstream"]["resistance"] = envelope(
            QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "1.5", "K/W", status="assumed"
        )
        assumed["candidates"][0]["assumption_paths"] = [BOUNDARY]
        assumed["compilation"]["outcome"] = "READY_WITH_ASSUMPTIONS"
        checked(assumed, "blocked", "I4-BIND-ACKNOWLEDGEMENT-CLOSURE")
        extra = baseline_problem()
        unused = envelope(QuantityKind.THERMAL_CONDUCTIVITY, "2000", "W/(m*K)", status="assumed")
        extra["candidates"][0]["materials"].append({
            "material_id": "MAT-003", "label": "Unused synthetic material",
            "material_class": "synthetic solid", "anisotropy_representation": "isotropic",
            "thermal_properties": [{
                "property_id": "PRP-003", "component": "isotropic",
                "thermal_conductivity": unused, "temperature_basis": "Synthetic constant basis.",
                "condition_basis": "Synthetic fixture.",
            }],
        })
        unused_path = "/materials/2/thermal_properties/0/thermal_conductivity"
        extra["candidates"][0]["assumption_paths"] = [unused_path]
        _restamp(extra)
        extra_plan = make_plan(extra)
        extra_plan["assumption_acknowledgements"] = [{
            "scope": "candidate", "candidate_id": "CND-001", "field_path": unused_path,
        }]
        extra_result = run(extra, extra_plan)
        self.assertEqual(first_candidate(extra_result)["core_scenarios"][0]["disposition"], "blocked")
        self.assertIn("I4-BIND-ACKNOWLEDGEMENT-CLOSURE", ids(first_candidate(extra_result)["core_scenarios"][0]["execution_findings"]))
        self.assertEqual(first_candidate(extra_result)["core_scenarios"][0]["assumption_acknowledgements_used"], [])
        temperature_law = baseline_problem()
        law_plan = make_plan(temperature_law)
        law_plan["model_options"]["strict_1d_validity_assertions"]["no_temperature_dependent_material_law"] = False
        law_result = run(temperature_law, law_plan)
        self.assertEqual(first_candidate(law_result)["core_scenarios"][0]["disposition"], "blocked")
        self.assertIn("I4-BIND-MISSING-INPUT", ids(first_candidate(law_result)["core_scenarios"][0]["execution_findings"]))
        mixed = baseline_problem()
        sweep = grid("SWP-001", "CND-001", "/geometry/layers/1/footprint_area", QuantityKind.AREA,
                     ["4", "9", "0"], "mm^2")
        mixed_result = run(mixed, make_plan(mixed, sweeps=[sweep]))
        self.assertEqual([item["disposition"] for item in first_candidate(mixed_result)["core_scenarios"]],
                         ["evaluated", "not_applicable", "invalid"])
        self.assertEqual(mixed_result["candidate_execution"][0]["applicability_status"], "applicable_with_warnings")
        self.assertIn("I4-SCENARIO-PARTIAL-COVERAGE", ids(mixed_result["warnings"]))
        self.assertEqual(mixed_result["execution_outcome"], "completed")
        all_not_applicable = grid("SWP-001", "CND-001", "/geometry/layers/1/footprint_area", QuantityKind.AREA,
                                  ["8", "9"], "mm^2")
        all_na_result = run(baseline_problem(), make_plan(baseline_problem(), sweeps=[all_not_applicable]))
        self.assertEqual(all_na_result["candidate_execution"][0]["execution_status"], "not_applicable")
        self.assertFalse(all_na_result["candidate_execution"][0]["result_presence"])
        not_applicable_and_invalid = grid("SWP-001", "CND-001", "/geometry/layers/1/footprint_area", QuantityKind.AREA,
                                          ["9", "0"], "mm^2")
        mixed_blocked = run(baseline_problem(), make_plan(baseline_problem(), sweeps=[not_applicable_and_invalid]))
        self.assertEqual([item["disposition"] for item in first_candidate(mixed_blocked)["core_scenarios"]],
                         ["not_applicable", "invalid"])
        self.assertEqual(mixed_blocked["candidate_execution"][0]["execution_status"], "blocked")
        self.assertFalse(mixed_blocked["candidate_execution"][0]["result_presence"])
        self.assertEqual(len(first_candidate(run(baseline_problem(), make_plan(baseline_problem())))["core_scenarios"]), 1)
        swept = grid("SWP-001", "CND-001", THICKNESS, QuantityKind.LENGTH, ["200", "500"], "um")
        swept_result = run(baseline_problem(), make_plan(baseline_problem(), sweeps=[swept]))
        self.assertEqual(len(first_candidate(swept_result)["core_scenarios"]), 2)
        self.assertTrue(all(item["sweep_coordinates"] for item in first_candidate(swept_result)["core_scenarios"]))
        self.assertEqual(swept_result["result_payload"]["content"]["candidate_comparison"]["candidate_eligibility"][0]["reason_ids"],
                         ["I4-RANK-INELIGIBLE-BASIS"])
        oat_failed = oat_plan(baseline_problem(), "total_thermal_resistance", [
            oat_parameter(THICKNESS, QuantityKind.LENGTH, "-100", "500", "um")
        ])
        self.assertEqual(run(baseline_problem(), oat_failed)["candidate_execution"][0]["execution_status"], "evaluated")
        original = first_candidate(run(baseline_problem(), make_plan(baseline_problem())))["core_scenarios"][0]["numerical_result"]
        reordered_problem = baseline_problem()
        for root in (reordered_problem, reordered_problem["candidates"][0]):
            layers = root["geometry"]["layers"]
            layers.reverse()
            for index, layer in enumerate(layers):
                layer["order"] = index
            root["interfaces"][0]["upstream_layer_id"] = layers[0]["layer_id"]
            root["interfaces"][0]["downstream_layer_id"] = layers[1]["layer_id"]
        reordered_problem["heat_sources"][0]["source_location"]["layer_id"] = reordered_problem["geometry"]["layers"][0]["layer_id"]
        reordered = checked(reordered_problem, "evaluated")["numerical_result"]
        self.assertEqual(reordered["total_thermal_resistance"], original["total_thermal_resistance"])
        self.assertNotEqual(reordered["node_temperatures"], original["node_temperatures"])
        thick = baseline_problem()
        thick["candidates"][0]["geometry"]["layers"][0]["thickness"] = envelope(QuantityKind.LENGTH, "200", "um")
        self.assertEqual(checked(thick, "evaluated")["numerical_result"]["layer_resistance_contributions"][0]["resistance"]["value"], "0.3125")
        high_k = baseline_problem()
        high_k["candidates"][0]["materials"][0]["thermal_properties"][0]["thermal_conductivity"] = envelope(
            QuantityKind.THERMAL_CONDUCTIVITY, "320", "W/(m*K)"
        )
        self.assertEqual(checked(high_k, "evaluated")["numerical_result"]["layer_resistance_contributions"][0]["resistance"]["value"], "0.078125")
        large = baseline_problem()
        for root in (large, large["candidates"][0]):
            for layer in root["geometry"]["layers"]:
                layer["footprint_area"] = envelope(QuantityKind.AREA, "8", "mm^2")
                layer["footprint_dimensions"] = [envelope(QuantityKind.LENGTH, "4", "mm"), envelope(QuantityKind.LENGTH, "2", "mm")]
            root["interfaces"][0]["effective_area"] = envelope(QuantityKind.AREA, "8", "mm^2")
        large["heat_sources"][0]["heated_area"] = envelope(QuantityKind.AREA, "8", "mm^2")
        large["heat_sources"][0]["footprint"]["dimensions"] = [envelope(QuantityKind.LENGTH, "4", "mm"), envelope(QuantityKind.LENGTH, "2", "mm")]
        large_num = checked(large, "evaluated")["numerical_result"]
        self.assertEqual(large_num["layer_resistance_contributions"][0]["resistance"]["value"], "0.078125")
        self.assertEqual(large_num["interface_resistance_contributions"][0]["resistance"]["value"], "0.000625")
        deterministic_problem = baseline_problem()
        deterministic_plan = oat_plan(deterministic_problem, "total_thermal_resistance", [
            oat_parameter(BOUNDARY, QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "0.5", "2.5", "K/W")
        ])
        self.assertEqual(canonical_json_bytes(run(deterministic_problem, deterministic_plan)),
                         canonical_json_bytes(run(deterministic_problem, deterministic_plan)))
        authoritative = canonical_json_bytes(run(deterministic_problem, deterministic_plan))
        with localcontext() as context:
            context.prec = 2
            context.rounding = "ROUND_UP"
            self.assertEqual(canonical_json_bytes(run(deterministic_problem, deterministic_plan)), authoritative)


if __name__ == "__main__":
    unittest.main()
