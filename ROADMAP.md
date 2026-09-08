# Roadmap

## Role of This Roadmap

This roadmap sequences repository structure and validation work without creating large technical documentation prematurely. It should be updated through reviewed PRs as the Lab OS matures.

## Phase 0: L0 Lab OS

Goal: establish repository operating structure.

- Create contribution rules, agent guidance, and PR review expectations.
- Add reusable templates for task briefs, design docs, simulation cases, measurement plans, substrate specs, and literature notes.
- Add MVP decision-system templates, issue forms, cost-control policy, API policy, confidentiality guide, claim ledger guide, and a sanitized example case.
- Define labels for layers, work type, status, domain, and priority.
- Keep README-level project framing separate from controlled technical artifacts.

## Phase 1: L1 Architecture

Goal: define non-confidential architecture framing.

- Identify public-safe architecture questions.
- Capture system boundaries and interfaces without proprietary implementation details.
- Define which decisions require simulation, measurement, or external literature support.

## Phase 2: L2 Engineering Case

Goal: create focused engineering cases.

- Use one task brief per case.
- Define assumptions, comparison basis, and expected outputs.
- Keep analysis scoped and avoid unreviewed performance claims.

## Phase 3: L3 Validation

Goal: establish measurement and evidence workflows.

- Create measurement plans with anonymized sample identifiers.
- Define data handling and review expectations.
- Separate raw data handling from public-safe repository summaries.

## Phase 4: L4 Specification

Goal: create reviewed public-safe specifications.

- Convert validated requirements into controlled specs.
- Track version history and review state.
- Keep restricted process details out of public-facing specification artifacts.

## Completed M0-M12

The initial Lab OS foundation is complete: canonical case structure, local no-API checks and CI, pattern and memory references, deterministic triage, Decision Board preview, review packages, Human Decision Records, and Canonical Decision Proposals.

## M13: Evidence And Prediction-Reality Foundation

M13 adds optional Evidence Objects, Measurement References, and Prediction-Reality Records. It is a deterministic local protocol for controlled references, hashes, traceability checks, and read-only comparison. It is not a complete Evidence Graph, Gold Case certification system, model-calibration system, or experiment adapter.

## M14: Reality-Calibrated Thermomechanical Triage

M14 adds deterministic qualitative screening for elevated-temperature deposited-layer integration on membranes or thin structures. It uses a Gold Case learning loop to expose missing thermomechanical evidence, process-fixture boundaries, scale-up evidence, and downstream compatibility requirements. It is a screening and learning milestone, not a validated thermomechanical solver, material database, or automatic calibration system.

## M15A: Retrospective Thermomechanical Scope-Boundary Benchmark

M15A adds a second public-safe, artifact-separated benchmark for the M14 rule family using a thermally grown SiO2 released-membrane literature case. It is outcome-value-withheld and retrospective, not agent-blind or prospective. The case records a strict M14 process-sequence scope boundary, unsupported adjacent-scope transfer, generic triage false positives, and Decision Board coherence defects without modifying M14 rules or frozen baseline artifacts.

## M15B: Independent In-Scope Generalization Benchmark

M15B Phase 5 assessment is complete. The protocol-defined Phase 6 independent review issued `RECOMMEND_MERGE` for the exact candidate head [`1242a45fac5e248c14a7eb8b81e67f4b440634a8`](https://github.com/Diamond-Thermal-Architecture-Lab/Diamond-Thermal-Lab-OS/pull/34#issuecomment-5472935707). The Phase 5 assessment artifacts were subsequently merged through [PR #34](https://github.com/Diamond-Thermal-Architecture-Lab/Diamond-Thermal-Lab-OS/pull/34). The accepted scientific disposition is `in_scope_generalization_supported`; the governance disposition is `governance_pass`; and P3 remains a historical `PARTIAL` assessment result.

The subsequent M14 process-history correction in [PR #35](https://github.com/Diamond-Thermal-Architecture-Lab/Diamond-Thermal-Lab-OS/pull/35) was merged after known/synthetic regression validation. It did not re-score M15B, update its historical execution baseline, or produce new independent generalization evidence. The repository/GitHub record does not establish a deployment conclusion for that correction.

The governing pre-registration protocol is
[`docs/benchmarks/M15B_PRE_REGISTRATION_PROTOCOL.md`](docs/benchmarks/M15B_PRE_REGISTRATION_PROTOCOL.md)

## Proposed M16A: Engineering Problem Compiler And Quantitative Thermal Core

M16A is the next proposed quantitative engineering capability milestone. It will define a provenance-bearing Engineering Problem Representation and a deterministic, auditable first thermal core for unit normalization, steady-state 1D multilayer/TBR evaluation, candidate comparison, parameter sweeps, sensitivity, evidence gaps, and model-applicability checks. The initial vertical is a public-safe GaN/high-power device to diamond heat-spreader layer to downstream cooling path. Calculation remains separate from human review and canonical approval. See [`docs/M16A_ENGINEERING_PROBLEM_COMPILER.md`](docs/M16A_ENGINEERING_PROBLEM_COMPILER.md).

## H1 Priorities

- Real Gold Cases with reviewed public-safe evidence.
- Evidence and measurement objects linked to real controlled data sources.
- Prediction-Reality learning loops with human review.
- Explicit PR-based canonical application after human review.

## Planned After Additional Case Validation

- A Quick Case / Visual Thermal Canvas interface after the professional kernel is validated through additional cases.

## Later Stages

Future work beyond M16A may include extensions to the Engineering Problem Compiler, higher-fidelity solver and experiment adapters, Agent support, and engineering benchmarks. These remain future capabilities and must not be represented as implemented.
