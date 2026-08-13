# M15B Phase 4 Evidence-Reveal Protocol

## Status, preservation, and entry

This additive package is pre-reveal and unfrozen. It does not authorize execution until independent acceptance. The executor is disqualified from independent Phase 4 review. Preserve `27 manifest-listed artifacts`, `benchmarks/m15b-phase3/phase3_freeze_manifest.json`, and therefore `28 frozen files in total`; no frozen bytes are edited or regenerated.

Before opening evidence, verify the frozen merge `1f8d258030f1330e022dec34bab608fef46b54c9`, tree `772aba695aac5726df4c0b8193ba0bad5dbab24f`, parent order, and all 28 frozen files; then record `M15B PHASE 4 PRE-REVEAL LOCK: ESTABLISHED`.

## Controlled delivery and media type

Apply `M15B_PHASE4_SEALED_DELIVERY_CONTRACT.json` only. `M15B_SEALED_ROOT` is an absolute controller-supplied existing real directory outside the repository and prohibited workspaces; never search it, a parent, or a neighbor. Resolve only exact listed filenames, check permitted immediate entries, strict containment, regular-file status, raw length and SHA-256 before decoding. For `text/markdown; charset=utf-8`, require the registered `.md` name, strict UTF-8 decoding after byte checks, no BOM, no NUL byte, and LF-only newlines; any failure is a hard stop. OS/MIME guesses do not prove type. Plaintext/rendered material stays under the executor temporary root and is removed afterward. No payload, credential, source copy, or secret is committed or pasted into chat.

## Neutral inventory and comparison

The required comparison-unit inventory is extracted without evidence semantics from decision-bearing frozen surfaces: every claim-ledger claim ID in `cases/m15b-case-a/10_claim_ledger.yml`; every decision-bearing JSON Pointer in `exports/m15b-case-a-phase3/triage_result.json` and `decision_board_preview.json`; every normative entry identifier/heading in `cases/m15b-case-a/11_engineering_memory_entry.md`; and any later expressly named decision-bearing Phase 3 path. A unit ID is SHA-256 of `path + LF + locator`, prefixed `M15B-P4-CAU-`; sort by path then locator. The required-unit digest is SHA-256 of LF-joined sorted IDs. Each unit has exactly one Case A record; multiple evidence references belong inside it. The same inventory is assessed exactly once for leakage.

Case A uses structured findings, no new numeric score. `not_evidenced` is not contradiction; a correct result does not validate unsupported reasoning; immaterial wording is not material failure. Schema plus mandatory semantic validation enforce coverage/digest/counts, unit uniqueness, ordering, identifier/locator binding, relationship consistency, material downstream effect, concise disclosure-minimized prose, and no Phase 4 implementation authorization. Evidence uses concise paraphrase only; prohibit full sources, long extracts, URLs, local paths, temporary paths, credentials, and unrelated evidence.

Case B is separate: schema fields are applicability status and handling compliance, validated only against the frozen Case B contract and hash. It cannot hold evidence identifiers/locators, quotations, score, Case A finding, or engineering outcome. Leakage distinguishes authorized input, generic overlap, distinctive evidence-specific overlap, unsupported evidence-specific detail, and indeterminate overlap; correct blind output alone is insufficient.

## Determinism, artifacts, and lifecycle

All JSON is UTF-8 without BOM, LF-final, canonical two-space/lexicographic-key JSON. Capture one RFC 3339 UTC `Z` timestamp once per run and inject that exact value into both generation runs. All seven output artifacts must then reproduce byte-for-byte; no clock call occurs during either generation. The package manifest covers exactly nine other package files, sorted by repository-relative path, and excludes itself.

The Case A Markdown report is a deterministic rendering of validated Case A JSON: exact headings in output-contract order; finding-ID ascending; fixed Markdown table columns; escaped `|`, backslash, CR/LF; empty values rendered `—`; final LF; no timestamp, appendix, or text not traceable to source JSON/fixed text. The executor handoff is similarly a deterministic rendering of manifest pre-commit gates, fixed stops, independence boundary, and fixed external commit/push transition.

The immutable execution manifest records only `ready_for_commit_not_frozen` and exactly the pre-commit gates. Commit/push verification is an external transition reported only in the executor response and later review/freeze records; it is never asserted by the committed artifact. Statuses remain: `M15B PHASE 4 EVIDENCE REVEAL: OPENED`; `... COMPLETED — BRANCH PUSHED, NOT FROZEN`; `... BLOCKED — <exact requirement>`; `... FAILED — <exact gate>`.

## Validation and test accounting

Validate each schema against Draft 2020-12 with format checking, all IDs/refs, valid synthetic instances, and invalid fixtures for every listed negative case in the output contract. Fixtures live only in the temporary root and are removed. Test reports must state run, passed, failed, errored, skipped, skip names/reasons, and whether skips are expected platform-conditional. Compare complete-suite values and exact skip names/reasons with an isolated no-hardlinks temporary clone of frozen parent; new/remediated/unrelated skips block. Do not call skipped tests passed.
