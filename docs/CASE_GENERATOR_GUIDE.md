# Case Generator Guide

## Purpose

The local case generator creates a complete canonical case folder for Diamond Thermal Lab OS. It is a no-API helper for starting reviewable thermal architecture cases without manually copying every numbered artifact.

The generator creates draft placeholders only. It does not produce final engineering conclusions, measured results, supplier recommendations, or customer claims.

## Create A Case

```bash
python scripts/labos_case.py new --case-id example-new-case --title "Example new thermal case"
```

Optional fields can be supplied when known:

```bash
python scripts/labos_case.py new \
  --case-id gan-pa-customer-a \
  --title "GaN PA customer A overheating intake" \
  --application "high-power RF" \
  --device-type "GaN RF PA" \
  --confidentiality-level "customer-confidential" \
  --owner "thermal architect"
```

## Select Approved Patterns

Use repeatable `--pattern` options to seed screening-only pattern scaffolding. Compact canonical IDs are stable repository identifiers. Exact, case-sensitive aliases are accepted as CLI conveniences and resolve to their canonical ID before generation. Use the local index rather than inventing an ID:

```bash
python scripts/labos_case.py list-patterns
```

For one candidate, either input style works:

```bash
python scripts/labos_case.py new \
  --case-id gan-pa-submount-screening \
  --title "GaN PA submount screening" \
  --pattern PAT-DIAMOND-SUBMOUNT
```

For a route comparison:

```bash
python scripts/labos_case.py new \
  --case-id gan-pa-route-comparison \
  --title "GaN PA route comparison" \
  --pattern PAT-CONVENTIONAL-PACKAGE-UPGRADE \
  --pattern PAT-DIAMOND-SUBMOUNT \
  --pattern PAT-GAN-ON-DIAMOND
```

For example, `PAT-DIAMOND-SUBMOUNT` resolves to `PAT-DIA-SUBMOUNT-001`. Generated and persisted case files always contain compact canonical IDs only.

The generator accepts up to five unique patterns after alias normalization. Duplicate canonical/alias selections are deduplicated in first-occurrence order. An unknown ID or more than five selected patterns stops the command before it creates a case folder.

Selected patterns create low-confidence, unvalidated screening scaffolds in the design passport, architecture genomes, scorecard, red flags, validation plan, supplier specification, and claim ledger. Selection is not validation and is not a final architecture recommendation.

The case id must contain only lowercase letters, numbers, hyphen, and underscore. Path traversal, spaces, absolute paths, and shell-special names are rejected.

## Check A Case

```bash
python scripts/labos_case.py check cases/example-new-case/
```

The check command reuses the local case checker. A newly generated case may return `WARN` because it is intentionally incomplete, but it should not return `FAIL` when all canonical files and required intake fields are present.

## List Cases

```bash
python scripts/labos_case.py list
```

The list command prints folders under `cases/` and reports whether the canonical files appear to exist.

## List Patterns

```bash
python scripts/labos_case.py list-patterns
```

The command prints each canonical pattern ID first, followed by its accepted aliases, route type, maturity level, typical use case, and pattern file from `patterns/pattern_index.yml`.

## Overwrite Policy

The generator refuses to write into an existing case folder by default. Use `--force` only when intentionally refreshing the canonical generated files:

```bash
python scripts/labos_case.py new --case-id example-new-case --title "Example new thermal case" --force
```

Even with `--force`, the command only writes canonical files inside the target case folder. It does not delete unrelated files.

## Confidentiality Reminder

Choose the lowest safe confidentiality level for the scaffold, then raise it during review if customer, supplier, process, cost, or restricted details are added. Do not put restricted process details or customer-identifying information into public examples.

## No-API Policy

The case generator is local and deterministic. It does not call the OpenAI API, does not require network access, does not require API keys, and does not add paid automation.
