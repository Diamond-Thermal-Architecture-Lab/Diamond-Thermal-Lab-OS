# Lab OS Structured Layer

## Purpose

`labos/` holds the optional structured layer for Diamond Thermal Lab OS. It supports consistent case files without replacing the Markdown templates or the docs-first workflow.

## Contents

- `schemas/`: YAML schema contracts for structured case artifacts.
- `examples/`: Small schema examples or future public-safe fixtures.

## Operating Rules

- Schemas are documentation and lightweight contracts first.
- No API, paid automation, or external service is required.
- Markdown remains the primary human review surface.
- YAML files capture structured fields that should stay stable across cases.
- Do not put proprietary process details or customer-confidential full case data in public-safe examples.

## Canonical Case Flow

Use numbered files under `cases/<case_id>/`:

```text
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

The numbered files are canonical for new MVP cases. Existing unnumbered Markdown files may remain as useful legacy or review-friendly artifacts.
