from __future__ import annotations

import unittest
from decimal import Context, Decimal, getcontext, localcontext

from labos.engineering.quantities import (
    UNIT_REGISTRY,
    UNIT_REGISTRY_VERSION,
    ConversionRecord,
    DecimalParseError,
    QuantityKind,
    QuantityKindMismatchError,
    QuantifiedValue,
    QuantityValidationError,
    UnknownUnitError,
    canonical_decimal_text,
    convert_canonical_to_unit,
    convert_quantity,
    parse_decimal,
)


class M16ADecimalTests(unittest.TestCase):
    def test_dec_01_plain_values_are_exact_and_canonical(self) -> None:
        expected = {"0": "0", "12": "12", "12.0": "12", "0.001": "0.001"}
        for token, canonical in expected.items():
            with self.subTest(token=token):
                value = parse_decimal(token)
                self.assertIs(type(value), Decimal)
                self.assertEqual(canonical_decimal_text(value), canonical)

    def test_dec_02_exponent_forms_expand_to_plain_text(self) -> None:
        expected = {"1e-3": "0.001", "15E-1": "1.5", "1E+6": "1000000"}
        for token, canonical in expected.items():
            with self.subTest(token=token):
                self.assertEqual(canonical_decimal_text(parse_decimal(token)), canonical)

    def test_dec_03_malformed_or_normalized_forms_fail(self) -> None:
        rejected = ("", " 1", "1 ", "+1", "01", ".5", "1.", "1,5", "1_000")
        for token in rejected:
            with self.subTest(token=token), self.assertRaises(DecimalParseError):
                parse_decimal(token)

    def test_dec_04_non_finite_values_fail(self) -> None:
        for token in ("NaN", "sNaN", "Infinity", "-Infinity", "+Infinity"):
            with self.subTest(token=token), self.assertRaises(DecimalParseError):
                parse_decimal(token)
        for value in (Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity")):
            with self.subTest(value=value), self.assertRaises(DecimalParseError):
                canonical_decimal_text(value)

    def test_dec_05_signed_zero_canonicalizes_but_lexical_value_is_retained(self) -> None:
        for token in ("-0", "-0.000", "-0e4"):
            with self.subTest(token=token):
                quantity = convert_quantity(QuantityKind.POWER, token, "W")
                self.assertEqual(canonical_decimal_text(quantity.canonical_value), "0")
                self.assertEqual(quantity.conversion.original_value, token)

    def test_dec_06_numeric_and_lexical_identity_are_separate(self) -> None:
        first = convert_quantity(QuantityKind.POWER, "1.500", "W")
        second = convert_quantity(QuantityKind.POWER, "1.5", "W")
        self.assertTrue(first.same_numeric_identity(second))
        self.assertFalse(first.same_lexical_identity(second))
        self.assertFalse(first.same_audit_identity(second))

    def test_dec_07_external_numeric_input_is_string_only(self) -> None:
        for value in (1, 1.0, True, Decimal("1")):
            with self.subTest(value=value), self.assertRaises(DecimalParseError):
                parse_decimal(value)  # type: ignore[arg-type]


class M16AUnitTests(unittest.TestCase):
    def test_unit_01_milliwatts_convert_exactly(self) -> None:
        quantity = convert_quantity(QuantityKind.POWER, "1000", "mW")
        self.assertEqual(quantity.canonical_value, Decimal("1"))
        self.assertEqual(quantity.canonical_unit, "W")
        self.assertEqual(quantity.conversion.unit_registry_version, UNIT_REGISTRY_VERSION)
        self.assertIn("MW", quantity.conversion.conversion_rule_id)

    def test_unit_02_length_tokens_convert_exactly(self) -> None:
        expected = (("1", "mm", "0.001"), ("100", "um", "0.0001"), ("100", "µm", "0.0001"))
        for value, unit, canonical in expected:
            with self.subTest(unit=unit):
                result = convert_quantity(QuantityKind.LENGTH, value, unit)
                self.assertEqual(result.canonical_value, Decimal(canonical))
                self.assertEqual(result.canonical_unit, "m")

    def test_unit_03_greek_mu_is_not_the_micro_sign(self) -> None:
        with self.assertRaises(UnknownUnitError):
            convert_quantity(QuantityKind.LENGTH, "100", "μm")

    def test_unit_04_area_and_heat_flux_are_physically_scaled(self) -> None:
        area = convert_quantity(QuantityKind.AREA, "4", "mm^2")
        flux = convert_quantity(QuantityKind.HEAT_FLUX, "2.5", "W/mm^2")
        self.assertEqual(area.canonical_value, Decimal("0.000004"))
        self.assertEqual(flux.canonical_value, Decimal("2500000"))

    def test_unit_05_area_thermal_resistance_is_exact(self) -> None:
        result = convert_quantity(QuantityKind.AREA_THERMAL_RESISTANCE, "0.005", "mm^2*K/W")
        self.assertEqual(result.canonical_value, Decimal("0.000000005"))

    def test_unit_06_unknown_misspelled_case_changed_and_trimmed_units_fail(self) -> None:
        for unit in ("meter", "MM", "Mm", "mm ", " w", "w"):
            with self.subTest(unit=unit), self.assertRaises(UnknownUnitError):
                convert_quantity(QuantityKind.LENGTH, "1", unit)

    def test_unit_07_absolute_and_area_resistance_are_not_interchangeable(self) -> None:
        absolute = convert_quantity(QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "1", "K/W")
        area = convert_quantity(QuantityKind.AREA_THERMAL_RESISTANCE, "1", "m^2*K/W")
        self.assertFalse(absolute.same_numeric_identity(area))
        with self.assertRaises(QuantityKindMismatchError):
            absolute.compare_numeric(area)
        with self.assertRaises(UnknownUnitError):
            convert_quantity(QuantityKind.ABSOLUTE_THERMAL_RESISTANCE, "1", "m^2*K/W")

    def test_unit_08_conductance_conductivity_and_resistance_are_distinct(self) -> None:
        conductance = convert_quantity(QuantityKind.AREA_THERMAL_CONDUCTANCE, "1", "W/(m^2*K)")
        conductivity = convert_quantity(QuantityKind.THERMAL_CONDUCTIVITY, "1", "W/(m*K)")
        resistance = convert_quantity(QuantityKind.AREA_THERMAL_RESISTANCE, "1", "m^2*K/W")
        for other in (conductivity, resistance):
            self.assertFalse(conductance.same_numeric_identity(other))
            with self.assertRaises(QuantityKindMismatchError):
                conductance.compare_numeric(other)

    def test_unit_09_round_trip_preserves_numeric_and_audit_identity(self) -> None:
        original = convert_quantity(QuantityKind.LENGTH, "100", "µm")
        reconstructed = QuantifiedValue.from_dict(original.to_dict())
        self.assertTrue(original.same_numeric_identity(reconstructed))
        self.assertTrue(original.same_lexical_identity(reconstructed))
        self.assertTrue(original.same_audit_identity(reconstructed))


class M16ATemperatureAndInvariantTests(unittest.TestCase):
    def test_temp_01_absolute_celsius_uses_offset(self) -> None:
        self.assertEqual(convert_quantity(QuantityKind.ABSOLUTE_TEMPERATURE, "50", "degC").canonical_value, Decimal("323.15"))
        self.assertEqual(convert_quantity(QuantityKind.ABSOLUTE_TEMPERATURE, "0", "°C").canonical_value, Decimal("273.15"))

    def test_temp_02_temperature_difference_has_no_offset(self) -> None:
        for unit in ("K", "degC", "°C"):
            with self.subTest(unit=unit):
                result = convert_quantity(QuantityKind.TEMPERATURE_DIFFERENCE, "25", unit)
                self.assertEqual(result.canonical_value, Decimal("25"))
                self.assertEqual(result.canonical_unit, "K")

    def test_temp_03_absolute_and_difference_kinds_never_compare(self) -> None:
        absolute = convert_quantity(QuantityKind.ABSOLUTE_TEMPERATURE, "25", "K")
        difference = convert_quantity(QuantityKind.TEMPERATURE_DIFFERENCE, "25", "K")
        self.assertFalse(absolute.same_numeric_identity(difference))
        with self.assertRaises(QuantityKindMismatchError):
            absolute.compare_numeric(difference)

    def test_inv_01_length_invariants_are_exact(self) -> None:
        self.assertEqual(convert_quantity(QuantityKind.LENGTH, "1", "mm").canonical_value, Decimal("1e-3"))
        self.assertEqual(convert_quantity(QuantityKind.LENGTH, "100", "um").canonical_value, Decimal("1e-4"))

    def test_inv_02_explicit_caller_derives_area_without_algebra_api(self) -> None:
        side = convert_quantity(QuantityKind.LENGTH, "2", "mm").canonical_value
        derived_area = side * side
        self.assertEqual(derived_area, Decimal("4e-6"))


class M16AReverseProjectionTests(unittest.TestCase):
    def test_unit_prj_01a_absolute_temperature_projects_to_degc(self) -> None:
        projected = convert_canonical_to_unit(
            QuantityKind.ABSOLUTE_TEMPERATURE, Decimal("323.15"), "degC"
        )
        self.assertEqual(projected.conversion.original_value, "50")
        self.assertEqual(projected.conversion.original_unit, "degC")
        self.assertEqual(projected.canonical_value, Decimal("323.15"))

    def test_unit_prj_01b_absolute_temperature_projects_to_degree_c(self) -> None:
        projected = convert_canonical_to_unit(
            "absolute_temperature", Decimal("273.15"), "°C"
        )
        self.assertEqual(projected.conversion.original_value, "0")
        self.assertEqual(projected.conversion.original_unit, "°C")

    def test_unit_prj_01c_temperature_difference_projects_without_offset(self) -> None:
        projected = convert_canonical_to_unit(
            QuantityKind.TEMPERATURE_DIFFERENCE, Decimal("25"), "degC"
        )
        self.assertEqual(projected.conversion.original_value, "25")
        self.assertEqual(projected.canonical_value, Decimal("25"))

    def test_unit_prj_01d_absolute_and_difference_kinds_cannot_cross(self) -> None:
        absolute = convert_canonical_to_unit(
            QuantityKind.ABSOLUTE_TEMPERATURE, Decimal("25"), "degC"
        )
        difference = convert_canonical_to_unit(
            QuantityKind.TEMPERATURE_DIFFERENCE, Decimal("25"), "degC"
        )
        self.assertEqual(absolute.conversion.original_value, "-248.15")
        self.assertEqual(difference.conversion.original_value, "25")
        self.assertFalse(absolute.same_numeric_identity(difference))
        with self.assertRaises(QuantityKindMismatchError):
            absolute.compare_numeric(difference)

    def test_unit_prj_01e_watts_project_to_milliwatts(self) -> None:
        projected = convert_canonical_to_unit(QuantityKind.POWER, Decimal("1"), "mW")
        self.assertEqual(projected.conversion.original_value, "1000")

    def test_unit_prj_01f_square_metres_project_to_square_millimetres(self) -> None:
        projected = convert_canonical_to_unit(QuantityKind.AREA, Decimal("1"), "mm^2")
        self.assertEqual(projected.conversion.original_value, "1000000")

    def test_unit_prj_01g_unknown_target_unit_rejects(self) -> None:
        with self.assertRaises(UnknownUnitError):
            convert_canonical_to_unit(QuantityKind.POWER, Decimal("1"), "kW")

    def test_unit_prj_01h_other_kind_target_unit_rejects(self) -> None:
        with self.assertRaises(UnknownUnitError):
            convert_canonical_to_unit(
                QuantityKind.ABSOLUTE_TEMPERATURE, Decimal("323.15"), "mW"
            )

    def test_unit_prj_01i_non_decimal_and_noncanonical_inputs_reject(self) -> None:
        for value in (323.15, "323.15", Decimal("323.150")):
            with self.subTest(value=value), self.assertRaises(QuantityValidationError):
                convert_canonical_to_unit(
                    QuantityKind.ABSOLUTE_TEMPERATURE, value, "degC"  # type: ignore[arg-type]
                )

    def test_unit_prj_01j_non_finite_decimal_rejects(self) -> None:
        for value in (Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")):
            with self.subTest(value=value), self.assertRaises(QuantityValidationError):
                convert_canonical_to_unit(QuantityKind.POWER, value, "mW")

    def test_unit_prj_01k_public_forward_round_trip_preserves_identity(self) -> None:
        canonical = Decimal("0.000004")
        projected = convert_canonical_to_unit(QuantityKind.AREA, canonical, "mm^2")
        round_trip = convert_quantity(
            QuantityKind.AREA,
            projected.conversion.original_value,
            projected.conversion.original_unit,
        )
        self.assertEqual(round_trip.numeric_identity, (QuantityKind.AREA, canonical))
        self.assertEqual(projected.to_dict(), round_trip.to_dict())

    def test_unit_prj_01l_ambient_decimal_context_does_not_change_result(self) -> None:
        expected = convert_canonical_to_unit(
            QuantityKind.ABSOLUTE_TEMPERATURE, Decimal("323.15"), "degC"
        ).to_dict()
        with localcontext(Context(prec=2, Emin=-2, Emax=2)):
            actual = convert_canonical_to_unit(
                QuantityKind.ABSOLUTE_TEMPERATURE, Decimal("323.15"), "degC"
            ).to_dict()
        self.assertEqual(actual, expected)


class M16ASafetyAndScopeTests(unittest.TestCase):
    def test_safe_01_missing_ambiguous_and_material_like_inputs_fail(self) -> None:
        with self.assertRaises(QuantityValidationError):
            convert_quantity(None, "1", "K")  # type: ignore[arg-type]
        with self.assertRaises(UnknownUnitError):
            convert_quantity(QuantityKind.LENGTH, "1", None)  # type: ignore[arg-type]
        with self.assertRaises(UnknownUnitError):
            convert_quantity(QuantityKind.LENGTH, "1", "diamond")
        with self.assertRaises(UnknownUnitError):
            convert_quantity(QuantityKind.ABSOLUTE_TEMPERATURE, "1", "C")

    def test_safe_02_registry_constants_and_extreme_conversions_are_exact(self) -> None:
        for definition in UNIT_REGISTRY.values():
            self.assertIs(type(definition.scale), Decimal)
            self.assertIs(type(definition.offset), Decimal)
        original_precision = getcontext().prec
        getcontext().prec = 6
        try:
            coefficient = "9" * 64
            high = convert_quantity(QuantityKind.HEAT_FLUX, coefficient + "e65", "W/mm^2")
            low = convert_quantity(QuantityKind.AREA_THERMAL_RESISTANCE, "1e-128", "mm^2*K/W")
            offset = convert_quantity(
                QuantityKind.ABSOLUTE_TEMPERATURE,
                coefficient + "e-191",
                "degC",
            )
        finally:
            getcontext().prec = original_precision
        self.assertEqual(high.canonical_value, Decimal(coefficient + "e71"))
        self.assertEqual(low.canonical_value, Decimal("1e-134"))
        with localcontext(Context(prec=384)):
            offset_increment = offset.canonical_value - Decimal("273.15")
        self.assertEqual(offset_increment, Decimal(coefficient + "e-191"))
        with self.assertRaises(DecimalParseError):
            parse_decimal("1e129")
        with self.assertRaises(DecimalParseError):
            parse_decimal("1" * 65)

    def test_scope_01_registry_has_exact_approved_vocabulary(self) -> None:
        expected = {
            QuantityKind.POWER: {"W", "mW"},
            QuantityKind.HEAT_FLUX: {"W/m^2", "W/mm^2"},
            QuantityKind.LENGTH: {"m", "mm", "um", "µm"},
            QuantityKind.AREA: {"m^2", "mm^2"},
            QuantityKind.THERMAL_CONDUCTIVITY: {"W/(m*K)"},
            QuantityKind.AREA_THERMAL_RESISTANCE: {"m^2*K/W", "mm^2*K/W"},
            QuantityKind.ABSOLUTE_THERMAL_RESISTANCE: {"K/W"},
            QuantityKind.AREA_THERMAL_CONDUCTANCE: {"W/(m^2*K)"},
            QuantityKind.ABSOLUTE_TEMPERATURE: {"K", "degC", "°C"},
            QuantityKind.TEMPERATURE_DIFFERENCE: {"K", "degC", "°C"},
            QuantityKind.PHYSICAL_DIMENSIONLESS: {"1"},
        }
        actual = {
            kind: {token for registered_kind, token in UNIT_REGISTRY if registered_kind is kind}
            for kind in QuantityKind
        }
        self.assertEqual(actual, expected)

    def test_quantified_value_rejects_incorrect_kind_unit_invariant(self) -> None:
        valid = convert_quantity(QuantityKind.LENGTH, "1", "mm")
        with self.assertRaises(QuantityValidationError):
            QuantifiedValue(
                quantity_kind=QuantityKind.LENGTH,
                canonical_value=valid.canonical_value,
                canonical_unit="mm",
                conversion=valid.conversion,
            )
        forged = ConversionRecord(
            original_value="1",
            original_unit="mm",
            canonical_value=Decimal("0.001"),
            canonical_unit="mm",
            conversion_rule_id=valid.conversion.conversion_rule_id,
            unit_registry_version=UNIT_REGISTRY_VERSION,
        )
        with self.assertRaises(QuantityValidationError):
            QuantifiedValue(QuantityKind.LENGTH, Decimal("0.001"), "m", forged)


if __name__ == "__main__":
    unittest.main()
