# Decision Review Package Guide

## Purpose

The Decision Review Package exporter writes the deterministic Decision Board preview into a separate package for human inspection, internal sharing, and archival. The package is not an approved engineering decision and does not replace human review.

## Package Contents

Each successful export creates exactly four files:

- `decision_board_preview.md`: human-readable deterministic preview.
- `decision_board_preview.json`: complete structured Decision Board result.
- `review_manifest.json`: deterministic source and artifact traceability.
- `human_review_checklist.md`: blank human-controlled approval fields and review questions.

The exporter does not write `02_decision_board.md` or any numbered canonical case artifact.

## Deterministic Hashing And Traceability

`review_manifest.json` records SHA256 hashes for all numbered canonical source case files and for the generated Markdown preview, JSON preview, and human review checklist. The manifest does not hash itself. It stores relative file names only and excludes timestamps, local usernames, hostnames, UUIDs, absolute paths, and Git credentials.

## Human Review Checklist

The checklist starts with `Review status: pending` and leaves reviewer, owner, approval, release, and comment fields blank. The exporter never approves an architecture, fills approval conditions, or converts a screening candidate into a recommendation.

## Output Directory Requirement

An explicit output directory is always required:

```bash
python scripts/labos_case.py export-decision-review \
  cases/example-incomplete-gan-rf-pa/ \
  --output-dir exports/example-incomplete-gan-rf-pa-review
```

There is no implicit default output location.

## Protected Output Paths

The exporter rejects output directories that are the canonical case directory, inside the canonical case directory, `patterns/`, inside `patterns/`, `memory/`, inside `memory/`, `.git/`, inside `.git/`, or the repository root. Symlinked output paths are resolved before safety checks.

## Overwrite Policy

By default, export refuses to overwrite any existing package file. With `--force`, it overwrites only the four known package files and preserves unrelated files in the output directory. It never recursively deletes the output directory.

## No Partial Package Guarantee

The exporter validates the case, output path, Decision Board preview, generated content, and overwrite state before writing package files. If validation fails, it returns an error and writes no package files.

## Why This Is Not Approval

The package preserves a deterministic preview for review. It keeps candidate routes, deferred routes, hold points, and claim guardrails visible, but it does not create an approved Decision Board or a customer-release decision. Human approval must remain explicit and separate.

## Future Approval Workflow

A Human Decision Record can be generated against a package and bound to `review_manifest.json` by SHA256. The record captures human-entered review outcome, route decisions, evidence references, customer-release posture, acknowledgements, and attestations. The validator checks the binding and guardrails, but it does not verify human identity or create a cryptographic signature.

A future workflow may copy reviewed conclusions into `02_decision_board.md`, but that must be opt-in, reviewable, and separate from this exporter and from Human Decision Record validation. Any future write workflow should preserve claim safety, confidentiality review, and validation traceability.
