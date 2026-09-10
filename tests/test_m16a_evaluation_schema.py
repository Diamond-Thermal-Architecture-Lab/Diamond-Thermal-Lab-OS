from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from labos.engineering import (
    CALCULATION_NOT_APPROVAL_NOTICE,
    CANONICAL_JSON_VERSION,
    DETERMINISTIC_RUNTIME_POLICY_VERSION,
    EER_CONTENT_IDENTITY_VERSION,
    ENGINEERING_EVALUATION_RESULT_FORMAT_VERSION,
    EVALUATION_INPUT_IDENTITY_VERSION,
    EVALUATION_PLAN_FORMAT_VERSION,
    EVALUATION_PLAN_IDENTITY_VERSION,
    MODEL_MANIFEST_FORMAT_VERSION,
    MODEL_MANIFEST_IDENTITY_VERSION,
    UNIT_REGISTRY_VERSION,
    EngineeringEvaluationResult,
    EngineeringEvaluationValidationError,
    EvaluationPlan,
    ModelManifest,
    QuantityKind,
    canonical_json_bytes,
    convert_quantity,
    engineering_evaluation_result_content_sha256,
    evaluation_input_sha256,
    evaluation_plan_sha256,
    model_manifest_sha256,
    result_payload_content_sha256,
)


ZERO_HASH = "0" * 64
EPR_HASH = "e" * 64
EPR_FILE_HASH = "f" * 64


def quantity(kind: QuantityKind, value: str, unit: str) -> dict:
    reconstructed = convert_quantity(kind, value, unit).to_dict()
    return {
        "value": reconstructed["canonical_value"],
        "unit": reconstructed["canonical_unit"],
        "quantity_kind": reconstructed["quantity_kind"],
        "conversion": reconstructed["conversion"],
    }


def acknowledgement(
    scope: str = "candidate",
    candidate_id: str | None = "CND-001",
    field_path: str = "/materials/0/thermal_properties/0/thermal_conductivity",
) -> dict:
    return {"scope": scope, "candidate_id": candidate_id, "field_path": field_path}


def base_plan() -> dict:
    return {
        "evaluation_plan_format_version": EVALUATION_PLAN_FORMAT_VERSION,
        "case_id": "synthetic-i3a-case",
        "problem_id": "EPR-001",
        "epr_compiled_content_sha256": EPR_HASH,
        "model_request": {"model_id": "synthetic-model", "model_version": "1.0"},
        "selected_candidate_ids": ["CND-001", "CND-002"],
        "objective": {
            "metric": "source_temperature",
            "direction": "minimize",
            "reference_requirement_id": None,
        },
        "constraint_handling": "report_only",
        "parameter_sweeps": [],
        "sensitivity_request": None,
        "assumption_acknowledgements": [
            acknowledgement(),
            acknowledgement("global", None, "/heat_sources/0/total_power"),
        ],
        "model_options": {"diagnostic_mode": True, "iteration_limit": 4},
        "maximum_requested_combination_count": 2,
    }


def base_manifest() -> dict:
    return {
        "model_manifest_format_version": MODEL_MANIFEST_FORMAT_VERSION,
        "model_id": "synthetic-model",
        "model_version": "1.0",
        "equation_set_version": "synthetic-equations-1.0",
        "implementation_version": "synthetic-implementation-1.0",
        "applicability_policy_version": "synthetic-applicability-1.0",
        "applicability_rule_ids": ["SYNTHETIC-APP-001"],
        "numerical_policy_version": "synthetic-numerical-1.0",
        "input_binding_policy_version": "synthetic-binding-1.0",
        "serialization_policy_version": CANONICAL_JSON_VERSION,
        "result_payload_schema_id": "synthetic-result",
        "result_payload_schema_version": "1.0",
        "required_input_features": ["geometry.length", "thermal.input"],
        "prohibited_input_features": ["transient.input"],
        "accepted_quantity_kinds": ["absolute_temperature", "length"],
        "canonical_units": {"absolute_temperature": "K", "length": "m"},
        "known_limitations": ["Synthetic contract fixture only."],
        "source_references": ["public-synthetic-reference"],
        "implementation_git_commit": None,
    }


def diagnostic(rule_id: str = "SYNTHETIC-DIAG-001") -> dict:
    return {
        "rule_id": rule_id,
        "classification": "MODEL_APPLICABILITY",
        "field_paths": ["/candidates/0"],
        "message": "Synthetic diagnostic.",
        "required_action": "Review the synthetic condition.",
    }


def candidate_execution(
    candidate_id: str,
    status: str = "blocked",
    *,
    used: list[dict] | None = None,
) -> dict:
    if status == "evaluated":
        applicability, presence = "applicable", True
    elif status == "not_applicable":
        applicability, presence = "not_applicable", False
    else:
        applicability, presence = "not_evaluated", False
    return {
        "candidate_id": candidate_id,
        "execution_status": status,
        "applicability_status": applicability,
        "applicability_findings": [],
        "assumption_acknowledgements_used": copy.deepcopy(used or []),
        "result_presence": presence,
    }


def stamp_eer(value: dict) -> dict:
    value["evaluation_plan_sha256"] = evaluation_plan_sha256(value["evaluation_plan"])
    value["model_manifest_sha256"] = model_manifest_sha256(value["model_manifest"])
    payload = value["result_payload"]
    if payload is not None:
        payload["content_sha256"] = result_payload_content_sha256(payload)
    value["evaluation_input_sha256"] = evaluation_input_sha256(
        epr_compiled_content_sha256=value["epr_compiled_content_sha256"],
        evaluation_plan_sha256=value["evaluation_plan_sha256"],
        model_manifest_sha256=value["model_manifest_sha256"],
        unit_registry_version=value["unit_registry_version"],
        deterministic_runtime_policy_version=value["deterministic_runtime_policy_version"],
    )
    value["eer_content_sha256"] = engineering_evaluation_result_content_sha256(value)
    return value


def not_evaluated_eer() -> dict:
    plan = base_plan()
    value = {
        "engineering_evaluation_result_format_version": ENGINEERING_EVALUATION_RESULT_FORMAT_VERSION,
        "evaluation_id": "EER-001",
        "case_id": plan["case_id"],
        "problem_id": plan["problem_id"],
        "epr_reference": "engineering/problems/EPR-001.json",
        "epr_compiled_content_sha256": plan["epr_compiled_content_sha256"],
        "epr_file_sha256": EPR_FILE_HASH,
        "evaluation_plan": plan,
        "evaluation_plan_sha256": ZERO_HASH,
        "model_manifest": base_manifest(),
        "model_manifest_sha256": ZERO_HASH,
        "unit_registry_version": UNIT_REGISTRY_VERSION,
        "deterministic_runtime_policy_version": DETERMINISTIC_RUNTIME_POLICY_VERSION,
        "evaluation_input_sha256": ZERO_HASH,
        "execution_outcome": "not_evaluated",
        "candidate_execution": [candidate_execution("CND-001"), candidate_execution("CND-002", "not_applicable")],
        "assumptions_used": [],
        "result_payload": None,
        "prediction_outputs": [],
        "findings": [],
        "warnings": [],
        "confidentiality_level": "public",
        "calculation_not_approval_notice": CALCULATION_NOT_APPROVAL_NOTICE,
        "eer_content_sha256": ZERO_HASH,
    }
    return stamp_eer(value)


def evaluated_eer() -> dict:
    value = not_evaluated_eer()
    used = [copy.deepcopy(value["evaluation_plan"]["assumption_acknowledgements"][1])]
    value["candidate_execution"] = [
        candidate_execution("CND-001", "evaluated", used=used),
        candidate_execution("CND-002", "not_applicable"),
    ]
    value["execution_outcome"] = "partial"
    value["assumptions_used"] = used
    value["result_payload"] = {
        "schema_id": "synthetic-result",
        "schema_version": "1.0",
        "content": {
            "candidate_results": [
                {"candidate_id": "CND-001", "junction_temperature": "323.15"}
            ]
        },
        "content_sha256": ZERO_HASH,
    }
    value["prediction_outputs"] = [{
        "output_id": "EER-001-OUT-001",
        "candidate_id": "CND-001",
        "quantity_label": "junction_temperature",
        "quantity_kind": "absolute_temperature",
        "value": "323.15",
        "unit": "K",
        "lower_bound": "320",
        "upper_bound": "325",
        "result_pointer": "/candidate_results/0/junction_temperature",
    }]
    return stamp_eer(value)


class M16AEvaluationSchemaParityTests(unittest.TestCase):
    def test_schema_runtime_parity_and_primary_sidecars(self) -> None:
        schema_path = Path("labos/schemas/engineering_evaluation_result.schema.json")
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["$id"], "labos/engineering_evaluation_result.schema.json")
        self.assertFalse(schema["additionalProperties"])
        self.assertIn("evaluation_plan", schema["$defs"])
        self.assertIn("model_manifest", schema["$defs"])
        self.assertIn("result_payload", schema["$defs"])
        self.assertIn("canonical_json_extension_value", schema["$defs"])
        self.assertEqual(
            schema["properties"]["engineering_evaluation_result_format_version"]["const"],
            ENGINEERING_EVALUATION_RESULT_FORMAT_VERSION,
        )
        self.assertEqual(
            schema["$defs"]["evaluation_plan"]["properties"]["evaluation_plan_format_version"]["const"],
            EVALUATION_PLAN_FORMAT_VERSION,
        )
        self.assertEqual(
            schema["$defs"]["model_manifest"]["properties"]["model_manifest_format_version"]["const"],
            MODEL_MANIFEST_FORMAT_VERSION,
        )
        self.assertFalse(Path("labos/schemas/evaluation_plan.schema.json").exists())
        self.assertFalse(Path("labos/schemas/model_manifest.schema.json").exists())
        top_fields = set(schema["properties"])
        self.assertFalse({"reviewed_by", "approval_status", "timestamp", "hostname"} & top_fields)
        schema_text = schema_path.read_text(encoding="utf-8")
        for solver_field in ("thermal_resistance", "source_temperature_result", "rank"):
            self.assertNotIn(f'"{solver_field}"', schema_text)

    def test_versions_are_exact(self) -> None:
        self.assertEqual(EVALUATION_PLAN_IDENTITY_VERSION, "m16a-evaluation-plan-content-identity-1.0")
        self.assertEqual(MODEL_MANIFEST_IDENTITY_VERSION, "m16a-model-manifest-content-identity-1.0")
        self.assertEqual(EVALUATION_INPUT_IDENTITY_VERSION, "m16a-evaluation-input-identity-1.0")
        self.assertEqual(EER_CONTENT_IDENTITY_VERSION, "m16a-eer-content-identity-1.0")
        self.assertEqual(DETERMINISTIC_RUNTIME_POLICY_VERSION, "m16a-evaluation-runtime-1.0")


class M16AEvaluationPlanTests(unittest.TestCase):
    def test_plan_01_determinism_mapping_order_and_immutability(self) -> None:
        first = base_plan()
        second = {key: first[key] for key in reversed(first)}
        one = EvaluationPlan.from_dict(first)
        two = EvaluationPlan.from_dict(second)
        self.assertEqual(one.canonical_bytes(), two.canonical_bytes())
        self.assertEqual(one.content_sha256, two.content_sha256)
        first["model_request"]["model_id"] = "mutated"
        self.assertEqual(one.to_dict()["model_request"]["model_id"], "synthetic-model")
        with self.assertRaises(TypeError):
            one._content["case_id"] = "mutated"  # type: ignore[index]

    def test_plan_02_every_authoritative_change_changes_hash(self) -> None:
        original = evaluation_plan_sha256(base_plan())
        mutations = (
            lambda p: p["model_request"].update(model_version="2.0"),
            lambda p: p.update(selected_candidate_ids=["CND-001"], maximum_requested_combination_count=1),
            lambda p: p.update(constraint_handling="exclude_violating_from_rank"),
            lambda p: p["objective"].update(metric="total_thermal_resistance"),
            lambda p: p.update(
                parameter_sweeps=[{
                    "sweep_id": "SWP-001",
                    "candidate_id": "CND-001",
                    "field_path": "/geometry/x",
                    "value_specification": {
                        "kind": "grid",
                        "values": [quantity(QuantityKind.LENGTH, "1", "m")],
                    },
                }]
            ),
            lambda p: p["assumption_acknowledgements"].pop(),
            lambda p: p["model_options"].update(mode="alternate"),
        )
        for mutate in mutations:
            value = base_plan()
            mutate(value)
            with self.subTest(mutate=mutate):
                plan = EvaluationPlan.from_dict(value)
                self.assertNotEqual(plan.content_sha256, original)

    def test_plan_03_plan_identity_uses_hash_input_without_epr_filesystem(self) -> None:
        first = base_plan()
        second = base_plan()
        second["model_options"]["iteration_limit"] = 5
        self.assertEqual(first["epr_compiled_content_sha256"], second["epr_compiled_content_sha256"])
        self.assertNotEqual(evaluation_plan_sha256(first), evaluation_plan_sha256(second))

    def test_plan_04_unselected_internal_references_reject(self) -> None:
        variants = []
        sweep = base_plan()
        sweep["parameter_sweeps"] = [{
            "sweep_id": "SWP-001", "candidate_id": "CND-003", "field_path": "/geometry/x",
            "value_specification": {"kind": "grid", "values": [quantity(QuantityKind.LENGTH, "1", "m")]},
        }]
        variants.append(sweep)
        oat = base_plan()
        oat["sensitivity_request"] = {
            "method": "oat", "baseline_candidate_id": "CND-003", "output_metric": "source_temperature",
            "parameters": [{
                "candidate_id": "CND-003", "field_path": "/geometry/x",
                "minus_value": quantity(QuantityKind.LENGTH, "1", "m"),
                "plus_value": quantity(QuantityKind.LENGTH, "2", "m"),
            }],
        }
        variants.append(oat)
        ack = base_plan()
        ack["assumption_acknowledgements"].append(acknowledgement("candidate", "CND-003", "/geometry/x"))
        variants.append(ack)
        for value in variants:
            with self.assertRaises(EngineeringEvaluationValidationError):
                EvaluationPlan.from_dict(value)

    def test_closed_versions_ids_order_pointer_and_float_reject(self) -> None:
        mutators = (
            lambda p: p.update(extra=True),
            lambda p: p.update(evaluation_plan_format_version="1.0"),
            lambda p: p.update(case_id="../unsafe"),
            lambda p: p.update(problem_id="EPR-1"),
            lambda p: p.update(epr_compiled_content_sha256="ABC"),
            lambda p: p["selected_candidate_ids"].reverse(),
            lambda p: p.update(selected_candidate_ids=["CND-001", "CND-001"]),
            lambda p: p["assumption_acknowledgements"][0].update(field_path="not-a-pointer"),
            lambda p: p["model_options"].update(tolerance=0.1),
        )
        for mutate in mutators:
            value = base_plan()
            mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(EngineeringEvaluationValidationError):
                EvaluationPlan.from_dict(value)

    def test_objective_direction_and_temperature_margin_reference(self) -> None:
        value = base_plan()
        value["objective"] = {
            "metric": "temperature_margin", "direction": "maximize", "reference_requirement_id": "REQ-001"
        }
        EvaluationPlan.from_dict(value)
        for reference, direction in ((None, "maximize"), ("REQ-1", "maximize"), ("REQ-001", "minimize")):
            broken = copy.deepcopy(value)
            broken["objective"].update(reference_requirement_id=reference, direction=direction)
            with self.assertRaises(EngineeringEvaluationValidationError):
                EvaluationPlan.from_dict(broken)

    def test_ack_01_ack_05_structure_only_without_consumed_input_closure(self) -> None:
        plan = EvaluationPlan.from_dict(base_plan())
        self.assertEqual(len(plan.to_dict()["assumption_acknowledgements"]), 2)
        self.assertFalse(hasattr(plan, "consumed_input_paths"))
        duplicate = base_plan()
        duplicate["assumption_acknowledgements"].append(copy.deepcopy(duplicate["assumption_acknowledgements"][-1]))
        with self.assertRaises(EngineeringEvaluationValidationError):
            EvaluationPlan.from_dict(duplicate)


class M16ASweepAndSensitivityTests(unittest.TestCase):
    def _grid(self, sweep_id: str, candidate_id: str, values: list[dict], path: str = "/geometry/x") -> dict:
        return {
            "sweep_id": sweep_id,
            "candidate_id": candidate_id,
            "field_path": path,
            "value_specification": {"kind": "grid", "values": values},
        }

    def _range(self, policy: str, stop: str = "3", step: str = "1") -> dict:
        return {
            "sweep_id": "SWP-001", "candidate_id": "CND-001", "field_path": "/geometry/x",
            "value_specification": {
                "kind": "range",
                "start": quantity(QuantityKind.LENGTH, "0", "m"),
                "stop": quantity(QuantityKind.LENGTH, stop, "m"),
                "step": quantity(QuantityKind.LENGTH, step, "m"),
                "endpoint_policy": policy,
            },
        }

    def test_swp_01_id_order_grid_order_and_duplicate_points(self) -> None:
        values = [quantity(QuantityKind.LENGTH, "2", "m"), quantity(QuantityKind.LENGTH, "1", "m")]
        first = base_plan()
        first["parameter_sweeps"] = [self._grid("SWP-001", "CND-001", values)]
        first["maximum_requested_combination_count"] = 3
        accepted = EvaluationPlan.from_dict(first)
        self.assertEqual(accepted.to_dict()["parameter_sweeps"][0]["value_specification"]["values"], values)
        reordered = copy.deepcopy(first)
        reordered["parameter_sweeps"][0]["value_specification"]["values"].reverse()
        self.assertNotEqual(accepted.content_sha256, EvaluationPlan.from_dict(reordered).content_sha256)

        bad_order = copy.deepcopy(first)
        bad_order["parameter_sweeps"] = [
            self._grid("SWP-002", "CND-001", [quantity(QuantityKind.LENGTH, "3", "m")]),
            bad_order["parameter_sweeps"][0],
        ]
        bad_order["maximum_requested_combination_count"] = 3
        duplicate = copy.deepcopy(first)
        duplicate["parameter_sweeps"][0]["value_specification"]["values"].append(quantity(QuantityKind.LENGTH, "1000", "mm"))
        duplicate_id = copy.deepcopy(first)
        duplicate_id["parameter_sweeps"].append(
            self._grid("SWP-001", "CND-002", [quantity(QuantityKind.LENGTH, "3", "m")])
        )
        duplicate_id["maximum_requested_combination_count"] = 3
        for broken in (bad_order, duplicate, duplicate_id):
            with self.assertRaises(EngineeringEvaluationValidationError):
                EvaluationPlan.from_dict(broken)

    def test_swp_02_exact_endpoint_behavior_and_temperature_increment(self) -> None:
        counts = []
        for policy, stop in (("include_stop", "3"), ("exclude_stop", "3"), ("include_stop", "3.5")):
            value = base_plan()
            value["parameter_sweeps"] = [self._range(policy, stop)]
            value["maximum_requested_combination_count"] = 10
            counts.append(EvaluationPlan.from_dict(value).total_requested_combination_count)
        self.assertEqual(counts, [5, 4, 5])  # sweep points plus CND-002 baseline

        temperature = base_plan()
        temperature["parameter_sweeps"] = [{
            "sweep_id": "SWP-001", "candidate_id": "CND-001", "field_path": "/boundary/temperature",
            "value_specification": {
                "kind": "range",
                "start": quantity(QuantityKind.ABSOLUTE_TEMPERATURE, "20", "degC"),
                "stop": quantity(QuantityKind.ABSOLUTE_TEMPERATURE, "24", "degC"),
                "step": quantity(QuantityKind.TEMPERATURE_DIFFERENCE, "2", "K"),
                "endpoint_policy": "include_stop",
            },
        }]
        temperature["maximum_requested_combination_count"] = 4
        self.assertEqual(EvaluationPlan.from_dict(temperature).total_requested_combination_count, 4)
        temperature["parameter_sweeps"][0]["value_specification"]["step"] = quantity(QuantityKind.ABSOLUTE_TEMPERATURE, "2", "K")
        with self.assertRaises(EngineeringEvaluationValidationError):
            EvaluationPlan.from_dict(temperature)

    def test_swp_03_cartesian_per_candidate_and_swp_04_maximum(self) -> None:
        value = base_plan()
        value["parameter_sweeps"] = [
            self._grid("SWP-001", "CND-001", [quantity(QuantityKind.LENGTH, "1", "m"), quantity(QuantityKind.LENGTH, "2", "m")]),
            self._grid("SWP-002", "CND-001", [quantity(QuantityKind.LENGTH, "3", "m"), quantity(QuantityKind.LENGTH, "4", "m"), quantity(QuantityKind.LENGTH, "5", "m")], "/geometry/y"),
            self._grid("SWP-003", "CND-002", [quantity(QuantityKind.LENGTH, "6", "m"), quantity(QuantityKind.LENGTH, "7", "m")]),
        ]
        value["maximum_requested_combination_count"] = 8
        self.assertEqual(EvaluationPlan.from_dict(value).total_requested_combination_count, 8)
        value["maximum_requested_combination_count"] = 7
        with self.assertRaises(EngineeringEvaluationValidationError):
            EvaluationPlan.from_dict(value)

    def test_invalid_range_direction_zero_and_equal_endpoint(self) -> None:
        for stop, step in (("3", "-1"), ("-3", "1"), ("3", "0"), ("0", "1")):
            value = base_plan()
            value["parameter_sweeps"] = [self._range("include_stop", stop, step)]
            value["maximum_requested_combination_count"] = 10
            with self.subTest(stop=stop, step=step), self.assertRaises(EngineeringEvaluationValidationError):
                EvaluationPlan.from_dict(value)

    def test_sen_01_and_sen_02_oat_contract(self) -> None:
        value = base_plan()
        value["sensitivity_request"] = {
            "method": "oat", "baseline_candidate_id": "CND-001", "output_metric": "source_temperature",
            "parameters": [
                {"candidate_id": "CND-001", "field_path": "/geometry/x", "minus_value": quantity(QuantityKind.LENGTH, "1", "m"), "plus_value": quantity(QuantityKind.LENGTH, "2", "m")},
                {"candidate_id": "CND-001", "field_path": "/geometry/y", "minus_value": quantity(QuantityKind.LENGTH, "3", "m"), "plus_value": quantity(QuantityKind.LENGTH, "4", "m")},
            ],
        }
        EvaluationPlan.from_dict(value)
        wrong_candidate = copy.deepcopy(value)
        wrong_candidate["sensitivity_request"]["parameters"][0]["candidate_id"] = "CND-002"
        reversed_parameters = copy.deepcopy(value)
        reversed_parameters["sensitivity_request"]["parameters"].reverse()
        duplicate_path = copy.deepcopy(value)
        duplicate_path["sensitivity_request"]["parameters"][1]["field_path"] = "/geometry/x"
        equal = copy.deepcopy(value)
        equal["sensitivity_request"]["parameters"][0]["plus_value"] = quantity(QuantityKind.LENGTH, "1000", "mm")
        for broken in (wrong_candidate, reversed_parameters, duplicate_path, equal):
            with self.assertRaises(EngineeringEvaluationValidationError):
                EvaluationPlan.from_dict(broken)


class M16AModelManifestAndIdentityTests(unittest.TestCase):
    def test_man_01_determinism_and_mapping_order(self) -> None:
        first = base_manifest()
        second = {key: first[key] for key in reversed(first)}
        one = ModelManifest.from_dict(first)
        two = ModelManifest.from_dict(second)
        self.assertEqual(one.canonical_bytes(), two.canonical_bytes())
        self.assertEqual(one.content_sha256, two.content_sha256)

    def test_man_02_authoritative_changes_change_hash(self) -> None:
        mutations = (
            lambda m: m.update(model_version="2.0"),
            lambda m: m.update(equation_set_version="equations-2.0"),
            lambda m: m.update(implementation_version="implementation-2.0"),
            lambda m: m.update(applicability_policy_version="applicability-2.0"),
            lambda m: m.update(numerical_policy_version="numerical-2.0"),
            lambda m: m.update(input_binding_policy_version="binding-2.0"),
            lambda m: m.update(result_payload_schema_version="2.0"),
            lambda m: m["required_input_features"].append("z.input"),
        )
        original = model_manifest_sha256(base_manifest())
        for mutate in mutations:
            value = base_manifest()
            mutate(value)
            with self.subTest(mutate=mutate):
                manifest = ModelManifest.from_dict(value)
                self.assertNotEqual(manifest.content_sha256, original)
        serialization_variant = base_manifest()
        serialization_variant["serialization_policy_version"] = "synthetic-serialization-2.0"
        self.assertNotEqual(model_manifest_sha256(serialization_variant), original)
        with self.assertRaises(EngineeringEvaluationValidationError):
            ModelManifest.from_dict(serialization_variant)

    def test_manifest_validation(self) -> None:
        mutators = (
            lambda m: m.update(extra=True),
            lambda m: m.update(model_manifest_format_version="1.0"),
            lambda m: m["applicability_rule_ids"].append(m["applicability_rule_ids"][0]),
            lambda m: m["required_input_features"].reverse(),
            lambda m: m["prohibited_input_features"].append("thermal.input"),
            lambda m: m.update(accepted_quantity_kinds=[]),
            lambda m: m["canonical_units"].update(length="mm"),
            lambda m: m["canonical_units"].update(power="W"),
            lambda m: m.update(implementation_git_commit="abc123"),
        )
        for mutate in mutators:
            value = base_manifest()
            mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(EngineeringEvaluationValidationError):
                ModelManifest.from_dict(value)

    def test_rid_01_through_rid_04_exact_allowlist(self) -> None:
        plan_hash = evaluation_plan_sha256(base_plan())
        manifest_hash = model_manifest_sha256(base_manifest())
        kwargs = {
            "epr_compiled_content_sha256": EPR_HASH,
            "evaluation_plan_sha256": plan_hash,
            "model_manifest_sha256": manifest_hash,
            "unit_registry_version": UNIT_REGISTRY_VERSION,
            "deterministic_runtime_policy_version": DETERMINISTIC_RUNTIME_POLICY_VERSION,
        }
        first = evaluation_input_sha256(**kwargs)
        self.assertEqual(first, evaluation_input_sha256(**kwargs))
        # No EER identifier is accepted by the allowlisted API, so changing one cannot affect this identity.
        self.assertNotIn("evaluation_id", kwargs)
        changed_unit = {**kwargs, "unit_registry_version": "synthetic-unit-registry-2.0"}
        changed_runtime = {**kwargs, "deterministic_runtime_policy_version": "synthetic-runtime-2.0"}
        self.assertNotEqual(first, evaluation_input_sha256(**changed_unit))
        self.assertNotEqual(first, evaluation_input_sha256(**changed_runtime))


class M16AEngineeringEvaluationResultTests(unittest.TestCase):
    def test_eer_01_determinism_mapping_order_and_caller_detachment(self) -> None:
        first = not_evaluated_eer()
        second = {key: first[key] for key in reversed(first)}
        one = EngineeringEvaluationResult.from_dict(first)
        two = EngineeringEvaluationResult.from_dict(second)
        self.assertEqual(one.canonical_bytes(), two.canonical_bytes())
        self.assertEqual(one.content_sha256, two.content_sha256)
        first["case_id"] = "mutated"
        first["evaluation_plan"]["model_options"]["iteration_limit"] = 99
        self.assertEqual(one.to_dict()["case_id"], "synthetic-i3a-case")
        self.assertEqual(one.to_dict()["evaluation_plan"]["model_options"]["iteration_limit"], 4)

    def test_eer_02_payload_change_updates_payload_and_eer_hash(self) -> None:
        first = evaluated_eer()
        second = evaluated_eer()
        second["result_payload"]["content"]["candidate_results"][0]["junction_temperature"] = "324"
        stamp_eer(second)
        self.assertNotEqual(first["result_payload"]["content_sha256"], second["result_payload"]["content_sha256"])
        self.assertNotEqual(first["eer_content_sha256"], second["eer_content_sha256"])
        EngineeringEvaluationResult.from_dict(second)

    def test_eer_03_eer_04_forged_plan_and_manifest_hashes_reject(self) -> None:
        for field in ("evaluation_plan_sha256", "model_manifest_sha256"):
            value = not_evaluated_eer()
            value[field] = "a" * 64
            value["eer_content_sha256"] = engineering_evaluation_result_content_sha256(value)
            with self.subTest(field=field), self.assertRaises(EngineeringEvaluationValidationError):
                EngineeringEvaluationResult.from_dict(value)

    def test_eer_05_not_evaluated_and_sep_01_no_rank(self) -> None:
        reconstructed = EngineeringEvaluationResult.from_dict(not_evaluated_eer())
        self.assertIsNone(reconstructed.to_dict()["result_payload"])
        self.assertEqual(reconstructed.to_dict()["prediction_outputs"], [])
        self.assertNotIn("rank", canonical_json_bytes(reconstructed.to_dict()).decode("utf-8"))

        with_disposition_payload = not_evaluated_eer()
        with_disposition_payload["result_payload"] = {
            "schema_id": "synthetic-result",
            "schema_version": "1.0",
            "content": {"scenario_dispositions": ["blocked", "not_applicable"]},
            "content_sha256": ZERO_HASH,
        }
        stamp_eer(with_disposition_payload)
        EngineeringEvaluationResult.from_dict(with_disposition_payload)

    def test_eer_06_evaluated_output_payload_and_pointer(self) -> None:
        reconstructed = EngineeringEvaluationResult.from_dict(evaluated_eer())
        self.assertEqual(reconstructed.to_dict()["prediction_outputs"][0]["value"], "323.15")
        bad_pointer = evaluated_eer()
        bad_pointer["prediction_outputs"][0]["result_pointer"] = "/candidate_results/1/value"
        stamp_eer(bad_pointer)
        with self.assertRaises(EngineeringEvaluationValidationError):
            EngineeringEvaluationResult.from_dict(bad_pointer)

    def test_eer_07_notice_is_exact(self) -> None:
        for notice in (None, "Model result only."):
            value = not_evaluated_eer()
            value["calculation_not_approval_notice"] = notice
            stamp_eer(value)
            with self.assertRaises(EngineeringEvaluationValidationError):
                EngineeringEvaluationResult.from_dict(value)

    def test_cross_binding_model_request_reference_versions_and_unknown_fields(self) -> None:
        mutators = (
            lambda e: e.update(extra=True),
            lambda e: e.update(engineering_evaluation_result_format_version="1.0"),
            lambda e: e.update(evaluation_id="EER-1"),
            lambda e: e.update(epr_reference="../EPR-001.json"),
            lambda e: e["evaluation_plan"].update(case_id="other-case"),
            lambda e: e["model_manifest"].update(model_version="2.0"),
            lambda e: e.update(unit_registry_version="other"),
            lambda e: e.update(deterministic_runtime_policy_version="other"),
        )
        for mutate in mutators:
            value = not_evaluated_eer()
            mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(EngineeringEvaluationValidationError):
                stamp_eer(value)
                EngineeringEvaluationResult.from_dict(value)

    def test_payload_schema_self_hash_outcome_and_float_reject(self) -> None:
        schema_mismatch = evaluated_eer()
        schema_mismatch["result_payload"]["schema_version"] = "2.0"
        stamp_eer(schema_mismatch)
        forged = evaluated_eer()
        forged["result_payload"]["content_sha256"] = "a" * 64
        forged["eer_content_sha256"] = engineering_evaluation_result_content_sha256(forged)
        outcome = evaluated_eer()
        outcome["execution_outcome"] = "completed"
        stamp_eer(outcome)
        floating = evaluated_eer()
        floating["result_payload"]["content"]["numeric"] = 1.25
        # Do not stamp: the public payload hash rejects float before any runtime trust decision.
        for broken in (schema_mismatch, forged, outcome, floating):
            with self.assertRaises((EngineeringEvaluationValidationError, TypeError)):
                EngineeringEvaluationResult.from_dict(broken)

    def test_assumptions_used_union_subset_scope_and_order(self) -> None:
        mismatch = evaluated_eer()
        mismatch["assumptions_used"] = []
        stamp_eer(mismatch)
        wrong_scope = evaluated_eer()
        wrong_scope["candidate_execution"][0]["assumption_acknowledgements_used"] = [
            acknowledgement("candidate", "CND-002", "/materials/x")
        ]
        stamp_eer(wrong_scope)
        not_in_plan = evaluated_eer()
        not_in_plan["candidate_execution"][0]["assumption_acknowledgements_used"] = [
            acknowledgement("candidate", "CND-001", "/materials/x")
        ]
        stamp_eer(not_in_plan)
        for broken in (mismatch, wrong_scope, not_in_plan):
            with self.assertRaises(EngineeringEvaluationValidationError):
                EngineeringEvaluationResult.from_dict(broken)

    def test_prediction_output_ids_bounds_units_status_and_canonical_decimal(self) -> None:
        mutators = (
            lambda e: e["prediction_outputs"][0].update(output_id="EER-002-OUT-001"),
            lambda e: e["prediction_outputs"][0].update(candidate_id="CND-002"),
            lambda e: e["prediction_outputs"][0].update(quantity_kind="length"),
            lambda e: e["prediction_outputs"][0].update(unit="degC"),
            lambda e: e["prediction_outputs"][0].update(value="323.150"),
            lambda e: e["prediction_outputs"][0].update(lower_bound="324"),
            lambda e: e["prediction_outputs"][0].update(upper_bound="322"),
        )
        for mutate in mutators:
            value = evaluated_eer()
            mutate(value)
            stamp_eer(value)
            with self.subTest(mutate=mutate), self.assertRaises(EngineeringEvaluationValidationError):
                EngineeringEvaluationResult.from_dict(value)

        duplicate = evaluated_eer()
        duplicate["prediction_outputs"].append(copy.deepcopy(duplicate["prediction_outputs"][0]))
        stamp_eer(duplicate)
        with self.assertRaises(EngineeringEvaluationValidationError):
            EngineeringEvaluationResult.from_dict(duplicate)

    def test_candidate_status_diagnostics_confidentiality_and_canonical_order(self) -> None:
        status = not_evaluated_eer()
        status["candidate_execution"][0].update(execution_status="evaluated", applicability_status="not_evaluated", result_presence=False)
        stamp_eer(status)
        bad_diagnostic = not_evaluated_eer()
        bad_diagnostic["warnings"] = [diagnostic("SYNTHETIC-DIAG-002"), diagnostic("SYNTHETIC-DIAG-001")]
        stamp_eer(bad_diagnostic)
        bad_confidentiality = not_evaluated_eer()
        bad_confidentiality["confidentiality_level"] = "secret"
        stamp_eer(bad_confidentiality)
        for broken in (status, bad_diagnostic, bad_confidentiality):
            with self.assertRaises(EngineeringEvaluationValidationError):
                EngineeringEvaluationResult.from_dict(broken)

    def test_sep_02_sep_03_no_review_or_model_execution_authority(self) -> None:
        eer = not_evaluated_eer()
        forbidden = {"reviewed_by", "approval_status", "solver", "rank", "sensitivity_values"}
        self.assertFalse(forbidden & set(eer))
        plan = EvaluationPlan.from_dict(base_plan())
        self.assertFalse(hasattr(plan, "execute"))
        self.assertFalse(hasattr(plan, "rank_candidates"))


if __name__ == "__main__":
    unittest.main()
