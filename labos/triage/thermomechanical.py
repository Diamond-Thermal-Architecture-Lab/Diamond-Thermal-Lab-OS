from __future__ import annotations

import json
import re
from pathlib import Path

from labos.evidence.loader import iter_sidecar_json

from .models import TriggeredRule
from .rules import MISSING_RE


MEMBRANE_TERMS = ("membrane", "thin film", "thin-film", "thin layer", "thin-layer")
PROCESS_TERMS = ("cvd", "deposition", "deposited", "growth", "grown", "anneal", "process temperature", "high-temperature")
INTEGRATION_TERMS = ("coating", "deposited", "deposition", "diamond", "film", "grown layer", "growth")
FIXTURE_TERMS = ("fixture", "sample holder", "carrier", "reactor", "plasma", "frame-to-fixture")
COMPATIBILITY_TERMS = ("lithography", "handling", "packaging", "metallization", "downstream")
DIMENSION_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:mm|millimeter(?:s)?)\b", re.IGNORECASE)


def _contains(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _unresolved_near(text: str, terms: tuple[str, ...]) -> bool:
    for line in text.splitlines():
        lowered = line.lower()
        if any(term in lowered for term in terms) and MISSING_RE.search(lowered):
            return True
    return False


def _listed_as_missing(text: str, terms: tuple[str, ...]) -> bool:
    """Recognize canonical intake `missing_data` entries that omit words such as TODO."""
    in_missing_data = False
    for line in text.splitlines():
        stripped = line.strip().lower()
        if stripped == "missing_data:":
            in_missing_data = True
            continue
        if in_missing_data and line and not line[0].isspace() and not stripped.startswith("-"):
            in_missing_data = False
        if in_missing_data and any(term in stripped for term in terms):
            return True
    return False


def _evidence_state(case_path: Path) -> tuple[set[str], bool, list[str]]:
    """Read optional public sidecars defensively; malformed files remain a limitation."""
    quantities: set[str] = set()
    reviewed_evidence = False
    limitations: list[str] = []
    for path in iter_sidecar_json(case_path, "evidence"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            limitations.append(f"{path.name} is not usable structured evidence.")
            continue
        if data.get("status") == "reviewed":
            reviewed_evidence = True
        else:
            limitations.append(f"{path.name} is source context pending human evidence review.")
    for path in iter_sidecar_json(case_path, "measurements"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            limitations.append(f"{path.name} is not usable structured measurement context.")
            continue
        quantity = data.get("quantity")
        if isinstance(quantity, str) and data.get("value") is not None:
            quantities.add(quantity.lower())
    return quantities, reviewed_evidence, limitations


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


def screen_thermomechanical(case_path: Path, text: str) -> tuple[dict[str, object], list[TriggeredRule]]:
    """Return deterministic qualitative guardrails for elevated-temperature membrane integration."""
    membrane = _contains(text, MEMBRANE_TERMS)
    process = _contains(text, PROCESS_TERMS)
    integration = _contains(text, INTEGRATION_TERMS)
    if not (membrane and process and integration):
        return {
            "status": "not_applicable",
            "known_inputs": [],
            "missing_evidence": [],
            "evidence_limitations": [],
        }, []

    quantities, reviewed_evidence, limitations = _evidence_state(case_path)
    known: list[str] = ["membrane or thin-layer context", "elevated-temperature material integration"]
    if _contains(text, ("temperature", "thermal history", "heating", "cooling")):
        known.append("process thermal history is described")
    if _contains(text, ("thermal expansion", "coefficient of thermal expansion", "cte")):
        known.append("thermal expansion difference is identified")
    if _contains(text, FIXTURE_TERMS):
        known.append("process fixture or reactor boundary context is identified")
    if quantities:
        known.append("optional source-documented measurement sidecars are present")

    rules: list[TriggeredRule] = []
    missing: list[str] = []
    property_terms = ("temperature-dependent", "thermal expansion coefficient", "coefficient of thermal expansion", "cte data")
    if not _contains(text, property_terms):
        gap = "temperature-dependent material-property basis for the integrated layer pair"
        missing.append(gap)
        rules.append(_rule(
            "TRIAGE-THERMOMECH-001",
            "Material-property basis is incomplete",
            "Thermomechanical material-property evidence is incomplete for elevated-temperature layer integration.",
            ["membrane or thin-layer context", "elevated-temperature deposited-layer integration"],
            [gap],
            "Thermal expansion differences alone do not establish residual stress, but they require a documented property and reference-temperature basis before route advancement.",
            "Obtain temperature-dependent material-property and stress-free-reference assumptions suitable for a qualitative thermomechanical review.",
        ))
    if not _contains(text, ("process temperature", "thermal history", "heating from", "cooling to", "growth temperature", "deposition temperature")):
        gap = "process thermal history or temperature range"
        missing.append(gap)
        rules.append(_rule(
            "TRIAGE-THERMOMECH-002",
            "Process thermal history is incomplete",
            "The deposited-layer route lacks a defined process thermal history for thermomechanical screening.",
            ["membrane or thin-layer context", "material integration process is referenced"],
            [gap],
            "A thermal route cannot be screened for thermomechanical evidence needs without knowing the relevant heating and cooling context.",
            "Define the public-safe process temperature range, dwell or exposure context, and cooling reference before advancing the route.",
        ))

    stress_terms = ("residual stress", "biaxial stress", "stress mapping", "raman")
    bow_terms = ("bow", "warpage", "curvature", "profilometry")
    has_stress_measurement = any("stress" in quantity for quantity in quantities)
    has_bow_measurement = any("bow" in quantity or "warpage" in quantity or "curvature" in quantity for quantity in quantities)
    stress_unresolved = _unresolved_near(text, stress_terms) or _listed_as_missing(text, stress_terms)
    bow_unresolved = _unresolved_near(text, bow_terms) or _listed_as_missing(text, bow_terms)
    has_stress_basis = has_stress_measurement or (_contains(text, stress_terms) and not stress_unresolved)
    has_bow_basis = has_bow_measurement or (_contains(text, bow_terms) and not bow_unresolved)
    stress_gap = "case-specific residual-stress acceptance and evidence basis"
    bow_gap = "pre/post-process bow or warpage acceptance and comparison basis"
    if stress_unresolved or not has_stress_basis:
        missing.append(stress_gap)
    if bow_unresolved or not has_bow_basis:
        missing.append(bow_gap)
    if stress_unresolved or bow_unresolved or not has_stress_basis or not has_bow_basis:
        evidence = ["elevated-temperature membrane integration"]
        if has_stress_measurement or has_bow_measurement:
            evidence.append("source-documented measurement sidecars")
        required = []
        if stress_unresolved or not has_stress_basis:
            required.append(stress_gap)
        if bow_unresolved or not has_bow_basis:
            required.append(bow_gap)
        rules.append(_rule(
            "TRIAGE-THERMOMECH-003",
            "Stress and warpage evidence remains incomplete",
            "Residual-stress or bow/warpage evidence is not sufficient to advance the membrane integration route.",
            evidence,
            required,
            "Reported or source-documented values do not replace case-specific acceptance criteria, initial-state comparison, or human evidence review.",
            "Obtain initial and post-process profilometry, a stress evidence basis such as Raman mapping where applicable, and explicit acceptance criteria before advancing the route.",
        ))

    adhesion_terms = ("adhesion", "delamination", "fracture energy", "bond strength", "interface strength")
    if _unresolved_near(text, adhesion_terms) or _listed_as_missing(text, adhesion_terms) or not _contains(text, adhesion_terms):
        gap = "interface adhesion, fracture, or delamination evidence"
        missing.append(gap)
        rules.append(_rule(
            "TRIAGE-THERMOMECH-004",
            "Interface mechanical evidence is incomplete",
            "The integrated layer interface lacks sufficient adhesion or mechanical-integrity evidence for thermomechanical screening.",
            ["deposited-layer integration on a membrane or thin-layer structure"],
            [gap],
            "Missing interface evidence does not predict delamination or cracking; it identifies a validation condition before stronger route conclusions.",
            "Define a public-safe adhesion or mechanical-integrity validation basis and the evidence needed to reconsider the route.",
        ))

    if _contains(text, FIXTURE_TERMS) and (
        _unresolved_near(text, FIXTURE_TERMS + ("thermal contact conductance", "boundary"))
        or _listed_as_missing(text, FIXTURE_TERMS + ("thermal contact conductance", "boundary"))
    ):
        gap = "process-fixture, carrier, or reactor thermal-boundary definition"
        missing.append(gap)
        rules.append(_rule(
            "TRIAGE-THERMOMECH-005",
            "Process thermal boundary is incomplete",
            "A process-fixture or reactor boundary is present but its relevant thermal contact or boundary evidence is unresolved.",
            ["fixture, carrier, frame, plasma, or reactor context"],
            [gap],
            "A process fixture is distinct from a conventional package-to-heat-sink boundary and can affect the thermal history used for screening.",
            "Define the public-safe fixture, carrier, reactor, contact, and ambient boundary assumptions before treating package screening as sufficient.",
        ))

    dimensions = set(DIMENSION_RE.findall(text))
    if len(dimensions) >= 2 or "scale-up" in text or "scaling" in text:
        scale_gap = "geometry scale-up and thickness-interaction evidence"
        scale_unresolved = (
            _unresolved_near(text, ("diameter", "size", "scale", "thickness", "process window"))
            or _listed_as_missing(text, ("diameter", "size", "scale", "thickness", "process window"))
            or "scale-up" not in text
        )
        if scale_unresolved:
            missing.append(scale_gap)
            rules.append(_rule(
                "TRIAGE-THERMOMECH-006",
                "Geometry scale-up evidence is incomplete",
                "Multiple membrane dimensions or a scale-up context are present without a bounded thermomechanical comparison basis.",
                ["multiple lateral dimensions or explicit scale-up context", "deposited-layer integration"],
                [scale_gap],
                "Lateral size and deposited-film/substrate thickness interaction can change thermomechanical behavior; this rule does not infer a direction or magnitude.",
                "Compare geometry, layer-thickness, initial-curvature, and process-boundary evidence across the intended size range before extrapolating the route.",
            ))

    if _contains(text, COMPATIBILITY_TERMS) and (
        _unresolved_near(text, COMPATIBILITY_TERMS + ("flatness", "acceptance", "allowable"))
        or _listed_as_missing(text, COMPATIBILITY_TERMS + ("flatness", "acceptance", "allowable"))
    ):
        gap = "downstream handling, lithography, packaging, or flatness compatibility criteria"
        missing.append(gap)
        rules.append(_rule(
            "TRIAGE-THERMOMECH-007",
            "Downstream compatibility criteria are incomplete",
            "Downstream handling or fabrication compatibility is relevant but the acceptance basis is unresolved.",
            ["downstream lithography, handling, packaging, or fabrication context"],
            [gap],
            "A route can remain a screening candidate while downstream compatibility evidence is collected; the absence of criteria is not a failure prediction.",
            "Define the downstream flatness, handling, packaging, or fabrication compatibility criteria before strengthening the route decision.",
        ))

    limitations = list(dict.fromkeys(limitations))
    if quantities and not reviewed_evidence:
        limitations.append("Source-documented measurement context remains pending human evidence review.")
    screening_status = "needs_evidence" if rules else "evidence_referenced"
    return {
        "status": screening_status,
        "known_inputs": known,
        "missing_evidence": list(dict.fromkeys(missing)),
        "evidence_limitations": limitations,
    }, rules
