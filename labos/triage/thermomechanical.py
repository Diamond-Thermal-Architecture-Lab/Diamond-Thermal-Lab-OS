from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from labos.evidence.loader import iter_sidecar_json

from .models import TriggeredRule
from .rules import MISSING_RE


STRUCTURAL_TERMS = ("membrane", "suspended region", "suspended area", "thin structural layer")
FIXTURE_TERMS = ("fixture", "sample holder", "carrier", "reactor", "plasma", "frame-to-fixture")
DOWNSTREAM_TERMS = ("lithography", "handling", "packaging", "metallization", "downstream")
POSITIVE_TERMS = ("defined", "documented", "measured", "reviewed", "bounded", "available", "compared", "evaluated", "validated")
UNRESOLVED_RE = re.compile(r"\b(unmeasured|unbounded|not measured|not available|not defined)\b", re.IGNORECASE)
DIMENSION_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:mm|millimeter(?:s)?)\b", re.IGNORECASE)
INTEGRATION_RE = re.compile(
    r"(?:\b(?:deposited|coated|bonded|grown|integrated)\b.{0,80}\b(?:on|to|with)\b|"
    r"\b(?:deposited|coated|grown)\b.{0,80}\b(?:film|coating|layer)\b.{0,80}\b(?:by|using)\s+(?:cvd|deposition)\b|"
    r"\b(?:add|adds|adding)\b.{0,80}\b(?:diamond|coating|film|layer)\b.{0,80}\b(?:on|to)\b|"
    r"\bdirect(?:ly)?\b.{0,80}\b(?:cvd|growth|deposition)\b)",
    re.IGNORECASE,
)
THERMAL_PROCESS_RE = re.compile(
    r"\b(?:mpcvd|cvd|anneal(?:ing)?|thermal\s+(?:growth|deposition|process)|process\s+temperature)\b",
    re.IGNORECASE,
)
LATERAL_TERMS = ("membrane diameter", "membrane size", "lateral dimension", "suspended area", "device area", "intended size range")
FIXTURE_BOUNDARY_TERMS = ("thermal boundary", "thermal contact", "contact conductance", "contact condition", "ambient boundary", "reactor wall")


@dataclass(frozen=True)
class EvidenceState:
    source_quantities: frozenset[str]
    reviewed_quantities: frozenset[str]
    limitations: tuple[str, ...]


def _lines(text: str) -> list[str]:
    return [line.strip().lower() for line in text.splitlines() if line.strip()]


def _has_unresolved_marker(line: str) -> bool:
    return MISSING_RE.search(line) is not None or UNRESOLVED_RE.search(line) is not None


def _listed_as_missing(lines: list[str], terms: tuple[str, ...]) -> bool:
    """Recognize canonical intake `missing_data` entries that omit words such as TODO."""
    in_missing_data = False
    for line in lines:
        if line == "missing_data:":
            in_missing_data = True
            continue
        if in_missing_data and not line.startswith("-"):
            in_missing_data = False
        if in_missing_data and any(term in line for term in terms):
            return True
    return False


def _resolved_declaration(lines: list[str], terms: tuple[str, ...], *, factual: bool = False) -> bool:
    """Recognize an explicit stated basis, never proof that the statement is true."""
    for line in lines:
        if not any(term in line for term in terms) or _has_unresolved_marker(line):
            continue
        if any(term in line for term in POSITIVE_TERMS):
            return True
        if factual and (
            re.search(r"\d", line)
            or "approximately" in line
            or any(marker in line for marker in ("cooling to", "cooling from", "to room temperature", "after cooling"))
        ):
            return True
    return False


def _applicable(lines: list[str]) -> bool:
    structural = any(any(term in line for term in STRUCTURAL_TERMS) for line in lines)
    integration = any(INTEGRATION_RE.search(line) for line in lines)
    thermal_process = any(THERMAL_PROCESS_RE.search(line) for line in lines)
    return structural and integration and thermal_process


def _case_id(case_path: Path) -> str | None:
    try:
        for line in (case_path / "00_problem_intake.yml").read_text(encoding="utf-8").splitlines():
            if line.startswith("case_id:"):
                value = line.partition(":")[2].strip()
                return value or None
    except OSError:
        return None
    return None


def _fixture_boundary_declared(lines: list[str]) -> bool:
    """Require boundary semantics, not a fixture identifier or operating parameter."""
    for line in lines:
        if _has_unresolved_marker(line):
            continue
        if not any(term in line for term in FIXTURE_TERMS) or not any(term in line for term in FIXTURE_BOUNDARY_TERMS):
            continue
        if any(term in line for term in POSITIVE_TERMS) or "contact conductance" in line:
            return True
    return False


def _evidence_state(case_path: Path) -> EvidenceState:
    """Classify sidecars by traceable parent evidence without promoting draft data."""
    case_id = _case_id(case_path)
    evidence_by_id: dict[str, dict[str, object]] = {}
    limitations: list[str] = []
    for path in iter_sidecar_json(case_path, "evidence"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            limitations.append(f"{path.name} is not usable structured evidence.")
            continue
        evidence_id = data.get("evidence_id")
        status = data.get("status")
        if not isinstance(evidence_id, str) or not isinstance(status, str):
            limitations.append(f"{path.name} lacks usable evidence identity or status.")
            continue
        evidence_by_id[evidence_id] = data

    source_quantities: set[str] = set()
    reviewed_quantities: set[str] = set()
    for path in iter_sidecar_json(case_path, "measurements"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            limitations.append(f"{path.name} is not usable structured measurement context.")
            continue
        measurement_id = data.get("measurement_id")
        evidence_id = data.get("evidence_id")
        status = data.get("status")
        quantity = data.get("quantity")
        value = data.get("value")
        if not isinstance(measurement_id, str) or not isinstance(evidence_id, str) or not isinstance(status, str) or not isinstance(quantity, str):
            limitations.append(f"{path.name} lacks usable measurement identity, parent, status, or quantity.")
            continue
        parent = evidence_by_id.get(evidence_id)
        if parent is None:
            limitations.append(f"{path.name} references missing parent Evidence Object {evidence_id}.")
            continue
        if status not in {"completed", "reviewed"} or not isinstance(value, (int, float)) or isinstance(value, bool):
            limitations.append(f"{path.name} is not a completed or reviewed numeric measurement context.")
            continue
        parent_status = parent.get("status")
        parent_case_id = parent.get("case_id")
        measurement_case_id = data.get("case_id")
        if parent_status in {"rejected", "deprecated"}:
            limitations.append(f"{path.name} has a rejected or deprecated parent Evidence Object {evidence_id}.")
            continue
        if parent_status not in {"draft", "reviewed"}:
            limitations.append(f"{path.name} has a parent Evidence Object {evidence_id} with an unusable status.")
            continue
        if case_id is None or parent_case_id != case_id or measurement_case_id != case_id:
            limitations.append(f"{path.name} or parent {evidence_id} does not match the triaged case ID.")
            continue
        source_quantities.add(quantity.lower())
        parent_measurements = parent.get("measurement_reference_ids")
        reciprocal_linked = isinstance(parent_measurements, list) and measurement_id in parent_measurements
        if not reciprocal_linked:
            limitations.append(f"{path.name} is not reciprocally linked from parent Evidence Object {evidence_id}.")
        if (
            status == "reviewed"
            and parent_status == "reviewed"
            and isinstance(data.get("reviewed_by"), str)
            and data["reviewed_by"].strip()
            and isinstance(parent.get("reviewed_by"), str)
            and parent["reviewed_by"].strip()
            and reciprocal_linked
        ):
            reviewed_quantities.add(quantity.lower())
        else:
            limitations.append(f"{path.name} is source-documented context pending linked human evidence review.")
    return EvidenceState(frozenset(source_quantities), frozenset(reviewed_quantities), tuple(dict.fromkeys(limitations)))


def _quantity_state(evidence: EvidenceState, terms: tuple[str, ...]) -> str:
    if any(any(term in quantity for term in terms) for quantity in evidence.reviewed_quantities):
        return "reviewed"
    if any(any(term in quantity for term in terms) for quantity in evidence.source_quantities):
        return "source_pending_review"
    return "missing"


def _rule(
    rule_id: str,
    title: str,
    finding: str,
    triggering_inputs: list[str],
    missing_evidence: list[str],
    rationale: str,
    action: str,
) -> TriggeredRule:
    return TriggeredRule(
        rule_id=rule_id,
        severity="WARN",
        finding=finding,
        evidence="; ".join(triggering_inputs),
        action_enabled=action,
        title=title,
        triggering_inputs=triggering_inputs,
        missing_evidence=missing_evidence,
        engineering_rationale=rationale,
        evidence_boundary="Qualitative screening guardrail only; it does not calculate stress, bow, warpage, or likelihood of failure.",
    )


def _process_history_complete(lines: list[str]) -> bool:
    temperature = _resolved_declaration(lines, ("growth temperature", "deposition temperature", "process temperature"), factual=True)
    dwell = _resolved_declaration(lines, ("dwell", "exposure", "hour", "hours"), factual=True)
    cooling = _resolved_declaration(lines, ("cooling", "cool-down", "cool down"), factual=True)
    return temperature and dwell and cooling


def _lateral_dimensions(lines: list[str]) -> set[str]:
    values: set[str] = set()
    for line in lines:
        if any(term in line for term in LATERAL_TERMS):
            values.update(DIMENSION_RE.findall(line))
    return values


def _lateral_comparison_declared(lines: list[str]) -> bool:
    comparison_terms = ("compared", "evaluated", "geometry-dependent evidence", "validated over")
    return any(
        any(term in line for term in LATERAL_TERMS)
        and any(marker in line for marker in comparison_terms)
        and not _has_unresolved_marker(line)
        for line in lines
    )


def screen_thermomechanical(case_path: Path, text: str) -> tuple[dict[str, object], list[TriggeredRule]]:
    """Return deterministic qualitative guardrails for credible high-temperature membrane integration context."""
    lines = _lines(text)
    if not _applicable(lines):
        return {
            "status": "not_applicable",
            "known_inputs": [],
            "missing_evidence": [],
            "evidence_limitations": [],
        }, []

    evidence = _evidence_state(case_path)
    known = ["membrane or thin structural context", "deposited, bonded, coated, or directly grown layer integration", "thermally significant process context"]
    rules: list[TriggeredRule] = []
    missing: list[str] = []

    property_terms = ("cte", "thermal expansion", "temperature-dependent material", "material-property")
    property_declared = _resolved_declaration(lines, property_terms) and not _listed_as_missing(lines, property_terms)
    if property_declared:
        known.append("material-property basis is declared in case text; it is not independently reviewed evidence")
    else:
        gap = "temperature-dependent material-property and reference-temperature basis"
        missing.append(gap)
        rules.append(_rule(
            "TRIAGE-THERMOMECH-001",
            "Material-property basis is incomplete",
            "Thermomechanical material-property evidence is incomplete for elevated-temperature layer integration.",
            ["credible membrane integration context"],
            [gap],
            "Thermal expansion context alone does not establish residual stress; a stated basis remains distinct from reviewed evidence.",
            "Obtain temperature-dependent material-property and stress-free-reference assumptions suitable for qualitative thermomechanical review.",
        ))

    process_complete = _process_history_complete(lines)
    if process_complete:
        known.append("growth or deposition temperature, exposure, and cooling route are stated in case text")
    else:
        gap = "growth or deposition temperature, dwell or exposure, and cooling-route evidence"
        missing.append(gap)
        rules.append(_rule(
            "TRIAGE-THERMOMECH-002",
            "Process thermal history is incomplete",
            "The deposited-layer route lacks a resolved process thermal history for thermomechanical screening.",
            ["thermally significant integration process"],
            [gap],
            "A topic mention or an unresolved temperature statement does not define the heating, exposure, cooling, or reference context.",
            "Define the public-safe growth or deposition temperature, dwell or exposure, cooling route, and relevant reference condition before advancing the route.",
        ))

    stress_state = _quantity_state(evidence, ("stress",))
    bow_state = _quantity_state(evidence, ("bow", "warpage", "curvature"))
    stress_acceptance_declared = _resolved_declaration(lines, ("stress acceptance", "allowable stress", "residual stress criteria", "residual stress limit"))
    bow_acceptance_declared = _resolved_declaration(lines, ("bow acceptance", "warpage acceptance", "curvature acceptance", "allowable bow", "allowable warpage", "allowable curvature"))
    comparison_declared = _resolved_declaration(lines, ("initial", "post-process", "post growth", "post-growth")) and any(
        "compar" in line or "evaluat" in line for line in lines if "initial" in line or "post" in line
    )
    if stress_state == "reviewed":
        known.append("reviewed structured residual-stress evidence is linked to reviewed Evidence Object")
    elif stress_state == "source_pending_review":
        known.append("source-documented residual-stress context is present pending human evidence review")
    if bow_state == "reviewed":
        known.append("reviewed structured bow or warpage evidence is linked to reviewed Evidence Object")
    elif bow_state == "source_pending_review":
        known.append("source-documented bow or warpage context is present pending human evidence review")
    required: list[str] = []
    if stress_state != "reviewed":
        required.append("reviewed residual-stress evidence relevant to the route")
    if bow_state != "reviewed":
        required.append("reviewed bow or warpage evidence relevant to the route")
    if not stress_acceptance_declared or _listed_as_missing(lines, ("stress acceptance", "allowable stress", "residual stress criteria", "residual stress limit")):
        required.append("case-specific residual-stress acceptance criteria")
    if not bow_acceptance_declared or _listed_as_missing(lines, ("bow acceptance", "warpage acceptance", "curvature acceptance", "allowable bow", "allowable warpage", "allowable curvature")):
        required.append("case-specific bow/warpage/curvature acceptance criteria")
    if not comparison_declared or _listed_as_missing(lines, ("initial", "curvature", "bow", "profilometry")):
        required.append("initial-state versus post-process comparison basis")
    if required:
        missing.extend(required)
        rules.append(_rule(
            "TRIAGE-THERMOMECH-003",
            "Stress and warpage evidence remains incomplete",
            "Residual-stress or bow/warpage context is not sufficient to advance the membrane integration route.",
            ["elevated-temperature membrane integration", f"stress evidence state: {stress_state}", f"bow evidence state: {bow_state}"],
            required,
            "Source-documented values and prose declarations do not replace reviewed evidence, applicable acceptance criteria, or initial/post-process comparison.",
            "Obtain reviewed stress and profilometry evidence where applicable, define acceptance criteria, and compare initial with post-process state before advancing the route.",
        ))

    adhesion_terms = ("adhesion", "delamination", "fracture energy", "bond strength", "interface strength")
    if not _resolved_declaration(lines, adhesion_terms) or _listed_as_missing(lines, adhesion_terms):
        gap = "interface adhesion, fracture, or delamination evidence"
        missing.append(gap)
        rules.append(_rule(
            "TRIAGE-THERMOMECH-004",
            "Interface mechanical evidence is incomplete",
            "The integrated layer interface lacks a stated adhesion or mechanical-integrity basis for thermomechanical screening.",
            ["deposited-layer integration on a membrane or thin structural layer"],
            [gap],
            "Missing interface evidence does not predict delamination or cracking; it identifies a validation condition before stronger route conclusions.",
            "Define a public-safe adhesion or mechanical-integrity validation basis and the evidence needed to reconsider the route.",
        ))

    fixture_defined = _fixture_boundary_declared(lines)
    if not fixture_defined or _listed_as_missing(lines, FIXTURE_TERMS + ("thermal contact", "boundary")):
        gap = "process-fixture, carrier, or reactor thermal-boundary definition"
        missing.append(gap)
        rules.append(_rule(
            "TRIAGE-THERMOMECH-005",
            "Process thermal boundary is incomplete",
            "The applicable process lacks a resolved fixture, carrier, or reactor thermal-boundary basis.",
            ["thermally significant membrane integration process"],
            [gap],
            "A process fixture is distinct from a conventional package-to-heat-sink boundary and can affect the process thermal history.",
            "Define the public-safe fixture, carrier, reactor, contact, and ambient boundary assumptions before treating package screening as sufficient.",
        ))

    dimensions = _lateral_dimensions(lines)
    if len(dimensions) >= 2 and not _lateral_comparison_declared(lines):
        gap = "geometry scale-up and thickness-interaction comparison evidence"
        missing.append(gap)
        rules.append(_rule(
            "TRIAGE-THERMOMECH-006",
            "Geometry scale-up evidence is incomplete",
            "Multiple lateral membrane dimensions are present without an explicit geometry-dependent comparison basis.",
            ["multiple membrane diameters or lateral dimensions", "deposited-layer integration"],
            [gap],
            "Lateral size and deposited-film/substrate thickness interaction can change thermomechanical behavior; this rule does not infer a direction or magnitude.",
            "Compare geometry, layer thickness, initial curvature, and process-boundary evidence across the intended lateral size range before extrapolating the route.",
        ))

    downstream_relevant = any(any(term in line for term in DOWNSTREAM_TERMS) for line in lines)
    downstream_defined = _resolved_declaration(lines, DOWNSTREAM_TERMS + ("flatness", "compatibility", "acceptance"))
    if downstream_relevant and (not downstream_defined or _listed_as_missing(lines, DOWNSTREAM_TERMS + ("flatness", "compatibility", "acceptance", "allowable"))):
        gap = "downstream handling, lithography, packaging, or flatness compatibility criteria"
        missing.append(gap)
        rules.append(_rule(
            "TRIAGE-THERMOMECH-007",
            "Downstream compatibility criteria are incomplete",
            "Downstream handling or fabrication compatibility is relevant but the acceptance basis is unresolved.",
            ["explicit downstream lithography, handling, packaging, or fabrication context"],
            [gap],
            "A route can remain a screening candidate while downstream compatibility evidence is collected; the absence of criteria is not a failure prediction.",
            "Define downstream flatness, handling, packaging, or fabrication compatibility criteria before strengthening the route decision.",
        ))

    limitations = list(evidence.limitations)
    if evidence.source_quantities and not evidence.reviewed_quantities:
        limitations.append("Source-documented measurement context remains pending linked human evidence review.")
    if rules:
        status = "needs_evidence"
    elif evidence.reviewed_quantities:
        status = "reviewed_evidence_referenced"
    elif evidence.source_quantities:
        status = "source_context_pending_review"
    else:
        status = "stated_context_no_explicit_gap"
    return {
        "status": status,
        "known_inputs": list(dict.fromkeys(known)),
        "missing_evidence": list(dict.fromkeys(missing)),
        "evidence_limitations": list(dict.fromkeys(limitations)),
    }, rules
