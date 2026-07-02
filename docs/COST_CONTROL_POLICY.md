# Cost Control Policy

## Default Mode

Default mode is no-API. The MVP must remain usable with GitHub issues, Markdown templates, case folders, and pull request review.

## Tool Roles

ChatGPT Plus is used for strategy, prompt design, review, and customer language. Use it manually when judgment, framing, or language quality matters.

Codex is used for repository edits, templates, tests, workflow files, and consistency checks. Codex should keep changes narrow and preserve confidentiality before completeness.

## API Position

API is reserved only for optional future decision-gate tasks. API must not be used for long-form report generation in the MVP. API must be disabled by default.

## Forbidden Cost Patterns In MVP

- API-generated long reports.
- API-generated full case packs.
- Paid API calls from GitHub Actions.
- Batch processing of confidential case files.
- Automatic customer memo generation.

## Review Rule

Any proposed API use must explain the task, expected cost, cheaper alternative, confidentiality level, and why manual review is insufficient.
