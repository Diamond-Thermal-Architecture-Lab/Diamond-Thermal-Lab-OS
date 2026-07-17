from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from labos.benchmarks.sealed_manifest import (
    M15B_SEALED_FILENAMES,
    SealedArtifactRecord,
    SealedManifest,
    build_sealed_manifest,
    find_sealed_presence,
    load_sealed_manifest,
    parse_sealed_manifest_bytes,
    serialize_sealed_manifest,
    verify_sealed_manifest,
    write_new_sealed_manifest,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
TIMESTAMP = "2026-07-17T04:30:00Z"


class SealedManifestTests(unittest.TestCase):
    def make_roots(self) -> tuple[tempfile.TemporaryDirectory[str], Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        base = Path(temporary.name)
        repo = base / "repo"
        sealed = base / "sealed"
        repo.mkdir()
        sealed.mkdir()
        return temporary, repo, sealed

    def write_artifact(self, sealed: Path, name: str = "one.md", data: bytes = b"sealed\r\nbytes\n") -> Path:
        path = sealed / name
        path.write_bytes(data)
        return path

    def build_one(self, repo: Path, sealed: Path, name: str = "one.md") -> SealedManifest:
        return build_sealed_manifest(
            repo_root=repo,
            sealed_root=sealed,
            artifact_filenames=[name],
            protocol_version="1.0",
            registered_at_utc=TIMESTAMP,
        )

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "scripts/labos_benchmark.py", *args],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_exact_artifact_bytes_determine_length_and_sha256(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            data = b"a\r\nb\n"
            self.write_artifact(sealed, data=data)
            manifest = self.build_one(repo, sealed)
            self.assertEqual(manifest.sealed_artifacts[0].byte_length, len(data))
            self.assertEqual(manifest.sealed_artifacts[0].sha256, hashlib.sha256(data).hexdigest())

    def test_crlf_and_lf_artifacts_have_different_exact_hashes(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            self.write_artifact(sealed, "lf.md", b"x\ny\n")
            self.write_artifact(sealed, "crlf.md", b"x\r\ny\r\n")
            manifest = build_sealed_manifest(repo_root=repo, sealed_root=sealed, artifact_filenames=["lf.md", "crlf.md"], protocol_version="1.0", registered_at_utc=TIMESTAMP)
            self.assertNotEqual(manifest.sealed_artifacts[0].sha256, manifest.sealed_artifacts[1].sha256)

    def test_artifact_records_are_sorted_deterministically(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            self.write_artifact(sealed, "z.md")
            self.write_artifact(sealed, "a.md")
            manifest = build_sealed_manifest(repo_root=repo, sealed_root=sealed, artifact_filenames=["z.md", "a.md"], protocol_version="1.0", registered_at_utc=TIMESTAMP)
            self.assertEqual([record.filename for record in manifest.sealed_artifacts], ["a.md", "z.md"])

    def test_input_filename_order_does_not_affect_serialized_output(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            self.write_artifact(sealed, "a.md")
            self.write_artifact(sealed, "b.md")
            first = build_sealed_manifest(repo_root=repo, sealed_root=sealed, artifact_filenames=["b.md", "a.md"], protocol_version="1.0", registered_at_utc=TIMESTAMP)
            second = build_sealed_manifest(repo_root=repo, sealed_root=sealed, artifact_filenames=["a.md", "b.md"], protocol_version="1.0", registered_at_utc=TIMESTAMP)
            self.assertEqual(serialize_sealed_manifest(first), serialize_sealed_manifest(second))

    def test_protocol_version_and_timestamp_are_preserved(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            self.write_artifact(sealed)
            manifest = self.build_one(repo, sealed)
            self.assertEqual((manifest.protocol_version, manifest.registered_at_utc), ("1.0", TIMESTAMP))

    def test_source_text_does_not_appear_in_serialized_manifest(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            source = b"synthetic private body"
            self.write_artifact(sealed, data=source)
            self.assertNotIn(source, serialize_sealed_manifest(self.build_one(repo, sealed)))

    def test_m15b_filenames_produce_exact_required_set(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            for name in M15B_SEALED_FILENAMES:
                self.write_artifact(sealed, name)
            manifest = build_sealed_manifest(repo_root=repo, sealed_root=sealed, artifact_filenames=reversed(M15B_SEALED_FILENAMES), protocol_version="1.0", registered_at_utc=TIMESTAMP)
            self.assertEqual({record.filename for record in manifest.sealed_artifacts}, set(M15B_SEALED_FILENAMES))

    def test_m15b_filenames_have_exact_lexicographic_tuple_order(self) -> None:
        self.assertEqual(
            M15B_SEALED_FILENAMES,
            (
                "RELEVANCE_REGISTRATION.md",
                "SCOPE_REGISTRATION.md",
                "SCORING_REGISTRATION.md",
                "SOURCE_DOSSIER.md",
            ),
        )
        self.assertEqual(M15B_SEALED_FILENAMES, tuple(sorted(M15B_SEALED_FILENAMES)))

    def test_manifest_parse_accepts_exact_m15b_expected_filename_set(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            for name in M15B_SEALED_FILENAMES:
                self.write_artifact(sealed, name)
            manifest = build_sealed_manifest(repo_root=repo, sealed_root=sealed, artifact_filenames=M15B_SEALED_FILENAMES, protocol_version="1.0", registered_at_utc=TIMESTAMP)
            self.assertEqual(parse_sealed_manifest_bytes(serialize_sealed_manifest(manifest), expected_filenames=M15B_SEALED_FILENAMES), manifest)

    def test_unsafe_filename_forms_are_rejected(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            for filename in ("nested/x.md", r"nested\\x.md", "../x.md", ".", "C:drive.md"):
                with self.subTest(filename=filename):
                    with self.assertRaises(ValueError):
                        build_sealed_manifest(repo_root=repo, sealed_root=sealed, artifact_filenames=[filename], protocol_version="1.0", registered_at_utc=TIMESTAMP)

    def test_sealed_root_inside_repository_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            sealed = repo / "sealed"
            sealed.mkdir(parents=True)
            self.write_artifact(sealed)
            with self.assertRaises(ValueError): self.build_one(repo, sealed)

    def test_repository_inside_sealed_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sealed = Path(tmp) / "sealed"
            repo = sealed / "repo"
            repo.mkdir(parents=True)
            self.write_artifact(sealed)
            with self.assertRaises(ValueError): self.build_one(repo, sealed)

    def test_additional_forbidden_root_overlap_is_rejected(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            self.write_artifact(sealed)
            with self.assertRaises(ValueError):
                build_sealed_manifest(repo_root=repo, sealed_root=sealed, artifact_filenames=["one.md"], protocol_version="1.0", registered_at_utc=TIMESTAMP, additional_forbidden_roots=[sealed.parent])

    def test_forbidden_root_symlink_is_rejected_when_supported(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            self.write_artifact(sealed)
            forbidden = repo.parent / "forbidden"; forbidden.mkdir()
            link = repo.parent / "forbidden-link"
            try: link.symlink_to(forbidden, target_is_directory=True)
            except (OSError, NotImplementedError) as exc: self.skipTest(f"symlink unavailable: {exc}")
            with self.assertRaises(ValueError):
                build_sealed_manifest(repo_root=repo, sealed_root=sealed, artifact_filenames=["one.md"], protocol_version="1.0", registered_at_utc=TIMESTAMP, additional_forbidden_roots=[link])

    def test_sealed_root_symlink_is_rejected_when_supported(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            link = sealed.parent / "sealed-link"
            try: link.symlink_to(sealed, target_is_directory=True)
            except (OSError, NotImplementedError) as exc: self.skipTest(f"symlink unavailable: {exc}")
            self.write_artifact(sealed)
            with self.assertRaises(ValueError): self.build_one(repo, link)

    def test_artifact_symlink_is_rejected_when_supported(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            target = sealed / "target.md"; target.write_bytes(b"x")
            try: (sealed / "one.md").symlink_to(target)
            except (OSError, NotImplementedError) as exc: self.skipTest(f"symlink unavailable: {exc}")
            with self.assertRaises(ValueError): self.build_one(repo, sealed)

    def test_broken_artifact_symlink_is_rejected_when_supported(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            try: (sealed / "one.md").symlink_to(sealed / "missing.md")
            except (OSError, NotImplementedError) as exc: self.skipTest(f"symlink unavailable: {exc}")
            with self.assertRaises(ValueError): self.build_one(repo, sealed)

    def test_nested_artifact_path_is_rejected(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            with self.assertRaises(ValueError):
                build_sealed_manifest(repo_root=repo, sealed_root=sealed, artifact_filenames=["nested/one.md"], protocol_version="1.0", registered_at_utc=TIMESTAMP)

    def test_missing_artifact_is_rejected(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            with self.assertRaises(ValueError): self.build_one(repo, sealed)

    def test_empty_artifact_is_rejected(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            self.write_artifact(sealed, data=b"")
            with self.assertRaises(ValueError): self.build_one(repo, sealed)

    def test_directory_artifact_is_rejected(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            (sealed / "one.md").mkdir()
            with self.assertRaises(ValueError): self.build_one(repo, sealed)

    def test_valid_manifest_round_trips(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            self.write_artifact(sealed)
            manifest = self.build_one(repo, sealed)
            self.assertEqual(parse_sealed_manifest_bytes(serialize_sealed_manifest(manifest)), manifest)

    def test_malformed_utf8_manifest_fails(self) -> None:
        with self.assertRaises(ValueError):
            parse_sealed_manifest_bytes(b"\xff")

    def malformed_manifest_fails(self, payload: str) -> None:
        with self.assertRaises(ValueError): parse_sealed_manifest_bytes(payload.encode("utf-8"))

    def test_unknown_top_level_field_fails(self) -> None:
        self.malformed_manifest_fails('{"manifest_version":"1.0","protocol_version":"1.0","registered_at_utc":"2026-07-17T04:30:00Z","sealed_artifacts":[],"extra":1}')

    def test_unknown_artifact_field_fails(self) -> None:
        self.malformed_manifest_fails('{"manifest_version":"1.0","protocol_version":"1.0","registered_at_utc":"2026-07-17T04:30:00Z","sealed_artifacts":[{"filename":"x.md","byte_length":1,"sha256":"' + 'a'*64 + '","extra":1}]}')

    def test_duplicate_top_level_json_key_fails(self) -> None:
        self.malformed_manifest_fails('{"manifest_version":"1.0","manifest_version":"1.0","protocol_version":"1.0","registered_at_utc":"2026-07-17T04:30:00Z","sealed_artifacts":[]}')

    def test_duplicate_nested_json_key_fails(self) -> None:
        self.malformed_manifest_fails('{"manifest_version":"1.0","protocol_version":"1.0","registered_at_utc":"2026-07-17T04:30:00Z","sealed_artifacts":[{"filename":"x.md","byte_length":1,"sha256":"' + 'a'*64 + '","sha256":"' + 'a'*64 + '"}]}')

    def test_duplicate_filename_fails(self) -> None:
        record = '{"filename":"x.md","byte_length":1,"sha256":"' + 'a'*64 + '"}'
        self.malformed_manifest_fails('{"manifest_version":"1.0","protocol_version":"1.0","registered_at_utc":"2026-07-17T04:30:00Z","sealed_artifacts":[' + record + ',' + record + ']}')

    def test_unsorted_artifacts_fail(self) -> None:
        record = lambda name: '{"filename":"' + name + '","byte_length":1,"sha256":"' + 'a'*64 + '"}'
        self.malformed_manifest_fails('{"manifest_version":"1.0","protocol_version":"1.0","registered_at_utc":"2026-07-17T04:30:00Z","sealed_artifacts":[' + record("z.md") + ',' + record("a.md") + ']}')

    def test_malformed_and_uppercase_sha256_fail(self) -> None:
        for value in ("a" * 63, "A" * 64):
            with self.subTest(value=value):
                self.malformed_manifest_fails('{"manifest_version":"1.0","protocol_version":"1.0","registered_at_utc":"2026-07-17T04:30:00Z","sealed_artifacts":[{"filename":"x.md","byte_length":1,"sha256":"' + value + '"}]}')

    def test_boolean_and_zero_byte_lengths_fail(self) -> None:
        for value in ("true", "0"):
            with self.subTest(value=value):
                self.malformed_manifest_fails('{"manifest_version":"1.0","protocol_version":"1.0","registered_at_utc":"2026-07-17T04:30:00Z","sealed_artifacts":[{"filename":"x.md","byte_length":' + value + ',"sha256":"' + 'a'*64 + '"}]}')

    def test_noncanonical_timestamps_fail(self) -> None:
        for timestamp in ("bad", "2026-07-17T04:30:00+00:00", "2026-07-17T04:30:00.1Z"):
            with self.subTest(timestamp=timestamp):
                self.malformed_manifest_fails('{"manifest_version":"1.0","protocol_version":"1.0","registered_at_utc":"' + timestamp + '","sealed_artifacts":[{"filename":"x.md","byte_length":1,"sha256":"' + 'a'*64 + '"}]}')

    def test_expected_filename_set_rejects_missing_and_extra(self) -> None:
        manifest = SealedManifest("1.0", "1.0", TIMESTAMP, (SealedArtifactRecord("x.md", 1, "a" * 64),))
        data = serialize_sealed_manifest(manifest)
        with self.assertRaises(ValueError): parse_sealed_manifest_bytes(data, expected_filenames=["y.md"])

    def test_output_symlink_is_rejected_when_supported(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            self.write_artifact(sealed); manifest = self.build_one(repo, sealed)
            target = repo / "target.json"; target.write_text("target")
            output = repo / "manifest.json"
            try: output.symlink_to(target)
            except (OSError, NotImplementedError) as exc: self.skipTest(f"symlink unavailable: {exc}")
            with self.assertRaises(ValueError): write_new_sealed_manifest(output, manifest, sealed_root=sealed)

    def test_existing_output_is_not_overwritten(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            self.write_artifact(sealed); manifest = self.build_one(repo, sealed)
            output = repo / "manifest.json"; output.write_bytes(b"existing")
            with self.assertRaises(ValueError): write_new_sealed_manifest(output, manifest, sealed_root=sealed)
            self.assertEqual(output.read_bytes(), b"existing")

    def test_exclusive_create_preserves_concurrent_output_after_stale_precheck(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            self.write_artifact(sealed)
            manifest = self.build_one(repo, sealed)
            output = repo / "manifest.json"
            original_open = Path.open

            def create_then_open(path: Path, mode: str = "r", *args: object, **kwargs: object):
                if path == output and mode == "xb" and not output.exists():
                    with open(output, "wb") as concurrent_output:
                        concurrent_output.write(b"concurrent creator bytes")
                return original_open(path, mode, *args, **kwargs)

            with mock.patch.object(Path, "open", new=create_then_open):
                with self.assertRaises(ValueError):
                    write_new_sealed_manifest(output, manifest, sealed_root=sealed)
            self.assertEqual(output.read_bytes(), b"concurrent creator bytes")

    def test_output_inside_sealed_root_is_rejected(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            self.write_artifact(sealed); manifest = self.build_one(repo, sealed)
            with self.assertRaises(ValueError): write_new_sealed_manifest(sealed / "manifest.json", manifest, sealed_root=sealed)

    def test_valid_output_is_canonical_and_has_one_final_newline(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            self.write_artifact(sealed); manifest = self.build_one(repo, sealed)
            output = repo / "manifest.json"; write_new_sealed_manifest(output, manifest, sealed_root=sealed)
            self.assertTrue(output.read_bytes().endswith(b"\n")); self.assertFalse(output.read_bytes().endswith(b"\n\n"))
            self.assertEqual(output.read_bytes(), serialize_sealed_manifest(manifest))
            self.assertEqual(list(repo.iterdir()), [output])

    def test_write_failure_removes_partial_output_created_by_this_invocation(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            artifact = self.write_artifact(sealed, data=b"sealed artifact bytes")
            manifest = self.build_one(repo, sealed)
            output = repo / "manifest.json"
            with mock.patch("labos.benchmarks.sealed_manifest.os.fsync", side_effect=OSError("simulated fsync failure")):
                with self.assertRaises(OSError):
                    write_new_sealed_manifest(output, manifest, sealed_root=sealed)
            self.assertFalse(output.exists())
            self.assertEqual(artifact.read_bytes(), b"sealed artifact bytes")
            self.assertEqual(list(sealed.iterdir()), [artifact])

    def test_unchanged_sealed_bytes_pass_verification(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            self.write_artifact(sealed); self.assertEqual(verify_sealed_manifest(self.build_one(repo, sealed), repo_root=repo, sealed_root=sealed), ())

    def test_modified_bytes_produce_sha_finding(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            self.write_artifact(sealed); manifest = self.build_one(repo, sealed); self.write_artifact(sealed, data=b"changed")
            self.assertIn("sha256_mismatch", [item.code for item in verify_sealed_manifest(manifest, repo_root=repo, sealed_root=sealed)])

    def test_byte_length_change_produces_length_finding(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            self.write_artifact(sealed); manifest = self.build_one(repo, sealed); self.write_artifact(sealed, data=b"longer bytes")
            self.assertIn("byte_length_mismatch", [item.code for item in verify_sealed_manifest(manifest, repo_root=repo, sealed_root=sealed)])

    def test_missing_artifact_is_found(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            artifact = self.write_artifact(sealed); manifest = self.build_one(repo, sealed); artifact.unlink()
            self.assertIn("missing_artifact", [item.code for item in verify_sealed_manifest(manifest, repo_root=repo, sealed_root=sealed)])

    def test_unexpected_artifact_is_found(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            self.write_artifact(sealed); manifest = self.build_one(repo, sealed); self.write_artifact(sealed, "extra.md")
            self.assertIn("unexpected_artifact", [item.code for item in verify_sealed_manifest(manifest, repo_root=repo, sealed_root=sealed)])

    def test_unsafe_artifact_type_is_found(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            self.write_artifact(sealed); manifest = self.build_one(repo, sealed); (sealed / "extra").mkdir()
            self.assertIn("unsafe_artifact_type", [item.code for item in verify_sealed_manifest(manifest, repo_root=repo, sealed_root=sealed)])

    def test_registered_artifact_symlink_is_unsafe_when_supported(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            artifact = self.write_artifact(sealed); manifest = self.build_one(repo, sealed); artifact.unlink()
            target = sealed / "target.md"; target.write_bytes(b"target")
            try: artifact.symlink_to(target)
            except (OSError, NotImplementedError) as exc: self.skipTest(f"symlink unavailable: {exc}")
            self.assertIn("unsafe_artifact_type", [item.code for item in verify_sealed_manifest(manifest, repo_root=repo, sealed_root=sealed)])

    def test_verification_finding_order_is_deterministic(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            self.write_artifact(sealed); manifest = self.build_one(repo, sealed); self.write_artifact(sealed, "z.md"); self.write_artifact(sealed, "a.md")
            self.assertEqual(verify_sealed_manifest(manifest, repo_root=repo, sealed_root=sealed), verify_sealed_manifest(manifest, repo_root=repo, sealed_root=sealed))

    def test_verification_findings_never_contain_artifact_contents(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            self.write_artifact(sealed, data=b"private-synthetic-content"); manifest = self.build_one(repo, sealed); self.write_artifact(sealed, data=b"changed")
            self.assertNotIn("private-synthetic-content", " ".join(item.detail for item in verify_sealed_manifest(manifest, repo_root=repo, sealed_root=sealed)))

    def test_forbidden_basename_is_found_recursively(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); nested = root / "nested"; nested.mkdir(); (nested / "RELEVANCE_REGISTRATION.md").write_bytes(b"x")
            findings = find_sealed_presence(roots=[root], forbidden_filenames=M15B_SEALED_FILENAMES)
            self.assertEqual(findings[0].code, "forbidden_filename_present")

    def test_unrelated_filenames_are_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / "ordinary.md").write_bytes(b"x")
            self.assertEqual(find_sealed_presence(roots=[root], forbidden_filenames=M15B_SEALED_FILENAMES), ())

    def test_symlink_is_reported_without_following_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"; root.mkdir(); target = root.parent / "target"; target.mkdir(); (target / "RELEVANCE_REGISTRATION.md").write_bytes(b"x")
            link = root / "link"
            try: link.symlink_to(target, target_is_directory=True)
            except (OSError, NotImplementedError) as exc: self.skipTest(f"symlink unavailable: {exc}")
            findings = find_sealed_presence(roots=[root], forbidden_filenames=M15B_SEALED_FILENAMES)
            self.assertEqual([item.code for item in findings], ["unsafe_symlink_present"])

    def test_ignored_directories_are_not_traversed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); ignored = root / "ignored"; ignored.mkdir(); (ignored / "RELEVANCE_REGISTRATION.md").write_bytes(b"x")
            self.assertEqual(find_sealed_presence(roots=[root], forbidden_filenames=M15B_SEALED_FILENAMES, ignored_directory_names=["ignored"]), ())

    def test_presence_root_symlink_is_rejected_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); target = root / "target"; target.mkdir(); link = root / "link"
            try: link.symlink_to(target, target_is_directory=True)
            except (OSError, NotImplementedError) as exc: self.skipTest(f"symlink unavailable: {exc}")
            with self.assertRaises(ValueError): find_sealed_presence(roots=[link], forbidden_filenames=M15B_SEALED_FILENAMES)

    def test_presence_symlink_with_forbidden_basename_reports_both_findings_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"; root.mkdir(); target = root.parent / "target.md"; target.write_bytes(b"x")
            link = root / "RELEVANCE_REGISTRATION.md"
            try: link.symlink_to(target)
            except (OSError, NotImplementedError) as exc: self.skipTest(f"symlink unavailable: {exc}")
            self.assertEqual({item.code for item in find_sealed_presence(roots=[root], forbidden_filenames=M15B_SEALED_FILENAMES)}, {"unsafe_symlink_present", "forbidden_filename_present"})

    def test_presence_paths_use_posix_and_results_are_sorted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / "b").mkdir(); (root / "a").mkdir(); (root / "b" / "SOURCE_DOSSIER.md").write_bytes(b"x"); (root / "a" / "SCOPE_REGISTRATION.md").write_bytes(b"x")
            findings = find_sealed_presence(roots=[root], forbidden_filenames=M15B_SEALED_FILENAMES)
            self.assertEqual(list(findings), sorted(findings, key=lambda item: (item.root, item.path, item.code)))
            self.assertTrue(all("\\" not in item.path for item in findings))

    def test_cli_build_writes_valid_deterministic_manifest(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            self.write_artifact(sealed)
            output = repo / "manifest.json"
            result = self.run_cli("build-sealed-manifest", "--repo-root", str(repo), "--sealed-root", str(sealed), "--protocol-version", "1.0", "--registered-at", TIMESTAMP, "--artifact-filename", "one.md", "--output", str(output))
            self.assertEqual(result.returncode, 0, result.stderr); self.assertTrue(json.loads(result.stdout)["artifact_count"] == 1); self.assertEqual(load_sealed_manifest(output).sealed_artifacts[0].filename, "one.md")

    def test_cli_build_refuses_existing_output(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            self.write_artifact(sealed); output = repo / "manifest.json"; output.write_text("x")
            result = self.run_cli("build-sealed-manifest", "--repo-root", str(repo), "--sealed-root", str(sealed), "--protocol-version", "1.0", "--registered-at", TIMESTAMP, "--artifact-filename", "one.md", "--output", str(output))
            self.assertEqual(result.returncode, 2)

    def test_cli_validate_valid_and_malformed_inputs(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            self.write_artifact(sealed); manifest = self.build_one(repo, sealed); output = repo / "manifest.json"; write_new_sealed_manifest(output, manifest, sealed_root=sealed)
            self.assertEqual(self.run_cli("validate-sealed-manifest", str(output), "--json").returncode, 0)
            output.write_text("{}")
            self.assertEqual(self.run_cli("validate-sealed-manifest", str(output), "--json").returncode, 2)

    def test_cli_verify_exact_and_changed_bytes_exit_codes(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            self.write_artifact(sealed); manifest = self.build_one(repo, sealed); output = repo / "manifest.json"; write_new_sealed_manifest(output, manifest, sealed_root=sealed)
            args = ("verify-sealed-manifest", str(output), "--repo-root", str(repo), "--sealed-root", str(sealed), "--json")
            self.assertEqual(self.run_cli(*args).returncode, 0); self.write_artifact(sealed, data=b"changed"); self.assertEqual(self.run_cli(*args).returncode, 1)

    def test_cli_absence_clean_and_finding_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); args = ("check-sealed-absence", "--root", str(root), "--filename", "RELEVANCE_REGISTRATION.md", "--json")
            self.assertEqual(self.run_cli(*args).returncode, 0); (root / "RELEVANCE_REGISTRATION.md").write_bytes(b"x"); self.assertEqual(self.run_cli(*args).returncode, 1)

    def test_cli_invalid_input_returns_exit_2(self) -> None:
        self.assertEqual(self.run_cli("check-sealed-absence", "--root", "missing", "--filename", "RELEVANCE_REGISTRATION.md", "--json").returncode, 2)

    def test_cli_json_output_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); args = ("check-sealed-absence", "--root", str(root), "--filename", "RELEVANCE_REGISTRATION.md", "--json")
            self.assertEqual(self.run_cli(*args).stdout, self.run_cli(*args).stdout)

    def test_cli_build_output_does_not_include_artifact_contents(self) -> None:
        temporary, repo, sealed = self.make_roots()
        with temporary:
            self.write_artifact(sealed, data=b"synthetic-private-body")
            output = repo / "manifest.json"
            result = self.run_cli("build-sealed-manifest", "--repo-root", str(repo), "--sealed-root", str(sealed), "--protocol-version", "1.0", "--registered-at", TIMESTAMP, "--artifact-filename", "one.md", "--output", str(output))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("synthetic-private-body", result.stdout)


if __name__ == "__main__":
    unittest.main()
