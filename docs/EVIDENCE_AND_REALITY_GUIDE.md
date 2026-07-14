# Evidence And Reality Guide

## Purpose

This optional sidecar layer connects engineering claims to Evidence Objects, Measurement References, and read-only Prediction-Reality Records. It supports future Gold Cases and evidence-graph work without changing the 12 numbered Canonical Case files.

## Objects And Relationships

`Evidence Object -> Measurement Reference -> Prediction-Reality Record`

Evidence Objects may support or contradict existing Claim Ledger IDs. Measurement References point to compatible evidence. Prediction-Reality Records point to a measurement and prediction evidence IDs. All links are checked locally; a link does not prove technical validity.

## Commands

```bash
python scripts/labos_case.py new-evidence cases/example-case/ --evidence-id EVD-001 --type measurement --output cases/example-case/evidence/EVD-001.json
python scripts/labos_case.py validate-evidence cases/example-case/ cases/example-case/evidence/EVD-001.json
python scripts/labos_case.py new-measurement-reference cases/example-case/ --measurement-id MSR-001 --evidence-id EVD-001 --output cases/example-case/measurements/MSR-001.json
python scripts/labos_case.py validate-measurement-reference cases/example-case/ cases/example-case/measurements/MSR-001.json
python scripts/labos_case.py new-prediction-reality-record cases/example-case/ --record-id PRL-001 --measurement-id MSR-001 --output cases/example-case/prediction_reality/PRL-001.json
python scripts/labos_case.py validate-prediction-reality-record cases/example-case/ cases/example-case/prediction_reality/PRL-001.json --json
python scripts/labos_case.py evidence-summary cases/example-case/ --json
```

## Status And Validation

`PASS` means the object is structurally suitable and traceable. `WARN` normally marks draft, planned, missing-value, unit-limitation, or human-review work. `FAIL` marks malformed input, broken references, invalid identifiers, unsafe paths, or prohibited state transitions. None of these statuses validates a model, approves an architecture, or authorizes customer release.

## Comparison

When quantity and unit strings match exactly, the read-only comparison calculates `signed_error = reality - prediction`, `absolute_error = abs(signed_error)`, and `relative_error_percent = absolute_error / abs(reality) * 100`. A zero reality value yields no relative percentage. Unit conversion and accuracy ranking are intentionally out of scope.

## Confidentiality Boundary

Store only opaque controlled references and optional lowercase SHA256 hashes. Do not copy raw CSVs, images, result databases, proprietary model files, absolute paths, credentials, customer names, supplier pricing, or process recipes. Templates contain TODO/null placeholders and do not fabricate results.

## Limits

This layer is not a complete Evidence Graph, Gold Case certification system, model calibration framework, solver adapter, experiment automation system, or AI orchestration layer. Human review remains required before learning or decision changes.
