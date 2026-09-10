from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import labos.engineering.evaluation_binding as binding_module
from labos.engineering import (
    BoundEvaluationPlan,
    EngineeringEvaluationBindingError,
    EngineeringEvaluationResult,
    EvaluationPlan,
    PersistedEngineeringEvaluationResult,
    QuantityKind,
    bind_evaluation_plan,
    canonical_json_bytes,
    load_engineering_evaluation_result,
    write_engineering_evaluation_result,
)
from tests.test_m16a_epr_schema import (
    base_problem,
    candidate_content_sha256,
    engineering_problem_content_sha256,
    envelope,
    missing_envelope,
)
from tests.test_m16a_evaluation_schema import (
    base_plan,
    not_evaluated_eer,
    quantity,
    stamp_eer,
)


ASSUMED_PATH = "/materials/0/thermal_properties/0/thermal_conductivity"
LENGTH_PATH = "/geometry/layers/0/thickness"
GLOBAL_PATH = "/heat_sources/0/total_power"


def restamp(problem: dict) -> dict:
    for candidate in problem["candidates"]:
        candidate["resolved_content_sha256"] = candidate_content_sha256(candidate)
    problem["compiled_content_sha256"] = engineering_problem_content_sha256(problem)
    return problem


class EvaluationBindingCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.case = self.root / "synthetic-i3b1-case"
        self.case.mkdir()
        self.problem = base_problem()
        self.problem["case_id"] = self.case.name
        restamp(self.problem)
        self.persist_problem()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @property
    def epr_path(self) -> Path:
        return self.case / "engineering" / "problems" / "EPR-001.json"

    def persist_problem(self, *, canonical: bool = True) -> bytes:
        restamp(self.problem)
        self.epr_path.parent.mkdir(parents=True, exist_ok=True)
        data = canonical_json_bytes(self.problem)
        if not canonical:
            data = (json.dumps(self.problem, indent=2, sort_keys=True) + "\n").encode("utf-8")
        self.epr_path.write_bytes(data)
        return data

    def plan(self) -> dict:
        value = base_plan()
        value["case_id"] = self.case.name
        value["epr_compiled_content_sha256"] = self.problem["compiled_content_sha256"]
        value["assumption_acknowledgements"] = []
        return value

    def bind(self, plan: dict | EvaluationPlan | None = None) -> BoundEvaluationPlan:
        return bind_evaluation_plan(self.case, plan or self.plan())

    def make_eer(
        self,
        bound: BoundEvaluationPlan,
        *,
        evaluation_id: str = "EER-001",
        confidentiality: str = "public",
    ) -> EngineeringEvaluationResult:
        value = not_evaluated_eer()
        value["evaluation_id"] = evaluation_id
        value["case_id"] = self.case.name
        value["problem_id"] = bound.engineering_problem.problem_id
        value["epr_reference"] = bound.epr_reference
        value["epr_compiled_content_sha256"] = bound.engineering_problem.content_sha256
        value["epr_file_sha256"] = bound.epr_file_sha256
        value["evaluation_plan"] = bound.evaluation_plan.to_dict()
        value["assumptions_used"] = []
        value["confidentiality_level"] = confidentiality
        for execution in value["candidate_execution"]:
            execution["assumption_acknowledgements_used"] = []
        return EngineeringEvaluationResult.from_dict(stamp_eer(value))

    def make_candidate_assumed(self, candidate_id: str = "CND-001") -> None:
        assumed = envelope(
            QuantityKind.THERMAL_CONDUCTIVITY,
            "100",
            "W/(m*K)",
            status="assumed",
        )
        candidate = next(item for item in self.problem["candidates"] if item["candidate_id"] == candidate_id)
        candidate["materials"][0]["thermal_properties"][0]["thermal_conductivity"] = copy.deepcopy(assumed)
        candidate["assumption_paths"] = [ASSUMED_PATH]
        if candidate_id == "CND-001":
            self.problem["materials"][0]["thermal_properties"][0]["thermal_conductivity"] = copy.deepcopy(assumed)
        self.persist_problem()


class PlanAndSourceBindingTests(EvaluationBindingCase):
    def test_src_01_canonical_epr_exact_bytes_and_hash_bind(self) -> None:
        exact = self.epr_path.read_bytes()
        bound = self.bind()
        self.assertIsInstance(bound, BoundEvaluationPlan)
        self.assertEqual(bound.case_path, self.case.resolve())
        self.assertEqual(bound.epr_path, self.epr_path.resolve())
        self.assertEqual(bound.epr_bytes, exact)
        self.assertEqual(bound.epr_file_sha256, hashlib.sha256(exact).hexdigest())
        self.assertEqual(bound.epr_reference, "engineering/problems/EPR-001.json")

    def test_c_noncanonical_semantically_equivalent_epr_rejects(self) -> None:
        self.persist_problem(canonical=False)
        with self.assertRaisesRegex(EngineeringEvaluationBindingError, "not the exact canonical"):
            self.bind()

    def test_e_wrong_case_problem_filename_and_content_hash_reject(self) -> None:
        plan = self.plan()
        plan["case_id"] = "wrong-case"
        with self.assertRaises(EngineeringEvaluationBindingError):
            self.bind(plan)

        plan = self.plan()
        plan["problem_id"] = "EPR-002"
        with self.assertRaises(EngineeringEvaluationBindingError):
            self.bind(plan)

        plan = self.plan()
        plan["epr_compiled_content_sha256"] = "a" * 64
        with self.assertRaises(EngineeringEvaluationBindingError):
            self.bind(plan)

        moved = self.epr_path.with_name("EPR-002.json")
        self.epr_path.rename(moved)
        with self.assertRaises(EngineeringEvaluationBindingError):
            self.bind()

    def test_plan_04_unknown_selected_candidate_rejects(self) -> None:
        plan = self.plan()
        plan["selected_candidate_ids"] = ["CND-001", "CND-999"]
        with self.assertRaisesRegex(EngineeringEvaluationBindingError, "unknown EPR candidates"):
            self.bind(plan)

    def test_a_same_parent_requirement_passes(self) -> None:
        self.assertIsInstance(self.bind(), BoundEvaluationPlan)

    def test_b_different_parent_requirement_rejects(self) -> None:
        second = copy.deepcopy(self.problem["requirements"][0])
        second["requirement_id"] = "REQ-002"
        self.problem["requirements"].append(second)
        self.problem["candidates"][1]["parent_requirement_id"] = "REQ-002"
        self.persist_problem()
        plan = self.plan()
        plan["epr_compiled_content_sha256"] = self.problem["compiled_content_sha256"]
        with self.assertRaisesRegex(EngineeringEvaluationBindingError, "share one parent_requirement_id"):
            self.bind(plan)

    def test_fail_01_fail_epr_has_no_executable_binding(self) -> None:
        self.problem["compilation"]["outcome"] = "FAIL"
        self.persist_problem()
        plan = self.plan()
        plan["epr_compiled_content_sha256"] = self.problem["compiled_content_sha256"]
        with self.assertRaisesRegex(EngineeringEvaluationBindingError, "FAIL EPRs"):
            self.bind(plan)

    def test_n_hold_for_input_binds_without_filling(self) -> None:
        self.problem["compilation"]["outcome"] = "HOLD_FOR_INPUT"
        before = self.persist_problem()
        plan = self.plan()
        plan["epr_compiled_content_sha256"] = self.problem["compiled_content_sha256"]
        bound = self.bind(plan)
        self.assertEqual(bound.epr_bytes, before)
        self.assertEqual(self.epr_path.read_bytes(), before)

    def test_safe_03_symlink_epr_target_rejects_when_supported(self) -> None:
        real = self.epr_path.with_name("real-epr.json")
        self.epr_path.rename(real)
        try:
            self.epr_path.symlink_to(real)
        except OSError:
            self.skipTest("symlink creation is unavailable")
        with self.assertRaises(EngineeringEvaluationBindingError):
            self.bind()


class ObjectiveAndTargetBindingTests(EvaluationBindingCase):
    def temperature_plan(self) -> dict:
        plan = self.plan()
        plan["objective"] = {
            "metric": "temperature_margin",
            "direction": "maximize",
            "reference_requirement_id": "REQ-001",
        }
        return plan

    def test_obj_01_temperature_margin_requires_absolute_temperature_target(self) -> None:
        with self.assertRaisesRegex(EngineeringEvaluationBindingError, "absolute_temperature"):
            self.bind(self.temperature_plan())

        self.problem["requirements"][0].pop("target")
        self.persist_problem()
        plan = self.temperature_plan()
        plan["epr_compiled_content_sha256"] = self.problem["compiled_content_sha256"]
        with self.assertRaisesRegex(EngineeringEvaluationBindingError, "no quantified target"):
            self.bind(plan)

        self.problem = base_problem()
        self.problem["case_id"] = self.case.name
        self.problem["requirements"][0]["target"] = envelope(
            QuantityKind.ABSOLUTE_TEMPERATURE, "350", "K"
        )
        self.persist_problem()
        plan = self.temperature_plan()
        plan["epr_compiled_content_sha256"] = self.problem["compiled_content_sha256"]
        self.assertIsInstance(self.bind(plan), BoundEvaluationPlan)

    def test_k_sweep_must_resolve_exact_selected_candidate_quantified_field(self) -> None:
        plan = self.plan()
        plan["parameter_sweeps"] = [{
            "sweep_id": "SWP-001",
            "candidate_id": "CND-001",
            "field_path": LENGTH_PATH,
            "value_specification": {
                "kind": "grid",
                "values": [quantity(QuantityKind.LENGTH, "0.0001", "m")],
            },
        }]
        self.assertIsInstance(self.bind(plan), BoundEvaluationPlan)

        wrong_kind = copy.deepcopy(plan)
        wrong_kind["parameter_sweeps"][0]["value_specification"]["values"] = [
            quantity(QuantityKind.POWER, "1", "W")
        ]
        with self.assertRaisesRegex(EngineeringEvaluationBindingError, "target kind"):
            self.bind(wrong_kind)

        unresolved = copy.deepcopy(plan)
        unresolved["parameter_sweeps"][0]["field_path"] = "/geometry/layers/0/not_a_field"
        with self.assertRaises(EngineeringEvaluationBindingError):
            self.bind(unresolved)

        non_envelope = copy.deepcopy(plan)
        non_envelope["parameter_sweeps"][0]["field_path"] = "/geometry/layers/0"
        with self.assertRaisesRegex(EngineeringEvaluationBindingError, "envelope itself"):
            self.bind(non_envelope)

    def test_rfc_6901_malformed_escape_wildcard_and_append_tokens_reject(self) -> None:
        for field_path in (
            "/geometry/~2malformed",
            "/geometry/*",
            "/geometry/layers/-",
        ):
            plan = self.plan()
            plan["parameter_sweeps"] = [{
                "sweep_id": "SWP-001",
                "candidate_id": "CND-001",
                "field_path": field_path,
                "value_specification": {
                    "kind": "grid",
                    "values": [quantity(QuantityKind.LENGTH, "0.0001", "m")],
                },
            }]
            with self.subTest(field_path=field_path), self.assertRaises(
                EngineeringEvaluationBindingError
            ):
                self.bind(plan)

    def test_l_oat_must_resolve_exact_baseline_candidate_quantified_field(self) -> None:
        plan = self.plan()
        plan["sensitivity_request"] = {
            "method": "oat",
            "baseline_candidate_id": "CND-001",
            "output_metric": "source_temperature",
            "parameters": [{
                "candidate_id": "CND-001",
                "field_path": LENGTH_PATH,
                "minus_value": quantity(QuantityKind.LENGTH, "0.00009", "m"),
                "plus_value": quantity(QuantityKind.LENGTH, "0.00011", "m"),
            }],
        }
        self.assertIsInstance(self.bind(plan), BoundEvaluationPlan)
        plan["sensitivity_request"]["parameters"][0]["field_path"] = "/geometry/layers/0/order"
        with self.assertRaisesRegex(EngineeringEvaluationBindingError, "envelope itself"):
            self.bind(plan)


class AcknowledgementBindingTests(EvaluationBindingCase):
    @staticmethod
    def acknowledgement(scope: str, candidate_id: str | None, field_path: str) -> dict:
        return {"scope": scope, "candidate_id": candidate_id, "field_path": field_path}

    def test_ack_01_candidate_and_global_assumed_envelopes_pass_structurally(self) -> None:
        self.make_candidate_assumed()
        self.problem["heat_sources"][0]["total_power"] = envelope(
            QuantityKind.POWER, "10", "W", status="assumed"
        )
        self.persist_problem()
        plan = self.plan()
        plan["epr_compiled_content_sha256"] = self.problem["compiled_content_sha256"]
        plan["assumption_acknowledgements"] = [
            self.acknowledgement("candidate", "CND-001", ASSUMED_PATH),
            self.acknowledgement("global", None, GLOBAL_PATH),
        ]
        bound = self.bind(plan)
        self.assertIsInstance(bound, BoundEvaluationPlan)
        self.assertFalse(hasattr(bound, "consumed_input_paths"))
        self.assertFalse(hasattr(bound, "required_used_assumptions"))
        self.assertFalse(hasattr(bound, "complete_used_assumption_set"))

    def test_f_and_ack_04_candidate_scope_is_exact_and_replacement_does_not_transfer(self) -> None:
        self.make_candidate_assumed("CND-001")
        self.problem["candidates"][1]["materials"][0]["thermal_properties"][0]["thermal_conductivity"] = envelope(
            QuantityKind.THERMAL_CONDUCTIVITY, "120", "W/(m*K)"
        )
        self.problem["candidates"][1]["changed_field_paths"] = [ASSUMED_PATH]
        self.problem["candidates"][1]["assumption_paths"] = []
        self.persist_problem()

        plan = self.plan()
        plan["epr_compiled_content_sha256"] = self.problem["compiled_content_sha256"]
        plan["assumption_acknowledgements"] = [
            self.acknowledgement("candidate", "CND-001", ASSUMED_PATH)
        ]
        self.assertIsInstance(self.bind(plan), BoundEvaluationPlan)

        plan["assumption_acknowledgements"] = [
            self.acknowledgement("candidate", "CND-002", ASSUMED_PATH)
        ]
        with self.assertRaisesRegex(EngineeringEvaluationBindingError, "this candidate's exact assumption path"):
            self.bind(plan)

    def test_h_i_wrong_scope_domains_reject(self) -> None:
        self.problem["heat_sources"][0]["total_power"] = envelope(
            QuantityKind.POWER, "10", "W", status="assumed"
        )
        self.make_candidate_assumed()
        self.persist_problem()
        for acknowledgement in (
            self.acknowledgement("global", None, ASSUMED_PATH),
            self.acknowledgement("candidate", "CND-001", GLOBAL_PATH),
        ):
            plan = self.plan()
            plan["epr_compiled_content_sha256"] = self.problem["compiled_content_sha256"]
            plan["assumption_acknowledgements"] = [acknowledgement]
            with self.subTest(acknowledgement=acknowledgement), self.assertRaises(
                EngineeringEvaluationBindingError
            ):
                self.bind(plan)

    def test_ack_03_non_assumed_states_reject(self) -> None:
        for status in ("provided", "missing", "conflicting", "evidence_required"):
            with self.subTest(status=status):
                if status == "missing":
                    target = missing_envelope(QuantityKind.THERMAL_CONDUCTIVITY, "W/(m*K)")
                else:
                    target = envelope(
                        QuantityKind.THERMAL_CONDUCTIVITY,
                        "100",
                        "W/(m*K)",
                        status=status,
                    )
                self.problem = base_problem()
                self.problem["case_id"] = self.case.name
                self.problem["materials"][0]["thermal_properties"][0]["thermal_conductivity"] = copy.deepcopy(target)
                candidate = self.problem["candidates"][0]
                candidate["materials"][0]["thermal_properties"][0]["thermal_conductivity"] = copy.deepcopy(target)
                candidate["assumption_paths"] = [ASSUMED_PATH]
                self.persist_problem()
                plan = self.plan()
                plan["assumption_acknowledgements"] = [
                    self.acknowledgement("candidate", "CND-001", ASSUMED_PATH)
                ]
                with self.assertRaises(EngineeringEvaluationBindingError):
                    self.bind(plan)

    def test_o_ack_05_ready_with_assumptions_does_not_claim_model_closure(self) -> None:
        self.problem["compilation"]["outcome"] = "READY_WITH_ASSUMPTIONS"
        self.make_candidate_assumed()
        plan = self.plan()
        plan["epr_compiled_content_sha256"] = self.problem["compiled_content_sha256"]
        plan["assumption_acknowledgements"] = []
        bound = self.bind(plan)
        self.assertEqual(bound.engineering_problem.to_dict()["compilation"]["outcome"], "READY_WITH_ASSUMPTIONS")
        self.assertEqual(bound.evaluation_plan.to_dict()["assumption_acknowledgements"], [])


class EERPersistenceTests(EvaluationBindingCase):
    def test_p_q_safe_writer_rejects_downgrade_and_binds_first_read_hash(self) -> None:
        self.problem["confidentiality_level"] = "internal"
        self.persist_problem()
        plan = self.plan()
        plan["epr_compiled_content_sha256"] = self.problem["compiled_content_sha256"]
        bound = self.bind(plan)
        self.assertEqual(bound.epr_file_sha256, hashlib.sha256(self.epr_path.read_bytes()).hexdigest())
        eer = self.make_eer(bound, confidentiality="public")
        with self.assertRaisesRegex(EngineeringEvaluationBindingError, "must not downgrade"):
            write_engineering_evaluation_result(bound, eer)
        self.assertFalse((self.case / "engineering" / "evaluations").exists())

    def test_safe_01_r_idempotent_same_bytes_and_loader_exact_hash(self) -> None:
        bound = self.bind()
        eer = self.make_eer(bound)
        first = write_engineering_evaluation_result(bound, eer)
        second = write_engineering_evaluation_result(bound, eer)
        self.assertEqual(first, second)
        exact = first.read_bytes()
        loaded = load_engineering_evaluation_result(self.case, "EER-001")
        self.assertIsInstance(loaded, PersistedEngineeringEvaluationResult)
        self.assertEqual(loaded.eer_bytes, exact)
        self.assertEqual(loaded.eer_file_sha256, hashlib.sha256(exact).hexdigest())
        self.assertEqual(loaded.evaluation_result.canonical_bytes(), exact)

    def test_safe_02_s_different_bytes_same_id_reject_without_overwrite(self) -> None:
        bound = self.bind()
        eer = self.make_eer(bound)
        target = self.case / "engineering" / "evaluations" / "EER-001.json"
        target.parent.mkdir()
        original = b"different immutable bytes\n"
        target.write_bytes(original)
        with self.assertRaisesRegex(EngineeringEvaluationBindingError, "different bytes"):
            write_engineering_evaluation_result(bound, eer)
        self.assertEqual(target.read_bytes(), original)

    def test_src_02_t_stale_epr_before_write_leaves_no_target(self) -> None:
        bound = self.bind()
        eer = self.make_eer(bound)
        self.problem["title"] = "Changed after evaluation snapshot"
        self.persist_problem()
        with self.assertRaisesRegex(EngineeringEvaluationBindingError, "changed after binding"):
            write_engineering_evaluation_result(bound, eer)
        self.assertFalse((self.case / "engineering" / "evaluations").exists())

    def test_u_w_second_stale_check_cleans_temp_and_publishes_nothing(self) -> None:
        bound = self.bind()
        eer = self.make_eer(bound)
        original_check = binding_module._assert_epr_fresh
        calls = 0

        def change_before_second_check(value: BoundEvaluationPlan) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                self.problem["title"] = "Changed between temporary write and publication"
                self.persist_problem()
            original_check(value)

        with patch.object(binding_module, "_assert_epr_fresh", side_effect=change_before_second_check):
            with self.assertRaises(EngineeringEvaluationBindingError):
                write_engineering_evaluation_result(bound, eer)
        evaluations = self.case / "engineering" / "evaluations"
        self.assertFalse((evaluations / "EER-001.json").exists())
        self.assertEqual(list(evaluations.glob("*.tmp")), [])

    def test_v_symlink_eer_target_rejects_when_supported(self) -> None:
        bound = self.bind()
        eer = self.make_eer(bound)
        evaluations = self.case / "engineering" / "evaluations"
        evaluations.mkdir()
        external = self.case / "outside.json"
        external.write_bytes(eer.canonical_bytes())
        target = evaluations / "EER-001.json"
        try:
            target.symlink_to(external)
        except OSError:
            self.skipTest("symlink creation is unavailable")
        with self.assertRaisesRegex(EngineeringEvaluationBindingError, "symlink"):
            write_engineering_evaluation_result(bound, eer)
        self.assertEqual(external.read_bytes(), eer.canonical_bytes())

    def test_v_symlink_evaluations_parent_rejects_when_supported(self) -> None:
        bound = self.bind()
        eer = self.make_eer(bound)
        engineering = self.case / "engineering"
        relocated = self.case / "relocated-evaluations"
        relocated.mkdir()
        evaluations = engineering / "evaluations"
        try:
            evaluations.symlink_to(relocated, target_is_directory=True)
        except OSError:
            self.skipTest("symlink creation is unavailable")
        with self.assertRaisesRegex(EngineeringEvaluationBindingError, "symlink"):
            write_engineering_evaluation_result(bound, eer)
        self.assertEqual(list(relocated.iterdir()), [])

    def test_safe_03_no_clobber_race_rejects_different_target(self) -> None:
        bound = self.bind()
        eer = self.make_eer(bound)
        real_link = os.link

        def collide(source: str | os.PathLike[str], target: str | os.PathLike[str]) -> None:
            Path(target).write_bytes(b"racing different bytes\n")
            raise FileExistsError

        with patch.object(binding_module.os, "link", side_effect=collide):
            with self.assertRaisesRegex(EngineeringEvaluationBindingError, "different bytes"):
                write_engineering_evaluation_result(bound, eer)
        target = self.case / "engineering" / "evaluations" / "EER-001.json"
        self.assertEqual(target.read_bytes(), b"racing different bytes\n")
        self.assertEqual(list(target.parent.glob("*.tmp")), [])
        self.assertIsNotNone(real_link)

    def test_x_loader_rejects_noncanonical_eer_bytes(self) -> None:
        bound = self.bind()
        eer = self.make_eer(bound)
        target = self.case / "engineering" / "evaluations" / "EER-001.json"
        target.parent.mkdir()
        target.write_bytes((json.dumps(eer.to_dict(), indent=2, sort_keys=True) + "\n").encode("utf-8"))
        with self.assertRaisesRegex(EngineeringEvaluationBindingError, "not the exact canonical"):
            load_engineering_evaluation_result(self.case, "EER-001")

    def test_loader_rejects_wrong_case_and_filename_identity(self) -> None:
        bound = self.bind()
        eer = self.make_eer(bound)
        target = self.case / "engineering" / "evaluations" / "EER-002.json"
        target.parent.mkdir()
        target.write_bytes(eer.canonical_bytes())
        with self.assertRaisesRegex(EngineeringEvaluationBindingError, "filename identity"):
            load_engineering_evaluation_result(self.case, "EER-002")


class SeparationBoundaryTests(EvaluationBindingCase):
    def test_sep_03_structural_module_contains_no_arithmetic_or_i3b2_surface(self) -> None:
        source = Path(binding_module.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "convert_canonical_to_unit",
            "compare_prediction_to_measurement",
            "prediction_reality_adapter",
            "consumed_input_paths",
            "rank_candidates",
        ):
            self.assertNotIn(forbidden, source)
        self.assertNotIn("reviewed_by", source)


if __name__ == "__main__":
    unittest.main()
