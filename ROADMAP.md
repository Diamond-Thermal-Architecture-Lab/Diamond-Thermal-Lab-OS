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

## Recommended Next Milestones

- Create the first L0 issue to review labels and templates.
- Open a first L1 architecture task brief for public-safe system boundaries.
- Draft one L2 engineering case template instance using sanitized assumptions.
- Define an L3 validation data handling policy before adding measurement-derived summaries.
- Review the example GaN RF PA case and decide which case artifacts should be required for every MVP pull request.
