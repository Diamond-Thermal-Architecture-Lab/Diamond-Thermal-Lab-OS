# Schema Guide

## Purpose

The structured schema layer gives Diamond Thermal Lab OS stable field names for case intake, architecture comparison, claim review, validation planning, supplier requests, customer memos, and engineering memory.

Schemas do not replace Markdown templates. They sit beside the docs-first workflow so engineers can review readable Markdown while preserving structured YAML fields for future validation, search, or lightweight automation.

## Schema Location

Schemas live in `labos/schemas/`.

| Schema | Canonical Case File | Purpose |
| --- | --- | --- |
| `thermal_problem.schema.yml` | `00_problem_intake.yml` | Captures the incomplete thermal problem and missing data. |
| `thermal_design_passport.schema.yml` | `01_thermal_design_passport.yml` | Summarizes bottlenecks, candidates, assumptions, and next route. |
| `architecture_genome.schema.yml` | `03_architecture_genomes.yml` | Describes one architecture route in structured form. |
| `design_space_scorecard.schema.yml` | `04_design_space_scorecard.md` | Defines route scoring categories. |
| `red_flags.schema.yml` | `05_red_flags.md` | Defines fields for decision risks. |
| `next_best_action.schema.yml` | `06_next_best_action.md` | Defines fields for the next action. |
| `validation_plan.schema.yml` | `07_validation_plan.md` | Defines validation questions and falsification criteria. |
| `supplier_specification.schema.yml` | `08_supplier_specification.md` | Defines supplier request fields. |
| `customer_memo.schema.yml` | `09_customer_memo.md` | Defines customer-safe memo fields. |
| `claim_ledger.schema.yml` | `10_claim_ledger.yml` | Defines claim safety and release fields. |
| `engineering_memory_entry.schema.yml` | `11_engineering_memory_entry.md` | Defines reusable engineering memory fields. |
| `case_manifest.schema.yml` | optional manifest | Defines case-level metadata and artifact state. |
| `evidence_object.schema.json` | optional `evidence/EVD-001.json` | Controlled evidence metadata and Claim Ledger relationships. |
| `measurement_reference.schema.json` | optional `measurements/MSR-001.json` | Measurement metadata, controlled raw-data reference, and uncertainty basis. |
| `prediction_reality_record.schema.json` | optional `prediction_reality/PRL-001.json` | Prediction-to-measurement comparison metadata. |

## Optional Evidence Sidecars

The three JSON sidecar contracts are optional and do not change the 12 numbered Canonical Case files. They store metadata, hashes, controlled references, uncertainty statements, and traceability only. Raw measurement data, simulation files, proprietary models, and restricted details remain outside this repository.

## Review Rules

- Treat schemas as contracts for field names, not as a source of technical truth.
- Keep claims conservative until validation is complete.
- Keep interface thermal resistance, cooling boundary, and missing input fields explicit when they are unknown.
- Do not infer that diamond is preferred unless the case evidence supports it.
- Do not add confidential process details to public-safe YAML examples.
- A schema or validator PASS means structural and traceability quality only, not technical validation, model validation, or decision approval.

## Future Tooling

Future validation may check YAML files against these schemas, but the MVP does not require a validator, package manager, CI job, API call, or paid automation.
