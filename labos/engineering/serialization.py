"""Canonical structured bytes and hashes for M16A engineering values."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from .quantities import canonical_decimal_text


CANONICAL_JSON_VERSION = "m16a-canonical-json-1.0"


class CanonicalSerializationError(TypeError):
    """Raised when a value is outside the canonical JSON input domain."""


def _canonical_primitive(value: Any) -> Any:
    if value is None or type(value) is bool or type(value) is str or type(value) is int:
        return value
    if type(value) is Decimal:
        try:
            return canonical_decimal_text(value)
        except ValueError as exc:
            raise CanonicalSerializationError("Decimal values must be finite.") from exc
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise CanonicalSerializationError("Canonical JSON mapping keys must be strings.")
            result[key] = _canonical_primitive(item)
        return result
    if type(value) in (list, tuple):
        return [_canonical_primitive(item) for item in value]
    raise CanonicalSerializationError(
        f"Unsupported canonical JSON value type: {type(value).__name__}."
    )


def canonical_json_bytes(value: Any) -> bytes:
    """Encode one supported value as compact deterministic UTF-8 JSON plus LF."""
    primitive = _canonical_primitive(value)
    try:
        text = json.dumps(
            primitive,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise CanonicalSerializationError("Value cannot be encoded as canonical JSON.") from exc
    return (text + "\n").encode("utf-8")


def canonical_sha256(value: Any) -> str:
    """Return lowercase SHA256 over exactly ``canonical_json_bytes(value)``."""
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()
