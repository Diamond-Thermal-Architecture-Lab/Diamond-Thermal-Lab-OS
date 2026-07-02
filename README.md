# Diamond Thermal Lab OS

Diamond Thermal Lab OS is a GitHub-native thermal architecture decision system. It helps engineers convert incomplete semiconductor thermal management problems into traceable architecture decisions, architecture comparisons, red flags, validation plans, supplier specifications, customer-facing memos, claim ledgers, and reusable engineering memory.

Mission: compile thermal problems into validated architecture decisions.

Chinese mission: 把热管理问题编译成可验证的热架构决策。

This is not a chatbot, not merely a report generator, and not an API automation project. The MVP is a manual, docs-first workflow that runs through GitHub issues, Markdown case folders, templates, and pull request review.

## MVP Loop

Thermal Intake
-> Thermal Design Passport
-> Decision Board
-> Architecture Comparison
-> Red Flags
-> Next Best Action
-> Validation Plan
-> Supplier Specification
-> Customer Memo
-> Claim Ledger
-> Engineering Memory Update

Each loop should leave behind a reusable engineering memory entry so later work can reuse reviewed assumptions, risks, and decision patterns.

## No API Required

API usage is not required for the MVP. Default operation is no-API. Use ChatGPT Plus manually for strategy, prompt design, review, and customer language when needed. Use Codex for repository edits, templates, workflow files, and consistency checks. Do not add paid automation or API-calling GitHub Actions for the MVP.

## How To Use

1. Open a GitHub issue using the closest issue template: thermal problem intake, supplier specification request, validation feedback, or customer question.
2. Create a case folder under `cases/<case_id>/`.
3. Copy the needed templates from `templates/` into the case folder.
4. Complete the case artifacts in the order described in `docs/CASE_WORKFLOW.md`.
5. Open a pull request and complete the PR confidentiality, claim safety, and API-use checks.

## Main Docs

- [Lab OS](LAB_OS.md)
- [Roadmap](ROADMAP.md)
- [Contributing](CONTRIBUTING.md)
- [MVP Execution Plan](docs/MVP_EXECUTION_PLAN.md)
- [Case Workflow](docs/CASE_WORKFLOW.md)
- [Cost Control Policy](docs/COST_CONTROL_POLICY.md)
- [API Usage Policy](docs/API_USAGE_POLICY.md)
- [Confidentiality Guide](docs/CONFIDENTIALITY_GUIDE.md)
- [Claim Ledger Guide](docs/CLAIM_LEDGER_GUIDE.md)

## Example Case

See `cases/example-incomplete-gan-rf-pa/` for a sanitized example where a customer is considering diamond and non-diamond routes for an overheating GaN RF power amplifier module. The example is public-safe and intentionally preliminary.
