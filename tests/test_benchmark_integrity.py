from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from labos.benchmarks.integrity import (
    TREE_HASH_ALGORITHM,
    analyze_newlines,
    digest_file,
    digest_git_blob,
    digest_tree,
    normalized_lf_sha256,
    sha256_bytes,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = "docs/benchmarks/M15B_PRE_REGISTRATION_PROTOCOL.md"
PROTOCOL_MERGE_COMMIT = "e35476d5fe4ccfa94f8438a7ef1fbf569fd67aa2"
PROTOCOL_BLOB_OID = "0c142382d7f94a1cfcc19f065d21cb61fe1f5c3e"
PROTOCOL_SHA256 = "4c5a5c09fb0822f70c87fff9f6a5162bd318d72da18cd4909d60a0b0f8a4e9b5"


class BenchmarkIntegrityHashTests(unittest.TestCase):
    def test_exact_file_digest_hashes_raw_bytes_without_normalization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.txt"
            data = b"alpha\r\nbeta\n"
            path.write_bytes(data)
            digest = digest_file(path)
            self.assertEqual(digest.sha256, hashlib.sha256(data).hexdigest())
            self.assertEqual(digest.byte_length, len(data))

    def test_lf_and_crlf_files_have_different_exact_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lf = root / "lf.txt"
            crlf = root / "crlf.txt"
            lf.write_bytes(b"same\ntext\n")
            crlf.write_bytes(b"same\r\ntext\r\n")
            self.assertNotEqual(digest_file(lf).sha256, digest_file(crlf).sha256)

    def test_normalized_lf_hashes_match_for_lf_and_crlf_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lf = root / "lf.txt"
            crlf = root / "crlf.txt"
            lf.write_bytes(b"same\ntext\n")
            crlf.write_bytes(b"same\r\ntext\r\n")
            self.assertEqual(normalized_lf_sha256(lf), normalized_lf_sha256(crlf))

    def test_normalized_hashing_rejects_invalid_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.txt"
            path.write_bytes(b"\xff")
            with self.assertRaises(UnicodeDecodeError):
                normalized_lf_sha256(path)

    def test_newline_metadata_distinguishes_crlf_lf_and_bare_cr(self) -> None:
        metadata = analyze_newlines(b"a\r\nb\nc\rd")
        self.assertEqual(metadata.crlf_count, 1)
        self.assertEqual(metadata.lf_count, 2)
        self.assertEqual(metadata.bare_cr_count, 1)

    def test_bom_and_final_newline_metadata_are_correct(self) -> None:
        metadata = analyze_newlines(b"\xef\xbb\xbfhello\n")
        self.assertTrue(metadata.utf8_bom)
        self.assertTrue(metadata.final_newline)
        self.assertFalse(analyze_newlines(b"hello").final_newline)


class BenchmarkIntegrityGitBlobTests(unittest.TestCase):
    def test_protocol_git_blob_identity_matches_record(self) -> None:
        digest = digest_git_blob(REPO_ROOT, PROTOCOL_MERGE_COMMIT, PROTOCOL_PATH)
        self.assertEqual(digest.git_blob_oid, PROTOCOL_BLOB_OID)

    def test_protocol_git_blob_hash_matches_record(self) -> None:
        digest = digest_git_blob(REPO_ROOT, PROTOCOL_MERGE_COMMIT, PROTOCOL_PATH)
        self.assertEqual(digest.sha256, PROTOCOL_SHA256)

    def test_protocol_git_blob_length_and_newlines_match_record(self) -> None:
        digest = digest_git_blob(REPO_ROOT, PROTOCOL_MERGE_COMMIT, PROTOCOL_PATH)
        self.assertEqual(digest.byte_length, 34793)
        self.assertEqual(digest.newline.lf_count, 1100)
        self.assertEqual(digest.newline.crlf_count, 0)
        self.assertEqual(digest.newline.bare_cr_count, 0)
        self.assertFalse(digest.newline.utf8_bom)
        self.assertTrue(digest.newline.final_newline)

    def test_invalid_ref_fails_clearly(self) -> None:
        with self.assertRaises(ValueError):
            digest_git_blob(REPO_ROOT, "not-a-real-ref", PROTOCOL_PATH)

    def test_traversal_and_absolute_git_paths_are_rejected(self) -> None:
        for bad_path in ("../README.md", "/README.md", r"C:\temp\file.txt", "a//b"):
            with self.subTest(bad_path=bad_path):
                with self.assertRaises(ValueError):
                    digest_git_blob(REPO_ROOT, "HEAD", bad_path)


class BenchmarkIntegrityTreeTests(unittest.TestCase):
    def test_tree_hash_is_independent_of_file_creation_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_a, tempfile.TemporaryDirectory() as tmp_b:
            root_a = Path(tmp_a)
            root_b = Path(tmp_b)
            (root_a / "b.txt").write_bytes(b"b")
            (root_a / "a.txt").write_bytes(b"a")
            (root_b / "a.txt").write_bytes(b"a")
            (root_b / "b.txt").write_bytes(b"b")
            self.assertEqual(digest_tree(root_a).sha256, digest_tree(root_b).sha256)

    def test_changing_file_bytes_changes_tree_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "a.txt"
            path.write_bytes(b"a")
            before = digest_tree(root).sha256
            path.write_bytes(b"b")
            self.assertNotEqual(before, digest_tree(root).sha256)

    def test_renaming_file_changes_tree_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "a.txt"
            path.write_bytes(b"a")
            before = digest_tree(root).sha256
            path.rename(root / "b.txt")
            self.assertNotEqual(before, digest_tree(root).sha256)

    def test_overlapping_include_paths_do_not_duplicate_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sub").mkdir()
            (root / "sub" / "a.txt").write_bytes(b"a")
            digest = digest_tree(root, include_paths=["sub", "sub/a.txt"])
            self.assertEqual([file.path for file in digest.files], ["sub/a.txt"])

    def test_exclusions_apply_recursively(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "keep").mkdir()
            (root / "skip").mkdir()
            (root / "keep" / "a.txt").write_bytes(b"a")
            (root / "skip" / "b.txt").write_bytes(b"b")
            digest = digest_tree(root, exclude_paths=["skip"])
            self.assertEqual([file.path for file in digest.files], ["keep/a.txt"])

    def test_ignored_directory_names_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "__pycache__").mkdir()
            (root / "__pycache__" / "a.pyc").write_bytes(b"a")
            (root / "b.py").write_bytes(b"b")
            digest = digest_tree(root, ignored_directory_names=["__pycache__"])
            self.assertEqual([file.path for file in digest.files], ["b.py"])

    def test_ignored_suffixes_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.pyc").write_bytes(b"a")
            (root / "b.py").write_bytes(b"b")
            digest = digest_tree(root, ignored_file_suffixes=[".pyc"])
            self.assertEqual([file.path for file in digest.files], ["b.py"])

    def test_output_paths_always_use_posix_separator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "nested").mkdir()
            (root / "nested" / "a.txt").write_bytes(b"a")
            digest = digest_tree(root)
            self.assertEqual(digest.files[0].path, "nested/a.txt")

    def test_traversal_and_absolute_include_paths_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for bad_path in ("../x", "/x", r"C:\x"):
                with self.subTest(bad_path=bad_path):
                    with self.assertRaises(ValueError):
                        digest_tree(root, include_paths=[bad_path])

    def test_nonexistent_explicit_include_path_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                digest_tree(Path(tmp), include_paths=["missing.txt"])

    def test_symlink_input_is_rejected_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target.txt"
            target.write_bytes(b"target")
            link = root / "link.txt"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink not available: {exc}")
            with self.assertRaises(ValueError):
                digest_tree(root)


class BenchmarkIntegrityRecordTests(unittest.TestCase):
    def test_protocol_record_has_exact_approved_key_set(self) -> None:
        record = json.loads((REPO_ROOT / "docs/benchmarks/M15B_PROTOCOL_INTEGRITY_RECORD.json").read_text())
        self.assertEqual(
            set(record),
            {
                "artifact_kind",
                "bare_cr_count",
                "byte_length",
                "content_sha256",
                "crlf_count",
                "final_newline",
                "git_blob_oid",
                "lf_count",
                "path",
                "protocol_merge_commit",
                "record_version",
                "utf8_bom",
            },
        )

    def test_protocol_record_serialization_has_one_final_newline(self) -> None:
        data = (REPO_ROOT / "docs/benchmarks/M15B_PROTOCOL_INTEGRITY_RECORD.json").read_bytes()
        self.assertTrue(data.endswith(b"\n"))
        self.assertFalse(data.endswith(b"\n\n"))

    def test_current_protocol_working_tree_bytes_match_record(self) -> None:
        data = (REPO_ROOT / PROTOCOL_PATH).read_bytes()
        self.assertEqual(sha256_bytes(data), PROTOCOL_SHA256)

    def test_raw_git_object_bytes_at_merge_commit_match_record(self) -> None:
        digest = digest_git_blob(REPO_ROOT, PROTOCOL_MERGE_COMMIT, PROTOCOL_PATH)
        self.assertEqual(digest.git_blob_oid, PROTOCOL_BLOB_OID)
        self.assertEqual(digest.sha256, PROTOCOL_SHA256)

    def test_record_contains_no_superseded_hash_prefix(self) -> None:
        text = (REPO_ROOT / "docs/benchmarks/M15B_PROTOCOL_INTEGRITY_RECORD.json").read_text()
        self.assertNotIn("aeaf" + "80", text)


class BenchmarkIntegrityCliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "scripts/labos_benchmark.py", *args],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_hash_file_json_is_deterministic(self) -> None:
        args = ("hash-file", PROTOCOL_PATH, "--json")
        first = self.run_cli(*args)
        second = self.run_cli(*args)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        result = json.loads(first.stdout)
        self.assertEqual(result["mode"], "exact_bytes")
        self.assertEqual(result["sha256"], PROTOCOL_SHA256)

    def test_hash_file_normalized_lf_json_identifies_diagnostic_mode(self) -> None:
        result = self.run_cli("hash-file", PROTOCOL_PATH, "--normalized-lf", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["mode"], "normalized_lf_diagnostic")

    def test_hash_git_object_json_reports_approved_protocol_identity(self) -> None:
        result = self.run_cli(
            "hash-git-object",
            "--repo-root",
            ".",
            "--ref",
            PROTOCOL_MERGE_COMMIT,
            "--path",
            PROTOCOL_PATH,
            "--json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["git_blob_oid"], PROTOCOL_BLOB_OID)
        self.assertEqual(payload["sha256"], PROTOCOL_SHA256)

    def test_hash_tree_json_is_deterministic(self) -> None:
        first = self.run_cli("hash-tree", "labos/benchmarks", "--json")
        second = self.run_cli("hash-tree", "labos/benchmarks", "--json")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(json.loads(first.stdout)["algorithm"], TREE_HASH_ALGORITHM)

    def test_invalid_cli_path_returns_exit_code_2(self) -> None:
        result = self.run_cli("hash-file", "missing-file.txt", "--json")
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
