# Benchmark Integrity Guide

## 1. Purpose

This guide documents the Phase 0.5A benchmark integrity core for Diamond Thermal Lab OS. It defines how benchmark artifacts are hashed before later M15B work introduces sealed manifests, private leakage policy checks, and execution-baseline records.

## 2. Hash Authority

Hash authority depends on the artifact class. A working-tree hash is not automatically authoritative for a committed file because local checkout settings may affect representation. A committed-file authority uses raw Git blob bytes. Exact-byte hashes never normalize line endings.

## 3. Exact Byte Hash

An exact byte hash is SHA256 over `Path.read_bytes()` with no decoding or normalization. It is suitable for ordinary local files, future external sealed files, and frozen byte artifacts.

## 4. Committed Git-Object Hash

A committed Git-object hash resolves the blob with `git rev-parse <ref>:<path>`, reads it with `git cat-file blob <oid>`, and hashes the captured raw stdout bytes. It does not use shell text redirection or working-tree bytes as a substitute.

## 5. Normalized LF Diagnostic Hash

The normalized LF hash decodes bytes as UTF-8, converts CRLF and bare CR to LF, re-encodes as UTF-8, and hashes the diagnostic result. Normalized LF hashes are diagnostic only. They are not exact-byte hashes, committed Git-object hashes, or sealed-artifact hashes.

## 6. Deterministic Tree Hash v1

`labos-tree-sha256-v1` sorts selected files by POSIX-relative path. For each file it hashes the path byte length, path bytes, file byte length, and exact file bytes. Tree hashing includes both path identity and file bytes, and does not depend on traversal order, modification time, permissions, locale, operating-system separators, or Git history.

## 7. Path and Symlink Safety

Repository-relative and tree-relative paths reject absolute paths, Windows drive-qualified paths, traversal, root escapes, empty unsafe components, and symlinks. Tree hashing does not follow symlinks.

## 8. M15B Protocol Integrity Record

`docs/benchmarks/M15B_PROTOCOL_INTEGRITY_RECORD.json` records the merged M15B protocol as a committed Git object:

* protocol merge commit: `e35476d5fe4ccfa94f8438a7ef1fbf569fd67aa2`
* Git blob OID: `0c142382d7f94a1cfcc19f065d21cb61fe1f5c3e`
* raw content SHA256: `4c5a5c09fb0822f70c87fff9f6a5162bd318d72da18cd4909d60a0b0f8a4e9b5`

Superseded pre-merge working values are not authoritative and are not used.

## 9. CLI Examples

Hash exact local bytes:

```bash
python scripts/labos_benchmark.py hash-file docs/benchmarks/M15B_PRE_REGISTRATION_PROTOCOL.md --json
```

Hash committed Git-object bytes:

```bash
python scripts/labos_benchmark.py hash-git-object --repo-root . --ref e35476d5fe4ccfa94f8438a7ef1fbf569fd67aa2 --path docs/benchmarks/M15B_PRE_REGISTRATION_PROTOCOL.md --json
```

Hash a deterministic tree:

```bash
python scripts/labos_benchmark.py hash-tree labos/benchmarks --json
```

## 10. Phase 0.5 Boundaries

This Phase 0.5A PR does not implement sealed manifests, leakage scanning, execution scope specifications, execution-baseline generation, or execution-baseline verification. Candidate screening remains prohibited.

## 11. Deferred Infrastructure

Later Phase 0.5 work should add sealed-manifest validation, private leakage-policy scanning, and execution-baseline records in separate reviewed PRs before candidate screening begins.
