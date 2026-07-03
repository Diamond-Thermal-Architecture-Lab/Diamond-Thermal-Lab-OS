# Case File Naming Standard

## Purpose

Numbered case files keep each thermal decision case readable, diffable, and consistent across GitHub issues and pull requests.

## Canonical MVP Case Folder

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

## Naming Rules

- Use two-digit numeric prefixes to preserve review order.
- Use snake_case file names.
- Use `.yml` when stable structured fields are the main artifact.
- Use `.md` when human-readable rationale, comparison, or memo language is the main artifact.
- Keep legacy unnumbered Markdown files when they contain useful review context.

## File Roles

| File | Role |
| --- | --- |
| `00_problem_intake.yml` | Structured intake for the incomplete problem. |
| `01_thermal_design_passport.yml` | Structured thermal context and route summary. |
| `02_decision_board.md` | Human-readable decision state. |
| `03_architecture_genomes.yml` | Structured architecture route definitions. |
| `04_design_space_scorecard.md` | Human-readable scorecard and assumptions. |
| `05_red_flags.md` | Risks that could invalidate a recommendation. |
| `06_next_best_action.md` | Bounded next step to reduce uncertainty. |
| `07_validation_plan.md` | Validation and falsification plan. |
| `08_supplier_specification.md` | Supplier request and acceptance framing. |
| `09_customer_memo.md` | Conservative customer-facing summary. |
| `10_claim_ledger.yml` | Structured claim safety ledger. |
| `11_engineering_memory_entry.md` | Reusable lesson after review. |

## Review Rule

The numbered sequence is canonical for new MVP cases. Existing Markdown templates remain available for drafting and detailed review.
