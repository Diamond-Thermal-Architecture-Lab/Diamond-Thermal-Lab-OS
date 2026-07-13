# Human Decision Record Guide

## Purpose

A Human Decision Record captures a human-controlled decision against one specific Decision Review Package. It is a JSON record for review traceability. It does not approve itself, modify the canonical case, publish customer claims, or write `02_decision_board.md`.

## Relationship To The Review Package

Each record is bound to `review_manifest.json` by SHA256. The validator checks that the manifest hash, case ID, board status, decision state, ruleset versions, and source case hash mapping match the bound package. A record that merely names the same case but points to a different manifest fails validation.

## Template Versus Final Record

Create a draft template with:

```bash
python scripts/labos_case.py new-decision-record \
  exports/example-incomplete-gan-rf-pa-review \
  --output decisions/example-incomplete-gan-rf-pa-decision.json
```

The generated template is deterministic. It leaves reviewer, decision owner, route decisions, rationale, evidence, approval fields, and attestations blank or false. It has `record_status: draft`, `review_outcome: pending`, and `customer_release_status: blocked`.

Validate a record with:

```bash
python scripts/labos_case.py validate-decision-record \
  exports/example-incomplete-gan-rf-pa-review \
  decisions/example-incomplete-gan-rf-pa-decision.json
```

Use `--json` for deterministic JSON output.

## Allowed Review Outcomes

- `pending`: draft record; route approvals must remain empty. Default validation normally returns `WARN`.
- `approved`: final human approval of one or more routes. It requires a `READY_FOR_HUMAN_DECISION` package, completed human fields, evidence references, acknowledgements, attestations, and addressed risk acceptance.
- `deferred`: final decision to defer. It requires rationale, additional evidence, acknowledgements, and attestations. Deferral is not rejection.
- `rejected`: final decision to reject one or more routes. It requires rejected route IDs and rationale. Rejection is not proof of physical impossibility unless evidence supports that claim.
- `more_evidence_required`: final decision that no route can be approved yet. It requires rationale and additional evidence, and it cannot approve a route.

`HOLD_FOR_DATA` and `HOLD_FOR_MEASUREMENT` packages cannot be approved. `READY_FOR_ARCHITECTURE_SCREENING` is still not final approval.

## Route List Semantics

Approved, rejected, and deferred route IDs must be canonical pattern IDs from the bound review package. Recognized aliases produce a warning and identify the canonical replacement. Unknown route IDs fail validation. The three route lists must be mutually disjoint.

## Customer Release Guardrails

`customer_release_status: approved` requires an approved final record, valid package binding, non-empty customer release basis, evidence references, all acknowledgements, both human attestations, and `READY_FOR_HUMAN_DECISION`. This validator does not replace legal, quality, regulatory, or corporate authorization.

## Identity And Attestation

The system does not verify identity. It validates that final records contain non-empty human-entered name and role fields where required. Human attestations are declarations only; they are not cryptographic or digital signatures, non-repudiation, tokens, or signature images.

## Validation Status And Exit Codes

- `PASS`: structure and decision guardrails pass; exit code `0`.
- `WARN`: draft, alias, duplicate, or incomplete-review warnings; exit code `1`.
- `FAIL`: binding mismatch, invalid package, malformed JSON, unsafe approval, unknown route, or schema/rule failure; exit code `2`.

## File Safety

`new-decision-record` writes only the explicit `--output` file. It refuses protected paths inside canonical case folders, `patterns/`, `memory/`, `.git/`, the repository root, and existing directories. It refuses overwrite unless `--force` is supplied.

`validate-decision-record` is read-only. It does not modify the decision record, review package, canonical case files, `02_decision_board.md`, `patterns/`, or `memory/`.

## Future Canonical Write Workflow

Any future workflow that copies an approved decision into `02_decision_board.md` must remain explicit, reviewable, and separate. The Human Decision Record is a prerequisite artifact, not an automatic write permission.
