# Pattern Library Guide

## What Patterns Are

Patterns are reusable thermal architecture route descriptions. They capture when a route might fit, when it should not be used, critical assumptions, red flags, validation paths, supplier questions, and claim-safety guidance.

Patterns are not automatic recommendations. They help compare diamond and non-diamond routes without forcing a diamond answer.

## Relationship To Architecture Genomes

Each pattern includes an architecture genome mapping:

- heat source
- substrate
- bonding interface
- heat spreader
- package path
- cooling boundary
- manufacturing route
- validation method
- risk profile

Case-specific architecture genomes may reference pattern IDs, then add case-specific assumptions and unknowns.

## Using `pattern_index.yml`

Use `patterns/pattern_index.yml` to scan available patterns by route type, maturity level, typical use case, primary risks, required validation, public-safe status, and related case artifacts.

Every pattern ID used in a case must match an entry in `patterns/pattern_index.yml`. The local checker reports known references, warns about unknown internal references, and fails when a customer memo relies on an unknown ID.

## Referencing Patterns In Case Files

Add pattern IDs to:

- `03_architecture_genomes.yml`
- `04_design_space_scorecard.md`
- `05_red_flags.md`
- `07_validation_plan.md`
- `08_supplier_specification.md`
- `10_claim_ledger.yml`

Pattern references should clarify why a route is being considered. They do not turn screening assumptions into validated claims.

When a pattern supports a claim, record the claim as `pattern_based`, `screening`, or `architecture_screening` where appropriate. Keep assumptions, confidence, validation status, evidence, reviewer, and public-release state explicit. A pattern is decision context, not validation evidence.

## Avoiding Overclaiming

- Do not cite a pattern as proof of performance.
- Do not compare bulk material values without interface and boundary context.
- Do not present screening ranges as measured values.
- Do not describe direct GaN-on-Diamond as the default first step without case evidence.
- Keep customer-facing language tied to claim ledger status.

## Adding A New Pattern

1. Add a Markdown file under `patterns/`.
2. Include the required pattern sections.
3. Add an entry to `patterns/pattern_index.yml`.
4. Add any reusable material, interface, validation, or supplier memory separately under `memory/`.
5. Keep the pattern public-safe unless there is a reviewed reason to restrict it.
