# Benchmark Execution Baseline Guide

## 1. Purpose

M15B Phase 0.5C freezes the candidate-independent execution environment before
literature screening begins. It records exact bytes for production code,
scripts, workflows, schemas, the M14 rule source, the frozen protocol, and the
presence and content of dependency manifests.

This phase does not select a candidate, create a Blind Input Packet, use a real
private leakage policy, create sealed artifacts, or change M14 semantics.

## 2. Approved Scope

The canonical scope is
[`benchmarks/M15B_EXECUTION_SCOPE_SPEC.json`](benchmarks/M15B_EXECUTION_SCOPE_SPEC.json).
The parser requires that file to equal the approved Phase 0.5C scope; changing
the JSON cannot weaken the hard-coded protected path set.

The protected tree groups are:

* `production_code`: `labos/`;
* `schemas`: `labos/schemas/` and `schemas/`;
* `scripts`: `scripts/`;
* `workflows`: `.github/workflows/`.

The record also freezes the exact protocol file, the M14 thermomechanical rule
source, and every recognized dependency manifest anywhere below the repository
root. A newly added dependency manifest is a mismatch even when the baseline
contains no dependency manifests.

Generated Python caches are excluded. Symlinks in protected trees or dependency
manifest paths fail closed.

## 3. Record and Commit Binding

The baseline record does not hash itself. It contains a
`protected_content_commit` identifying the reviewed commit whose protected
bytes were measured. The record is then committed without changing those
protected paths.

The final M15B execution-baseline commit is the exact commit containing the
record. Its SHA is recorded in the Phase 0.5C freeze declaration after
exact-head CI succeeds. Phase 1 must branch from that exact SHA.

Verification has two layers:

1. Offline verification checks current exact bytes and file sets without
   network access or `.git`.
2. Git-aware verification checks protocol ancestry, protected-content ancestry,
   ref availability, and byte-identical protected paths between the reviewed
   content commit and the requested execution-baseline ref.

## 4. Commands

Validate the immutable scope:

```bash
python scripts/labos_benchmark.py validate-execution-scope \
  docs/benchmarks/M15B_EXECUTION_SCOPE_SPEC.json --json
```

Build a new record only after the protected implementation commit is reviewed:

```bash
python scripts/labos_benchmark.py build-execution-baseline \
  --repo-root . \
  --scope docs/benchmarks/M15B_EXECUTION_SCOPE_SPEC.json \
  --protected-content-commit <full-commit-sha> \
  --recorded-at <YYYY-MM-DDTHH:MM:SSZ> \
  --output docs/benchmarks/M15B_EXECUTION_BASELINE_RECORD.json
```

The builder uses exclusive creation and refuses to overwrite a record.

Validate record structure:

```bash
python scripts/labos_benchmark.py validate-execution-baseline \
  docs/benchmarks/M15B_EXECUTION_BASELINE_RECORD.json --json
```

Verify offline exact bytes:

```bash
python scripts/labos_benchmark.py verify-execution-baseline \
  docs/benchmarks/M15B_EXECUTION_BASELINE_RECORD.json \
  --repo-root . \
  --scope docs/benchmarks/M15B_EXECUTION_SCOPE_SPEC.json \
  --json
```

Add Git ancestry and ref checks in a repository checkout:

```bash
python scripts/labos_benchmark.py verify-execution-baseline \
  docs/benchmarks/M15B_EXECUTION_BASELINE_RECORD.json \
  --repo-root . \
  --scope docs/benchmarks/M15B_EXECUTION_SCOPE_SPEC.json \
  --git-ref HEAD \
  --json
```

Validation errors return exit code `2`. A valid record with a baseline mismatch
returns `1`. A valid and matching baseline returns `0`.

## 5. Freeze Gate

Candidate screening remains prohibited until all of the following are true:

* the Phase 0.5C implementation is independently reviewed;
* the exact final head passes CI;
* the committed baseline record verifies offline and with Git;
* the final execution-baseline commit SHA and hashes are recorded;
* Phase 0.5C is explicitly declared frozen with no unresolved blockers.

Any later protected-path change cancels the current M15B run or requires a
separately reviewed execution baseline under the governing protocol.
