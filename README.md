# Diamond Thermal Lab OS

Diamond Thermal Lab OS is a GitHub-backed, model-agnostic, evidence-centered engineering intelligence operating system for complex thermal engineering. It preserves persistent engineering state and helps compile incomplete thermal problems into traceable decisions, evidence references, prediction-versus-reality comparisons, and human-reviewed learning records.

Mission: compile thermal problems into executable, evidence-backed and continuously learning engineering capabilities. Structured data and validator PASS states provide structural and traceability quality only; they are not technical validation or architecture approval.

Chinese mission: 把热管理问题编译成可执行、有证据支持、能够持续学习的工程能力。

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

## Local Case Checker

Run the local no-API case checker before review:

```bash
python scripts/labos_check_case.py cases/example-incomplete-gan-rf-pa/
python scripts/labos_check_case.py cases/example-incomplete-gan-rf-pa/ --strict
```

The checker screens for missing files, missing thermal inputs, unsafe claims, confidentiality markers, and common thermal architecture red flags. It does not validate a design or replace engineering judgment.

## Evidence And Reality Foundation

M13 adds optional, JSON sidecar engineering objects. Existing 12-file canonical cases remain unchanged, and raw confidential data stays outside the repository as controlled references and hashes.

```bash
python scripts/labos_case.py new-evidence cases/example-case/ --evidence-id EVD-001 --type measurement --output cases/example-case/evidence/EVD-001.json
python scripts/labos_case.py new-measurement-reference cases/example-case/ --measurement-id MSR-001 --evidence-id EVD-001 --output cases/example-case/measurements/MSR-001.json
python scripts/labos_case.py new-prediction-reality-record cases/example-case/ --record-id PRL-001 --measurement-id MSR-001 --output cases/example-case/prediction_reality/PRL-001.json
python scripts/labos_case.py evidence-summary cases/example-case/ --json
```

Implemented today: deterministic templates, structural validation, controlled references, exact-unit comparison, and read-only summaries. Future targets include Gold Cases, solver and experiment adapters, an Engineering Problem Compiler, and evidence-graph capabilities; they are not implemented here.

## Deterministic Triage

```bash
python scripts/labos_case.py triage cases/example-incomplete-gan-rf-pa/
python scripts/labos_case.py triage cases/example-incomplete-gan-rf-pa/ --json
```

Triage is read-only, deterministic screening. It identifies missing data, candidate bottlenecks, rule traces, and a conservative next action; it is not validation.

## Decision Board Preview

```bash
python scripts/labos_case.py decision-board cases/example-incomplete-gan-rf-pa/
python scripts/labos_case.py decision-board cases/example-incomplete-gan-rf-pa/ --json
```

The Decision Board preview combines deterministic triage, selected pattern candidates, missing data, hold points, and claim guardrails into one read-only decision view. It does not edit `02_decision_board.md`, select a winning route, or turn a pattern into a recommendation.

## Decision Review Package

```bash
python scripts/labos_case.py export-decision-review \
  cases/example-incomplete-gan-rf-pa/ \
  --output-dir exports/example-incomplete-gan-rf-pa-review
```

The exporter writes a deterministic review package outside the canonical case folder. It includes the Decision Board preview, structured JSON, source/artifact hashes, and a blank human review checklist. It does not approve a decision or edit `02_decision_board.md`.

## Human Decision Record

```bash
python scripts/labos_case.py new-decision-record \
  exports/example-incomplete-gan-rf-pa-review \
  --output decisions/example-incomplete-gan-rf-pa-decision.json

python scripts/labos_case.py validate-decision-record \
  exports/example-incomplete-gan-rf-pa-review \
  decisions/example-incomplete-gan-rf-pa-decision.json
```

The Human Decision Record binds a human-entered decision to one review package manifest. The template is blank and pending by default, and validation checks structure, binding, route IDs, customer-release guardrails, and attestations. It does not verify identity, create a cryptographic signature, or update canonical case files.

## Canonical Decision Proposal

```bash
python scripts/labos_case.py propose-canonical-decision \
  cases/example-case/ \
  exports/example-case-review/ \
  decisions/example-case-decision.json \
  --output-dir proposals/example-case-canonical-decision
```

This creates a deterministic proposal package only after a final Human Decision Record validates as `PASS` and its source case hashes still match. It produces a proposed Decision Board replacement, a review diff, a manifest, and a blank application checklist. It does not edit `02_decision_board.md` or apply a decision.

## Create A New Case

Use the local no-API case generator to create a complete numbered case folder:

```bash
python scripts/labos_case.py new --case-id example-new-case --title "Example new thermal case"
python scripts/labos_case.py check cases/example-new-case/
python scripts/labos_case.py list
```

List approved patterns and initialize a screening-only route comparison with exact aliases from the local index:

```bash
python scripts/labos_case.py list-patterns

python scripts/labos_case.py new \
  --case-id gan-pa-route-comparison \
  --title "GaN PA route comparison" \
  --pattern PAT-CONVENTIONAL-PACKAGE-UPGRADE \
  --pattern PAT-DIAMOND-SUBMOUNT
```

The generator resolves aliases to stable compact canonical IDs, so generated case files store `PAT-CONV-PKG-001` and `PAT-DIA-SUBMOUNT-001`. It creates conservative draft placeholders only. Pattern selection creates screening candidates, not validated recommendations. It does not generate final conclusions, measured results, customer claims, or API output.

## Continuous Integration

CI runs local no-API repository checks on pull requests to `main` and pushes to `main`. It does not use the OpenAI API, does not require API keys, and does not run paid AI automation. The workflow checks required repository structure, runs the example case checker, allows the intentionally incomplete example case to produce a strict-mode WARN, and runs the standard-library unit tests.

## How To Use

1. Open a GitHub issue using the closest issue template: thermal problem intake, supplier specification request, validation feedback, or customer question.
2. Create a case folder under `cases/<case_id>/`.
3. Copy the needed templates from `templates/` into the case folder.
4. Complete the case artifacts in the order described in `docs/CASE_WORKFLOW.md` and `docs/CASE_FILE_NAMING_STANDARD.md`.
5. Open a pull request and complete the PR confidentiality, claim safety, and API-use checks.

## Main Docs

- [Lab OS](LAB_OS.md)
- [Roadmap](ROADMAP.md)
- [Contributing](CONTRIBUTING.md)
- [MVP Execution Plan](docs/MVP_EXECUTION_PLAN.md)
- [Case Workflow](docs/CASE_WORKFLOW.md)
- [Case Generator Guide](docs/CASE_GENERATOR_GUIDE.md)
- [Triage Engine Guide](docs/TRIAGE_ENGINE_GUIDE.md)
- [Decision Board Guide](docs/DECISION_BOARD_GUIDE.md)
- [Decision Review Package Guide](docs/DECISION_REVIEW_PACKAGE_GUIDE.md)
- [Human Decision Record Guide](docs/HUMAN_DECISION_RECORD_GUIDE.md)
- [Canonical Decision Proposal Guide](docs/CANONICAL_DECISION_PROPOSAL_GUIDE.md)
- [Case File Naming Standard](docs/CASE_FILE_NAMING_STANDARD.md)
- [Schema Guide](docs/SCHEMA_GUIDE.md)
- [Evidence And Reality Guide](docs/EVIDENCE_AND_REALITY_GUIDE.md)
- [Pattern Library Guide](docs/PATTERN_LIBRARY_GUIDE.md)
- [Memory Policy](docs/MEMORY_POLICY.md)
- [Cost Control Policy](docs/COST_CONTROL_POLICY.md)
- [API Usage Policy](docs/API_USAGE_POLICY.md)
- [Confidentiality Guide](docs/CONFIDENTIALITY_GUIDE.md)
- [Claim Ledger Guide](docs/CLAIM_LEDGER_GUIDE.md)
- [Structured Lab OS Layer](labos/README.md)
- [Pattern Library](patterns/README.md)
- [Engineering Memory](memory/README.md)

## Example Case

See `cases/example-incomplete-gan-rf-pa/` for a sanitized example where a customer is considering diamond and non-diamond routes for an overheating GaN RF power amplifier module. The example is public-safe and intentionally preliminary.
