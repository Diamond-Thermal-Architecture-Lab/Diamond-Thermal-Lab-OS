# API Usage Policy

## MVP Rule

The MVP does not require API calls. API use is disabled by default and must not be introduced through templates, GitHub Actions, scripts, or hidden dependencies.

## Allowed Future API Tasks

Only the following future tasks may justify API use after explicit review:

1. Judge whether a task is executable.
2. Break a task into a short plan.
3. Decide whether Codex is needed.
4. Recommend a cheaper alternative.

These tasks are decision gates, not content factories.

## Explicitly Forbidden In MVP

- API-generated long reports.
- API-generated customer memos.
- API-generated full case packs.
- GitHub Actions that automatically call paid APIs.
- Sending confidential full case files to API by default.

## Confidentiality Rule

Do not send restricted, customer-confidential, or full internal case files to an API by default. If future API use is reviewed, send only the minimum sanitized context required for the decision gate.

## PR Requirement

Every pull request must state whether API was used, whether it was necessary, and what data was exposed. For the MVP, the expected answer is `No API used`.
