from __future__ import annotations

import copy
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
    convert_quantity,
)
from labos.thermal import (
    Strict1DValidationError,
    build_strict_1d_engineering_evaluation_result,
    orchestrate_strict_1d,
)
from labos.thermal.strict_1d_orchestration import _aggregate_candidate
from tests.test_m16a_strict_1d_kernel import (
    _restamp,
    baseline_problem,
    envelope,
    plan_for,
)


def quantity(kind: QuantityKind, value: str, unit: str) -> dict:
    item = convert_quantity(kind, value, unit).to_dict()
    return {
        "value": item["canonical_value"],
        "unit": item["canonical_unit"],
        "quantity_kind": item["quantity_kind"],
        "conversion": item["conversion"],
    }


def grid(
    sweep_id: str,
    candidate_id: str,
    field_path: str,
    kind: QuantityKind,
    values: list[str],
    unit: str,
) -> dict:
    return {
        "sweep_id": sweep_id,
        "candidate_id": candidate_id,
        "field_path": field_path,
        "value_specification": {
            "kind": "grid",
            "values": [quantity(kind, value, unit) for value in values],
        },
    }


def range_sweep(
    start: str,
    stop: str,
    step: str,
    policy: str,
) -> dict:
    return {
        "sweep_id": "SWP-001",
        "candidate_id": "CND-001",
        "field_path": "/boundary_conditions/downstream/resistance",
        "value_specification": {
            "kind": "range",
            "start": quantity(QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, start, "K/W"),
            "stop": quantity(QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, stop, "K/W"),
            "step": quantity(QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, step, "K/W"),
            "endpoint_policy": policy,
        },
    }


def run(problem: dict, plan: dict) -> dict:
    return orchestrate_strict_1d(
        EngineeringProblem.from_dict(problem),
        EvaluationPlan.from_dict(plan),
    ).to_dict()


def candidate_result(result: dict, index: int = 0) -> dict:
    return result["result_payload"]["content"]["candidate_results"][index]


def add_constraint(
    problem: dict,
    *,
    operator: str = "le",
    disposition: str = "machine_evaluable",
    limit: str = "75",
    status: str = "provided",
    candidates: tuple[int, ...] = (0,),
) -> None:
    problem["constraints"] = [
        {
            "constraint_id": "CON-001",
            "target_path": "/heat_sources/0/source_location",
            "operator": operator,
            "threshold": envelope(
                QuantityKind.ABSOLUTE_TEMPERATURE,
                limit,
                "degC",
                status=status,
            ),
            "severity": "blocking",
            "provenance": copy.deepcopy(problem["requirements"][0]["provenance"]),
            "evaluation_disposition": disposition,
        }
    ]
    for index in candidates:
        problem["candidates"][index]["applicable_constraint_ids"] = ["CON-001"]
    if status == "assumed":
        problem["compilation"]["outcome"] = "READY_WITH_ASSUMPTIONS"
    _restamp(problem)


def set_temperature_margin(problem: dict) -> None:
    problem["requirements"][0]["target_path"] = "/heat_sources/0/source_location"
    problem["requirements"][0]["target"] = envelope(
        QuantityKind.ABSOLUTE_TEMPERATURE, "75", "degC"
    )
    _restamp(problem)


def make_plan(
    problem: dict,
    *,
    candidates: list[str] | None = None,
    sweeps: list[dict] | None = None,
) -> dict:
    selected = candidates or ["CND-001"]
    plan = plan_for(problem, candidate_ids=selected)
    plan["parameter_sweeps"] = copy.deepcopy(sweeps or [])
    parsed = EvaluationPlan.from_dict(
        {
            **plan,
            "maximum_requested_combination_count": 1000,
        }
    )
    plan["maximum_requested_combination_count"] = parsed.total_requested_combination_count
    return plan


class ScenarioAcceptanceTests(unittest.TestCase):
    def test_scn_01_unswept_baseline(self) -> None:
        problem = baseline_problem()
        result = run(problem, make_plan(problem))
        scenarios = candidate_result(result)["core_scenarios"]
        self.assertEqual([item["scenario_id"] for item in scenarios], ["SCN-C001-K000001"])
        self.assertEqual(scenarios[0]["sweep_coordinates"], [])

    def test_scn_02_swept_cartesian_has_no_hidden_baseline(self) -> None:
        problem = baseline_problem()
        sweeps = [
            grid(
                "SWP-001",
                "CND-001",
                "/geometry/layers/1/thickness",
                QuantityKind.LENGTH,
                ["200", "300"],
                "um",
            ),
            grid(
                "SWP-002",
                "CND-001",
                "/materials/1/thermal_properties/0/thermal_conductivity",
                QuantityKind.THERMAL_CONDUCTIVITY,
                ["800", "1500"],
                "W/(m*K)",
            ),
        ]
        scenarios = candidate_result(run(problem, make_plan(problem, sweeps=sweeps)))[
            "core_scenarios"
        ]
        self.assertEqual(len(scenarios), 4)
        self.assertEqual(
            [item["scenario_id"] for item in scenarios],
            [f"SCN-C001-K{index:06d}" for index in range(1, 5)],
        )
        self.assertTrue(all(len(item["sweep_coordinates"]) == 2 for item in scenarios))

    def test_scn_03_candidate_and_core_order_without_oat(self) -> None:
        problem = baseline_problem()
        plan = make_plan(problem, candidates=["CND-001", "CND-002"])
        result = run(problem, plan)
        results = result["result_payload"]["content"]["candidate_results"]
        self.assertEqual([item["candidate_id"] for item in results], ["CND-001", "CND-002"])
        self.assertEqual(
            [item["core_scenarios"][0]["scenario_id"] for item in results],
            ["SCN-C001-K000001", "SCN-C002-K000001"],
        )
        self.assertTrue(all(item["oat_result"] is None for item in results))
        cross_plan = make_plan(
            problem,
            candidates=["CND-001", "CND-002"],
            sweeps=[
                grid(
                    "SWP-001", "CND-001", "/geometry/layers/1/thickness",
                    QuantityKind.LENGTH, ["200", "300"], "um",
                ),
                grid(
                    "SWP-002", "CND-002", "/geometry/layers/1/thickness",
                    QuantityKind.LENGTH, ["200", "300", "500"], "um",
                ),
            ],
        )
        cross = run(problem, cross_plan)
        self.assertEqual(
            [item["coverage_summary"]["requested_core_scenarios"] for item in cross["result_payload"]["content"]["candidate_results"]],
            [2, 3],
        )
        rejected = copy.deepcopy(plan)
        rejected["sensitivity_request"] = {
            "method": "oat",
            "baseline_candidate_id": "CND-001",
            "output_metric": "source_temperature",
            "parameters": [
                {
                    "candidate_id": "CND-001",
                    "field_path": "/geometry/layers/1/thickness",
                    "minus_value": quantity(QuantityKind.LENGTH, "200", "um"),
                    "plus_value": quantity(QuantityKind.LENGTH, "500", "um"),
                }
            ],
        }
        with self.assertRaisesRegex(Strict1DValidationError, "I4B defers"):
            run(problem, rejected)

    def test_scn_04_nonphysical_override_is_retained_invalid(self) -> None:
        problem = baseline_problem()
        sweep = grid(
            "SWP-001",
            "CND-001",
            "/geometry/layers/1/thickness",
            QuantityKind.LENGTH,
            ["300", "0"],
            "um",
        )
        scenarios = candidate_result(run(problem, make_plan(problem, sweeps=[sweep])))[
            "core_scenarios"
        ]
        self.assertEqual([item["disposition"] for item in scenarios], ["evaluated", "invalid"])
        self.assertIn(
            "I4-SCENARIO-INVALID-OVERRIDE",
            {item["rule_id"] for item in scenarios[1]["execution_findings"]},
        )
        tbr = grid(
            "SWP-001", "CND-001", "/interfaces/0/value",
            QuantityKind.AREA_THERMAL_RESISTANCE,
            ["0", "-1e-9"], "m^2*K/W",
        )
        tbr_scenarios = candidate_result(run(problem, make_plan(problem, sweeps=[tbr])))[
            "core_scenarios"
        ]
        self.assertEqual([item["disposition"] for item in tbr_scenarios], ["evaluated", "invalid"])
        self.assertEqual(
            tbr_scenarios[0]["numerical_result"]["interface_resistance_contributions"][0]["resistance"]["value"],
            "0",
        )


class AggregationAcceptanceTests(unittest.TestCase):
    @staticmethod
    def coverage(*dispositions: str) -> dict:
        return {
            "requested_core_scenarios": len(dispositions),
            "evaluated_core_scenarios": dispositions.count("evaluated"),
            "blocked_core_scenarios": dispositions.count("blocked"),
            "invalid_core_scenarios": dispositions.count("invalid"),
            "not_applicable_core_scenarios": dispositions.count("not_applicable"),
            "oat_coverage": None,
        }

    @staticmethod
    def scenarios(*dispositions: str) -> list[dict]:
        return [
            {
                "disposition": disposition,
                "applicability_status": "applicable" if disposition == "evaluated" else "not_evaluated",
            }
            for disposition in dispositions
        ]

    def test_agg_01_evaluated_and_blocked(self) -> None:
        scenarios = self.scenarios("evaluated", "blocked")
        self.assertEqual(
            _aggregate_candidate(scenarios, self.coverage("evaluated", "blocked")),
            ("evaluated", "applicable_with_warnings", True),
        )

    def test_agg_02_evaluated_and_invalid(self) -> None:
        problem = baseline_problem()
        sweep = grid(
            "SWP-001",
            "CND-001",
            "/geometry/layers/1/thickness",
            QuantityKind.LENGTH,
            ["300", "0"],
            "um",
        )
        result = run(problem, make_plan(problem, sweeps=[sweep]))
        execution = result["candidate_execution"][0]
        self.assertEqual(
            (execution["execution_status"], execution["applicability_status"], execution["result_presence"]),
            ("evaluated", "applicable_with_warnings", True),
        )

    def test_agg_03_evaluated_and_not_applicable(self) -> None:
        problem = baseline_problem()
        sweep = grid(
            "SWP-001",
            "CND-001",
            "/geometry/layers/1/footprint_area",
            QuantityKind.AREA,
            ["4", "9"],
            "mm^2",
        )
        result = run(problem, make_plan(problem, sweeps=[sweep]))
        self.assertEqual(
            [item["disposition"] for item in candidate_result(result)["core_scenarios"]],
            ["evaluated", "not_applicable"],
        )
        self.assertEqual(result["candidate_execution"][0]["applicability_status"], "applicable_with_warnings")

    def test_agg_04_all_not_applicable(self) -> None:
        problem = baseline_problem()
        sweep = grid(
            "SWP-001",
            "CND-001",
            "/geometry/layers/1/footprint_area",
            QuantityKind.AREA,
            ["8", "9"],
            "mm^2",
        )
        execution = run(problem, make_plan(problem, sweeps=[sweep]))["candidate_execution"][0]
        self.assertEqual(
            (execution["execution_status"], execution["applicability_status"], execution["result_presence"]),
            ("not_applicable", "not_applicable", False),
        )

    def test_agg_05_not_applicable_and_invalid_without_result(self) -> None:
        problem = baseline_problem()
        sweep = grid(
            "SWP-001",
            "CND-001",
            "/geometry/layers/1/footprint_area",
            QuantityKind.AREA,
            ["9", "0"],
            "mm^2",
        )
        result = run(problem, make_plan(problem, sweeps=[sweep]))
        self.assertEqual(
            [item["disposition"] for item in candidate_result(result)["core_scenarios"]],
            ["not_applicable", "invalid"],
        )
        self.assertEqual(result["candidate_execution"][0]["execution_status"], "blocked")

    def test_agg_06_completed_with_partial_coverage_warning(self) -> None:
        problem = baseline_problem()
        sweep = grid(
            "SWP-001",
            "CND-001",
            "/geometry/layers/1/thickness",
            QuantityKind.LENGTH,
            ["300", "0"],
            "um",
        )
        result = run(problem, make_plan(problem, sweeps=[sweep]))
        self.assertEqual(result["execution_outcome"], "completed")
        self.assertIn(
            "I4-SCENARIO-PARTIAL-COVERAGE",
            {item["rule_id"] for item in result["warnings"]},
        )

    def test_agg_07_coverage_reconciles_exactly(self) -> None:
        problem = baseline_problem()
        sweep = grid(
            "SWP-001",
            "CND-001",
            "/geometry/layers/1/footprint_area",
            QuantityKind.AREA,
            ["4", "9", "0"],
            "mm^2",
        )
        coverage = candidate_result(run(problem, make_plan(problem, sweeps=[sweep])))[
            "coverage_summary"
        ]
        self.assertEqual(coverage["requested_core_scenarios"], 3)
        self.assertEqual(
            sum(
                coverage[field]
                for field in (
                    "evaluated_core_scenarios",
                    "blocked_core_scenarios",
                    "invalid_core_scenarios",
                    "not_applicable_core_scenarios",
                )
            ),
            3,
        )
        self.assertIsNone(coverage["oat_coverage"])
        two_candidates = baseline_problem()
        two_candidates["candidates"][1]["geometry"]["layers"][1]["footprint_area"] = envelope(
            QuantityKind.AREA, "9", "mm^2"
        )
        _restamp(two_candidates)
        partial = run(
            two_candidates,
            make_plan(two_candidates, candidates=["CND-001", "CND-002"]),
        )
        self.assertEqual(partial["execution_outcome"], "partial")


class SweepAcceptanceTests(unittest.TestCase):
    def test_swp_01_outermost_and_authored_order(self) -> None:
        problem = baseline_problem()
        sweeps = [
            grid(
                "SWP-001", "CND-001", "/geometry/layers/1/thickness",
                QuantityKind.LENGTH, ["500", "200"], "um",
            ),
            grid(
                "SWP-002", "CND-001",
                "/materials/1/thermal_properties/0/thermal_conductivity",
                QuantityKind.THERMAL_CONDUCTIVITY, ["1500", "800"], "W/(m*K)",
            ),
        ]
        scenarios = candidate_result(run(problem, make_plan(problem, sweeps=sweeps)))["core_scenarios"]
        coordinates = [
            tuple(point["value"]["value"] for point in scenario["sweep_coordinates"])
            for scenario in scenarios
        ]
        self.assertEqual(
            coordinates,
            [
                ("0.0005", "1500"),
                ("0.0005", "800"),
                ("0.0002", "1500"),
                ("0.0002", "800"),
            ],
        )

        fixtures = (
            (
                "/geometry/layers/1/thickness",
                QuantityKind.LENGTH,
                ["200", "300", "500"],
                "um",
                ["340.225", "340.475", "340.975"],
            ),
            (
                "/interfaces/0/value",
                QuantityKind.AREA_THERMAL_RESISTANCE,
                ["2e-9", "10e-9"],
                "m^2*K/W",
                ["340.4675", "340.4875"],
            ),
        )
        for path, kind, values, unit, expected in fixtures:
            with self.subTest(path=path):
                fixture_problem = baseline_problem()
                fixture_sweep = grid("SWP-001", "CND-001", path, kind, values, unit)
                fixture_scenarios = candidate_result(
                    run(fixture_problem, make_plan(fixture_problem, sweeps=[fixture_sweep]))
                )["core_scenarios"]
                self.assertEqual(
                    [
                        item["numerical_result"]["source_temperature"]["value"]
                        for item in fixture_scenarios
                    ],
                    expected,
                )

    def test_swp_02_exact_range_endpoint_rules(self) -> None:
        cases = (
            ("0.5", "2.5", "1", "include_stop", ["0.5", "1.5", "2.5"]),
            ("0.5", "2.5", "1", "exclude_stop", ["0.5", "1.5"]),
            ("0.5", "2.6", "1", "include_stop", ["0.5", "1.5", "2.5"]),
            ("2.5", "0.5", "-1", "include_stop", ["2.5", "1.5", "0.5"]),
        )
        for start, stop, step, policy, expected in cases:
            with self.subTest(start=start, stop=stop, step=step, policy=policy):
                problem = baseline_problem()
                plan = make_plan(problem, sweeps=[range_sweep(start, stop, step, policy)])
                scenarios = candidate_result(run(problem, plan))["core_scenarios"]
                self.assertEqual(
                    [item["sweep_coordinates"][0]["value"]["value"] for item in scenarios],
                    expected,
                )
        problem = baseline_problem()
        plan = EvaluationPlan.from_dict(
            make_plan(problem, sweeps=[range_sweep("0.5", "2.6", "0.3", "include_stop")])
        )
        epr = EngineeringProblem.from_dict(problem)
        expected = orchestrate_strict_1d(epr, plan).canonical_bytes()
        with localcontext() as context:
            context.prec = 2
            actual = orchestrate_strict_1d(epr, plan).canonical_bytes()
        self.assertEqual(actual, expected)

    def test_swp_03_assumed_override_keeps_acknowledgement_and_epr_identity(self) -> None:
        problem = baseline_problem()
        path = "/materials/1/thermal_properties/0/thermal_conductivity"
        assumed = envelope(
            QuantityKind.THERMAL_CONDUCTIVITY,
            "1000",
            "W/(m*K)",
            status="assumed",
        )
        problem["candidates"][0]["materials"][1]["thermal_properties"][0][
            "thermal_conductivity"
        ] = copy.deepcopy(assumed)
        problem["candidates"][0]["assumption_paths"] = [path]
        problem["compilation"]["outcome"] = "READY_WITH_ASSUMPTIONS"
        _restamp(problem)
        identity = problem["compiled_content_sha256"]
        sweep = grid(
            "SWP-001", "CND-001", path,
            QuantityKind.THERMAL_CONDUCTIVITY, ["800", "1500"], "W/(m*K)",
        )
        without = run(problem, make_plan(problem, sweeps=[sweep]))
        self.assertTrue(
            all(item["disposition"] == "blocked" for item in candidate_result(without)["core_scenarios"])
        )
        acknowledgement = {"scope": "candidate", "candidate_id": "CND-001", "field_path": path}
        plan = make_plan(problem, sweeps=[sweep])
        plan["assumption_acknowledgements"] = [acknowledgement]
        with_ack = run(problem, plan)
        scenarios = candidate_result(with_ack)["core_scenarios"]
        self.assertEqual(
            [item["numerical_result"]["source_temperature"]["value"] for item in scenarios],
            ["340.6625", "340.225"],
        )
        self.assertTrue(all(item["assumption_acknowledgements_used"] == [acknowledgement] for item in scenarios))
        self.assertEqual(problem["compiled_content_sha256"], identity)
        self.assertEqual(
            problem["candidates"][0]["materials"][1]["thermal_properties"][0]["thermal_conductivity"]["status"],
            "assumed",
        )
        original_envelope = problem["candidates"][0]["materials"][1]["thermal_properties"][0]["thermal_conductivity"]
        self.assertEqual(original_envelope["value"], "1000")
        self.assertEqual(
            [item["input_overrides"][0]["value"]["value"] for item in scenarios],
            ["800", "1500"],
        )


class ConstraintAcceptanceTests(unittest.TestCase):
    def test_cns_01_source_temperature_constraint_and_signed_margin(self) -> None:
        problem = baseline_problem()
        add_constraint(problem)
        baseline = candidate_result(run(problem, make_plan(problem)))["core_scenarios"][0]
        self.assertEqual(baseline["constraint_results"][0]["status"], "pass")
        self.assertEqual(baseline["constraint_results"][0]["margin"]["value"], "7.675")
        sweep = grid(
            "SWP-001", "CND-001", "/boundary_conditions/downstream/resistance",
            QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, ["0.5", "2.5"], "K/W",
        )
        scenarios = candidate_result(run(problem, make_plan(problem, sweeps=[sweep])))["core_scenarios"]
        self.assertEqual(
            [item["numerical_result"]["source_temperature"]["value"] for item in scenarios],
            ["330.475", "350.475"],
        )
        self.assertEqual(scenarios[1]["constraint_results"][0]["status"], "fail")
        self.assertEqual(scenarios[1]["constraint_results"][0]["margin"]["value"], "-2.325")

    def test_cns_02_non_evaluated_and_review_only_are_not_evaluable(self) -> None:
        problem = baseline_problem()
        add_constraint(problem)
        sweep = grid(
            "SWP-001", "CND-001", "/geometry/layers/1/footprint_area",
            QuantityKind.AREA, ["9"], "mm^2",
        )
        scenario = candidate_result(run(problem, make_plan(problem, sweeps=[sweep])))["core_scenarios"][0]
        constraint = scenario["constraint_results"][0]
        self.assertEqual(constraint["status"], "not_evaluable")
        self.assertIsNone(constraint["evaluated_quantity"])
        self.assertIsNone(constraint["margin"])

        review = baseline_problem()
        add_constraint(review, operator="review_only", disposition="review_required")
        review["constraints"][0]["threshold"] = None
        _restamp(review)
        result = run(review, make_plan(review))
        review_constraint = candidate_result(result)["core_scenarios"][0]["constraint_results"][0]
        self.assertEqual(review_constraint["status"], "not_evaluable")
        self.assertEqual(review_constraint["finding_ids"], ["I4-CNS-NOT-EVALUABLE"])

        conflicting = baseline_problem()
        add_constraint(conflicting, status="conflicting")
        conflicting["compilation"]["outcome"] = "HOLD_FOR_INPUT"
        _restamp(conflicting)
        result = run(conflicting, make_plan(conflicting))
        scenario = candidate_result(result)["core_scenarios"][0]
        self.assertEqual(scenario["disposition"], "evaluated")
        self.assertEqual(scenario["constraint_results"][0]["status"], "not_evaluable")
        self.assertNotIn(
            "/constraints/0/threshold",
            [item["field_path"] for item in scenario["consumed_input_paths"]],
        )

    def test_cns_03_temperature_margin_and_assumed_threshold_ack_boundary(self) -> None:
        problem = baseline_problem()
        set_temperature_margin(problem)
        plan = make_plan(problem, candidates=["CND-001", "CND-002"])
        plan["objective"] = {
            "metric": "temperature_margin",
            "direction": "maximize",
            "reference_requirement_id": "REQ-001",
        }
        result = run(problem, plan)
        ranked = result["result_payload"]["content"]["candidate_comparison"]["ranked_entries"]
        self.assertEqual([item["candidate_id"] for item in ranked], ["CND-001", "CND-002"])
        self.assertEqual([item["objective_value"]["value"] for item in ranked], ["7.675", "6.55"])

        threshold_problem = baseline_problem()
        add_constraint(threshold_problem, status="assumed")
        threshold_path = "/constraints/0/threshold"
        blocked = run(threshold_problem, make_plan(threshold_problem))
        self.assertEqual(blocked["candidate_execution"][0]["execution_status"], "blocked")
        acknowledged_plan = make_plan(threshold_problem)
        acknowledged_plan["assumption_acknowledgements"] = [
            {"scope": "global", "candidate_id": None, "field_path": threshold_path}
        ]
        evaluated = run(threshold_problem, acknowledged_plan)
        self.assertEqual(evaluated["candidate_execution"][0]["execution_status"], "evaluated")
        scenario = candidate_result(evaluated)["core_scenarios"][0]
        self.assertIn(
            threshold_path,
            [item["field_path"] for item in scenario["consumed_input_paths"]],
        )
        self.assertEqual(scenario["assumption_acknowledgements_used"], acknowledged_plan["assumption_acknowledgements"])

        evidence_problem = baseline_problem()
        add_constraint(evidence_problem, status="evidence_required")
        evidence_problem["compilation"]["outcome"] = "HOLD_FOR_INPUT"
        _restamp(evidence_problem)
        evidence_result = run(evidence_problem, make_plan(evidence_problem))
        evidence_scenario = candidate_result(evidence_result)["core_scenarios"][0]
        self.assertEqual(evidence_scenario["constraint_results"][0]["status"], "pass")
        self.assertIn(
            "I4-BIND-EVIDENCE-REQUIRED",
            {item["rule_id"] for item in evidence_scenario["execution_findings"]},
        )


class RankingAcceptanceTests(unittest.TestCase):
    def test_rank_01_diamond_before_copper(self) -> None:
        problem = baseline_problem()
        result = run(problem, make_plan(problem, candidates=["CND-001", "CND-002"]))
        comparison = result["result_payload"]["content"]["candidate_comparison"]
        self.assertEqual(comparison["ranking_status"], "performed")
        self.assertEqual(
            [item["candidate_id"] for item in comparison["ranked_entries"]],
            ["CND-001", "CND-002"],
        )
        self.assertEqual(
            [item["objective_value"]["value"] for item in comparison["ranked_entries"]],
            ["340.475", "341.6"],
        )
        self.assertEqual(Decimal("341.6") - Decimal("340.475"), Decimal("1.125"))

    def test_rank_02_blocked_or_not_applicable_never_ranks(self) -> None:
        problem = baseline_problem()
        problem["candidates"][1]["geometry"]["layers"][1]["footprint_area"] = envelope(
            QuantityKind.AREA, "9", "mm^2"
        )
        _restamp(problem)
        result = run(problem, make_plan(problem, candidates=["CND-001", "CND-002"]))
        comparison = result["result_payload"]["content"]["candidate_comparison"]
        second = comparison["candidate_eligibility"][1]
        self.assertFalse(second["eligible"])
        self.assertEqual(second["reason_ids"], ["I4-RANK-INELIGIBLE-BASIS"])
        self.assertEqual(comparison["ranking_status"], "not_performed")

    def test_rank_03_swept_candidate_is_ineligible(self) -> None:
        problem = baseline_problem()
        sweep = grid(
            "SWP-001", "CND-001", "/geometry/layers/1/thickness",
            QuantityKind.LENGTH, ["300"], "um",
        )
        result = run(
            problem,
            make_plan(problem, candidates=["CND-001", "CND-002"], sweeps=[sweep]),
        )
        comparison = result["result_payload"]["content"]["candidate_comparison"]
        first = comparison["candidate_eligibility"][0]
        self.assertFalse(first["eligible"])
        self.assertIsNone(first["basis_scenario_id"])
        self.assertEqual(first["reason_ids"], ["I4-RANK-INELIGIBLE-BASIS"])

    def test_rank_04_constraint_policy_and_lexical_tie(self) -> None:
        problem = baseline_problem()
        add_constraint(problem, limit="67.5", candidates=(0, 1))
        report = make_plan(problem, candidates=["CND-001", "CND-002"])
        report_result = run(problem, report)
        report_comparison = report_result["result_payload"]["content"]["candidate_comparison"]
        self.assertEqual(report_comparison["ranking_status"], "performed")
        exclude = copy.deepcopy(report)
        exclude["constraint_handling"] = "exclude_violating_from_rank"
        exclude_comparison = run(problem, exclude)["result_payload"]["content"]["candidate_comparison"]
        self.assertEqual(exclude_comparison["ranking_status"], "not_performed")
        self.assertEqual(
            exclude_comparison["candidate_eligibility"][1]["reason_ids"],
            ["I4-RANK-CONSTRAINT-VIOLATION"],
        )

        tied = baseline_problem()
        tied["candidates"][1]["materials"][1]["thermal_properties"][0][
            "thermal_conductivity"
        ] = envelope(QuantityKind.THERMAL_CONDUCTIVITY, "1000", "W/(m*K)")
        _restamp(tied)
        tied_entries = run(
            tied, make_plan(tied, candidates=["CND-001", "CND-002"])
        )["result_payload"]["content"]["candidate_comparison"]["ranked_entries"]
        self.assertEqual([item["candidate_id"] for item in tied_entries], ["CND-001", "CND-002"])


class EERIntegrationTests(unittest.TestCase):
    def test_eer_integration_determinism_prediction_boundary_and_zero_result_payload(self) -> None:
        problem = baseline_problem()
        problem["candidates"][0]["geometry"]["layers"][1]["footprint_area"] = envelope(
            QuantityKind.AREA, "9", "mm^2"
        )
        _restamp(problem)
        plan = make_plan(problem)
        with tempfile.TemporaryDirectory() as temporary:
            case = Path(temporary) / problem["case_id"]
            problems = case / "engineering" / "problems"
            problems.mkdir(parents=True)
            (problems / "EPR-001.json").write_bytes(canonical_json_bytes(problem))
            bound = bind_evaluation_plan(case, EvaluationPlan.from_dict(plan))
            first = build_strict_1d_engineering_evaluation_result(bound, "EER-001")
            second = build_strict_1d_engineering_evaluation_result(bound, "EER-001")
        value = first.to_dict()
        self.assertEqual(first.canonical_bytes(), second.canonical_bytes())
        self.assertEqual(value["execution_outcome"], "not_evaluated")
        self.assertIsNotNone(value["result_payload"])
        self.assertEqual(value["prediction_outputs"], [])
        self.assertEqual(value["assumptions_used"], [])

    def test_eer_completed_identity_and_pure_builder(self) -> None:
        problem = baseline_problem()
        plan = make_plan(problem, candidates=["CND-001", "CND-002"])
        with tempfile.TemporaryDirectory() as temporary:
            case = Path(temporary) / problem["case_id"]
            problems = case / "engineering" / "problems"
            problems.mkdir(parents=True)
            (problems / "EPR-001.json").write_bytes(canonical_json_bytes(problem))
            bound = bind_evaluation_plan(case, EvaluationPlan.from_dict(plan))
            first = build_strict_1d_engineering_evaluation_result(bound, "EER-001")
            second = build_strict_1d_engineering_evaluation_result(bound, "EER-001")
            self.assertFalse((case / "engineering" / "evaluations").exists())
            self.assertEqual(first.canonical_bytes(), second.canonical_bytes())
            value = first.to_dict()
            self.assertEqual(value["epr_file_sha256"], bound.epr_file_sha256)
            self.assertEqual(value["epr_reference"], bound.epr_reference)
            self.assertEqual(value["execution_outcome"], "completed")
            self.assertEqual(value["prediction_outputs"], [])
            self.assertEqual(value["findings"], value["result_payload"]["content"]["findings"])
            self.assertEqual(value["warnings"], value["result_payload"]["content"]["warnings"])


if __name__ == "__main__":
    unittest.main()
