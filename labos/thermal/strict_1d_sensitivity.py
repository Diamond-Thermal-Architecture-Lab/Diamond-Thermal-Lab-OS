"""Pure exact arithmetic and output construction for strict-1D OAT analysis."""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from decimal import Decimal, localcontext
from typing import Any

from labos.engineering import QuantityKind, canonical_decimal_text

from .strict_1d import _decimal_context, _result_quantity


def _metric_result(
    scenario: Mapping[str, Any], metric: str, margin_target: Decimal | None
) -> Mapping[str, str] | None:
    numerical = scenario["numerical_result"]
    if numerical is None:
        return None
    if metric != "temperature_margin":
        return numerical[metric]
    if margin_target is None:
        raise ValueError("temperature_margin requires the exact Plan target")
    with localcontext(_decimal_context()) as context:
        margin = context.subtract(
            margin_target, Decimal(numerical["source_temperature"]["value"])
        )
    return _result_quantity(margin, QuantityKind.TEMPERATURE_DIFFERENCE, "K")


def _parameter_arithmetic(
    *,
    metric: str,
    x_reference: Mapping[str, str],
    x_minus: Mapping[str, str],
    x_plus: Mapping[str, str],
    y_reference: Mapping[str, str] | None,
    y_minus: Mapping[str, str] | None,
    y_plus: Mapping[str, str] | None,
) -> tuple[str, dict[str, str] | None, dict[str, str] | None, str, list[str]]:
    """Return the frozen central derivative and normalization disposition."""
    if y_reference is None or y_minus is None or y_plus is None:
        return "incomplete", None, None, "incomplete", ["I4-OAT-INCOMPLETE"]
    x_ref = Decimal(x_reference["value"])
    minus = Decimal(x_minus["value"])
    plus = Decimal(x_plus["value"])
    if plus == minus:
        return "incomplete", None, None, "incomplete", ["I4-OAT-INCOMPLETE"]
    y_ref = Decimal(y_reference["value"])
    with localcontext(_decimal_context()) as context:
        numerator = context.subtract(Decimal(y_plus["value"]), Decimal(y_minus["value"]))
        denominator = context.subtract(plus, minus)
        derivative_value = context.divide(numerator, denominator)
    derivative = {
        "value": canonical_decimal_text(derivative_value),
        "output_quantity_kind": y_reference["quantity_kind"],
        "output_unit": y_reference["unit"],
        "input_quantity_kind": x_reference["quantity_kind"],
        "input_unit": x_reference["unit"],
    }
    if metric == "source_temperature":
        disposition = "absolute_temperature_not_normalized"
    elif x_ref == 0:
        disposition = "zero_x_reference"
    elif y_ref == 0:
        disposition = "zero_y_reference"
    else:
        with localcontext(_decimal_context()) as context:
            ratio = context.divide(x_ref, y_ref)
            normalized_value = context.multiply(derivative_value, ratio)
        return (
            "complete", derivative,
            _result_quantity(normalized_value, QuantityKind.PHYSICAL_DIMENSIONLESS, "1"),
            "evaluated", [],
        )
    return "complete", derivative, None, disposition, ["I4-OAT-NORMALIZED-NOT-DEFINED"]


def _sensitivity_ranking(
    parameters: Sequence[Mapping[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    eligible = [
        item for item in parameters
        if item["disposition"] == "complete" and item["normalized_sensitivity"] is not None
    ]
    eligible.sort(
        key=lambda item: (
            Decimal(item["normalized_sensitivity"]["value"]).copy_abs().copy_negate(),
            item["field_path"],
        )
    )
    return (
        "performed" if eligible else "not_performed",
        [
            {
                "rank": ordinal,
                "field_path": item["field_path"],
                "normalized_sensitivity": copy.deepcopy(item["normalized_sensitivity"]),
            }
            for ordinal, item in enumerate(eligible, start=1)
        ],
    )


def _prediction_outputs(
    content: Mapping[str, Any],
    executions: Sequence[Mapping[str, Any]],
    evaluation_id: str,
) -> list[dict[str, Any]]:
    """Emit and independently resolve each sole-baseline value pointer."""
    outputs: list[dict[str, Any]] = []
    metrics = ("source_temperature", "temperature_rise", "total_thermal_resistance")
    for candidate_index, (candidate, execution) in enumerate(
        zip(content["candidate_results"], executions)
    ):
        if execution["execution_status"] != "evaluated" or not execution["result_presence"]:
            continue
        if candidate["sweep_result"] is not None or len(candidate["core_scenarios"]) != 1:
            continue
        baseline = candidate["core_scenarios"][0]
        if baseline["disposition"] != "evaluated" or baseline["sweep_coordinates"]:
            continue
        for metric in metrics:
            quantity = baseline["numerical_result"][metric]
            pointer = (
                f"/candidate_results/{candidate_index}/core_scenarios/0/"
                f"numerical_result/{metric}/value"
            )
            output = {
                "output_id": f"{evaluation_id}-OUT-{len(outputs) + 1:03d}",
                "candidate_id": candidate["candidate_id"],
                "quantity_label": metric,
                "quantity_kind": quantity["quantity_kind"],
                "value": quantity["value"],
                "unit": quantity["unit"],
                "lower_bound": None,
                "upper_bound": None,
                "result_pointer": pointer,
            }
            tokens = pointer.split("/")[1:]
            resolved: Any = content
            for token in tokens[:-2]:
                resolved = resolved[int(token)] if type(resolved) is list else resolved[token]
            resolved_quantity = resolved[tokens[-2]]
            if (
                resolved_quantity["value"] != output["value"]
                or resolved_quantity["quantity_kind"] != output["quantity_kind"]
                or resolved_quantity["unit"] != output["unit"]
                or tokens[-1] != "value"
            ):
                raise ValueError(f"prediction output pointer does not identify {metric}")
            outputs.append(output)
    return outputs
