# Benchmark Sealing Guide

## 1. Purpose

This guide documents the candidate-independent sealed-registration infrastructure implemented for M15B Phase 0.5B1.

## 2. Phase 0.5B1 Boundary

This phase implements sealed-manifest creation, structural validation, reveal-time byte verification, and sealed-filename absence auditing. It does not create a real M15B registration or begin candidate screening.

## 3. External Sealed Storage

Sealed source documents stay outside the repository, benchmark worktree, and Role D context. The controlled sealed root must be an existing non-symlink directory that is disjoint from the repository and every declared forbidden root.

## 4. Exact Artifact Bytes

Manifest records contain the exact byte length and SHA256 of each supplied regular file. Line endings are not normalized. Source contents are never copied into a manifest or command output.

## 5. Manifest Schema

The manifest has a version, protocol version, explicit UTC registration timestamp, and sorted artifact records. Strict parsing rejects duplicate keys, unknown keys, invalid timestamps, unsafe names, duplicate filenames, and non-canonical record ordering.

## 6. Deterministic Serialization

Manifest JSON is UTF-8, uses two-space indentation and sorted object keys, orders artifacts by filename, and ends with exactly one newline.

## 7. Write-Once Registration

Manifest creation requires an explicit timestamp. The CLI refuses an existing output path, an unsafe output path, or an output inside sealed storage; it has no overwrite option.

## 8. Reveal-Time Verification

Verification rechecks storage separation and compares the direct-child artifact set, file type, exact byte length, and SHA256 to the manifest. It is read-only and returns deterministic findings without artifact content.

## 9. Sealed-Filename Absence Audit

The absence audit recursively checks only explicitly supplied working-tree or packet roots. It does not read ordinary source content, does not invoke Git, and never follows symlinks. It does not prove absence from unavailable Git history, external logs, or prior conversations.

## 10. CLI Examples

```bash
python scripts/labos_benchmark.py build-sealed-manifest --repo-root . --sealed-root /controlled/sealed --protocol-version 1.0 --registered-at 2026-07-17T04:30:00Z --artifact-filename RELEVANCE_REGISTRATION.md --output /controlled/manifest.json
python scripts/labos_benchmark.py validate-sealed-manifest /controlled/manifest.json --json
python scripts/labos_benchmark.py verify-sealed-manifest /controlled/manifest.json --repo-root . --sealed-root /controlled/sealed --json
python scripts/labos_benchmark.py check-sealed-absence --root . --filename RELEVANCE_REGISTRATION.md --json
```

## 11. M15B Required Filenames

The candidate-independent required filenames are `RELEVANCE_REGISTRATION.md`, `SCORING_REGISTRATION.md`, `SCOPE_REGISTRATION.md`, and `SOURCE_DOSSIER.md`. No files with these names are created by this PR.

## 12. Security Limits

The manifest is a non-semantic integrity record, not a secrecy guarantee. It protects exact-byte identity at registration and reveal but does not replace controlled storage, role separation, or human review.

## 13. Deferred Leakage Scanner

Private leakage-token policy loading and source-identity or outcome-content scanning are not implemented in this PR.

## 14. Deferred Execution Baseline

Execution-scope specification, execution-baseline generation, execution-baseline verification, and immutable M15B execution-baseline recording remain deferred. Candidate screening remains prohibited.
