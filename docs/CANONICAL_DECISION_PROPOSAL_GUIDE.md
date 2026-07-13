# Canonical Decision Proposal Guide

## Purpose

`propose-canonical-decision` turns one validated final Human Decision Record into a separate, inspectable proposal for `cases/<case_id>/02_decision_board.md`. It is proposal-only: it does not edit the canonical case, apply a patch, approve an architecture, or create a commit.

## Eligibility And Binding

A proposal requires a complete, hash-verified Decision Review Package and a Human Decision Record that validates as `PASS`. The record must be `final`, non-pending, and bound to the exact review manifest. The current numbered canonical case files must still match the source hashes in both the review manifest and decision record. A draft, `WARN`, `FAIL`, stale, or pending record is rejected without creating output.

Supported final outcomes are `approved`, `deferred`, `rejected`, and `more_evidence_required`. A proposal records the human outcome; it does not add a route, establish technical validation, or authorize customer release.

## Usage

```bash
python scripts/labos_case.py propose-canonical-decision \
  cases/example-case/ \
  exports/example-case-review/ \
  decisions/example-case-decision.json \
  --output-dir proposals/example-case-canonical-decision
```

`--output-dir` is required. `--force` overwrites only the four known proposal files and preserves unrelated files in that directory.

## Proposal Files

- `proposed_02_decision_board.md`: a complete proposed replacement, clearly marked as unapplied.
- `proposed_02_decision_board.diff`: deterministic unified diff against the current canonical board, for human inspection only.
- `canonical_proposal_manifest.json`: source binding and SHA256 traceability.
- `canonical_application_checklist.md`: blank or pending human-controlled application checks.

All paths in the manifest are relative. It contains no timestamps, usernames, hostnames, UUIDs, credentials, or self-hash. Route IDs remain canonical pattern IDs.

## Output Safety

The output directory cannot be the repository root, the canonical case, the review package, `patterns/`, `memory/`, or `.git/`, including paths that resolve there through symlinks. The builder validates eligibility, bindings, hashes, path safety, overwrite state, and all content before it writes the package. It refuses overwrite by default.

## Application Boundary

The proposal does not modify `02_decision_board.md`. It also does not verify reviewer identity or create a cryptographic signature. Any canonical write remains a separate, explicit PR-based workflow with confidentiality and claim-ledger review. Customer-release status in the record does not replace legal, regulatory, quality, or corporate authorization.
