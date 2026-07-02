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

Each case should use:

```text
cases/<case_id>/
  intake.md
  thermal_design_passport.md
  decision_board.md
  architecture_comparison.md
  red_flags.md
  next_best_action.md
  validation_plan.md
  supplier_specification.md
  customer_memo.md
  claim_ledger.md
  engineering_memory_entry.md
```

## Operating Rules

- Start with missing information, not preferred solutions.
- Compare diamond and non-diamond routes neutrally.
- Separate assumptions from facts.
- Identify red flags before making supplier requests.
- Recommend validation before expensive simulation when boundaries are unclear.
- Keep customer memo language conservative.
- Update memory only with reviewed and reusable lessons.
