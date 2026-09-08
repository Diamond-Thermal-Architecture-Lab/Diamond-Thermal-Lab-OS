"""Deterministic quantitative primitives for the M16A engineering layer."""

from .quantities import (
    UNIT_REGISTRY_VERSION,
    ConversionRecord,
    DecimalParseError,
    QuantityKind,
    QuantityKindMismatchError,
    QuantifiedValue,
    QuantityValidationError,
    UnitDefinition,
    UnknownUnitError,
    canonical_decimal_text,
    convert_quantity,
    parse_decimal,
)
from .serialization import (
    CANONICAL_JSON_VERSION,
    CanonicalSerializationError,
    canonical_json_bytes,
    canonical_sha256,
)

__all__ = [
    "CANONICAL_JSON_VERSION",
    "UNIT_REGISTRY_VERSION",
    "CanonicalSerializationError",
    "ConversionRecord",
    "DecimalParseError",
    "QuantityKind",
    "QuantityKindMismatchError",
    "QuantifiedValue",
    "QuantityValidationError",
    "UnitDefinition",
    "UnknownUnitError",
    "canonical_decimal_text",
    "canonical_json_bytes",
    "canonical_sha256",
    "convert_quantity",
    "parse_decimal",
]
