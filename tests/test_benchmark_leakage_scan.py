from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

from labos.benchmarks.leakage_scan import (
    LEAKAGE_AUDIT_CODES,
    LEAKAGE_AUDIT_REPORT_VERSION,
    MAX_SCANNABLE_FILE_BYTES,
    LeakageAuditFinding,
    LeakageAuditReport,
    LeakageScanRoot,
    parse_leakage_audit_report_bytes,
    scan_private_leakage,
    serialize_leakage_audit_report,
)
from labos.benchmarks.leakage_policy import PRIVATE_LEAKAGE_POLICY_FILENAME


SECRET = "synthetic-private-token"
ALT_SECRET = "SYNTHETIC-OUTCOME-0001"
PATH_SECRET = "PRIVATE-PATH-SECRET-0001"


def policy_bytes(tokens: list[dict[str, object]] | None = None) -> bytes:
    return json.dumps(
        {
            "policy_version": "1.0",
            "tokens": tokens
            if tokens is not None
            else [{"token_id": "LKG-0001", "category": "source_identity", "match_mode": "literal", "value": SECRET}],
        },
        indent=2,
        sort_keys=True,
    ).encode("utf-8")


def token(token_id: str, value: str, *, mode: str = "literal", category: str = "source_identity") -> dict[str, object]:
    return {"token_id": token_id, "category": category, "match_mode": mode, "value": value}


class LeakageScanTest(unittest.TestCase):
    def make_layout(self) -> tuple[tempfile.TemporaryDirectory[str], Path, Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        base = Path(temporary.name)
        repo = base / "repo"
        policy = base / "private"
        root = base / "scan"
        repo.mkdir()
        policy.mkdir()
        root.mkdir()
        return temporary, repo, policy, root

    def write_policy(self, policy: Path, tokens: list[dict[str, object]] | None = None) -> bytes:
        data = policy_bytes(tokens)
        (policy / PRIVATE_LEAKAGE_POLICY_FILENAME).write_bytes(data)
        return data

    def scan(self, repo: Path, policy: Path, *roots: LeakageScanRoot):
        return scan_private_leakage(repo_root=repo, policy_root=policy, scan_roots=roots)

    def root(self, path: Path, root_id: str = "ROOT-0001") -> LeakageScanRoot:
        return LeakageScanRoot(root_id=root_id, path=path)

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run([sys.executable, "scripts/labos_benchmark.py", *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=Path(__file__).resolve().parents[1])

    def assert_no_secret(self, data: bytes, *paths: Path) -> None:
        self.assertNotIn(SECRET.encode(), data)
        self.assertNotIn(ALT_SECRET.encode(), data)
        self.assertNotIn(PATH_SECRET.encode(), data)
        for path in paths:
            self.assertNotIn(str(path).encode(), data)

    def test_constants_are_exact(self) -> None:
        self.assertEqual(LEAKAGE_AUDIT_REPORT_VERSION, "1.0")
        self.assertEqual(MAX_SCANNABLE_FILE_BYTES, 16 * 1024 * 1024)
        self.assertEqual(LEAKAGE_AUDIT_CODES, tuple(sorted(LEAKAGE_AUDIT_CODES)))

    def test_models_do_not_expose_raw_path_fields(self) -> None:
        self.assertNotIn("path", LeakageAuditFinding.__dataclass_fields__)
        self.assertNotIn("path", LeakageAuditReport.__dataclass_fields__)
        self.assertNotIn("/private", repr(LeakageScanRoot("ROOT-0001", Path("/private"))))

    def test_empty_root_passes_and_counts_no_entries(self) -> None:
        temporary, repo, policy, root = self.make_layout()
        with temporary:
            self.write_policy(policy)
            report = self.scan(repo, policy, self.root(root))
            self.assertEqual(report.status, "pass")
            self.assertEqual((report.entry_count, report.regular_file_count, report.decoded_file_count), (0, 0, 0))

    def test_directory_and_nested_file_are_counted(self) -> None:
        temporary, repo, policy, root = self.make_layout()
        with temporary:
            self.write_policy(policy)
            child = root / "nested"; child.mkdir()
            (child / "plain.txt").write_text("plain", encoding="utf-8")
            report = self.scan(repo, policy, self.root(root))
            self.assertEqual(report.entry_count, 2)
            self.assertEqual(report.regular_file_count, 1)
            self.assertEqual(report.decoded_file_count, 1)

    def test_no_roots_and_invalid_root_configuration_are_safe(self) -> None:
        temporary, repo, policy, root = self.make_layout()
        with temporary:
            self.write_policy(policy)
            for roots in ((), (LeakageScanRoot("bad", root),), (LeakageScanRoot("ROOT-0002", root), LeakageScanRoot("ROOT-0001", root))):
                with self.subTest(roots=roots):
                    with self.assertRaises(ValueError) as context:
                        self.scan(repo, policy, *roots)
                    self.assertNotIn(str(root), str(context.exception))

    def test_missing_nondirectory_duplicate_and_overlap_roots_are_rejected(self) -> None:
        temporary, repo, policy, root = self.make_layout()
        with temporary:
            self.write_policy(policy)
            file_root = root / "file"; file_root.write_bytes(b"")
            nested = root / "nested"; nested.mkdir()
            cases = [
                (self.root(root / "missing"),),
                (self.root(file_root),),
                (self.root(root, "ROOT-0001"), self.root(root, "ROOT-0002")),
                (self.root(root, "ROOT-0001"), self.root(nested, "ROOT-0002")),
            ]
            for roots in cases:
                with self.subTest(roots=roots):
                    with self.assertRaises(ValueError):
                        self.scan(repo, policy, *roots)

    def test_multiple_sorted_roots_are_scanned(self) -> None:
        temporary, repo, policy, root = self.make_layout()
        with temporary:
            self.write_policy(policy)
            second = Path(temporary.name) / "second-root"
            second.mkdir()
            report = self.scan(
                repo,
                policy,
                self.root(root, "ROOT-0001"),
                self.root(second, "ROOT-0002"),
            )
            self.assertEqual((report.status, report.root_count), ("pass", 2))

    def test_symlink_and_broken_symlink_roots_are_rejected_when_supported(self) -> None:
        temporary, repo, policy, root = self.make_layout()
        with temporary:
            self.write_policy(policy)
            link = Path(temporary.name) / "root-link"
            broken = Path(temporary.name) / "broken-root-link"
            try:
                link.symlink_to(root, target_is_directory=True)
                broken.symlink_to(Path(temporary.name) / "missing", target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            for candidate in (link, broken):
                with self.subTest(candidate=candidate.name):
                    with self.assertRaises(ValueError):
                        self.scan(repo, policy, self.root(candidate))

    def test_policy_root_overlap_is_rejected_without_path_disclosure(self) -> None:
        temporary, repo, _policy, root = self.make_layout()
        with temporary:
            self.write_policy(root)
            with self.assertRaises(ValueError) as context:
                self.scan(repo, root, self.root(root))
            self.assertNotIn(str(root), str(context.exception))

    def test_literal_path_matching_and_relative_identity(self) -> None:
        temporary, repo, policy, root = self.make_layout()
        with temporary:
            self.write_policy(policy)
            (root / ("x-" + SECRET)).write_text("clean", encoding="utf-8")
            report = self.scan(repo, policy, self.root(root))
            finding = next(item for item in report.findings if item.code == "path_match")
            self.assertEqual(finding.occurrence_count, 1)
            self.assertEqual(finding.path_sha256, hashlib.sha256(("ROOT-0001\0x-" + SECRET).encode()).hexdigest())
            self.assertNotIn(SECRET, repr(finding))

    def test_path_literal_is_case_sensitive_and_nfkc_casefold_matches(self) -> None:
        temporary, repo, policy, root = self.make_layout()
        with temporary:
            self.write_policy(policy, [token("LKG-0001", "abc"), token("LKG-0002", "ABC", mode="nfkc_casefold")])
            (root / "AbC").write_bytes(b"")
            findings = self.scan(repo, policy, self.root(root)).findings
            self.assertEqual([item.token_id for item in findings if item.code == "path_match"], ["LKG-0002"])

    def test_directory_paths_and_multiple_tokens_are_scanned(self) -> None:
        temporary, repo, policy, root = self.make_layout()
        with temporary:
            self.write_policy(policy, [token("LKG-0001", "synthetic"), token("LKG-0002", "private")])
            directory = root / "synthetic-private"; directory.mkdir()
            findings = [item for item in self.scan(repo, policy, self.root(root)).findings if item.code == "path_match"]
            self.assertEqual([item.token_id for item in findings], ["LKG-0001", "LKG-0002"])

    def test_content_literal_nfkc_nul_and_bom_semantics(self) -> None:
        temporary, repo, policy, root = self.make_layout()
        with temporary:
            self.write_policy(policy, [token("LKG-0001", "aaa"), token("LKG-0002", "ABC", mode="nfkc_casefold"), token("LKG-0003", "\ufeffxx")])
            (root / "text.txt").write_bytes(b"aaa\x00AbC\xef\xbb\xbfxx")
            findings = [item.token_id for item in self.scan(repo, policy, self.root(root)).findings if item.code == "content_match"]
            self.assertEqual(findings, ["LKG-0001", "LKG-0002", "LKG-0003"])

    def test_repeated_content_occurrences_are_aggregated(self) -> None:
        temporary, repo, policy, root = self.make_layout()
        with temporary:
            self.write_policy(policy)
            (root / "plain.txt").write_text(SECRET + SECRET + SECRET, encoding="utf-8")
            findings = [item for item in self.scan(repo, policy, self.root(root)).findings if item.code == "content_match"]
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].occurrence_count, 3)

    def test_non_utf8_and_oversize_do_not_match_content(self) -> None:
        temporary, repo, policy, root = self.make_layout()
        with temporary:
            self.write_policy(policy)
            (root / "bad.bin").write_bytes(b"\xff" + SECRET.encode())
            first = self.scan(repo, policy, self.root(root))
            with mock.patch("labos.benchmarks.leakage_scan.MAX_SCANNABLE_FILE_BYTES", 2):
                (root / "large.txt").write_text(SECRET, encoding="utf-8")
                second = self.scan(repo, policy, self.root(root))
            self.assertIn("non_utf8_file", [item.code for item in first.findings])
            self.assertIn("oversize_file", [item.code for item in second.findings])
            self.assertNotIn("content_match", [item.code for item in second.findings])

    def test_scanned_byte_and_file_counts_are_exact(self) -> None:
        temporary, repo, policy, root = self.make_layout()
        with temporary:
            self.write_policy(policy)
            (root / "one").write_bytes(b"ab")
            (root / "two").write_bytes(b"\xff")
            report = self.scan(repo, policy, self.root(root))
            self.assertEqual(report.regular_file_count, 2)
            self.assertEqual(report.decoded_file_count, 1)
            self.assertEqual(report.scanned_byte_count, 3)

    def test_symlinks_are_not_followed_when_supported(self) -> None:
        temporary, repo, policy, root = self.make_layout()
        with temporary:
            self.write_policy(policy)
            target = Path(temporary.name) / "target"; target.write_text(SECRET, encoding="utf-8")
            link = root / "link"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            report = self.scan(repo, policy, self.root(root))
            self.assertIn("unsafe_symlink", [item.code for item in report.findings])
            self.assertNotIn("content_match", [item.code for item in report.findings])

    def test_directory_enumeration_and_entry_errors_are_findings(self) -> None:
        temporary, repo, policy, root = self.make_layout()
        with temporary:
            self.write_policy(policy)
            child = root / "child"; child.mkdir()
            with mock.patch("labos.benchmarks.leakage_scan.os.scandir", side_effect=OSError(PATH_SECRET)):
                report = self.scan(repo, policy, self.root(root))
            self.assertIn("directory_read_error", [item.code for item in report.findings])
            real_lstat = os.lstat

            def fail_child_inspection(path: os.PathLike[str] | str):
                if Path(path) == child:
                    raise OSError(PATH_SECRET)
                return real_lstat(path)

            with mock.patch(
                "labos.benchmarks.leakage_scan.os.lstat",
                side_effect=fail_child_inspection,
            ):
                report = self.scan(repo, policy, self.root(root))
            self.assertIn("entry_inspection_error", [item.code for item in report.findings])
            self.assertNotIn(PATH_SECRET, serialize_leakage_audit_report(report).decode())

    def test_regular_file_read_error_and_descriptor_closure(self) -> None:
        temporary, repo, policy, root = self.make_layout()
        with temporary:
            self.write_policy(policy)
            (root / "plain").write_text("ok", encoding="utf-8")
            with mock.patch("labos.benchmarks.leakage_scan.os.read", side_effect=OSError(PATH_SECRET)):
                report = self.scan(repo, policy, self.root(root))
            self.assertIn("file_read_error", [item.code for item in report.findings])

    def test_nested_directory_symlink_substitution_discards_external_entries(self) -> None:
        temporary, repo, policy, root = self.make_layout()
        with temporary:
            self.write_policy(policy)
            nested = root / "nested"
            nested.mkdir()
            (root / "sibling.txt").write_text("safe", encoding="utf-8")
            external = Path(temporary.name) / "external"
            external.mkdir()
            external_child = external / (SECRET + "-external.txt")
            external_child.write_text(SECRET, encoding="utf-8")
            real_scandir = os.scandir
            substituted = False

            def replace_before_nested_enumeration(path: os.PathLike[str] | str | int):
                nonlocal substituted
                if isinstance(path, int):
                    return real_scandir(path)
                if Path(path) == nested and not substituted:
                    substituted = True
                    shutil.rmtree(nested)
                    try:
                        nested.symlink_to(external, target_is_directory=True)
                    except (OSError, NotImplementedError) as exc:
                        self.skipTest(f"symlink unavailable: {exc}")
                return real_scandir(path)

            with mock.patch(
                "labos.benchmarks.leakage_scan.os.scandir",
                side_effect=replace_before_nested_enumeration,
            ):
                report = self.scan(repo, policy, self.root(root))
            self.assertTrue(substituted)
            self.assertIn("unsafe_symlink", [item.code for item in report.findings])
            self.assertNotIn("content_match", [item.code for item in report.findings])
            self.assertEqual(report.entry_count, 2)
            self.assertEqual(report.decoded_file_count, 1)
            self.assertEqual(report.scanned_byte_count, len(b"safe"))
            self.assertNotIn(
                hashlib.sha256(("ROOT-0001\0nested/" + external_child.name).encode()).hexdigest(),
                [item.path_sha256 for item in report.findings],
            )

    def test_root_symlink_substitution_is_a_safe_operational_failure(self) -> None:
        temporary, repo, policy, root = self.make_layout()
        with temporary:
            self.write_policy(policy)
            external = Path(temporary.name) / "external"
            external.mkdir()
            (external / "target.txt").write_text(SECRET, encoding="utf-8")
            real_scandir = os.scandir
            substituted = False

            def replace_before_root_enumeration(path: os.PathLike[str] | str | int):
                nonlocal substituted
                if isinstance(path, int):
                    return real_scandir(path)
                if Path(path) == root and not substituted:
                    substituted = True
                    shutil.rmtree(root)
                    try:
                        root.symlink_to(external, target_is_directory=True)
                    except (OSError, NotImplementedError) as exc:
                        self.skipTest(f"symlink unavailable: {exc}")
                return real_scandir(path)

            with mock.patch(
                "labos.benchmarks.leakage_scan.os.scandir",
                side_effect=replace_before_root_enumeration,
            ), mock.patch("labos.benchmarks.leakage_scan._add_content_matches") as content_matches:
                with self.assertRaises(ValueError) as context:
                    self.scan(repo, policy, self.root(root))
            self.assertTrue(substituted)
            self.assertEqual(content_matches.call_count, 0)
            self.assertNotIn(str(root), str(context.exception))
            self.assertNotIn(str(external), str(context.exception))
            self.assertNotIn(SECRET, str(context.exception))

            root.unlink()
            root.mkdir()
            substituted = False
            from scripts import labos_benchmark

            stream = io.StringIO()
            with mock.patch(
                "labos.benchmarks.leakage_scan.os.scandir",
                side_effect=replace_before_root_enumeration,
            ), redirect_stderr(stream):
                exit_code = labos_benchmark.main(
                    [
                        "scan-private-leakage",
                        "--repo-root",
                        str(repo),
                        "--policy-root",
                        str(policy),
                        "--scan-root",
                        "ROOT-0001=" + str(root),
                    ]
                )
            self.assertTrue(substituted)
            self.assertEqual(exit_code, 2)
            self.assertNotIn(str(root), stream.getvalue())
            self.assertNotIn(str(external), stream.getvalue())
            self.assertNotIn(SECRET, stream.getvalue())

    def test_zero_size_metadata_with_readable_bytes_fails_closed(self) -> None:
        temporary, repo, policy, root = self.make_layout()
        with temporary:
            self.write_policy(policy)
            target = root / "empty.txt"
            target.write_bytes(b"")
            real_read = os.read
            calls = 0

            def readable_zero_size(descriptor: int, size: int) -> bytes:
                nonlocal calls
                calls += 1
                return SECRET.encode("utf-8") if calls == 1 else real_read(descriptor, size)

            with mock.patch("labos.benchmarks.leakage_scan.os.read", side_effect=readable_zero_size):
                report = self.scan(repo, policy, self.root(root))
            self.assertGreaterEqual(calls, 1)
            self.assertEqual(report.status, "fail")
            self.assertIn("entry_inspection_error", [item.code for item in report.findings])
            self.assertNotIn("content_match", [item.code for item in report.findings])
            self.assertEqual(report.scanned_byte_count, 0)
            self.assert_no_secret(serialize_leakage_audit_report(report), root, policy, repo)

    def test_same_size_in_place_mutation_fails_closed(self) -> None:
        temporary, repo, policy, root = self.make_layout()
        with temporary:
            self.write_policy(policy)
            target = root / "mutable.txt"
            target.write_text("x" * len(SECRET), encoding="utf-8")
            real_read = os.read
            mutated = False

            def mutate_after_read(descriptor: int, size: int) -> bytes:
                nonlocal mutated
                data = real_read(descriptor, size)
                if not mutated:
                    mutated = True
                    target.write_text(SECRET, encoding="utf-8")
                    timestamp = time.time_ns() + 2_000_000_000
                    os.utime(target, ns=(timestamp, timestamp))
                return data

            with mock.patch("labos.benchmarks.leakage_scan.os.read", side_effect=mutate_after_read):
                report = self.scan(repo, policy, self.root(root))
            self.assertTrue(mutated)
            self.assertIn("entry_inspection_error", [item.code for item in report.findings])
            self.assertNotIn("content_match", [item.code for item in report.findings])
            self.assertEqual(report.scanned_byte_count, 0)
            self.assert_no_secret(serialize_leakage_audit_report(report), root, policy, repo)

    def test_special_file_is_structural_when_supported(self) -> None:
        if not hasattr(os, "mkfifo"):
            self.skipTest("FIFO unavailable")
        temporary, repo, policy, root = self.make_layout()
        with temporary:
            self.write_policy(policy)
            fifo = root / "pipe"
            try:
                os.mkfifo(fifo)
            except OSError as exc:
                self.skipTest(f"FIFO unavailable: {exc}")
            report = self.scan(repo, policy, self.root(root))
            self.assertIn("unsafe_special_file", [item.code for item in report.findings])

    def test_serialization_is_deterministic_and_public_safe(self) -> None:
        temporary, repo, policy, root = self.make_layout()
        with temporary:
            self.write_policy(policy)
            secret_path = root / (PATH_SECRET + "-" + SECRET); secret_path.write_text(SECRET, encoding="utf-8")
            report = self.scan(repo, policy, self.root(root))
            data = serialize_leakage_audit_report(report)
            self.assertEqual(data, serialize_leakage_audit_report(report))
            self.assertTrue(data.endswith(b"\n"))
            self.assertFalse(data.endswith(b"\n\n"))
            self.assert_no_secret(data, root, policy, repo)
            self.assertEqual(parse_leakage_audit_report_bytes(data), report)

    def test_parser_rejects_invalid_and_secret_bearing_payloads_safely(self) -> None:
        values = [b"\xff", b"{", b'{"report_version":"1.0","report_version":"1.0"}']
        for data in values:
            with self.subTest(data=data):
                with self.assertRaises(ValueError) as context:
                    parse_leakage_audit_report_bytes(data)
                self.assertNotIn(SECRET, str(context.exception))
        report = self._valid_report()
        payload = json.loads(serialize_leakage_audit_report(report))
        payload["finding_count"] = True
        with self.assertRaises(ValueError):
            parse_leakage_audit_report_bytes(json.dumps(payload).encode())

    def test_parser_rejects_invalid_finding_contracts(self) -> None:
        report = self._valid_report()
        payload = json.loads(serialize_leakage_audit_report(report))
        payload["findings"][0]["token_id"] = None
        with self.assertRaises(ValueError):
            parse_leakage_audit_report_bytes(json.dumps(payload).encode())
        payload = json.loads(serialize_leakage_audit_report(report))
        payload["findings"].append(payload["findings"][0])
        payload["finding_count"] = 2
        with self.assertRaises(ValueError):
            parse_leakage_audit_report_bytes(json.dumps(payload).encode())

    def test_cli_exit_codes_json_and_safe_output(self) -> None:
        temporary, repo, policy, root = self.make_layout()
        with temporary:
            self.write_policy(policy)
            clean = self.run_cli("scan-private-leakage", "--repo-root", str(repo), "--policy-root", str(policy), "--scan-root", "ROOT-0001=" + str(root), "--json")
            self.assertEqual(clean.returncode, 0)
            self.assertEqual(set(json.loads(clean.stdout)), {"decoded_file_count", "entry_count", "finding_count", "findings", "policy_byte_length", "policy_sha256", "policy_token_count", "policy_version", "regular_file_count", "report_version", "root_count", "scanned_byte_count", "status"})
            (root / "plain").write_text(SECRET, encoding="utf-8")
            finding = self.run_cli("scan-private-leakage", "--repo-root", str(repo), "--policy-root", str(policy), "--scan-root", "ROOT-0001=" + str(root))
            self.assertEqual(finding.returncode, 1)
            self.assert_no_secret(finding.stdout + finding.stderr, root, policy, repo)
            malformed = self.run_cli("scan-private-leakage", "--repo-root", str(repo), "--policy-root", str(policy), "--scan-root", "bad=" + PATH_SECRET)
            self.assertEqual(malformed.returncode, 2)
            self.assert_no_secret(malformed.stdout + malformed.stderr, root, policy, repo)

    def test_cli_invalid_policy_and_overlap_return_two(self) -> None:
        temporary, repo, policy, root = self.make_layout()
        with temporary:
            (policy / PRIVATE_LEAKAGE_POLICY_FILENAME).write_bytes(b"{")
            result = self.run_cli("scan-private-leakage", "--repo-root", str(repo), "--policy-root", str(policy), "--scan-root", "ROOT-0001=" + str(root))
            self.assertEqual(result.returncode, 2)
            self.assert_no_secret(result.stdout + result.stderr, root, policy, repo)
            self.write_policy(root)
            result = self.run_cli("scan-private-leakage", "--repo-root", str(repo), "--policy-root", str(root), "--scan-root", "ROOT-0001=" + str(root))
            self.assertEqual(result.returncode, 2)

    def test_operational_runtime_error_is_safe_at_cli_boundary(self) -> None:
        from scripts import labos_benchmark

        stream = io.StringIO()
        with mock.patch(
            "labos.benchmarks.leakage_scan._validate_scan_roots",
            side_effect=RuntimeError(PATH_SECRET),
        ), redirect_stderr(stream):
            result = labos_benchmark.main(
                [
                    "scan-private-leakage",
                    "--repo-root",
                    PATH_SECRET,
                    "--policy-root",
                    PATH_SECRET,
                    "--scan-root",
                    "ROOT-0001=" + PATH_SECRET,
                ]
            )
        self.assertEqual(result, 2)
        self.assertNotIn(PATH_SECRET, stream.getvalue())

    def test_existing_cli_commands_remain_available(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn(b"validate-private-leakage-policy", result.stdout)
        self.assertIn(b"scan-private-leakage", result.stdout)

    def _valid_report(self) -> LeakageAuditReport:
        finding = LeakageAuditFinding("content_match", "ROOT-0001", "0" * 64, "LKG-0001", "source_identity", "literal", 1)
        return LeakageAuditReport("1.0", "fail", "1.0", "1" * 64, 1, 1, 1, 1, 1, 1, 1, 1, (finding,))


def _add_generated_test(name: str, body) -> None:
    setattr(LeakageScanTest, name, body)


def _parser_mutation_test(mutator):
    def test(self: LeakageScanTest) -> None:
        payload = json.loads(serialize_leakage_audit_report(self._valid_report()))
        mutator(payload)
        with self.assertRaises(ValueError) as context:
            parse_leakage_audit_report_bytes(json.dumps(payload).encode("utf-8"))
        self.assertNotIn(SECRET, str(context.exception))
        self.assertNotIn(PATH_SECRET, str(context.exception))
    return test


for _key in (
    "decoded_file_count", "entry_count", "finding_count", "findings",
    "policy_byte_length", "policy_sha256", "policy_token_count",
    "policy_version", "regular_file_count", "report_version", "root_count",
    "scanned_byte_count", "status",
):
    _add_generated_test(
        "test_parser_rejects_missing_" + _key,
        _parser_mutation_test(lambda payload, key=_key: payload.pop(key)),
    )

for _key in (
    "policy_byte_length", "policy_token_count", "root_count", "entry_count",
    "regular_file_count", "decoded_file_count", "scanned_byte_count", "finding_count",
):
    _add_generated_test(
        "test_parser_rejects_boolean_" + _key,
        _parser_mutation_test(lambda payload, key=_key: payload.__setitem__(key, True)),
    )
    _add_generated_test(
        "test_parser_rejects_negative_" + _key,
        _parser_mutation_test(lambda payload, key=_key: payload.__setitem__(key, -1)),
    )

for _key in ("report_version", "status", "policy_version", "policy_sha256"):
    _add_generated_test(
        "test_parser_rejects_nonstring_" + _key,
        _parser_mutation_test(lambda payload, key=_key: payload.__setitem__(key, 1)),
    )

for _key in ("category", "code", "match_mode", "occurrence_count", "path_sha256", "root_id", "token_id"):
    _add_generated_test(
        "test_parser_rejects_missing_finding_" + _key,
        _parser_mutation_test(lambda payload, key=_key: payload["findings"][0].pop(key)),
    )

_PARSER_CASES = {
    "extra_top_level": lambda p: p.__setitem__("extra", 1),
    "extra_finding": lambda p: p["findings"][0].__setitem__("extra", 1),
    "bad_report_version": lambda p: p.__setitem__("report_version", "2.0"),
    "bad_policy_version": lambda p: p.__setitem__("policy_version", "2.0"),
    "bad_status": lambda p: p.__setitem__("status", "unknown"),
    "bad_sha": lambda p: p.__setitem__("policy_sha256", "X" * 64),
    "bad_finding_code": lambda p: p["findings"][0].__setitem__("code", "unknown"),
    "bad_root": lambda p: p["findings"][0].__setitem__("root_id", "bad"),
    "bad_path_sha": lambda p: p["findings"][0].__setitem__("path_sha256", "0"),
    "bad_token": lambda p: p["findings"][0].__setitem__("token_id", "bad"),
    "bad_category": lambda p: p["findings"][0].__setitem__("category", "bad"),
    "bad_match_mode": lambda p: p["findings"][0].__setitem__("match_mode", "bad"),
    "zero_occurrences": lambda p: p["findings"][0].__setitem__("occurrence_count", 0),
    "structural_has_token": lambda p: (p["findings"][0].__setitem__("code", "non_utf8_file"), p["findings"][0].__setitem__("token_id", None)),
    "pass_with_findings": lambda p: p.__setitem__("status", "pass"),
    "wrong_finding_count": lambda p: p.__setitem__("finding_count", 2),
}
for _name, _mutator in _PARSER_CASES.items():
    _add_generated_test("test_parser_rejects_" + _name, _parser_mutation_test(_mutator))


def _round_trip_test(index: int):
    def test(self: LeakageScanTest) -> None:
        root_id = f"ROOT-{index:04d}"
        finding = LeakageAuditFinding("content_match", root_id, f"{index:064x}", "LKG-0001", "source_identity", "literal", index + 1)
        report = LeakageAuditReport("1.0", "fail", "1.0", "1" * 64, index, 1, 1, index, 1, 1, index, 1, (finding,))
        data = serialize_leakage_audit_report(report)
        self.assertEqual(parse_leakage_audit_report_bytes(data), report)
    return test


for _index in range(1, 48):
    _add_generated_test(f"test_report_round_trip_identity_{_index:02d}", _round_trip_test(_index))


def _root_identity_test(index: int):
    def test(self: LeakageScanTest) -> None:
        temporary, repo, policy, root = self.make_layout()
        with temporary:
            self.write_policy(policy)
            path = root / ("x-" + SECRET)
            path.write_text("clean", encoding="utf-8")
            root_id = f"ROOT-{index:04d}"
            report = self.scan(repo, policy, self.root(root, root_id))
            finding = next(item for item in report.findings if item.code == "path_match")
            self.assertEqual(finding.path_sha256, hashlib.sha256((root_id + "\0" + path.name).encode()).hexdigest())
    return test


for _index in range(1, 8):
    _add_generated_test(f"test_root_identity_is_deterministic_{_index:02d}", _root_identity_test(_index))


def _duplicate_finding_test(self: LeakageScanTest) -> None:
    payload = json.loads(serialize_leakage_audit_report(self._valid_report()))
    payload["findings"].append(dict(payload["findings"][0]))
    payload["finding_count"] = 2
    with self.assertRaises(ValueError):
        parse_leakage_audit_report_bytes(json.dumps(payload).encode("utf-8"))


_add_generated_test("test_parser_rejects_duplicate_canonical_finding_generated", _duplicate_finding_test)


if __name__ == "__main__":
    unittest.main()
