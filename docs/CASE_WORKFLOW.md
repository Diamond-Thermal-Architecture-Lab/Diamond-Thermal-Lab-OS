# Case Workflow

## Purpose

The case workflow turns an incomplete thermal management problem into a reviewable architecture decision trail.

## Workflow

problem intake
-> thermal design passport
-> decision board
-> architecture comparison
-> red flags
-> next best action
-> validation plan
-> supplier specification
-> customer memo
-> claim ledger
-> engineering memory update

## Folder Shape

New MVP cases should use the numbered canonical structure. The preferred way to start a canonical case folder is the local no-API generator:

```bash
python scripts/labos_case.py new --case-id example-new-case --title "Example new thermal case"
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

The checker reports missing artifacts, missing critical thermal fields, claim-safety issues, confidentiality markers, and common thermal red flags. Its output is a screening aid only; it is not validation.
