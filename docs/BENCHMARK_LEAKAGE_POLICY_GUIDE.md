# Benchmark Leakage Policy Guide

## 1. Purpose

This guide documents the candidate-independent private leakage-policy validation implemented for M15B Phase 0.5B2A.

## 2. Phase 0.5B2A Boundary

This phase validates a private external leakage policy, computes exact policy-byte identity, and returns a public-safe validation summary. It does not scan repository files, Blind Input Packets, prompts, attachments, conversations, or any other content.

## 3. Why the Policy Is Private

The real policy may contain source identity, outcomes, expected judgments, and known result-derived interpretations. Those token values must remain outside the repository, benchmark worktree, Role D packet paths, Role D prompts, Role D attachments, and Role D execution context.

Token values must never be copied into public reports, command output, validation summaries, or errors.

## 4. External Storage Contract

The private policy root is controlled private storage. It must be an existing non-symlink directory that is disjoint from the repository and every declared forbidden root. Equality, policy-root-inside-forbidden-root, and forbidden-root-inside-policy-root are all rejected.

The validator does not reject ordinary operating-system ancestors merely because they use platform links.

## 5. Fixed Policy Filename

The validator always reads:

```text
PRIVATE_LEAKAGE_POLICY.json
```

from the supplied private policy root. This repository must not contain a real file with that name.

## 6. Policy Schema

The policy is UTF-8 JSON with exactly two top-level keys:

```json
{
  "policy_version": "1.0",
  "tokens": [
    {
      "token_id": "LKG-0001",
      "category": "source_identity",
      "match_mode": "literal",
      "value": "synthetic-private-token"
    }
  ]
}
```

Token records must contain exactly `token_id`, `category`, `match_mode`, and `value`. Unknown keys, missing keys, duplicate JSON keys, malformed UTF-8, malformed JSON, unsorted token IDs, duplicate token IDs, invalid categories, invalid match modes, unsafe values, and duplicate matching signatures are rejected.

## 7. Opaque Token IDs

Token IDs are opaque numeric identifiers matching `LKG-[0-9]{4,8}`. They exist only to make policy records stable. They must not encode candidate identity, source identity, outcomes, rule expectations, or scoring expectations.

## 8. Leakage Categories

The allowed categories are:

```text
expected_rule
expected_score
expected_status
known_error_label
outcome
result_explanation
rule_fix
source_identity
trigger_rewrite
```

These categories are candidate-independent policy labels. They are not candidate facts.

## 9. Match Modes

The allowed match modes are:

```text
literal
nfkc_casefold
```

`literal` preserves the exact token value for later case-sensitive matching.

`nfkc_casefold` precomputes `unicodedata.normalize("NFKC", value).casefold()` for later scanner use.

This phase validates and precomputes semantics only. It does not implement content scanning, regular expressions, fuzzy matching, stemming, phonetic matching, or external search.

## 10. Exact Policy-Byte Identity

Exact policy bytes are identified by byte length and SHA256. Whitespace and line endings affect policy identity. No line-ending normalization is applied.

## 11. Safe Validation Summary

The public-safe summary contains only:

```text
valid
policy_version
token_count
byte_length
sha256
```

It does not include policy paths, policy roots, forbidden roots, token IDs, categories, match modes, token values, or normalized values.

## 12. Safe Error Contract

Validation errors are safe to display. They may identify candidate-independent structural failures, token list indexes, and already-valid opaque token IDs. They must not include token values, normalized token values, decoded policy contents, snippets, source identity, outcomes, or absolute private paths.

## 13. CLI Example

```bash
python scripts/labos_benchmark.py validate-private-leakage-policy --repo-root . --policy-root /controlled/private-policy --json
```

The command validates storage separation, loads `PRIVATE_LEAKAGE_POLICY.json`, validates schema and token semantics, computes exact byte identity, and prints only the public-safe summary.

## 14. Security Limits

Policy validation is not a secrecy guarantee. It does not prove that private information is absent from unavailable files, logs, prompts, attachments, shells, external storage, or prior conversations. It must be paired with role separation, controlled storage, later leakage scanning, and human review.

## 15. Deferred Content Scanner

Phase 0.5B2B will add the scanner and safe public audit report. This PR does not scan files, paths, packets, prompts, or conversations and does not generate a leakage-audit report.

## 16. Deferred Execution Baseline

Execution-scope specification, execution-baseline generation, execution-baseline verification, and immutable M15B execution-baseline recording remain deferred. No candidate screening has begun.
