"""Strict decimal quantities and the closed M16A-I1 unit registry."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import (
    Clamped,
    Context,
    Decimal,
    DivisionByZero,
    FloatOperation,
    Inexact,
    InvalidOperation,
    Overflow,
    Rounded,
    Underflow,
    localcontext,
)
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


UNIT_REGISTRY_VERSION = "m16a-unit-registry-1.0"

_MAX_LEXICAL_CHARACTERS = 128
_MAX_COEFFICIENT_DIGITS = 64
_MIN_ADJUSTED_EXPONENT = -128
_MAX_ADJUSTED_EXPONENT = 128
_DECIMAL_PATTERN = re.compile(
    r"^-?(?P<integer>0|[1-9][0-9]*)(?:\.(?P<fraction>[0-9]+))?"
    r"(?:[eE](?P<exponent>[+-]?[0-9]+))?$"
)

# A 64-digit coefficient at adjusted exponent -128 can have exponent -191.
# Adding the exact Celsius offset then needs about 194 significant places.
_DECIMAL_CONTEXT = Context(prec=384, Emin=-999, Emax=999, clamp=0)
for _signal in (
    Clamped,
    DivisionByZero,
    FloatOperation,
    Inexact,
    InvalidOperation,
    Overflow,
    Rounded,
    Underflow,
):
    _DECIMAL_CONTEXT.traps[_signal] = True


class QuantityValidationError(ValueError):
    """Base error for invalid M16A quantity data."""


class DecimalParseError(QuantityValidationError):
    """Raised when an external physical value violates the decimal contract."""


class UnknownUnitError(QuantityValidationError):
    """Raised when a token is absent from the closed registry for its kind."""


class QuantityKindMismatchError(QuantityValidationError):
    """Raised when comparison is requested across different quantity kinds."""


class QuantityKind(str, Enum):
    POWER = "power"
    HEAT_FLUX = "heat_flux"
    LENGTH = "length"
    AREA = "area"
    THERMAL_CONDUCTIVITY = "thermal_conductivity"
    AREA_THERMAL_RESISTANCE = "area_thermal_resistance"
    ABSOLUTE_THERMAL_RESISTANCE = "absolute_thermal_resistance"
    AREA_THERMAL_CONDUCTANCE = "area_thermal_conductance"
    ABSOLUTE_TEMPERATURE = "absolute_temperature"
    TEMPERATURE_DIFFERENCE = "temperature_difference"
    PHYSICAL_DIMENSIONLESS = "physical_dimensionless"


def parse_decimal(value: str) -> Decimal:
    """Parse one external physical numeric token without coercion or cleanup."""
    if type(value) is not str:
        raise DecimalParseError("External physical numeric input must be a string.")
    if len(value) > _MAX_LEXICAL_CHARACTERS:
        raise DecimalParseError("Decimal input exceeds the 128-character safety limit.")
    match = _DECIMAL_PATTERN.fullmatch(value)
    if match is None:
        raise DecimalParseError("Decimal input does not match the approved base-10 grammar.")
    coefficient_digits = len(match.group("integer")) + len(match.group("fraction") or "")
    if coefficient_digits > _MAX_COEFFICIENT_DIGITS:
        raise DecimalParseError("Decimal coefficient exceeds the 64-digit safety limit.")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise DecimalParseError("Decimal input is invalid.") from exc
    if not parsed.is_finite():
        raise DecimalParseError("Decimal input must be finite.")
    if not parsed.is_zero() and not (
        _MIN_ADJUSTED_EXPONENT <= parsed.adjusted() <= _MAX_ADJUSTED_EXPONENT
    ):
        raise DecimalParseError("Decimal adjusted exponent is outside -128 through +128.")
    return parsed


def canonical_decimal_text(value: Decimal) -> str:
    """Return exact, plain base-10 text for one finite Decimal."""
    if type(value) is not Decimal:
        raise DecimalParseError("Canonical decimal input must be a Decimal.")
    if not value.is_finite():
        raise DecimalParseError("Canonical decimal input must be finite.")
    if value.is_zero():
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text.startswith("."):
        text = "0" + text
    elif text.startswith("-."):
        text = "-0" + text[1:]
    return text


def _canonical_decimal(value: Decimal) -> Decimal:
    return Decimal(canonical_decimal_text(value))


@dataclass(frozen=True)
class UnitDefinition:
    token: str
    quantity_kind: QuantityKind
    canonical_unit: str
    scale: Decimal
    offset: Decimal
    rule_id: str

    def __post_init__(self) -> None:
        if type(self.token) is not str or not self.token:
            raise QuantityValidationError("Unit token must be a non-empty string.")
        if type(self.quantity_kind) is not QuantityKind:
            raise QuantityValidationError("Unit quantity kind must be a QuantityKind.")
        if type(self.canonical_unit) is not str or not self.canonical_unit:
            raise QuantityValidationError("Canonical unit must be a non-empty string.")
        if type(self.scale) is not Decimal or not self.scale.is_finite() or self.scale.is_zero():
            raise QuantityValidationError("Unit scale must be a finite non-zero Decimal.")
        if type(self.offset) is not Decimal or not self.offset.is_finite():
            raise QuantityValidationError("Unit offset must be a finite Decimal.")
        if type(self.rule_id) is not str or not self.rule_id:
            raise QuantityValidationError("Conversion rule ID must be a non-empty string.")


@dataclass(frozen=True)
class ConversionRecord:
    original_value: str
    original_unit: str
    canonical_value: Decimal
    canonical_unit: str
    conversion_rule_id: str
    unit_registry_version: str

    def to_dict(self) -> dict[str, str]:
        return {
            "original_value": self.original_value,
            "original_unit": self.original_unit,
            "canonical_value": canonical_decimal_text(self.canonical_value),
            "canonical_unit": self.canonical_unit,
            "conversion_rule_id": self.conversion_rule_id,
            "unit_registry_version": self.unit_registry_version,
        }


def _definition(
    kind: QuantityKind,
    token: str,
    canonical_unit: str,
    scale: str,
    offset: str,
    rule_id: str,
) -> UnitDefinition:
    return UnitDefinition(
        token=token,
        quantity_kind=kind,
        canonical_unit=canonical_unit,
        scale=Decimal(scale),
        offset=Decimal(offset),
        rule_id=rule_id,
    )


_UNIT_DEFINITIONS = (
    _definition(QuantityKind.POWER, "W", "W", "1", "0", "M16A-UNIT-POWER-W"),
    _definition(QuantityKind.POWER, "mW", "W", "1e-3", "0", "M16A-UNIT-POWER-MW"),
    _definition(QuantityKind.HEAT_FLUX, "W/m^2", "W/m^2", "1", "0", "M16A-UNIT-HEAT-FLUX-M2"),
    _definition(QuantityKind.HEAT_FLUX, "W/mm^2", "W/m^2", "1e6", "0", "M16A-UNIT-HEAT-FLUX-MM2"),
    _definition(QuantityKind.LENGTH, "m", "m", "1", "0", "M16A-UNIT-LENGTH-M"),
    _definition(QuantityKind.LENGTH, "mm", "m", "1e-3", "0", "M16A-UNIT-LENGTH-MM"),
    _definition(QuantityKind.LENGTH, "um", "m", "1e-6", "0", "M16A-UNIT-LENGTH-UM-ASCII"),
    _definition(QuantityKind.LENGTH, "µm", "m", "1e-6", "0", "M16A-UNIT-LENGTH-UM-MICRO-SIGN"),
    _definition(QuantityKind.AREA, "m^2", "m^2", "1", "0", "M16A-UNIT-AREA-M2"),
    _definition(QuantityKind.AREA, "mm^2", "m^2", "1e-6", "0", "M16A-UNIT-AREA-MM2"),
    _definition(QuantityKind.THERMAL_CONDUCTIVITY, "W/(m*K)", "W/(m*K)", "1", "0", "M16A-UNIT-CONDUCTIVITY"),
    _definition(QuantityKind.AREA_THERMAL_RESISTANCE, "m^2*K/W", "m^2*K/W", "1", "0", "M16A-UNIT-AREA-RESISTANCE-M2"),
    _definition(QuantityKind.AREA_THERMAL_RESISTANCE, "mm^2*K/W", "m^2*K/W", "1e-6", "0", "M16A-UNIT-AREA-RESISTANCE-MM2"),
    _definition(QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "K/W", "K/W", "1", "0", "M16A-UNIT-ABSOLUTE-RESISTANCE"),
    _definition(QuantityKind.AREA_THERMAL_CONDUCTANCE, "W/(m^2*K)", "W/(m^2*K)", "1", "0", "M16A-UNIT-AREA-CONDUCTANCE"),
    _definition(QuantityKind.ABSOLUTE_TEMPERATURE, "K", "K", "1", "0", "M16A-UNIT-ABSOLUTE-TEMP-K"),
    _definition(QuantityKind.ABSOLUTE_TEMPERATURE, "degC", "K", "1", "273.15", "M16A-UNIT-ABSOLUTE-TEMP-DEGC"),
    _definition(QuantityKind.ABSOLUTE_TEMPERATURE, "°C", "K", "1", "273.15", "M16A-UNIT-ABSOLUTE-TEMP-DEGREE-C"),
    _definition(QuantityKind.TEMPERATURE_DIFFERENCE, "K", "K", "1", "0", "M16A-UNIT-DELTA-TEMP-K"),
    _definition(QuantityKind.TEMPERATURE_DIFFERENCE, "degC", "K", "1", "0", "M16A-UNIT-DELTA-TEMP-DEGC"),
    _definition(QuantityKind.TEMPERATURE_DIFFERENCE, "°C", "K", "1", "0", "M16A-UNIT-DELTA-TEMP-DEGREE-C"),
    _definition(QuantityKind.PHYSICAL_DIMENSIONLESS, "1", "1", "1", "0", "M16A-UNIT-DIMENSIONLESS"),
)

UNIT_REGISTRY: Mapping[tuple[QuantityKind, str], UnitDefinition] = MappingProxyType(
    {(item.quantity_kind, item.token): item for item in _UNIT_DEFINITIONS}
)
_CANONICAL_UNITS: Mapping[QuantityKind, str] = MappingProxyType(
    {item.quantity_kind: item.canonical_unit for item in _UNIT_DEFINITIONS}
)


def _coerce_kind(kind: QuantityKind | str) -> QuantityKind:
    if type(kind) is QuantityKind:
        return kind
    if type(kind) is str:
        try:
            return QuantityKind(kind)
        except ValueError as exc:
            raise QuantityValidationError(f"Unknown quantity kind: {kind!r}.") from exc
    raise QuantityValidationError("Quantity kind must be a QuantityKind or its exact string value.")


def _lookup_unit(kind: QuantityKind, unit: str) -> UnitDefinition:
    if type(unit) is not str:
        raise UnknownUnitError("Unit token must be a string.")
    try:
        return UNIT_REGISTRY[(kind, unit)]
    except KeyError as exc:
        raise UnknownUnitError(
            f"Unit {unit!r} is not registered for quantity kind {kind.value!r}."
        ) from exc


def _converted_decimal(value: Decimal, definition: UnitDefinition) -> Decimal:
    try:
        with localcontext(_DECIMAL_CONTEXT) as context:
            scaled = context.multiply(value, definition.scale)
            converted = context.add(scaled, definition.offset)
    except (Clamped, DivisionByZero, FloatOperation, Inexact, InvalidOperation, Overflow, Rounded, Underflow) as exc:
        raise QuantityValidationError("Quantity conversion cannot be represented exactly.") from exc
    return _canonical_decimal(converted)


@dataclass(frozen=True, eq=False)
class QuantifiedValue:
    quantity_kind: QuantityKind
    canonical_value: Decimal
    canonical_unit: str
    conversion: ConversionRecord

    def __post_init__(self) -> None:
        if type(self.quantity_kind) is not QuantityKind:
            raise QuantityValidationError("QuantifiedValue kind must be a QuantityKind.")
        if type(self.canonical_value) is not Decimal or not self.canonical_value.is_finite():
            raise QuantityValidationError("QuantifiedValue canonical value must be a finite Decimal.")
        normalized = _canonical_decimal(self.canonical_value)
        if self.canonical_value.as_tuple() != normalized.as_tuple():
            raise QuantityValidationError("QuantifiedValue value must use canonical Decimal representation.")
        required_unit = _CANONICAL_UNITS[self.quantity_kind]
        if self.canonical_unit != required_unit:
            raise QuantityValidationError(
                f"Canonical unit for {self.quantity_kind.value!r} must be {required_unit!r}."
            )
        if type(self.conversion) is not ConversionRecord:
            raise QuantityValidationError("QuantifiedValue requires a ConversionRecord.")
        record = self.conversion
        if record.unit_registry_version != UNIT_REGISTRY_VERSION:
            raise QuantityValidationError("Conversion record has the wrong unit-registry version.")
        definition = _lookup_unit(self.quantity_kind, record.original_unit)
        original = parse_decimal(record.original_value)
        expected = _converted_decimal(original, definition)
        if record.conversion_rule_id != definition.rule_id:
            raise QuantityValidationError("Conversion record has the wrong conversion rule ID.")
        if record.canonical_unit != required_unit:
            raise QuantityValidationError("Conversion record has the wrong canonical unit.")
        if type(record.canonical_value) is not Decimal or record.canonical_value.as_tuple() != expected.as_tuple():
            raise QuantityValidationError("Conversion record has the wrong canonical value.")
        if self.canonical_value.as_tuple() != expected.as_tuple():
            raise QuantityValidationError("QuantifiedValue does not match its conversion record.")

    @property
    def numeric_identity(self) -> tuple[QuantityKind, Decimal]:
        return (self.quantity_kind, self.canonical_value)

    @property
    def lexical_identity(self) -> tuple[str, str]:
        return (self.conversion.original_value, self.conversion.original_unit)

    def same_numeric_identity(self, other: object) -> bool:
        return isinstance(other, QuantifiedValue) and self.numeric_identity == other.numeric_identity

    def same_lexical_identity(self, other: object) -> bool:
        return isinstance(other, QuantifiedValue) and self.lexical_identity == other.lexical_identity

    def same_audit_identity(self, other: object) -> bool:
        return isinstance(other, QuantifiedValue) and self.to_dict() == other.to_dict()

    def compare_numeric(self, other: QuantifiedValue) -> int:
        if not isinstance(other, QuantifiedValue):
            raise TypeError("Numeric comparison requires another QuantifiedValue.")
        if self.quantity_kind is not other.quantity_kind:
            raise QuantityKindMismatchError(
                f"Cannot compare {self.quantity_kind.value!r} with {other.quantity_kind.value!r}."
            )
        return (self.canonical_value > other.canonical_value) - (
            self.canonical_value < other.canonical_value
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "quantity_kind": self.quantity_kind.value,
            "canonical_value": canonical_decimal_text(self.canonical_value),
            "canonical_unit": self.canonical_unit,
            "conversion": self.conversion.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> QuantifiedValue:
        if not isinstance(value, Mapping):
            raise QuantityValidationError("QuantifiedValue data must be a mapping.")
        expected_keys = {"quantity_kind", "canonical_value", "canonical_unit", "conversion"}
        if set(value) != expected_keys or not isinstance(value.get("conversion"), Mapping):
            raise QuantityValidationError("QuantifiedValue data has an invalid shape.")
        conversion_data = value["conversion"]
        expected_conversion_keys = {
            "original_value",
            "original_unit",
            "canonical_value",
            "canonical_unit",
            "conversion_rule_id",
            "unit_registry_version",
        }
        if set(conversion_data) != expected_conversion_keys:
            raise QuantityValidationError("Conversion record data has an invalid shape.")
        reconstructed = convert_quantity(
            value["quantity_kind"],
            conversion_data["original_value"],
            conversion_data["original_unit"],
        )
        if reconstructed.to_dict() != dict(value):
            raise QuantityValidationError("Serialized quantity is inconsistent with its conversion record.")
        return reconstructed


def convert_quantity(
    quantity_kind: QuantityKind | str,
    value: str,
    unit: str,
) -> QuantifiedValue:
    """Convert an external decimal string and exact unit token to canonical form."""
    kind = _coerce_kind(quantity_kind)
    definition = _lookup_unit(kind, unit)
    original = parse_decimal(value)
    canonical = _converted_decimal(original, definition)
    record = ConversionRecord(
        original_value=value,
        original_unit=unit,
        canonical_value=canonical,
        canonical_unit=definition.canonical_unit,
        conversion_rule_id=definition.rule_id,
        unit_registry_version=UNIT_REGISTRY_VERSION,
    )
    return QuantifiedValue(
        quantity_kind=kind,
        canonical_value=canonical,
        canonical_unit=definition.canonical_unit,
        conversion=record,
    )


def convert_canonical_to_unit(
    quantity_kind: QuantityKind | str,
    canonical_value: Decimal,
    target_unit: str,
) -> QuantifiedValue:
    """Project one canonical Decimal to an exact registered target unit."""
    kind = _coerce_kind(quantity_kind)
    if type(canonical_value) is not Decimal:
        raise QuantityValidationError("Canonical value must be a Decimal.")
    if not canonical_value.is_finite():
        raise QuantityValidationError("Canonical value must be finite.")
    if canonical_value.as_tuple() != _canonical_decimal(canonical_value).as_tuple():
        raise QuantityValidationError("Canonical value must use canonical Decimal representation.")
    definition = _lookup_unit(kind, target_unit)
    try:
        with localcontext(_DECIMAL_CONTEXT) as context:
            shifted = context.subtract(canonical_value, definition.offset)
            target = context.divide(shifted, definition.scale)
    except (
        Clamped,
        DivisionByZero,
        FloatOperation,
        Inexact,
        InvalidOperation,
        Overflow,
        Rounded,
        Underflow,
    ) as exc:
        raise QuantityValidationError("Reverse quantity conversion cannot be represented exactly.") from exc

    target_text = canonical_decimal_text(_canonical_decimal(target))
    projected = convert_quantity(kind, target_text, target_unit)
    if projected.numeric_identity != (kind, canonical_value):
        raise QuantityValidationError("Reverse quantity conversion did not preserve numeric identity.")
    return projected
