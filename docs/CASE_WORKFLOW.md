# Case Workflow

## Purpose

The case workflow turns an incomplete thermal management problem into a reviewable architecture decision trail.

## Workflow

case initialization
-> intake completion
-> deterministic triage
-> thermomechanical screening when elevated-temperature layer integration is in scope
-> Decision Board preview
-> Decision Review Package
-> Human Decision Record
-> record validation
-> Canonical Decision Proposal
-> explicit PR-based canonical application
-> thermal design passport
-> architecture comparison
-> approved Decision Board
-> validation planning
-> optional evidence capture and measurement references
-> optional prediction-versus-reality comparison
-> optional artifact-separated Gold Case benchmark
-> human-reviewed learning record
-> red flags
-> next best action
-> supplier specification
-> customer memo
-> claim ledger
-> engineering memory update

## Folder Shape

New MVP cases should use the numbered canonical structure. The preferred way to start a canonical case folder is the local no-API generator:

```bash
python scripts/labos_case.py new --case-id example-new-case --title "Example new thermal case"
```

When reusable route candidates are already known, initialize up to five approved patterns during case creation:

```bash
python scripts/labos_case.py new --case-id example-pattern-case --title "Example pattern case" --pattern PAT-CONVENTIONAL-PACKAGE-UPGRADE --pattern PAT-DIAMOND-SUBMOUNT
```

Run deterministic triage after completing the initial intake and before human route review. It reads the case only and cannot replace the validation plan:

```bash
python scripts/labos_case.py triage cases/example-incomplete-gan-rf-pa/
```

For a membrane or thin-layer route with elevated-temperature material integration, read the thermomechanical screening output before advancing the candidate. It may request property, thermal-history, stress/warpage, fixture-boundary, scale-up, or downstream-compatibility evidence. It is a qualitative guardrail, not a stress model or a route approval.

Use the Decision Board preview after triage to combine the current evidence, candidate patterns, hold points, and next actions. It is also read-only; a separate reviewed workflow is required before editing `02_decision_board.md`:

```bash
python scripts/labos_case.py decision-board cases/example-incomplete-gan-rf-pa/
python scripts/labos_case.py decision-board cases/example-incomplete-gan-rf-pa/ --json
```

After validation planning, cases may optionally add evidence, measurements, and prediction-reality sidecars. These do not alter the canonical 12-file standard and are not an approval workflow:

```bash
python scripts/labos_case.py evidence-summary cases/example-incomplete-gan-rf-pa/
```

For a Gold Case benchmark, freeze the completed canonical input and its deterministic export in a separate commit before adding source outcome evidence. Treat any missed screening concern, false positive, scope mismatch, or Decision Board coherence defect as a benchmark result for later human-reviewed rule work; never rewrite the frozen input or export after evidence reveal.

M15A is a retrospective, outcome-value-withheld scope-boundary benchmark rather than a knowledge-isolated in-scope generalization test. A future M15B benchmark should separate phase-one and reveal execution context, predeclare applicability and scoring, include a negative or boundary control, and keep rule changes out of the benchmark PR.

M15B execution is governed by
[`M15B_PRE_REGISTRATION_PROTOCOL.md`](benchmarks/M15B_PRE_REGISTRATION_PROTOCOL.md).
Candidate selection, sealed relevance registration, Blind Input Packet
construction, phase-one execution, evidence reveal, and scoring must follow that
protocol in order.

Candidate-independent benchmark hash authority, committed Git-object identity,
and deterministic tree hashing are documented in
[`BENCHMARK_INTEGRITY_GUIDE.md`](BENCHMARK_INTEGRITY_GUIDE.md).
Sealed-manifest, leakage-audit, and execution-baseline infrastructure remain
separate Phase 0.5 gates before candidate screening.

External sealed-artifact hashing, strict registration-manifest validation,
reveal-time byte verification, and sealed-filename absence auditing are
documented in
[`BENCHMARK_SEALING_GUIDE.md`](BENCHMARK_SEALING_GUIDE.md).
Private leakage-policy scanning and execution-baseline verification remain
separate Phase 0.5 gates before candidate screening.

Private external leakage-policy validation, exact policy-byte identity, opaque
token IDs, and public-safe validation summaries are documented in
[`BENCHMARK_LEAKAGE_POLICY_GUIDE.md`](BENCHMARK_LEAKAGE_POLICY_GUIDE.md).
Role D content scanning, leakage-audit report generation, and execution-baseline
verification remain separate Phase 0.5 gates before candidate screening.

Export a Decision Review Package when the preview should be shared, archived, or inspected by reviewers without modifying the canonical case:

```bash
python scripts/labos_case.py export-decision-review cases/example-incomplete-gan-rf-pa/ --output-dir exports/example-incomplete-gan-rf-pa-review
```

Create and validate a Human Decision Record only after a review package exists. The template is blank and pending; the validator checks binding and guardrails but does not verify identity or write the canonical Decision Board:

```bash
python scripts/labos_case.py new-decision-record exports/example-incomplete-gan-rf-pa-review --output decisions/example-incomplete-gan-rf-pa-decision.json
python scripts/labos_case.py validate-decision-record exports/example-incomplete-gan-rf-pa-review decisions/example-incomplete-gan-rf-pa-decision.json
```

```text
cases/<case_id>/
  00_problem_intake.yml
  01_thermal_design_passport.yml
  02_decision_board.md
  03_architecture_genomes.yml
  04_design_space_scorecard.md
  05_red_flags.md
  06_next_best_action.md
  07_validation_plan.md
  08_supplier_specification.md
  09_customer_memo.md
  10_claim_ledger.yml
  11_engineering_memory_entry.md
```

Existing unnumbered Markdown files may remain when they contain useful review context.

## Operating Rules

- Start with missing information, not preferred solutions.
- Compare diamond and non-diamond routes neutrally.
- Separate assumptions from facts.
- Add pattern references during architecture genome and scorecard creation when reusable routes apply, and verify every persisted ID against `patterns/pattern_index.yml`. CLI aliases are resolved to compact canonical IDs before case files are written.
- Pattern selection during case initialization creates screening scaffolding only. Keep all selected routes as candidates until case evidence and review support a stronger decision.
- Treat pattern references as decision support, not validation; pattern-based claims still require assumptions, confidence, validation status, and claim-ledger review.
- Treat the Decision Board preview as a screening aid, not an approved Decision Board. Keep route selection deferred until evidence and human review support it.
- Treat the Decision Review Package as review evidence only. It exports preview content and hashes, but it does not approve a route or write `02_decision_board.md`.
- Treat the Human Decision Record as a human-entered review artifact. It is not a cryptographic signature and does not automatically modify canonical case files.
- Identify red flags before making supplier requests.
- Recommend validation before expensive simulation when boundaries are unclear.
- Keep customer memo language conservative.
- Update memory only with reviewed and reusable lessons.

## Local Case Check

Run the local no-API checker before pull request review:

```bash
python scripts/labos_check_case.py cases/example-incomplete-gan-rf-pa/
python scripts/labos_check_case.py cases/example-incomplete-gan-rf-pa/ --strict
```

The checker reports missing artifacts, missing critical thermal fields, known and unknown pattern references, unsafe pattern-based claim states, confidentiality markers, and common thermal red flags. Its output is a screening aid only; it is not validation.
