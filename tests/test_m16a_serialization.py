from __future__ import annotations

import hashlib
import locale
import subprocess
import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from labos.engineering.quantities import QuantityKind, convert_quantity
from labos.engineering.serialization import (
    CANONICAL_JSON_VERSION,
    CanonicalSerializationError,
    canonical_json_bytes,
    canonical_sha256,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION_START = "95c8dcf6135f1ecd7e0e23be5f16b2aeeb5fcd6f"


class M16ACanonicalSerializationTests(unittest.TestCase):
    def test_ser_01_mapping_order_is_irrelevant_and_arrays_keep_order(self) -> None:
        first = {"z": [2, 1], "a": "µm"}
        second = {"a": "µm", "z": [2, 1]}
        expected = '{"a":"µm","z":[2,1]}\n'.encode("utf-8")
        self.assertEqual(canonical_json_bytes(first), expected)
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))
        self.assertNotEqual(canonical_json_bytes({"z": [1, 2], "a": "µm"}), expected)

    def test_ser_02_equivalent_decimals_have_identical_canonical_strings(self) -> None:
        values = (Decimal("1.500"), Decimal("1.5"), Decimal("15e-1"))
        outputs = {canonical_json_bytes({"value": value}) for value in values}
        self.assertEqual(outputs, {b'{"value":"1.5"}\n'})
        self.assertEqual(canonical_json_bytes([Decimal("1e-3"), Decimal("-0.00")]), b'["0.001","0"]\n')

    def test_ser_03_output_is_locale_independent_utf8_lf_and_exactly_hashed(self) -> None:
        payload = {"unit": "°C", "value": Decimal("1234.500")}
        baseline = canonical_json_bytes(payload)
        baseline_hash = canonical_sha256(payload)
        original = locale.setlocale(locale.LC_ALL)
        try:
            for candidate in ("C", ""):
                try:
                    locale.setlocale(locale.LC_ALL, candidate)
                except locale.Error:
                    continue
                self.assertEqual(canonical_json_bytes(payload), baseline)
                self.assertEqual(canonical_sha256(payload), baseline_hash)
        finally:
            locale.setlocale(locale.LC_ALL, original)
        self.assertFalse(baseline.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\r", baseline)
        self.assertTrue(baseline.endswith(b"\n"))
        self.assertFalse(baseline.endswith(b"\n\n"))
        self.assertEqual(baseline_hash, hashlib.sha256(baseline).hexdigest())
        self.assertEqual(CANONICAL_JSON_VERSION, "m16a-canonical-json-1.0")

    def test_ser_04_unsupported_values_and_non_string_keys_fail(self) -> None:
        unsupported = (
            1.0,
            Path("relative"),
            datetime(2026, 1, 1),
            {"set"},
            b"bytes",
            object(),
            Decimal("NaN"),
            Decimal("Infinity"),
            {1: "non-string-key"},
        )
        for value in unsupported:
            with self.subTest(value=repr(value)), self.assertRaises(CanonicalSerializationError):
                canonical_json_bytes(value)
        self.assertEqual(canonical_json_bytes({"bool": True, "integer": 1}), b'{"bool":true,"integer":1}\n')

    def test_ser_05_caller_owned_allowlist_projection_excludes_metadata(self) -> None:
        first = {
            "case_id": "SYN-001",
            "result": Decimal("1.500"),
            "hostname": "host-a",
            "username": "user-a",
            "absolute_path": "C:/a",
            "timestamp": "2026-01-01T00:00:00Z",
        }
        second = dict(first, hostname="host-b", username="user-b", absolute_path="D:/b", timestamp="2027-01-01T00:00:00Z")

        def identity_projection(payload: dict[str, object]) -> dict[str, object]:
            return {key: payload[key] for key in ("case_id", "result")}

        self.assertNotEqual(canonical_sha256(first), canonical_sha256(second))
        self.assertEqual(canonical_sha256(identity_projection(first)), canonical_sha256(identity_projection(second)))

    def test_i1_to_dict_value_is_explicitly_serializable(self) -> None:
        quantity = convert_quantity(QuantityKind.LENGTH, "100", "um")
        encoded = canonical_json_bytes(quantity.to_dict())
        self.assertIn(b'"canonical_value":"0.0001"', encoded)
        with self.assertRaises(CanonicalSerializationError):
            canonical_json_bytes(quantity)


class M16ACompatibilityTests(unittest.TestCase):
    def test_comp_01_prediction_reality_contract_files_are_byte_unchanged(self) -> None:
        paths = (
            "labos/schemas/prediction_reality_record.schema.json",
            "labos/prediction_reality/comparison.py",
            "labos/prediction_reality/validator.py",
            "tests/test_evidence_reality.py",
        )
        for relative in paths:
            with self.subTest(path=relative):
                baseline = subprocess.check_output(
                    ["git", "show", f"{IMPLEMENTATION_START}:{relative}"],
                    cwd=REPO_ROOT,
                )
                self.assertEqual((REPO_ROOT / relative).read_bytes(), baseline)

    def test_comp_02_historical_paths_have_no_git_identity_changes(self) -> None:
        changed = subprocess.check_output(
            ["git", "diff", "--name-only", IMPLEMENTATION_START, "--"],
            cwd=REPO_ROOT,
            text=True,
        ).splitlines()

        def is_historical(path: str) -> bool:
            lowered = path.lower()
            return (
                lowered.startswith("benchmarks/")
                or lowered.startswith("docs/benchmarks/")
                or lowered.startswith("labos/benchmarks/")
                or lowered.startswith("exports/m15b")
                or "/evidence/" in lowered
                or "/measurements/" in lowered
                or "/prediction_reality/" in lowered
                or "m15b" in lowered
                or path in {
                    "labos/schemas/evidence_object.schema.json",
                    "labos/schemas/measurement_reference.schema.json",
                    "labos/schemas/prediction_reality_record.schema.json",
                }
            )

        self.assertEqual([path for path in changed if is_historical(path)], [])


if __name__ == "__main__":
    unittest.main()
