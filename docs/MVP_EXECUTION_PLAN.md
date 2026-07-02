# MVP Execution Plan

## Purpose

This plan defines the first docs-only implementation of Diamond Thermal Lab OS. The goal is to make the system usable through GitHub issues, Markdown case folders, templates, and pull request review without API calls or runtime dependencies.

## MVP Scope

In scope:

- Issue templates for thermal intake, supplier requests, validation feedback, and customer questions.
- Case folders under `cases/<case_id>/`.
- Markdown templates for all decision-system outputs.
- Claim ledger guidance and confidentiality rules.
- Manual PR review checks for assumptions, validation paths, and customer-safe language.

Out of scope:

- API automation.
- Paid GitHub Actions.
- Automatic report generation.
- Confidential data ingestion.
- Validated thermal simulation results.

## Execution Order

1. Open a problem intake issue.
2. Create a case folder.
3. Fill the intake and thermal design passport.
4. Build the decision board and architecture comparison.
5. Record red flags and next best action.
6. Draft validation plan and supplier specification.
7. Draft customer memo with conservative language.
8. Create claim ledger.
9. Add engineering memory entry.
10. Review in a pull request.

## Definition Of Done

- Every claim has a basis or is marked as an assumption.
- No measured result is invented.
- No proprietary process detail is exposed.
- Diamond and non-diamond routes are compared neutrally.
- The next best action is bounded, reviewable, and validation-oriented.
- API usage is absent or explicitly justified as not used.
