from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from scripts import labos_benchmark
from labos.benchmarks.leakage_policy import (
    LEAKAGE_CATEGORIES,
    LEAKAGE_MATCH_MODES,
    PRIVATE_LEAKAGE_POLICY_FILENAME,
    LeakageToken,
    LoadedPrivateLeakagePolicy,
    PrivateLeakagePolicy,
    PrivateLeakagePolicySummary,
    load_private_leakage_policy,
    parse_private_leakage_policy_bytes,
    summarize_private_leakage_policy,
)


SECRET = "synthetic-private-token"
ALT_SECRET = "SYNTHETIC-OUTCOME-0001"
SOURCE_MARKER = "synthetic-source-marker"
PRIVATE_PATH_MARKER = "SYNTHETIC_PRIVATE_PATH_MARKER"
FILESYSTEM_SECRET = "SYNTHETIC_FILESYSTEM_ERROR_SECRET"


def policy_bytes(tokens: list[dict[str, object]] | None = None, *, suffix: bytes = b"") -> bytes:
    payload = {
        "policy_version": "1.0",
        "tokens": tokens
        if tokens is not None
        else [
            {
                "token_id": "LKG-0001",
                "category": "source_identity",
                "match_mode": "literal",
                "value": SECRET,
            }
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + suffix


def valid_token(token_id: str = "LKG-0001", **overrides: object) -> dict[str, object]:
    token: dict[str, object] = {
        "token_id": token_id,
        "category": "source_identity",
        "match_mode": "literal",
        "value": SECRET,
    }
    token.update(overrides)
    return token


class PrivateLeakagePolicyTest(unittest.TestCase):
    def assertSafeFailure(self, data: bytes, *, secret: str = SECRET) -> None:
        with self.assertRaises(ValueError) as context:
            parse_private_leakage_policy_bytes(data)
        text = str(context.exception)
        self.assertNotIn(secret, text)
        self.assertNotIn("{", text)

    def make_roots(self) -> tuple[tempfile.TemporaryDirectory[str], Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        repo = root / "repo"
        policy = root / "private"
        repo.mkdir()
        policy.mkdir()
        return temporary, repo, policy

    def write_policy(self, policy_root: Path, data: bytes | None = None) -> Path:
        path = policy_root / PRIVATE_LEAKAGE_POLICY_FILENAME
        path.write_bytes(data if data is not None else policy_bytes())
        return path

    def assertOperationalFailureSafe(
        self,
        context: unittest.case._AssertRaisesContext[ValueError],
    ) -> None:
        message = str(context.exception)
        for marker in (PRIVATE_PATH_MARKER, FILESYSTEM_SECRET, SECRET):
            self.assertNotIn(marker, message)

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [sys.executable, "scripts/labos_benchmark.py", *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=Path(__file__).resolve().parents[1],
        )

    def test_private_policy_filename_is_exact(self) -> None:
        self.assertEqual(PRIVATE_LEAKAGE_POLICY_FILENAME, "PRIVATE_LEAKAGE_POLICY.json")

    def test_categories_equal_required_tuple(self) -> None:
        self.assertEqual(
            LEAKAGE_CATEGORIES,
            (
                "expected_rule",
                "expected_score",
                "expected_status",
                "known_error_label",
                "outcome",
                "result_explanation",
                "rule_fix",
                "source_identity",
                "trigger_rewrite",
            ),
        )

    def test_categories_are_sorted(self) -> None:
        self.assertEqual(LEAKAGE_CATEGORIES, tuple(sorted(LEAKAGE_CATEGORIES)))

    def test_match_modes_equal_required_tuple(self) -> None:
        self.assertEqual(LEAKAGE_MATCH_MODES, ("literal", "nfkc_casefold"))

    def test_minimal_valid_policy_parses(self) -> None:
        policy = parse_private_leakage_policy_bytes(policy_bytes())
        self.assertEqual(policy.policy_version, "1.0")
        self.assertEqual(len(policy.tokens), 1)

    def test_multiple_valid_records_parse(self) -> None:
        policy = parse_private_leakage_policy_bytes(
            policy_bytes(
                [
                    valid_token("LKG-0001", value=SECRET),
                    valid_token("LKG-0002", category="outcome", value=ALT_SECRET),
                ]
            )
        )
        self.assertEqual(len(policy.tokens), 2)

    def test_token_order_is_preserved(self) -> None:
        policy = parse_private_leakage_policy_bytes(
            policy_bytes([valid_token("LKG-0001"), valid_token("LKG-0002", value=ALT_SECRET)])
        )
        self.assertEqual([token.token_id for token in policy.tokens], ["LKG-0001", "LKG-0002"])

    def test_literal_match_value_remains_exact(self) -> None:
        token = parse_private_leakage_policy_bytes(policy_bytes()).tokens[0]
        self.assertEqual(token.match_value, SECRET)

    def test_nfkc_casefold_match_value_is_precomputed(self) -> None:
        token = parse_private_leakage_policy_bytes(
            policy_bytes([valid_token(match_mode="nfkc_casefold", value="ＡbC")])
        ).tokens[0]
        self.assertEqual(token.match_value, "abc")

    def test_malformed_utf8_fails_safely(self) -> None:
        self.assertSafeFailure(b"\xff")

    def test_malformed_json_fails_safely(self) -> None:
        self.assertSafeFailure(b"{")

    def test_unknown_top_level_key_fails(self) -> None:
        self.assertSafeFailure(b'{"policy_version":"1.0","tokens":[],"extra":1}')

    def test_missing_top_level_key_fails(self) -> None:
        self.assertSafeFailure(b'{"policy_version":"1.0"}')

    def test_unknown_token_key_fails(self) -> None:
        token = valid_token()
        token["extra"] = "x"
        self.assertSafeFailure(policy_bytes([token]))

    def test_missing_token_key_fails(self) -> None:
        token = valid_token()
        del token["value"]
        self.assertSafeFailure(policy_bytes([token]))

    def test_duplicate_top_level_key_fails(self) -> None:
        self.assertSafeFailure(b'{"policy_version":"1.0","policy_version":"1.0","tokens":[]}')

    def test_duplicate_nested_key_fails(self) -> None:
        data = b'{"policy_version":"1.0","tokens":[{"token_id":"LKG-0001","category":"source_identity","match_mode":"literal","value":"synthetic-private-token","value":"synthetic-private-token"}]}'
        self.assertSafeFailure(data)

    def test_wrong_policy_version_fails(self) -> None:
        self.assertSafeFailure(b'{"policy_version":"2.0","tokens":[]}')

    def test_empty_token_list_fails(self) -> None:
        self.assertSafeFailure(policy_bytes([]))

    def test_unsorted_token_records_fail(self) -> None:
        self.assertSafeFailure(policy_bytes([valid_token("LKG-0002"), valid_token("LKG-0001", value=ALT_SECRET)]))

    def test_duplicate_token_ids_fail(self) -> None:
        self.assertSafeFailure(policy_bytes([valid_token("LKG-0001"), valid_token("LKG-0001", value=ALT_SECRET)]))

    def test_invalid_opaque_token_id_fails(self) -> None:
        self.assertSafeFailure(policy_bytes([valid_token("secret-token-id")]))

    def test_candidate_controlled_invalid_token_id_is_not_echoed(self) -> None:
        bad_id = "secret-token-id"
        with self.assertRaises(ValueError) as context:
            parse_private_leakage_policy_bytes(policy_bytes([valid_token(bad_id)]))
        self.assertNotIn(bad_id, str(context.exception))

    def test_invalid_category_fails(self) -> None:
        self.assertSafeFailure(policy_bytes([valid_token(category="synthetic-category")]))

    def test_invalid_match_mode_fails(self) -> None:
        self.assertSafeFailure(policy_bytes([valid_token(match_mode="synthetic-mode")]))

    def test_non_string_value_fails(self) -> None:
        for value in (True, 1, 1.5, ["x"], {"x": "y"}, None):
            with self.subTest(value=type(value).__name__):
                self.assertSafeFailure(policy_bytes([valid_token(value=value)]))

    def test_value_shorter_than_three_fails(self) -> None:
        self.assertSafeFailure(policy_bytes([valid_token(value="ab")]))

    def test_value_longer_than_1024_fails(self) -> None:
        self.assertSafeFailure(policy_bytes([valid_token(value="x" * 1025)]), secret="x" * 1025)

    def test_leading_whitespace_fails(self) -> None:
        self.assertSafeFailure(policy_bytes([valid_token(value=" " + SECRET)]))

    def test_trailing_whitespace_fails(self) -> None:
        self.assertSafeFailure(policy_bytes([valid_token(value=SECRET + " ")]))

    def test_lf_fails(self) -> None:
        self.assertSafeFailure(policy_bytes([valid_token(value="abc\ndef")]), secret="abc\ndef")

    def test_cr_fails(self) -> None:
        self.assertSafeFailure(policy_bytes([valid_token(value="abc\rdef")]), secret="abc\rdef")

    def test_nul_fails(self) -> None:
        self.assertSafeFailure(policy_bytes([valid_token(value="abc\x00def")]), secret="abc\x00def")

    def test_empty_normalized_nfkc_casefold_value_fails(self) -> None:
        with mock.patch("labos.benchmarks.leakage_policy._nfkc_casefold", return_value=""):
            self.assertSafeFailure(policy_bytes([valid_token(match_mode="nfkc_casefold", value=SECRET)]))

    def test_duplicate_literal_signature_fails(self) -> None:
        self.assertSafeFailure(policy_bytes([valid_token("LKG-0001"), valid_token("LKG-0002")]))

    def test_duplicate_nfkc_casefold_signature_fails(self) -> None:
        self.assertSafeFailure(
            policy_bytes(
                [
                    valid_token("LKG-0001", match_mode="nfkc_casefold", value="ＡBC"),
                    valid_token("LKG-0002", match_mode="nfkc_casefold", value="abc"),
                ]
            ),
            secret="abc",
        )

    def test_duplicate_signature_across_categories_fails(self) -> None:
        self.assertSafeFailure(
            policy_bytes([valid_token("LKG-0001"), valid_token("LKG-0002", category="outcome")])
        )

    def test_repr_leakage_token_does_not_expose_values(self) -> None:
        token = parse_private_leakage_policy_bytes(policy_bytes()).tokens[0]
        self.assertNotIn(SECRET, repr(token))
        self.assertNotIn(token.match_value, repr(token))

    def test_repr_policy_does_not_expose_values(self) -> None:
        policy = parse_private_leakage_policy_bytes(policy_bytes())
        self.assertNotIn(SECRET, repr(policy))

    def test_repr_loaded_policy_does_not_expose_values(self) -> None:
        loaded = LoadedPrivateLeakagePolicy(parse_private_leakage_policy_bytes(policy_bytes()), 1, "0" * 64)
        self.assertNotIn(SECRET, repr(loaded))

    def test_every_tested_validation_exception_omits_secret(self) -> None:
        bad_inputs = [
            policy_bytes([valid_token(value=" " + SECRET)]),
            policy_bytes([valid_token(category="bad")]),
            policy_bytes([valid_token(match_mode="bad")]),
        ]
        for data in bad_inputs:
            with self.subTest(data=data[:10]):
                self.assertSafeFailure(data)

    def test_parser_exceptions_never_contain_decoded_json_document(self) -> None:
        with self.assertRaises(ValueError) as context:
            parse_private_leakage_policy_bytes(policy_bytes([valid_token(value=" " + SECRET)]))
        self.assertNotIn('"policy_version"', str(context.exception))

    def test_exact_bytes_determine_sha256_and_byte_length(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            data = policy_bytes()
            self.write_policy(policy, data)
            loaded = load_private_leakage_policy(repo_root=repo, policy_root=policy)
            self.assertEqual(loaded.byte_length, len(data))
            self.assertEqual(loaded.sha256, hashlib.sha256(data).hexdigest())

    def test_trailing_newline_changes_policy_sha256(self) -> None:
        self.assertNotEqual(hashlib.sha256(policy_bytes()).hexdigest(), hashlib.sha256(policy_bytes(suffix=b"\n")).hexdigest())

    def test_crlf_versus_lf_changes_policy_sha256(self) -> None:
        lf = policy_bytes(suffix=b"\n")
        crlf = lf.replace(b"\n", b"\r\n")
        self.assertNotEqual(hashlib.sha256(lf).hexdigest(), hashlib.sha256(crlf).hexdigest())

    def test_json_whitespace_changes_policy_sha256(self) -> None:
        compact = json.dumps(json.loads(policy_bytes().decode("utf-8")), separators=(",", ":")).encode("utf-8")
        self.assertNotEqual(hashlib.sha256(policy_bytes()).hexdigest(), hashlib.sha256(compact).hexdigest())

    def test_summary_reports_exact_identity(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            data = policy_bytes()
            self.write_policy(policy, data)
            summary = summarize_private_leakage_policy(load_private_leakage_policy(repo_root=repo, policy_root=policy))
            self.assertEqual(summary.byte_length, len(data))
            self.assertEqual(summary.sha256, hashlib.sha256(data).hexdigest())

    def test_summary_contains_no_token_ids_or_values(self) -> None:
        summary = PrivateLeakagePolicySummary(True, "1.0", 1, 1, "0" * 64)
        text = repr(summary)
        self.assertNotIn("LKG-0001", text)
        self.assertNotIn(SECRET, text)

    def test_valid_external_policy_root_loads(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            self.write_policy(policy)
            loaded = load_private_leakage_policy(repo_root=repo, policy_root=policy)
            self.assertEqual(len(loaded.policy.tokens), 1)

    def test_policy_root_inside_repository_is_rejected(self) -> None:
        temporary, repo, _policy = self.make_roots()
        with temporary:
            inside = repo / "private"; inside.mkdir()
            self.write_policy(inside)
            with self.assertRaises(ValueError):
                load_private_leakage_policy(repo_root=repo, policy_root=inside)

    def test_repository_inside_policy_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            policy = Path(tmp) / "private"; repo = policy / "repo"; repo.mkdir(parents=True)
            self.write_policy(policy)
            with self.assertRaises(ValueError):
                load_private_leakage_policy(repo_root=repo, policy_root=policy)

    def test_policy_root_equal_repository_is_rejected(self) -> None:
        temporary, repo, _policy = self.make_roots()
        with temporary:
            self.write_policy(repo)
            with self.assertRaises(ValueError):
                load_private_leakage_policy(repo_root=repo, policy_root=repo)

    def test_overlap_with_additional_forbidden_root_is_rejected(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            forbidden = Path(temporary.name) / "forbidden"; forbidden.mkdir()
            with self.assertRaises(ValueError):
                load_private_leakage_policy(repo_root=repo, policy_root=policy, additional_forbidden_roots=[policy])
            with self.assertRaises(ValueError):
                load_private_leakage_policy(repo_root=repo, policy_root=policy, additional_forbidden_roots=[forbidden / "missing"])

    def test_additional_forbidden_root_inside_policy_root_is_rejected(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            child = policy / "child"; child.mkdir()
            self.write_policy(policy)
            with self.assertRaises(ValueError):
                load_private_leakage_policy(repo_root=repo, policy_root=policy, additional_forbidden_roots=[child])

    def test_policy_root_inside_additional_forbidden_root_is_rejected(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            forbidden = policy.parent
            self.write_policy(policy)
            with self.assertRaises(ValueError):
                load_private_leakage_policy(repo_root=repo, policy_root=policy, additional_forbidden_roots=[forbidden])

    def test_policy_root_symlink_is_rejected_when_supported(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            link = Path(temporary.name) / "link"
            try:
                link.symlink_to(policy, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            with self.assertRaises(ValueError):
                load_private_leakage_policy(repo_root=repo, policy_root=link)

    def test_broken_policy_root_symlink_is_rejected_when_supported(self) -> None:
        temporary, repo, _policy = self.make_roots()
        with temporary:
            link = Path(temporary.name) / "broken"
            try:
                link.symlink_to(Path(temporary.name) / "missing", target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            with self.assertRaises(ValueError):
                load_private_leakage_policy(repo_root=repo, policy_root=link)

    def test_forbidden_root_symlink_is_rejected_when_supported(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            target = Path(temporary.name) / "forbidden"; target.mkdir()
            link = Path(temporary.name) / "forbidden-link"
            try:
                link.symlink_to(target, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            self.write_policy(policy)
            with self.assertRaises(ValueError):
                load_private_leakage_policy(repo_root=repo, policy_root=policy, additional_forbidden_roots=[link])

    def test_missing_policy_file_is_rejected(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            with self.assertRaises(ValueError):
                load_private_leakage_policy(repo_root=repo, policy_root=policy)

    def test_policy_file_symlink_is_rejected_when_supported(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            target = Path(temporary.name) / "target.json"; target.write_bytes(policy_bytes())
            link = policy / PRIVATE_LEAKAGE_POLICY_FILENAME
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            with self.assertRaises(ValueError):
                load_private_leakage_policy(repo_root=repo, policy_root=policy)

    def test_broken_policy_file_symlink_is_rejected_when_supported(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            link = policy / PRIVATE_LEAKAGE_POLICY_FILENAME
            try:
                link.symlink_to(Path(temporary.name) / "missing.json")
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            with self.assertRaises(ValueError):
                load_private_leakage_policy(repo_root=repo, policy_root=policy)

    def test_policy_file_directory_is_rejected(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            (policy / PRIVATE_LEAKAGE_POLICY_FILENAME).mkdir()
            with self.assertRaises(ValueError):
                load_private_leakage_policy(repo_root=repo, policy_root=policy)

    def test_empty_policy_file_is_rejected(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            self.write_policy(policy, b"")
            with self.assertRaises(ValueError):
                load_private_leakage_policy(repo_root=repo, policy_root=policy)

    def test_policy_read_failure_produces_safe_path_free_error(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            self.write_policy(policy)
            with mock.patch("pathlib.Path.read_bytes", side_effect=OSError("private-path-secret")):
                with self.assertRaises(ValueError) as context:
                    load_private_leakage_policy(repo_root=repo, policy_root=policy)
            self.assertNotIn(str(policy), str(context.exception))
            self.assertNotIn("private-path-secret", str(context.exception))

    def test_directory_resolution_oserror_is_sanitized(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            self.write_policy(policy)
            error = OSError(f"{PRIVATE_PATH_MARKER} {FILESYSTEM_SECRET}")
            with mock.patch.object(Path, "resolve", side_effect=error):
                with self.assertRaises(ValueError) as context:
                    load_private_leakage_policy(repo_root=repo, policy_root=policy)
            self.assertOperationalFailureSafe(context)

    def test_directory_resolution_runtimeerror_is_sanitized(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            self.write_policy(policy)
            error = RuntimeError(f"{PRIVATE_PATH_MARKER} {FILESYSTEM_SECRET}")
            with mock.patch.object(Path, "resolve", side_effect=error):
                with self.assertRaises(ValueError) as context:
                    load_private_leakage_policy(repo_root=repo, policy_root=policy)
            self.assertOperationalFailureSafe(context)

    def test_directory_probe_oserror_is_sanitized(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            self.write_policy(policy)
            error = OSError(f"{PRIVATE_PATH_MARKER} {FILESYSTEM_SECRET}")
            with mock.patch.object(Path, "exists", side_effect=error):
                with self.assertRaises(ValueError) as context:
                    load_private_leakage_policy(repo_root=repo, policy_root=policy)
            self.assertOperationalFailureSafe(context)

    def test_policy_file_probe_oserror_is_sanitized(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            self.write_policy(policy)
            error = OSError(f"{PRIVATE_PATH_MARKER} {FILESYSTEM_SECRET}")
            with mock.patch.object(Path, "is_file", side_effect=error):
                with self.assertRaises(ValueError) as context:
                    load_private_leakage_policy(repo_root=repo, policy_root=policy)
            self.assertOperationalFailureSafe(context)

    def test_cli_operational_error_returns_two_without_private_details(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            self.write_policy(policy)
            stdout = io.StringIO()
            stderr = io.StringIO()
            error = RuntimeError(f"{PRIVATE_PATH_MARKER} {FILESYSTEM_SECRET} {SECRET}")
            with mock.patch.object(Path, "resolve", side_effect=error):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    result = labos_benchmark.main(
                        [
                            "validate-private-leakage-policy",
                            "--repo-root",
                            str(repo),
                            "--policy-root",
                            str(policy),
                        ]
                    )
            self.assertEqual(result, 2)
            self.assertEqual(stdout.getvalue(), "")
            for marker in (PRIVATE_PATH_MARKER, FILESYSTEM_SECRET, SECRET):
                self.assertNotIn(marker, stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())

    def test_cli_valid_policy_returns_zero(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            self.write_policy(policy)
            result = self.run_cli("validate-private-leakage-policy", "--repo-root", str(repo), "--policy-root", str(policy))
            self.assertEqual(result.returncode, 0)

    def test_cli_invalid_policy_returns_two(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            self.write_policy(policy, b"{")
            result = self.run_cli("validate-private-leakage-policy", "--repo-root", str(repo), "--policy-root", str(policy))
            self.assertEqual(result.returncode, 2)

    def test_cli_unsafe_storage_returns_two(self) -> None:
        temporary, repo, _policy = self.make_roots()
        with temporary:
            inside = repo / "private"; inside.mkdir()
            self.write_policy(inside)
            result = self.run_cli("validate-private-leakage-policy", "--repo-root", str(repo), "--policy-root", str(inside))
            self.assertEqual(result.returncode, 2)

    def test_cli_success_json_has_approved_keys(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            self.write_policy(policy)
            result = self.run_cli("validate-private-leakage-policy", "--repo-root", str(repo), "--policy-root", str(policy), "--json")
            self.assertEqual(set(json.loads(result.stdout)), {"valid", "policy_version", "token_count", "byte_length", "sha256"})

    def test_cli_success_output_contains_no_token_id(self) -> None:
        self.assertCliOmits("LKG-0001")

    def test_cli_success_output_contains_no_category(self) -> None:
        self.assertCliOmits("source_identity")

    def test_cli_success_output_contains_no_match_mode(self) -> None:
        self.assertCliOmits("literal")

    def test_cli_success_output_contains_no_token_value(self) -> None:
        self.assertCliOmits(SECRET)

    def test_cli_success_output_contains_no_policy_path(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            self.write_policy(policy)
            result = self.run_cli("validate-private-leakage-policy", "--repo-root", str(repo), "--policy-root", str(policy), "--json")
            self.assertNotIn(str(policy).encode(), result.stdout)

    def test_cli_error_output_contains_no_token_value(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            self.write_policy(policy, policy_bytes([valid_token(value=" " + SECRET)]))
            result = self.run_cli("validate-private-leakage-policy", "--repo-root", str(repo), "--policy-root", str(policy))
            self.assertNotIn(SECRET.encode(), result.stderr)

    def test_cli_error_output_contains_no_absolute_policy_path(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            result = self.run_cli("validate-private-leakage-policy", "--repo-root", str(repo), "--policy-root", str(policy))
            self.assertNotIn(str(policy).encode(), result.stderr)

    def test_cli_deterministic_inputs_produce_identical_stdout(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            self.write_policy(policy)
            args = ("validate-private-leakage-policy", "--repo-root", str(repo), "--policy-root", str(policy), "--json")
            self.assertEqual(self.run_cli(*args).stdout, self.run_cli(*args).stdout)

    def test_cli_json_output_ends_in_one_newline(self) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            self.write_policy(policy)
            result = self.run_cli("validate-private-leakage-policy", "--repo-root", str(repo), "--policy-root", str(policy), "--json")
            self.assertTrue(result.stdout.endswith(b"\n"))
            self.assertFalse(result.stdout.endswith(b"\n\n"))

    def test_existing_benchmark_cli_commands_remain_available(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn(b"hash-file", result.stdout)
        self.assertIn(b"build-sealed-manifest", result.stdout)

    def assertCliOmits(self, text: str) -> None:
        temporary, repo, policy = self.make_roots()
        with temporary:
            self.write_policy(policy)
            result = self.run_cli("validate-private-leakage-policy", "--repo-root", str(repo), "--policy-root", str(policy), "--json")
            self.assertEqual(result.returncode, 0)
            self.assertNotIn(text.encode(), result.stdout)
            self.assertNotIn(text.encode(), result.stderr)


if __name__ == "__main__":
    unittest.main()
