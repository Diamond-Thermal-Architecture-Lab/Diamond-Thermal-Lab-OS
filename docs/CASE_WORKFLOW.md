# Case Workflow

## Purpose

The case workflow turns an incomplete thermal management problem into a reviewable architecture decision trail.

## Workflow

case initialization
-> intake completion
-> deterministic triage
-> Decision Board preview
-> Decision Review Package
-> human review
-> thermal design passport
-> architecture comparison
-> approved Decision Board
-> validation planning
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

Use the Decision Board preview after triage to combine the current evidence, candidate patterns, hold points, and next actions. It is also read-only; a separate reviewed workflow is required before editing `02_decision_board.md`:

```bash
python scripts/labos_case.py decision-board cases/example-incomplete-gan-rf-pa/
python scripts/labos_case.py decision-board cases/example-incomplete-gan-rf-pa/ --json
```

Export a Decision Review Package when the preview should be shared, archived, or inspected by reviewers without modifying the canonical case:

```bash
python scripts/labos_case.py export-decision-review cases/example-incomplete-gan-rf-pa/ --output-dir exports/example-incomplete-gan-rf-pa-review
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
