from __future__ import annotations

import re


MISSING_RE = re.compile(r"\b(todo|unknown|uncertain|incomplete|missing|tbd|not specified|to be defined)\b", re.IGNORECASE)
CRITICAL_FIELDS = ("heat_source_geometry", "power_or_power_density", "cooling_boundary")
INTERFACE_TERMS = ("interface thermal resistance", "thermal boundary resistance", "contact resistance", "bonding quality", r"\btbr\b")
MEASUREMENT_TERMS = ("thermal map", "junction estimate", "transient", "raman", "ir thermal", "measured temperature", "calibrated measurement")
PACKAGE_TERMS = ("package-to-heat-sink", "package path", "package_path", "mounting", "baseplate", "tim", "heat-sink interface")


def is_missing(value: str) -> bool:
    return not value.strip() or MISSING_RE.search(value) is not None


def has_interface_evidence(text: str) -> bool:
    return any(re.search(term, text, re.IGNORECASE) for term in INTERFACE_TERMS)


def has_bounded_interface_evidence(text: str) -> bool:
    """Return true only when interface context is present and not explicitly unresolved."""
    unresolved = re.compile(
        r"(?:interface thermal resistance|thermal boundary resistance|contact resistance|\btbr\b).{0,100}"
        r"\b(?:todo|unknown|uncertain|unbounded|missing|tbd)\b",
        re.IGNORECASE,
    )
    return has_interface_evidence(text) and unresolved.search(text) is None


def has_package_uncertainty(text: str) -> bool:
    """Keep a package candidate tied to an unresolved package-specific statement."""
    for line in text.splitlines():
        for segment in re.split(r"[;|]", line):
            if any(term in segment.lower() for term in PACKAGE_TERMS) and MISSING_RE.search(segment):
                return True
    return False


def has_measurement_evidence(text: str) -> bool:
    return any(term in text.lower() for term in MEASUREMENT_TERMS)
