# Decision Board Preview Guide

## Purpose

`labos_case.py decision-board` produces a concise, deterministic preview that brings together an existing canonical case, its structured triage result, referenced pattern candidates, current gaps, hold points, and next actions. It is a screening aid for human review, not an approved engineering decision.

## Read-only Behavior

The command reads the case but does not create, edit, rename, or delete any canonical artifact. In particular, it does not write `02_decision_board.md`. A future explicit write workflow must remain separate, reviewable, and opt-in.

## Board Statuses And Decision States

- `HOLD_FOR_DATA`: triage found missing critical thermal inputs.
- `HOLD_FOR_MEASUREMENT`: triage found measurement evidence is the primary blocker.
- `READY_FOR_ARCHITECTURE_SCREENING`: inputs support first-pass route comparison only.
- `READY_FOR_HUMAN_DECISION`: complete inputs plus an explicit reviewed comparison-evidence marker support human decision review.

The decision state is `deferred`, `screening`, or `human_review_required` as appropriate. Pattern selection by itself can never create `READY_FOR_HUMAN_DECISION`.

## Triage And Patterns

The builder calls the structured triage engine directly; it does not parse triage terminal output or duplicate triage rules. It carries triage rule IDs into the preview and uses only board-specific `BOARD-*` rule IDs for board status, route framing, actions, holds, and claim guardrails.

Referenced patterns are screening candidates, not recommendations. Canonical IDs are shown in output even if a manually written case uses a recognized alias. Diamond-related candidates retain interface and bonding/contact validation needs. `PAT-GAN-DIA-001` remains a higher-integration-risk candidate, while `PAT-CONV-PKG-001` remains a legitimate neutral package-level route.

## Candidate And Deferred Routes

Candidate routes show the evidence state, key uncertainties, required validation, and a decision status. A deferred route has not been rejected: it is held until a named data, measurement, interface, or integration evidence gap is resolved. The preview does not rank routes without case-specific comparison evidence and does not invent routes when no approved pattern candidate is referenced.

## Hold Points And Claims

Hold points prevent premature FEM, material optimization, supplier commitments, or customer claims when their prerequisites are absent. Claim guardrails keep screening output, supplier statements, simulations, and measurements distinct. Use the claim ledger and validation plan before strengthening any external statement.

## Usage

```bash
python scripts/labos_case.py decision-board cases/example-incomplete-gan-rf-pa/
python scripts/labos_case.py decision-board cases/example-incomplete-gan-rf-pa/ --json
```

`--json` prints valid JSON only and is deterministic for an unchanged case. A valid preview, including a HOLD state, exits with code `0`; invalid or unreadable case input exits with code `2`.

## Review Package Export

The preview can be exported into a separate Decision Review Package for human inspection:

```bash
python scripts/labos_case.py export-decision-review \
  cases/example-incomplete-gan-rf-pa/ \
  --output-dir exports/example-incomplete-gan-rf-pa-review
```

The exporter uses the structured preview result directly. It writes package artifacts outside the canonical case folder and does not modify `02_decision_board.md`.

## Canonical Proposal Boundary

The preview is an initial screening artifact; the review package archives it; the Human Decision Record captures a human outcome; and a Canonical Decision Proposal renders a separate proposed replacement plus a unified diff. None of those layers writes the actual approved canonical `02_decision_board.md`. Any application remains a separate explicit PR workflow.

## Adding A Board Rule

Add a focused, deterministic rule only for logic beyond triage. Give it a stable `BOARD-<FAMILY>-<NUMBER>` ID, preserve triage rule IDs instead of restating them, add a unit test, and document any new decision consequence. Keep the rule conservative: it may frame a hold or a next action, but it must not fabricate validation or select a winning architecture.
