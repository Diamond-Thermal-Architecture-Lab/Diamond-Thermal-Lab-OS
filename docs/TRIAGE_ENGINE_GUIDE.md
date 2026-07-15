# Triage Engine Guide

## Purpose

`labos_case.py triage` is a read-only deterministic first-pass assessment. It does not modify cases, recommend a final architecture, or validate a thermal conclusion.

## Classifications

The engine reports conservative classes including `insufficient_data`, `measurement_limited`, `cooling_boundary_limited`, `interface_limited_candidate`, `package_limited_candidate`, `material_limited_candidate`, and `design_space_unclear`.

Critical intake gaps take precedence. `NEEDS_DATA` identifies a missing critical input; `NEEDS_MEASUREMENT` identifies a decision blocked mainly by evidence; and `READY_FOR_SCREENING` means core inputs are adequate for first-pass comparison only. None of these statuses is a validated conclusion or a basis for customer performance claims.

## Rules and Confidence

Rules use stable `TRIAGE-<FAMILY>-<NUMBER>` IDs. Each triggered rule records its severity, finding, evidence, and enabled action. The engine normally reports `low` or `medium` confidence; it does not infer high confidence from incomplete case data. It selects one next action with the highest immediate decision impact and names conservative actions that should not be taken first, such as detailed FEM before geometry and cooling boundaries are defined.

## Thermomechanical Screening

When an existing case combines credible membrane or suspended-structure context, deposited/bonded/directly grown layer integration, and a thermally significant process, triage adds an optional `thermomechanical_screening` result. It reports known inputs, missing evidence, source-evidence limitations, and stable `TRIAGE-THERMOMECH-*` rules for property basis, thermal history, stress/warpage evidence, interface mechanical evidence, process-fixture boundaries, geometry scale-up, and downstream compatibility. A diamond submount, a generic film mention, or a deposition term alone does not activate this family.

This is qualitative screening only. It does not calculate stress, bow, warpage, delamination, or a probability of failure; it does not add numerical thresholds; and it does not make a route recommendation. A topic mention is not evidence. A positive case-text declaration is stated context, not independently reviewed evidence. A completed measurement remains source context pending review unless its relevant parent Evidence Object and Measurement Reference both match the case, are reviewed with non-empty reviewers, and link to each other by ID. A source-documented measurement or validator result remains distinct from separate case-specific stress and bow/warpage acceptance evidence and human review. Fixture identifiers and operating parameters alone do not define a process thermal boundary.

## Patterns and Read-only Behavior

Canonical and recognized alias pattern references are normalized through the shared pattern index. Patterns are screening context only: diamond routes require interface-risk consideration, direct GaN-on-Diamond remains a higher-integration-risk candidate, and conventional package improvement remains a legitimate candidate. The command reads existing canonical case files and does not write reports, scorecards, or other case artifacts.

## Decision Board Preview Input

Triage provides the structured input for the read-only Decision Board preview. The preview reuses the `TriageResult` directly, retaining its classifications, next-best action, confidence, and triggered rule IDs. It adds decision status, candidate-route framing, hold points, and claim guardrails without rerunning or duplicating triage rules. See [Decision Board Guide](DECISION_BOARD_GUIDE.md).

## Usage

```bash
python scripts/labos_case.py triage cases/example-incomplete-gan-rf-pa/
python scripts/labos_case.py triage cases/example-incomplete-gan-rf-pa/ --json
```

Every result includes stable rule IDs, evidence text, an action enabled by each rule, confidence, and a validation note. Patterns are screening context only; aliases normalize to canonical IDs. Add a rule by giving it a stable `TRIAGE-<FAMILY>-<NUMBER>` identifier and a focused test.
