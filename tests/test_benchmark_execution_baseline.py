from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from labos.benchmarks.execution_baseline import (
    DEPENDENCY_MANIFEST_BASENAMES,
    DEPENDENCY_MANIFEST_GLOBS,
    EXECUTION_BASELINE_RECORD_VERSION,
    EXECUTION_SCOPE_VERSION,
    M14_RULE_PATH,
    M15B_EXECUTION_BASELINE_RECORD_PATH,
    M15B_EXECUTION_SCOPE_PATH,
    M15B_PROTOCOL_MERGE_COMMIT,
    M15B_PROTOCOL_PATH,
    PROTECTED_TREE_GROUPS,
    BaselineFileRecord,
    ExecutionBaselineRecord,
    ExecutionScope,
    ExecutionScopeTree,
    build_execution_baseline_record,
    canonical_execution_scope,
    load_execution_baseline_record,
    parse_execution_baseline_record_bytes,
    parse_execution_scope_bytes,
    serialize_execution_baseline_record,
    serialize_execution_scope,
    verify_execution_baseline,
    verify_execution_baseline_git,
    write_new_execution_baseline_record,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SCOPE_PATH = REPO_ROOT / M15B_EXECUTION_SCOPE_PATH
COMMIT = "a" * 40
TIMESTAMP = "2026-08-11T06:00:00Z"


class ExecutionBaselineFixture(unittest.TestCase):
    def make_repo(self) -> tuple[tempfile.TemporaryDirectory[str], Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        files = {
            "labos/__init__.py": b"",
            "labos/triage/thermomechanical.py": b"RULE = 'frozen'\n",
            "labos/schemas/case.yml": b"type: object\n",
            "schemas/record.json": b"{}\n",
            "scripts/tool.py": b"print('ok')\n",
            ".github/workflows/ci.yml": b"name: ci\n",
            M15B_PROTOCOL_PATH: b"# Synthetic frozen protocol\n",
            M15B_EXECUTION_SCOPE_PATH: serialize_execution_scope(canonical_execution_scope()),
        }
        for relative, data in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return temporary, root, root / M15B_EXECUTION_SCOPE_PATH

    def build(self, root: Path, scope_path: Path) -> ExecutionBaselineRecord:
        return build_execution_baseline_record(
            repo_root=root,
            scope_path=scope_path,
            protected_content_commit=COMMIT,
            recorded_at_utc=TIMESTAMP,
        )


class ExecutionScopeTests(ExecutionBaselineFixture):
    def test_canonical_scope_has_exact_versions_and_paths(self) -> None:
        scope = canonical_execution_scope()
        self.assertEqual(scope.scope_version, EXECUTION_SCOPE_VERSION)
        self.assertEqual(scope.protocol_path, M15B_PROTOCOL_PATH)
        self.assertEqual(scope.m14_rule_path, M14_RULE_PATH)

    def test_canonical_scope_has_exact_tree_groups(self) -> None:
        scope = canonical_execution_scope()
        self.assertEqual(
            tuple((item.group_id, item.include_paths) for item in scope.protected_trees),
            PROTECTED_TREE_GROUPS,
        )

    def test_canonical_scope_has_exact_dependency_names(self) -> None:
        scope = canonical_execution_scope()
        self.assertEqual(scope.dependency_manifest_basenames, DEPENDENCY_MANIFEST_BASENAMES)
        self.assertEqual(scope.dependency_manifest_globs, DEPENDENCY_MANIFEST_GLOBS)

    def test_committed_scope_is_canonical_serialization(self) -> None:
        self.assertEqual(SCOPE_PATH.read_bytes(), serialize_execution_scope(canonical_execution_scope()))

    def test_scope_round_trip_is_exact(self) -> None:
        data = serialize_execution_scope(canonical_execution_scope())
        self.assertEqual(serialize_execution_scope(parse_execution_scope_bytes(data)), data)

    def test_scope_rejects_invalid_utf8(self) -> None:
        with self.assertRaises(ValueError):
            parse_execution_scope_bytes(b"\xff")

    def test_scope_rejects_duplicate_keys(self) -> None:
        data = serialize_execution_scope(canonical_execution_scope()).replace(
            b'"scope_version": "1.0"', b'"scope_version": "1.0", "scope_version": "1.0"'
        )
        with self.assertRaises(ValueError):
            parse_execution_scope_bytes(data)

    def test_scope_rejects_unknown_key(self) -> None:
        payload = json.loads(serialize_execution_scope(canonical_execution_scope()))
        payload["extra"] = True
        with self.assertRaises(ValueError):
            parse_execution_scope_bytes(json.dumps(payload).encode())

    def test_scope_rejects_weakened_protected_tree(self) -> None:
        payload = json.loads(serialize_execution_scope(canonical_execution_scope()))
        payload["protected_trees"][0]["include_paths"] = ["labos/benchmarks"]
        with self.assertRaises(ValueError):
            parse_execution_scope_bytes(json.dumps(payload).encode())

    def test_scope_rejects_removed_dependency_name(self) -> None:
        payload = json.loads(serialize_execution_scope(canonical_execution_scope()))
        payload["dependency_manifest_basenames"].pop()
        with self.assertRaises(ValueError):
            parse_execution_scope_bytes(json.dumps(payload).encode())


class ExecutionBaselineBuildTests(ExecutionBaselineFixture):
    def test_build_records_exact_four_tree_groups(self) -> None:
        temporary, root, scope_path = self.make_repo()
        self.addCleanup(temporary.cleanup)
        record = self.build(root, scope_path)
        self.assertEqual([item.group_id for item in record.protected_trees], [x[0] for x in PROTECTED_TREE_GROUPS])

    def test_build_records_protocol_and_m14_files(self) -> None:
        temporary, root, scope_path = self.make_repo()
        self.addCleanup(temporary.cleanup)
        record = self.build(root, scope_path)
        self.assertEqual(record.protocol_file.path, M15B_PROTOCOL_PATH)
        self.assertEqual(record.m14_rule_file.path, M14_RULE_PATH)

    def test_build_records_no_dependency_manifests_when_absent(self) -> None:
        temporary, root, scope_path = self.make_repo()
        self.addCleanup(temporary.cleanup)
        self.assertEqual(self.build(root, scope_path).dependency_manifests, ())

    def test_build_records_root_requirements_manifest(self) -> None:
        temporary, root, scope_path = self.make_repo()
        self.addCleanup(temporary.cleanup)
        (root / "requirements-dev.txt").write_bytes(b"example==1\n")
        record = self.build(root, scope_path)
        self.assertEqual([item.path for item in record.dependency_manifests], ["requirements-dev.txt"])

    def test_build_records_empty_dependency_manifest(self) -> None:
        temporary, root, scope_path = self.make_repo()
        self.addCleanup(temporary.cleanup)
        (root / "requirements.txt").write_bytes(b"")
        record = self.build(root, scope_path)
        self.assertEqual(record.dependency_manifests[0].byte_length, 0)

    def test_build_records_nested_package_manifest(self) -> None:
        temporary, root, scope_path = self.make_repo()
        self.addCleanup(temporary.cleanup)
        nested = root / "tools" / "package.json"
        nested.parent.mkdir()
        nested.write_bytes(b"{}\n")
        record = self.build(root, scope_path)
        self.assertEqual([item.path for item in record.dependency_manifests], ["tools/package.json"])

    def test_build_rejects_symlink_dependency_manifest_when_supported(self) -> None:
        temporary, root, scope_path = self.make_repo()
        self.addCleanup(temporary.cleanup)
        target = root / "dependency.txt"
        target.write_bytes(b"x\n")
        link = root / "requirements.txt"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink unavailable: {exc}")
        with self.assertRaises(ValueError):
            self.build(root, scope_path)

    def test_build_rejects_short_commit(self) -> None:
        temporary, root, scope_path = self.make_repo()
        self.addCleanup(temporary.cleanup)
        with self.assertRaises(ValueError):
            build_execution_baseline_record(
                repo_root=root,
                scope_path=scope_path,
                protected_content_commit="abc",
                recorded_at_utc=TIMESTAMP,
            )

    def test_build_rejects_invalid_timestamp(self) -> None:
        temporary, root, scope_path = self.make_repo()
        self.addCleanup(temporary.cleanup)
        with self.assertRaises(ValueError):
            build_execution_baseline_record(
                repo_root=root,
                scope_path=scope_path,
                protected_content_commit=COMMIT,
                recorded_at_utc="2026-02-30T00:00:00Z",
            )

    def test_build_rejects_external_scope_copy(self) -> None:
        temporary, root, scope_path = self.make_repo()
        self.addCleanup(temporary.cleanup)
        external = Path(temporary.name) / "scope-copy.json"
        external.write_bytes(scope_path.read_bytes())
        with self.assertRaises(ValueError):
            self.build(root, external)

    def test_build_rejects_symlinked_directory_in_dependency_scan_when_supported(self) -> None:
        temporary, root, scope_path = self.make_repo()
        self.addCleanup(temporary.cleanup)
        target = Path(temporary.name) / "outside"
        target.mkdir()
        link = root / "linked-directory"
        try:
            link.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink unavailable: {exc}")
        with self.assertRaises(ValueError):
            self.build(root, scope_path)


class ExecutionBaselineRecordTests(ExecutionBaselineFixture):
    def make_record(self) -> tuple[tempfile.TemporaryDirectory[str], ExecutionBaselineRecord]:
        temporary, root, scope_path = self.make_repo()
        return temporary, self.build(root, scope_path)

    def test_record_round_trip_is_exact(self) -> None:
        temporary, record = self.make_record()
        self.addCleanup(temporary.cleanup)
        data = serialize_execution_baseline_record(record)
        self.assertEqual(serialize_execution_baseline_record(parse_execution_baseline_record_bytes(data)), data)

    def test_record_serialization_is_deterministic(self) -> None:
        temporary, record = self.make_record()
        self.addCleanup(temporary.cleanup)
        self.assertEqual(serialize_execution_baseline_record(record), serialize_execution_baseline_record(record))

    def test_record_has_one_final_newline(self) -> None:
        temporary, record = self.make_record()
        self.addCleanup(temporary.cleanup)
        data = serialize_execution_baseline_record(record)
        self.assertTrue(data.endswith(b"\n"))
        self.assertFalse(data.endswith(b"\n\n"))

    def test_record_rejects_duplicate_keys(self) -> None:
        temporary, record = self.make_record()
        self.addCleanup(temporary.cleanup)
        data = serialize_execution_baseline_record(record).replace(
            b'"record_version": "1.0"', b'"record_version": "1.0", "record_version": "1.0"'
        )
        with self.assertRaises(ValueError):
            parse_execution_baseline_record_bytes(data)

    def test_record_rejects_unknown_top_level_key(self) -> None:
        temporary, record = self.make_record()
        self.addCleanup(temporary.cleanup)
        payload = json.loads(serialize_execution_baseline_record(record))
        payload["extra"] = True
        with self.assertRaises(ValueError):
            parse_execution_baseline_record_bytes(json.dumps(payload).encode())

    def test_record_rejects_wrong_protocol_merge(self) -> None:
        temporary, record = self.make_record()
        self.addCleanup(temporary.cleanup)
        with self.assertRaises(ValueError):
            serialize_execution_baseline_record(replace(record, protocol_merge_commit="b" * 40))

    def test_record_rejects_invalid_tree_hash(self) -> None:
        temporary, record = self.make_record()
        self.addCleanup(temporary.cleanup)
        trees = list(record.protected_trees)
        trees[0] = replace(trees[0], sha256="bad")
        with self.assertRaises(ValueError):
            serialize_execution_baseline_record(replace(record, protected_trees=tuple(trees)))

    def test_record_rejects_reordered_tree_groups(self) -> None:
        temporary, record = self.make_record()
        self.addCleanup(temporary.cleanup)
        with self.assertRaises(ValueError):
            serialize_execution_baseline_record(replace(record, protected_trees=tuple(reversed(record.protected_trees))))

    def test_record_rejects_non_manifest_dependency_path(self) -> None:
        temporary, record = self.make_record()
        self.addCleanup(temporary.cleanup)
        dependency = BaselineFileRecord(path="notes.txt", byte_length=1, sha256="0" * 64)
        with self.assertRaises(ValueError):
            serialize_execution_baseline_record(replace(record, dependency_manifests=(dependency,)))

    def test_write_new_record_refuses_overwrite(self) -> None:
        temporary, record = self.make_record()
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name) / "record.json"
        write_new_execution_baseline_record(output, record)
        with self.assertRaises(ValueError):
            write_new_execution_baseline_record(output, record)

    def test_load_record_rejects_symlink_when_supported(self) -> None:
        temporary, record = self.make_record()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        target = root / "record.json"
        target.write_bytes(serialize_execution_baseline_record(record))
        link = root / "link.json"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink unavailable: {exc}")
        with self.assertRaises(ValueError):
            load_execution_baseline_record(link)


class ExecutionBaselineVerificationTests(ExecutionBaselineFixture):
    def assertFinding(self, findings: tuple, code: str) -> None:
        self.assertIn(code, {item.code for item in findings})

    def test_clean_offline_tree_verifies_without_git(self) -> None:
        temporary, root, scope_path = self.make_repo()
        self.addCleanup(temporary.cleanup)
        record = self.build(root, scope_path)
        self.assertFalse((root / ".git").exists())
        self.assertEqual(verify_execution_baseline(record, repo_root=root, scope_path=scope_path), ())

    def test_production_code_mutation_fails(self) -> None:
        temporary, root, scope_path = self.make_repo()
        self.addCleanup(temporary.cleanup)
        record = self.build(root, scope_path)
        (root / "labos/__init__.py").write_bytes(b"changed\n")
        self.assertFinding(verify_execution_baseline(record, repo_root=root, scope_path=scope_path), "protected_tree_mismatch")

    def test_script_addition_fails(self) -> None:
        temporary, root, scope_path = self.make_repo()
        self.addCleanup(temporary.cleanup)
        record = self.build(root, scope_path)
        (root / "scripts/new.py").write_bytes(b"x\n")
        self.assertFinding(verify_execution_baseline(record, repo_root=root, scope_path=scope_path), "protected_tree_mismatch")

    def test_workflow_removal_fails(self) -> None:
        temporary, root, scope_path = self.make_repo()
        self.addCleanup(temporary.cleanup)
        record = self.build(root, scope_path)
        (root / ".github/workflows/ci.yml").unlink()
        self.assertFinding(verify_execution_baseline(record, repo_root=root, scope_path=scope_path), "protected_tree_mismatch")

    def test_top_level_schema_mutation_fails(self) -> None:
        temporary, root, scope_path = self.make_repo()
        self.addCleanup(temporary.cleanup)
        record = self.build(root, scope_path)
        (root / "schemas/record.json").write_bytes(b'{"changed":true}\n')
        self.assertFinding(verify_execution_baseline(record, repo_root=root, scope_path=scope_path), "protected_tree_mismatch")

    def test_m14_mutation_has_specific_finding(self) -> None:
        temporary, root, scope_path = self.make_repo()
        self.addCleanup(temporary.cleanup)
        record = self.build(root, scope_path)
        (root / M14_RULE_PATH).write_bytes(b"changed\n")
        self.assertFinding(verify_execution_baseline(record, repo_root=root, scope_path=scope_path), "m14_rule_file_mismatch")

    def test_protocol_mutation_has_specific_finding(self) -> None:
        temporary, root, scope_path = self.make_repo()
        self.addCleanup(temporary.cleanup)
        record = self.build(root, scope_path)
        (root / M15B_PROTOCOL_PATH).write_bytes(b"changed\n")
        self.assertFinding(verify_execution_baseline(record, repo_root=root, scope_path=scope_path), "protocol_file_mismatch")

    def test_scope_byte_change_fails_even_when_semantics_parse(self) -> None:
        temporary, root, scope_path = self.make_repo()
        self.addCleanup(temporary.cleanup)
        record = self.build(root, scope_path)
        scope_path.write_bytes(serialize_execution_scope(canonical_execution_scope()).replace(b"  ", b"    ", 1))
        self.assertFinding(verify_execution_baseline(record, repo_root=root, scope_path=scope_path), "scope_spec_sha256_mismatch")

    def test_new_dependency_manifest_fails(self) -> None:
        temporary, root, scope_path = self.make_repo()
        self.addCleanup(temporary.cleanup)
        record = self.build(root, scope_path)
        (root / "pyproject.toml").write_bytes(b"[project]\n")
        self.assertFinding(verify_execution_baseline(record, repo_root=root, scope_path=scope_path), "dependency_manifest_set_mismatch")

    def test_dependency_manifest_byte_change_fails(self) -> None:
        temporary, root, scope_path = self.make_repo()
        self.addCleanup(temporary.cleanup)
        manifest = root / "requirements.txt"
        manifest.write_bytes(b"a==1\n")
        record = self.build(root, scope_path)
        manifest.write_bytes(b"a==2\n")
        self.assertFinding(verify_execution_baseline(record, repo_root=root, scope_path=scope_path), "dependency_manifest_bytes_mismatch")

    def test_pycache_and_pyc_do_not_change_baseline(self) -> None:
        temporary, root, scope_path = self.make_repo()
        self.addCleanup(temporary.cleanup)
        record = self.build(root, scope_path)
        cache = root / "labos/__pycache__"
        cache.mkdir()
        (cache / "x.pyc").write_bytes(b"cache")
        self.assertEqual(verify_execution_baseline(record, repo_root=root, scope_path=scope_path), ())

    def test_tracked_style_pyc_outside_cache_changes_baseline(self) -> None:
        temporary, root, scope_path = self.make_repo()
        self.addCleanup(temporary.cleanup)
        record = self.build(root, scope_path)
        (root / "labos/checked.pyc").write_bytes(b"tracked-style-bytecode")
        self.assertFinding(verify_execution_baseline(record, repo_root=root, scope_path=scope_path), "protected_tree_mismatch")


class ExecutionBaselineGitAndCliTests(ExecutionBaselineFixture):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "scripts/labos_benchmark.py", *args],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def make_committed_baseline(
        self,
    ) -> tuple[tempfile.TemporaryDirectory[str], Path, ExecutionBaselineRecord, str]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name) / "repo"
        subprocess.run(
            ["git", "clone", "--quiet", "--no-hardlinks", str(REPO_ROOT), str(root)],
            check=True,
        )
        subprocess.run(["git", "config", "user.name", "Phase 0.5C Test"], cwd=root, check=True)
        subprocess.run(
            ["git", "config", "user.email", "phase-0.5c-test@example.invalid"],
            cwd=root,
            check=True,
        )
        content_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip()
        record = build_execution_baseline_record(
            repo_root=root,
            scope_path=root / M15B_EXECUTION_SCOPE_PATH,
            protected_content_commit=content_commit,
            recorded_at_utc=TIMESTAMP,
        )
        record_path = root / M15B_EXECUTION_BASELINE_RECORD_PATH
        write_new_execution_baseline_record(record_path, record)
        subprocess.run(
            ["git", "add", M15B_EXECUTION_BASELINE_RECORD_PATH], cwd=root, check=True
        )
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "Record synthetic execution baseline"],
            cwd=root,
            check=True,
        )
        return temporary, root, record, content_commit

    def test_git_verification_accepts_committed_canonical_record(self) -> None:
        temporary, root, record, _ = self.make_committed_baseline()
        self.addCleanup(temporary.cleanup)
        self.assertEqual(verify_execution_baseline_git(record, repo_root=root), ())

    def test_git_verification_rejects_record_not_committed_at_ref(self) -> None:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
        record = build_execution_baseline_record(
            repo_root=REPO_ROOT,
            scope_path=SCOPE_PATH,
            protected_content_commit=head,
            recorded_at_utc=TIMESTAMP,
        )
        findings = verify_execution_baseline_git(record, repo_root=REPO_ROOT)
        self.assertIn("baseline_record_not_committed", {item.code for item in findings})

    def test_git_verification_rejects_record_bytes_not_matching_ref(self) -> None:
        temporary, root, record, _ = self.make_committed_baseline()
        self.addCleanup(temporary.cleanup)
        changed = replace(record, recorded_at_utc="2026-08-11T06:00:01Z")
        findings = verify_execution_baseline_git(changed, repo_root=root)
        self.assertIn("baseline_record_git_mismatch", {item.code for item in findings})

    def test_git_verification_rejects_ref_that_is_not_checked_out(self) -> None:
        temporary, root, record, content_commit = self.make_committed_baseline()
        self.addCleanup(temporary.cleanup)
        findings = verify_execution_baseline_git(record, repo_root=root, ref=content_commit)
        self.assertIn("git_ref_not_checked_out", {item.code for item in findings})

    def test_git_verification_detects_dependency_change_after_content_commit(self) -> None:
        temporary, root, record, _ = self.make_committed_baseline()
        self.addCleanup(temporary.cleanup)
        (root / "requirements.txt").write_bytes(b"unexpected==1\n")
        subprocess.run(["git", "add", "requirements.txt"], cwd=root, check=True)
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "Mutate dependency state"],
            cwd=root,
            check=True,
        )
        findings = verify_execution_baseline_git(record, repo_root=root)
        self.assertIn("dependency_manifest_git_mismatch", {item.code for item in findings})

    def test_git_verification_rejects_unknown_protected_commit(self) -> None:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
        record = build_execution_baseline_record(
            repo_root=REPO_ROOT,
            scope_path=SCOPE_PATH,
            protected_content_commit=head,
            recorded_at_utc=TIMESTAMP,
        )
        record = replace(record, protected_content_commit="f" * 40)
        findings = verify_execution_baseline_git(record, repo_root=REPO_ROOT)
        self.assertIn("protected_content_not_ancestor", {item.code for item in findings})

    def test_git_verification_detects_protected_change_after_content_commit(self) -> None:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
        record = build_execution_baseline_record(
            repo_root=REPO_ROOT,
            scope_path=SCOPE_PATH,
            protected_content_commit=M15B_PROTOCOL_MERGE_COMMIT,
            recorded_at_utc=TIMESTAMP,
        )
        findings = verify_execution_baseline_git(record, repo_root=REPO_ROOT, ref=head)
        self.assertIn("protected_scope_git_mismatch", {item.code for item in findings})

    def test_validate_scope_cli_is_deterministic(self) -> None:
        args = ("validate-execution-scope", M15B_EXECUTION_SCOPE_PATH, "--json")
        first = self.run_cli(*args)
        second = self.run_cli(*args)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)

    def test_cli_rejects_uncommitted_external_record_for_git_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "record.json"
            head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
            built = self.run_cli(
                "build-execution-baseline",
                "--repo-root", ".",
                "--scope", M15B_EXECUTION_SCOPE_PATH,
                "--protected-content-commit", head,
                "--recorded-at", TIMESTAMP,
                "--output", str(output),
            )
            self.assertEqual(built.returncode, 0, built.stderr)
            validated = self.run_cli("validate-execution-baseline", str(output), "--json")
            self.assertEqual(validated.returncode, 0, validated.stderr)
            verified = self.run_cli(
                "verify-execution-baseline", str(output),
                "--repo-root", ".",
                "--scope", M15B_EXECUTION_SCOPE_PATH,
                "--git-ref", "HEAD",
                "--json",
            )
            self.assertEqual(verified.returncode, 1, verified.stderr)
            result = json.loads(verified.stdout)
            self.assertFalse(result["valid"])
            self.assertIn(
                "baseline_record_not_committed",
                {item["code"] for item in result["findings"]},
            )

    def test_build_validate_and_verify_committed_baseline_cli(self) -> None:
        temporary, root, _, _ = self.make_committed_baseline()
        self.addCleanup(temporary.cleanup)
        record_path = root / M15B_EXECUTION_BASELINE_RECORD_PATH
        validated = self.run_cli("validate-execution-baseline", str(record_path), "--json")
        self.assertEqual(validated.returncode, 0, validated.stderr)
        verified = self.run_cli(
            "verify-execution-baseline", str(record_path),
            "--repo-root", str(root),
            "--scope", str(root / M15B_EXECUTION_SCOPE_PATH),
            "--git-ref", "HEAD",
            "--json",
        )
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertTrue(json.loads(verified.stdout)["valid"])

    def test_verify_cli_returns_one_for_mismatch(self) -> None:
        temporary, root, scope_path = self.make_repo()
        self.addCleanup(temporary.cleanup)
        record = self.build(root, scope_path)
        record_path = root / "record.json"
        record_path.write_bytes(serialize_execution_baseline_record(record))
        (root / "scripts/tool.py").write_bytes(b"changed\n")
        result = self.run_cli(
            "verify-execution-baseline", str(record_path),
            "--repo-root", str(root),
            "--scope", str(scope_path),
            "--json",
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertFalse(json.loads(result.stdout)["valid"])

    def test_constants_preserve_frozen_protocol_commit(self) -> None:
        self.assertEqual(M15B_PROTOCOL_MERGE_COMMIT, "e35476d5fe4ccfa94f8438a7ef1fbf569fd67aa2")
        self.assertEqual(EXECUTION_BASELINE_RECORD_VERSION, "1.0")


if __name__ == "__main__":
    unittest.main()
