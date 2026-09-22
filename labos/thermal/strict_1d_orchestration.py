"""Deterministic I4B orchestration around the frozen strict-1D kernel."""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, localcontext
from itertools import product
from types import MappingProxyType
from typing import Any

from labos.engineering import (
    CALCULATION_NOT_APPROVAL_NOTICE,
    DETERMINISTIC_RUNTIME_POLICY_VERSION,
    ENGINEERING_EVALUATION_RESULT_FORMAT_VERSION,
    UNIT_REGISTRY_VERSION,
    BoundEvaluationPlan,
    EngineeringEvaluationResult,
    EngineeringProblem,
    EvaluationPlan,
    QuantifiedValue,
    QuantityKind,
    canonical_decimal_text,
    canonical_json_bytes,
    convert_quantity,
    engineering_evaluation_result_content_sha256,
    evaluation_input_sha256,
    evaluation_plan_sha256,
    model_manifest_sha256,
)

from .strict_1d import (
    CONSTRAINT_POLICY_VERSION,
    OAT_POLICY_VERSION,
    RANKING_POLICY_VERSION,
    SCENARIO_POLICY_VERSION,
    Strict1DValidationError,
    _ack_key,
    _bind_strict_1d_inputs,
    _decimal_context,
    _deduplicate_diagnostics,
    _diagnostic,
    _evaluate_strict_1d_scenario,
    _machine_constraint_threshold,
    _numeric_precondition_findings,
    _quantity_from_envelope,
    _resolve_pointer,
    _result_quantity,
    _scenario_envelope,
    build_strict_1d_model_manifest,
)
from .strict_1d_result import (
    build_strict_1d_result_payload,
    validate_strict_1d_result_content,
)
from .strict_1d_sensitivity import (
    _metric_result,
    _parameter_arithmetic,
    _prediction_outputs,
    _sensitivity_ranking,
)


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_thaw(item) for item in value]
    return value


def _quantity(value: Mapping[str, Any], path: str) -> QuantifiedValue:
    try:
        return QuantifiedValue.from_dict(
            {
                "quantity_kind": value["quantity_kind"],
                "canonical_value": value["value"],
                "canonical_unit": value["unit"],
                "conversion": value["conversion"],
            }
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise Strict1DValidationError(
            f"{path}: does not reconstruct through frozen I1 quantity authority: {exc}"
        ) from exc


def _scaled_integer(value: Decimal, exponent: int) -> int:
    parts = value.as_tuple()
    coefficient = 0
    for digit in parts.digits:
        coefficient = coefficient * 10 + digit
    if parts.sign:
        coefficient = -coefficient
    return coefficient * (10 ** (parts.exponent - exponent))


def _decimal_from_scaled_integer(value: int, exponent: int) -> Decimal:
    sign = 1 if value < 0 else 0
    digits_text = str(abs(value))
    digits = tuple(int(character) for character in digits_text)
    return Decimal((sign, digits, exponent))


def _canonical_quantity(kind: QuantityKind, value: Decimal, unit: str) -> QuantifiedValue:
    return convert_quantity(kind, canonical_decimal_text(value), unit)


def _expand_sweep(sweep: Mapping[str, Any], path: str) -> list[QuantifiedValue]:
    specification = sweep["value_specification"]
    if specification["kind"] == "grid":
        return [
            _quantity(point, f"{path}/value_specification/values/{index}")
            for index, point in enumerate(specification["values"])
        ]

    start = _quantity(specification["start"], f"{path}/value_specification/start")
    stop = _quantity(specification["stop"], f"{path}/value_specification/stop")
    step = _quantity(specification["step"], f"{path}/value_specification/step")
    exponent = min(
        start.canonical_value.as_tuple().exponent,
        stop.canonical_value.as_tuple().exponent,
        step.canonical_value.as_tuple().exponent,
    )
    current = _scaled_integer(start.canonical_value, exponent)
    stop_integer = _scaled_integer(stop.canonical_value, exponent)
    step_integer = _scaled_integer(step.canonical_value, exponent)
    ascending = step_integer > 0
    points: list[QuantifiedValue] = []
    while current < stop_integer if ascending else current > stop_integer:
        points.append(
            _canonical_quantity(
                start.quantity_kind,
                _decimal_from_scaled_integer(current, exponent),
                start.canonical_unit,
            )
        )
        current += step_integer
    if current == stop_integer and specification["endpoint_policy"] == "include_stop":
        points.append(
            _canonical_quantity(
                start.quantity_kind,
                _decimal_from_scaled_integer(current, exponent),
                start.canonical_unit,
            )
        )
    if not points:
        raise Strict1DValidationError(f"{path}: exact range expansion produced no points")
    return points


def _quantity_result(quantity: QuantifiedValue) -> dict[str, str]:
    return _result_quantity(
        quantity.canonical_value,
        quantity.quantity_kind,
        quantity.canonical_unit,
    )


def _replace_pointer(document: dict[str, Any], pointer: str, value: Any) -> None:
    tokens = pointer.split("/")[1:]
    current: Any = document
    for raw in tokens[:-1]:
        token = raw.replace("~1", "/").replace("~0", "~")
        current = current[int(token)] if type(current) is list else current[token]
    final = tokens[-1].replace("~1", "/").replace("~0", "~")
    if type(current) is list:
        current[int(final)] = value
    else:
        current[final] = value


def _diagnostic_union(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return _deduplicate_diagnostics(items)


def _constraint_results(
    problem: Mapping[str, Any],
    candidate: Mapping[str, Any],
    scenario: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    applicable = set(candidate["applicable_constraint_ids"])
    constraints = sorted(
        (item for item in problem["constraints"] if item["constraint_id"] in applicable),
        key=lambda item: item["constraint_id"],
    )
    results: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for constraint in constraints:
        supported = _machine_constraint_threshold(constraint)
        finding_ids: list[str] = []
        evaluated_quantity = None
        limit = None
        margin = None
        status = "not_evaluable"
        if not supported:
            finding_ids = ["I4-CNS-NOT-EVALUABLE"]
            diagnostics.append(
                _diagnostic(
                    "I4-CNS-NOT-EVALUABLE",
                    "MODEL_CONSTRAINT",
                    [constraint["target_path"]],
                    "The applicable constraint is outside strict-1D machine-evaluation semantics.",
                    "Review the constraint without treating it as a computed pass or fail.",
                )
            )
        elif scenario["disposition"] == "evaluated":
            threshold = _quantity_from_envelope(
                constraint["threshold"],
                f"/constraints/{constraint['constraint_id']}/threshold",
            )
            if threshold is not None:
                source = Decimal(
                    scenario["numerical_result"]["source_temperature"]["value"]
                )
                bound = threshold.canonical_value
                operator = constraint["operator"]
                with localcontext(_decimal_context()) as context:
                    if operator in {"le", "lt"}:
                        signed_margin = context.subtract(bound, source)
                    elif operator in {"ge", "gt"}:
                        signed_margin = context.subtract(source, bound)
                    else:
                        signed_margin = context.minus(abs(context.subtract(source, bound)))
                passed = {
                    "lt": source < bound,
                    "le": source <= bound,
                    "eq": source == bound,
                    "ge": source >= bound,
                    "gt": source > bound,
                }[operator]
                status = "pass" if passed else "fail"
                evaluated_quantity = _result_quantity(
                    source, QuantityKind.ABSOLUTE_TEMPERATURE, "K"
                )
                limit = _result_quantity(
                    bound, QuantityKind.ABSOLUTE_TEMPERATURE, "K"
                )
                margin = _result_quantity(
                    signed_margin, QuantityKind.TEMPERATURE_DIFFERENCE, "K"
                )
        results.append(
            {
                "constraint_id": constraint["constraint_id"],
                "scenario_id": scenario["scenario_id"],
                "status": status,
                "evaluated_quantity": evaluated_quantity,
                "limit": limit,
                "margin": margin,
                "operator": constraint["operator"],
                "finding_ids": finding_ids,
            }
        )
    return results, diagnostics


def _objective_value(
    problem: Mapping[str, Any], plan: Mapping[str, Any], scenario: Mapping[str, Any]
) -> dict[str, str] | None:
    numerical = scenario["numerical_result"]
    if numerical is None:
        return None
    metric = plan["objective"]["metric"]
    if metric == "source_temperature":
        return copy.deepcopy(numerical["source_temperature"])
    if metric == "total_thermal_resistance":
        return copy.deepcopy(numerical["total_thermal_resistance"])
    requirement = next(
        item
        for item in problem["requirements"]
        if item["requirement_id"] == plan["objective"]["reference_requirement_id"]
    )
    target = _quantity_from_envelope(requirement["target"], "/requirements/target")
    if target is None:
        return None
    source = Decimal(numerical["source_temperature"]["value"])
    with localcontext(_decimal_context()) as context:
        value = context.subtract(target.canonical_value, source)
    return _result_quantity(value, QuantityKind.TEMPERATURE_DIFFERENCE, "K")


def _coverage(scenarios: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "requested_core_scenarios": len(scenarios),
        "evaluated_core_scenarios": sum(item["disposition"] == "evaluated" for item in scenarios),
        "blocked_core_scenarios": sum(item["disposition"] == "blocked" for item in scenarios),
        "invalid_core_scenarios": sum(item["disposition"] == "invalid" for item in scenarios),
        "not_applicable_core_scenarios": sum(
            item["disposition"] == "not_applicable" for item in scenarios
        ),
        "oat_coverage": None,
    }


def _aggregate_candidate(
    scenarios: Sequence[Mapping[str, Any]], coverage: Mapping[str, Any]
) -> tuple[str, str, bool]:
    evaluated = coverage["evaluated_core_scenarios"]
    if evaluated:
        clean = evaluated == coverage["requested_core_scenarios"] and all(
            item["applicability_status"] == "applicable" for item in scenarios
        )
        return "evaluated", "applicable" if clean else "applicable_with_warnings", True
    if coverage["not_applicable_core_scenarios"] == coverage["requested_core_scenarios"]:
        return "not_applicable", "not_applicable", False
    return "blocked", "not_evaluated", False


def _execute_oat(
    problem: Mapping[str, Any],
    bound: Any,
    candidate: Mapping[str, Any],
    candidate_id: str,
    candidate_position: int,
    parameters: Sequence[tuple[Mapping[str, Any], QuantifiedValue, QuantifiedValue, QuantifiedValue]],
    metric: str,
    margin_target: Decimal | None,
    core_scenarios: Sequence[Mapping[str, Any]],
    has_sweeps: bool,
) -> tuple[dict[str, Any], dict[str, int], list[dict[str, Any]], list[dict[str, Any]]]:
    """Execute one auxiliary reference and each explicitly authored OAT side."""
    prefix = f"SCN-C{candidate_position:03d}"
    constraint_findings: list[dict[str, Any]] = []

    def scenario(
        scenario_id: str,
        kind: str,
        ordinal: int,
        field_path: str | None,
        side: str,
        point: QuantifiedValue | None = None,
    ) -> dict[str, Any]:
        if kind == "oat_reference" and not has_sweeps and core_scenarios[0]["disposition"] == "evaluated":
            record = copy.deepcopy(dict(core_scenarios[0]))
            record["scenario_id"] = scenario_id
            record["reused_core_scenario_id"] = core_scenarios[0]["scenario_id"]
            record["constraint_results"] = [
                {**copy.deepcopy(item), "scenario_id": scenario_id}
                for item in core_scenarios[0]["constraint_results"]
            ]
        else:
            detached = copy.deepcopy(dict(candidate))
            overrides: list[dict[str, Any]] = []
            invalid_paths: list[str] = []
            if field_path is not None and point is not None:
                original = _resolve_pointer(detached, field_path)
                _replace_pointer(detached, field_path, _scenario_envelope(original, point))
                overrides.append(
                    {
                        "source_kind": "oat",
                        "source_id": None,
                        "field_path": field_path,
                        "point_ordinal": ordinal,
                        "side": side,
                        "value": _quantity_result(point),
                    }
                )
                if any(
                    field_path in finding["field_paths"]
                    for finding in _numeric_precondition_findings(problem, detached)
                ):
                    invalid_paths.append(field_path)
            record = _evaluate_strict_1d_scenario(
                bound,
                candidate_id,
                scenario_id=scenario_id,
                candidate=detached,
                input_overrides=overrides,
                invalid_override_paths=invalid_paths,
            ).to_dict()
            constraints, diagnostics = _constraint_results(problem, detached, record)
            record["constraint_results"] = constraints
            constraint_findings.extend(diagnostics)
        record["scenario_kind"] = kind
        record["oat_coordinate"] = {
            "parameter_ordinal": ordinal,
            "field_path": field_path,
            "side": side,
        }
        return record

    reference = scenario(f"{prefix}-O000-REF", "oat_reference", 0, None, "reference")
    results: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    oat_scenarios = [reference]
    for ordinal, (parameter, x_reference, minus, plus) in enumerate(parameters, start=1):
        path = parameter["field_path"]
        minus_scenario = scenario(
            f"{prefix}-O{ordinal:03d}-MINUS", "oat_minus", ordinal, path, "minus", minus
        )
        plus_scenario = scenario(
            f"{prefix}-O{ordinal:03d}-PLUS", "oat_plus", ordinal, path, "plus", plus
        )
        oat_scenarios.extend((minus_scenario, plus_scenario))
        disposition, derivative, normalized, normalized_disposition, finding_ids = _parameter_arithmetic(
            metric=metric,
            x_reference=_quantity_result(x_reference),
            x_minus=_quantity_result(minus),
            x_plus=_quantity_result(plus),
            y_reference=_metric_result(reference, metric, margin_target),
            y_minus=_metric_result(minus_scenario, metric, margin_target),
            y_plus=_metric_result(plus_scenario, metric, margin_target),
        )
        results.append(
            {
                "parameter_ordinal": ordinal,
                "field_path": path,
                "x_reference": _quantity_result(x_reference),
                "minus_scenario": minus_scenario,
                "plus_scenario": plus_scenario,
                "disposition": disposition,
                "dimensional_derivative": derivative,
                "normalized_sensitivity": normalized,
                "normalized_sensitivity_disposition": normalized_disposition,
                "finding_ids": finding_ids,
            }
        )
        if disposition == "incomplete":
            unavailable = [
                item["scenario_id"]
                for item in (reference, minus_scenario, plus_scenario)
                if item["disposition"] != "evaluated"
            ]
            diagnostics.append(
                _diagnostic(
                    "I4-OAT-INCOMPLETE",
                    "MODEL_EXECUTION",
                    [path],
                    "Central sensitivity is unavailable for requested scenario(s): "
                    + ", ".join(unavailable),
                    "Review the exact unavailable OAT scenario findings; no one-sided derivative is used.",
                )
            )
        elif normalized_disposition != "evaluated":
            diagnostics.append(
                _diagnostic(
                    "I4-OAT-NORMALIZED-NOT-DEFINED",
                    "MODEL_SENSITIVITY",
                    [path],
                    f"Normalized sensitivity is undefined: {normalized_disposition}.",
                    "Use the complete dimensional derivative without a normalized rank.",
                )
            )
    ranking_status, ranking = _sensitivity_ranking(results)
    oat_result = {
        "method": "oat",
        "output_metric": metric,
        "reference_scenario": reference,
        "parameters": results,
        "ranking_status": ranking_status,
        "sensitivity_ranking": ranking,
    }
    coverage = {
        "requested_oat_points": len(oat_scenarios),
        "evaluated_oat_points": sum(item["disposition"] == "evaluated" for item in oat_scenarios),
        "blocked_oat_points": sum(item["disposition"] == "blocked" for item in oat_scenarios),
        "invalid_oat_points": sum(item["disposition"] == "invalid" for item in oat_scenarios),
        "not_applicable_oat_points": sum(item["disposition"] == "not_applicable" for item in oat_scenarios),
    }
    return oat_result, coverage, diagnostics, constraint_findings


@dataclass(frozen=True, slots=True)
class Strict1DOrchestrationResult:
    """Immutable pure I4B orchestration authority."""

    _content: Mapping[str, Any]

    @property
    def execution_outcome(self) -> str:
        return self._content["execution_outcome"]

    @property
    def candidate_execution(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(_freeze(_thaw(item)) for item in self._content["candidate_execution"])

    @property
    def assumptions_used(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(_freeze(_thaw(item)) for item in self._content["assumptions_used"])

    @property
    def result_payload(self) -> Mapping[str, Any]:
        return _freeze(_thaw(self._content["result_payload"]))

    @property
    def findings(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(_freeze(_thaw(item)) for item in self._content["findings"])

    @property
    def warnings(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(_freeze(_thaw(item)) for item in self._content["warnings"])

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._content)

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self._content)


def orchestrate_strict_1d(
    engineering_problem: EngineeringProblem,
    evaluation_plan: EvaluationPlan,
    implementation_git_commit: str | None = None,
) -> Strict1DOrchestrationResult:
    """Execute deterministic core and auxiliary OAT scenarios without persistence."""
    if not isinstance(engineering_problem, EngineeringProblem):
        raise TypeError("engineering_problem must be an EngineeringProblem")
    if not isinstance(evaluation_plan, EvaluationPlan):
        raise TypeError("evaluation_plan must be an EvaluationPlan")
    problem = engineering_problem.to_dict()
    plan = evaluation_plan.to_dict()
    sensitivity = plan["sensitivity_request"]
    if sensitivity is not None and sensitivity["output_metric"] == "temperature_margin" and (
        plan["objective"]["metric"] != "temperature_margin"
        or plan["objective"]["reference_requirement_id"] is None
    ):
        raise Strict1DValidationError(
            "/sensitivity_request/output_metric: temperature_margin requires the exact Plan temperature-margin objective reference"
        )
    if plan["objective"]["metric"] == "temperature_margin":
        requirement = next(
            (
                item
                for item in problem["requirements"]
                if item["requirement_id"]
                == plan["objective"]["reference_requirement_id"]
            ),
            None,
        )
        if (
            requirement is None
            or requirement["target_path"] != "/heat_sources/0/source_location"
        ):
            raise Strict1DValidationError(
                "/objective/reference_requirement_id: temperature_margin requires the exact source-location target"
            )
        target = requirement.get("target")
        if (
            not isinstance(target, Mapping)
            or target.get("quantity_kind") != QuantityKind.ABSOLUTE_TEMPERATURE.value
            or target.get("status") not in {"provided", "assumed", "evidence_required"}
            or target.get("value") is None
            or target.get("conversion") is None
        ):
            raise Strict1DValidationError(
                "/objective/reference_requirement_id: temperature_margin requires a usable absolute-temperature target"
            )
        target_quantity = _quantity_from_envelope(target, "/requirements/target")
        if target_quantity is None or target_quantity.canonical_value < 0:
            raise Strict1DValidationError(
                "/objective/reference_requirement_id: temperature target is nonphysical"
            )

    build_strict_1d_model_manifest(implementation_git_commit)
    # I4A's frozen binder intentionally rejects OAT requests. Bind the identical
    # core request through its existing authority; retain the original Plan for
    # OAT execution and all EER identities.
    binding_plan = copy.deepcopy(plan)
    binding_plan["sensitivity_request"] = None
    bound = _bind_strict_1d_inputs(
        engineering_problem,
        EvaluationPlan.from_dict(binding_plan),
        allow_parameter_sweeps=True,
        include_machine_constraint_thresholds=True,
    )
    candidates = {item["candidate_id"]: item for item in problem["candidates"]}
    oat_parameters: list[tuple[Mapping[str, Any], QuantifiedValue, QuantifiedValue, QuantifiedValue]] = []
    margin_target: Decimal | None = None
    if sensitivity is not None:
        baseline = candidates[sensitivity["baseline_candidate_id"]]
        for index, parameter in enumerate(sensitivity["parameters"]):
            path = parameter["field_path"]
            target = _resolve_pointer(baseline, path)
            if not isinstance(target, Mapping):
                raise Strict1DValidationError(
                    f"/sensitivity_request/parameters/{index}/field_path: must resolve to a quantified-value envelope"
                )
            x_reference = _quantity_from_envelope(target, path)
            if x_reference is None:
                raise Strict1DValidationError(
                    f"/sensitivity_request/parameters/{index}/field_path: requires a resolved numeric baseline value"
                )
            minus = _quantity(parameter["minus_value"], f"/sensitivity_request/parameters/{index}/minus_value")
            plus = _quantity(parameter["plus_value"], f"/sensitivity_request/parameters/{index}/plus_value")
            if minus.quantity_kind is not x_reference.quantity_kind or plus.quantity_kind is not x_reference.quantity_kind:
                raise Strict1DValidationError(
                    f"/sensitivity_request/parameters/{index}: point QuantityKind does not match target"
                )
            oat_parameters.append((parameter, x_reference, minus, plus))
        if sensitivity["output_metric"] == "temperature_margin":
            requirement = next(
                item for item in problem["requirements"]
                if item["requirement_id"] == plan["objective"]["reference_requirement_id"]
            )
            margin_target = _quantity_from_envelope(
                requirement["target"], "/requirements/target"
            ).canonical_value
    expanded: list[tuple[Mapping[str, Any], list[QuantifiedValue]]] = []
    seen_targets: set[tuple[str, str]] = set()
    for index, sweep in enumerate(plan["parameter_sweeps"]):
        target_key = (sweep["candidate_id"], sweep["field_path"])
        if target_key in seen_targets:
            raise Strict1DValidationError(
                f"/parameter_sweeps/{index}/field_path: duplicate candidate target has no unambiguous scenario override"
            )
        seen_targets.add(target_key)
        candidate = candidates[sweep["candidate_id"]]
        target = _resolve_pointer(candidate, sweep["field_path"])
        if not isinstance(target, Mapping):
            raise Strict1DValidationError(
                f"/parameter_sweeps/{index}/field_path: must resolve to a quantified-value envelope"
            )
        target_quantity = _quantity_from_envelope(target, sweep["field_path"])
        if target_quantity is None:
            raise Strict1DValidationError(
                f"/parameter_sweeps/{index}/field_path: target must have a usable numeric value"
            )
        points = _expand_sweep(sweep, f"/parameter_sweeps/{index}")
        if any(point.quantity_kind is not target_quantity.quantity_kind for point in points):
            raise Strict1DValidationError(
                f"/parameter_sweeps/{index}: point QuantityKind does not match target"
            )
        expanded.append((sweep, points))

    total = 0
    candidate_results: list[dict[str, Any]] = []
    candidate_execution: list[dict[str, Any]] = []
    ranking_basis: dict[str, tuple[dict[str, Any], dict[str, str]] | None] = {}
    for candidate_position, candidate_id in enumerate(plan["selected_candidate_ids"], start=1):
        candidate = candidates[candidate_id]
        candidate_sweeps = [item for item in expanded if item[0]["candidate_id"] == candidate_id]
        combinations = list(product(*(points for _sweep, points in candidate_sweeps))) if candidate_sweeps else [()]
        total += len(combinations)
        scenarios: list[dict[str, Any]] = []
        constraint_diagnostics: list[dict[str, Any]] = []
        for scenario_ordinal, combination in enumerate(combinations, start=1):
            scenario_id = f"SCN-C{candidate_position:03d}-K{scenario_ordinal:06d}"
            detached = copy.deepcopy(candidate)
            coordinates: list[dict[str, Any]] = []
            overrides: list[dict[str, Any]] = []
            override_paths: list[str] = []
            for (sweep, _points), point in zip(candidate_sweeps, combination):
                path = sweep["field_path"]
                original = _resolve_pointer(detached, path)
                _replace_pointer(detached, path, _scenario_envelope(original, point))
                point_ordinal = next(
                    index
                    for index, candidate_point in enumerate(_points, start=1)
                    if candidate_point.numeric_identity == point.numeric_identity
                )
                quantity = _quantity_result(point)
                coordinates.append(
                    {
                        "sweep_id": sweep["sweep_id"],
                        "field_path": path,
                        "point_ordinal": point_ordinal,
                        "value": quantity,
                    }
                )
                overrides.append(
                    {
                        "source_kind": "sweep",
                        "source_id": sweep["sweep_id"],
                        "field_path": path,
                        "point_ordinal": point_ordinal,
                        "side": None,
                        "value": copy.deepcopy(quantity),
                    }
                )
                override_paths.append(path)
            numerical_findings = _numeric_precondition_findings(problem, detached)
            invalid_paths = sorted(
                {
                    path
                    for finding in numerical_findings
                    for path in finding["field_paths"]
                    if path in set(override_paths)
                }
            )
            scenario = _evaluate_strict_1d_scenario(
                bound,
                candidate_id,
                scenario_id=scenario_id,
                candidate=detached,
                sweep_coordinates=coordinates,
                input_overrides=overrides,
                invalid_override_paths=invalid_paths,
            ).to_dict()
            constraint_results, diagnostics = _constraint_results(
                problem, detached, scenario
            )
            scenario["constraint_results"] = constraint_results
            constraint_diagnostics.extend(diagnostics)
            scenarios.append(scenario)

        coverage = _coverage(scenarios)
        status, applicability, result_presence = _aggregate_candidate(scenarios, coverage)
        oat_result = None
        oat_diagnostics: list[dict[str, Any]] = []
        oat_scenarios: list[dict[str, Any]] = []
        if sensitivity is not None and sensitivity["baseline_candidate_id"] == candidate_id:
            oat_result, oat_coverage, oat_diagnostics, oat_constraint_diagnostics = _execute_oat(
                problem,
                bound,
                candidate,
                candidate_id,
                candidate_position,
                oat_parameters,
                sensitivity["output_metric"],
                margin_target,
                scenarios,
                bool(candidate_sweeps),
            )
            coverage["oat_coverage"] = oat_coverage
            oat_scenarios = [oat_result["reference_scenario"]] + [
                scenario
                for parameter in oat_result["parameters"]
                for scenario in (parameter["minus_scenario"], parameter["plus_scenario"])
            ]
            constraint_diagnostics.extend(oat_constraint_diagnostics)
            if status == "evaluated" and (
                oat_coverage["evaluated_oat_points"] != oat_coverage["requested_oat_points"]
                or any(item["applicability_status"] == "applicable_with_warnings" for item in oat_scenarios)
                or any(item["disposition"] == "incomplete" for item in oat_result["parameters"])
            ):
                applicability = "applicable_with_warnings"
        findings = _diagnostic_union(
            [item for scenario in scenarios + oat_scenarios for item in scenario["applicability_findings"]]
            + constraint_diagnostics
            + [item for item in oat_diagnostics if item["rule_id"] == "I4-OAT-NORMALIZED-NOT-DEFINED"]
        )
        warnings = _diagnostic_union(
            [item for scenario in scenarios + oat_scenarios for item in scenario["execution_findings"]]
            + [item for item in oat_diagnostics if item["rule_id"] == "I4-OAT-INCOMPLETE"]
        )
        partial = status == "evaluated" and (
            coverage["evaluated_core_scenarios"] != coverage["requested_core_scenarios"]
            or any(item["applicability_status"] == "applicable_with_warnings" for item in scenarios)
            or (oat_result is not None and applicability == "applicable_with_warnings")
        )
        if partial:
            warnings = _diagnostic_union(
                warnings
                + [
                    _diagnostic(
                        "I4-SCENARIO-PARTIAL-COVERAGE",
                        "MODEL_EXECUTION",
                        [f"/candidate_results/{candidate_position - 1}/coverage_summary"],
                        "An evaluated candidate has incomplete or warning-bearing requested scenario coverage.",
                        "Review every explicit core and OAT scenario before relying on the candidate result.",
                    )
                ]
            )
        applicability_findings = _diagnostic_union(
            [
                item
                for scenario in scenarios + oat_scenarios
                for item in scenario["applicability_findings"]
            ]
            + [
                item
                for item in warnings
                if item["rule_id"] == "I4-SCENARIO-PARTIAL-COVERAGE"
            ]
        )
        used = {
            canonical_json_bytes(item): item
            for scenario in scenarios + oat_scenarios
            if scenario["disposition"] == "evaluated"
            for item in scenario["assumption_acknowledgements_used"]
        }
        used_ordered = sorted(used.values(), key=_ack_key)
        sweep_result = None
        if candidate_sweeps:
            sweep_result = {
                "sweep_ids": [item[0]["sweep_id"] for item in candidate_sweeps],
                "field_paths": [item[0]["field_path"] for item in candidate_sweeps],
                "enumeration_rule": "first_sweep_outermost_last_sweep_innermost",
                "scenario_ids": [item["scenario_id"] for item in scenarios],
            }
        candidate_result = {
            "candidate_id": candidate_id,
            "coverage_summary": coverage,
            "core_scenarios": scenarios,
            "sweep_result": sweep_result,
            "oat_result": oat_result,
            "findings": findings,
            "warnings": warnings,
        }
        candidate_results.append(candidate_result)
        candidate_execution.append(
            {
                "candidate_id": candidate_id,
                "execution_status": status,
                "applicability_status": applicability,
                "applicability_findings": applicability_findings,
                "assumption_acknowledgements_used": used_ordered,
                "result_presence": result_presence,
            }
        )
        basis = None
        if not candidate_sweeps and scenarios[0]["disposition"] == "evaluated":
            objective_value = _objective_value(problem, plan, scenarios[0])
            if objective_value is not None:
                basis = (scenarios[0], objective_value)
        ranking_basis[candidate_id] = basis

    if total != evaluation_plan.total_requested_combination_count:
        raise Strict1DValidationError(
            "/parameter_sweeps: generated Cartesian count does not match frozen I3 plan authority"
        )

    eligibility: list[dict[str, Any]] = []
    eligible: list[tuple[str, dict[str, Any], dict[str, str]]] = []
    for eligibility_index, (candidate_result, execution) in enumerate(
        zip(candidate_results, candidate_execution)
    ):
        candidate_id = candidate_result["candidate_id"]
        basis = ranking_basis[candidate_id]
        reason_ids: list[str] = []
        basis_scenario_id = None
        if candidate_result["sweep_result"] is not None or basis is None or execution["execution_status"] != "evaluated":
            reason_ids.append("I4-RANK-INELIGIBLE-BASIS")
        else:
            scenario, objective_value = basis
            basis_scenario_id = scenario["scenario_id"]
            if (
                plan["constraint_handling"] == "exclude_violating_from_rank"
                and any(item["status"] == "fail" for item in scenario["constraint_results"])
            ):
                reason_ids.append("I4-RANK-CONSTRAINT-VIOLATION")
            else:
                eligible.append((candidate_id, scenario, objective_value))
        eligibility.append(
            {
                "candidate_id": candidate_id,
                "eligible": not reason_ids,
                "basis_scenario_id": basis_scenario_id,
                "reason_ids": sorted(set(reason_ids)),
            }
        )
        ranking_diagnostics: list[dict[str, Any]] = []
        if "I4-RANK-INELIGIBLE-BASIS" in reason_ids:
            ranking_diagnostics.append(
                _diagnostic(
                    "I4-RANK-INELIGIBLE-BASIS",
                    "MODEL_COMPARISON",
                    [f"/candidate_comparison/candidate_eligibility/{eligibility_index}"],
                    "The candidate has no authorized sole unswept evaluated ranking basis.",
                    "Use an evaluated unswept baseline when candidate-level ranking is required.",
                )
            )
        if "I4-RANK-CONSTRAINT-VIOLATION" in reason_ids:
            ranking_diagnostics.append(
                _diagnostic(
                    "I4-RANK-CONSTRAINT-VIOLATION",
                    "MODEL_COMPARISON",
                    [f"/candidate_comparison/candidate_eligibility/{eligibility_index}"],
                    "The declared constraint policy excludes a basis scenario with a failed machine-evaluable constraint.",
                    "Review the failed constraint or use report_only without treating ranking as approval.",
                )
            )
        if ranking_diagnostics:
            candidate_result["findings"] = _diagnostic_union(
                candidate_result["findings"] + ranking_diagnostics
            )

    direction = plan["objective"]["direction"]
    eligible.sort(
        key=lambda item: (
            Decimal(item[2]["value"])
            if direction == "minimize"
            else Decimal(item[2]["value"]).copy_negate(),
            item[0],
        )
    )
    ranked_entries = []
    ranking_status = "performed" if len(eligible) >= 2 else "not_performed"
    if ranking_status == "performed":
        ranked_entries = [
            {
                "rank": index,
                "candidate_id": candidate_id,
                "scenario_id": scenario["scenario_id"],
                "objective_metric": plan["objective"]["metric"],
                "objective_value": copy.deepcopy(objective_value),
            }
            for index, (candidate_id, scenario, objective_value) in enumerate(eligible, start=1)
        ]
    comparison = {
        "objective": copy.deepcopy(plan["objective"]),
        "comparison_basis_rule": "sole_unswept_baseline_only",
        "constraint_handling": plan["constraint_handling"],
        "ranking_status": ranking_status,
        "candidate_eligibility": eligibility,
        "ranked_entries": ranked_entries,
        "tie_rule": "objective_value_then_candidate_id",
        "calculation_notice": "Ranking is a conditional calculation, not a recommendation or approval.",
    }
    top_findings = _diagnostic_union(
        [item for candidate in candidate_results for item in candidate["findings"]]
    )
    top_warnings = _diagnostic_union(
        [item for candidate in candidate_results for item in candidate["warnings"]]
    )
    content = {
        "scenario_policy_version": SCENARIO_POLICY_VERSION,
        "constraint_policy_version": CONSTRAINT_POLICY_VERSION,
        "ranking_policy_version": RANKING_POLICY_VERSION,
        "oat_policy_version": OAT_POLICY_VERSION,
        "candidate_results": candidate_results,
        "candidate_comparison": comparison,
        "findings": top_findings,
        "warnings": top_warnings,
    }
    validate_strict_1d_result_content(content)
    payload = dict(build_strict_1d_result_payload(content))
    evaluated_count = sum(
        item["execution_status"] == "evaluated" for item in candidate_execution
    )
    outcome = (
        "completed"
        if evaluated_count == len(candidate_execution)
        else "partial"
        if evaluated_count
        else "not_evaluated"
    )
    assumption_union = {
        canonical_json_bytes(item): item
        for execution in candidate_execution
        if execution["execution_status"] == "evaluated"
        for item in execution["assumption_acknowledgements_used"]
    }
    result = {
        "execution_outcome": outcome,
        "candidate_execution": candidate_execution,
        "assumptions_used": sorted(assumption_union.values(), key=_ack_key),
        "result_payload": payload,
        "findings": top_findings,
        "warnings": top_warnings,
    }
    return Strict1DOrchestrationResult(_freeze(result))


def build_strict_1d_engineering_evaluation_result(
    bound_plan: BoundEvaluationPlan,
    evaluation_id: str,
    implementation_git_commit: str | None = None,
) -> EngineeringEvaluationResult:
    """Construct, but do not persist, the frozen I3 EER around one I4 run."""
    if not isinstance(bound_plan, BoundEvaluationPlan):
        raise TypeError("bound_plan must be a BoundEvaluationPlan")
    orchestration = orchestrate_strict_1d(
        bound_plan.engineering_problem,
        bound_plan.evaluation_plan,
        implementation_git_commit,
    ).to_dict()
    plan = bound_plan.evaluation_plan
    problem = bound_plan.engineering_problem
    manifest = build_strict_1d_model_manifest(implementation_git_commit)
    plan_hash = evaluation_plan_sha256(plan)
    manifest_hash = model_manifest_sha256(manifest)
    input_hash = evaluation_input_sha256(
        epr_compiled_content_sha256=problem.content_sha256,
        evaluation_plan_sha256=plan_hash,
        model_manifest_sha256=manifest_hash,
        unit_registry_version=UNIT_REGISTRY_VERSION,
        deterministic_runtime_policy_version=DETERMINISTIC_RUNTIME_POLICY_VERSION,
    )
    value = {
        "engineering_evaluation_result_format_version": ENGINEERING_EVALUATION_RESULT_FORMAT_VERSION,
        "evaluation_id": evaluation_id,
        "case_id": plan.to_dict()["case_id"],
        "problem_id": problem.problem_id,
        "epr_reference": bound_plan.epr_reference,
        "epr_compiled_content_sha256": problem.content_sha256,
        "epr_file_sha256": bound_plan.epr_file_sha256,
        "evaluation_plan": plan.to_dict(),
        "evaluation_plan_sha256": plan_hash,
        "model_manifest": manifest.to_dict(),
        "model_manifest_sha256": manifest_hash,
        "unit_registry_version": UNIT_REGISTRY_VERSION,
        "deterministic_runtime_policy_version": DETERMINISTIC_RUNTIME_POLICY_VERSION,
        "evaluation_input_sha256": input_hash,
        "execution_outcome": orchestration["execution_outcome"],
        "candidate_execution": orchestration["candidate_execution"],
        "assumptions_used": orchestration["assumptions_used"],
        "result_payload": orchestration["result_payload"],
        "prediction_outputs": _prediction_outputs(
            orchestration["result_payload"]["content"],
            orchestration["candidate_execution"],
            evaluation_id,
        ),
        "findings": orchestration["findings"],
        "warnings": orchestration["warnings"],
        "confidentiality_level": problem.to_dict()["confidentiality_level"],
        "calculation_not_approval_notice": CALCULATION_NOT_APPROVAL_NOTICE,
        "eer_content_sha256": "0" * 64,
    }
    value["eer_content_sha256"] = engineering_evaluation_result_content_sha256(value)
    return EngineeringEvaluationResult.from_dict(value)


__all__ = [
    "Strict1DOrchestrationResult",
    "build_strict_1d_engineering_evaluation_result",
    "orchestrate_strict_1d",
]
