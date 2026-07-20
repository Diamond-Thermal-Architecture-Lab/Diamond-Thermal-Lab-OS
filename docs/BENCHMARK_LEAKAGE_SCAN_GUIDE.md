# Benchmark Leakage Scan Guide

## 1. Purpose

M15B Phase 0.5B2B provides deterministic, candidate-independent leakage auditing with a private external policy.

## 2. Phase 0.5B2B Boundary

This phase scans explicit roots and emits a public-safe audit report. It does not create a policy, select a candidate, create sealed artifacts, or record an execution baseline.

## 3. Explicit Scan Roots

Only caller-supplied, non-symlink directory roots are scanned. Git is not invoked, parent and sibling directories are not inferred, and a clean audit does not prove absence from unscanned locations.

## 4. Opaque Root IDs

Each root has a sorted opaque `ROOT-` identifier. Raw root paths are never emitted.

## 5. Private Policy Separation

The policy remains in external storage and must be disjoint from the repository, scan roots, and declared forbidden roots.

## 6. Deterministic Traversal

Roots, directory entries, and findings are ordered deterministically. Directory symlinks are never followed.

## 7. Path Scanning

The scanner applies B2A literal and NFKC-casefold token semantics to each relative POSIX path.

## 8. Safe Regular-File Opening

Regular files are opened through file descriptors with no-follow protections where available, plus identity checks before and after opening.

## 9. Strict UTF-8 Content Scanning

Strict UTF-8 is the only supported content encoding. Invalid UTF-8 is a finding and is not content-scanned.

## 10. Symlink and Special-File Handling

Symlinks are never followed. Symlinks, special files, inspection failures, and unreadable directories fail closed as structural findings.

## 11. File Size Limit

Files larger than 16 MiB produce an `oversize_file` finding without decoding or content scanning.

## 12. Finding Codes

The report uses candidate-independent codes for path/content matches and unsafe or unscannable filesystem entries.

## 13. Finding Aggregation

Matches are aggregated by root, opaque path identity, code, and opaque token ID. Structural findings are aggregated per root, path identity, and code.

## 14. Public-Safe Path Identity

`path_sha256` is SHA256 of the opaque root ID, a NUL separator, and the relative POSIX path. Raw paths are never included in the public report.

## 15. Audit Report Schema

Reports include only policy identity, aggregate counts, opaque root IDs, opaque path hashes, token metadata, and finding counts. Token values and matched snippets are never emitted.

## 16. Deterministic Serialization

Report JSON uses UTF-8, sorted keys, two-space indentation, canonical finding order, and exactly one final newline.

## 17. CLI

```bash
python scripts/labos_benchmark.py scan-private-leakage --repo-root . --policy-root /controlled/private-policy --scan-root ROOT-0001=./packet --json
```

## 18. Exit Codes

`0` means a completed pass, `1` means a completed audit with findings, and `2` means invalid input or an operational failure.

## 19. Security Limits

Token values, normalized values, raw paths, snippets, lines, and offsets are not emitted. The audit cannot establish absence from unavailable or unscanned locations.

## 20. Deferred Execution Scope

Execution-scope specification remains a separate Phase 0.5 gate.

## 21. Deferred Execution Baseline

Execution-baseline generation, verification, and immutable recording remain deferred.

## 22. Candidate Work Not Started

No real policy or candidate is used in this PR, and candidate screening remains prohibited.
