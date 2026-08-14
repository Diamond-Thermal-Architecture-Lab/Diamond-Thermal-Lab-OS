# M15B Phase 4 Evidence-Reveal Protocol

## Status, preservation, and entry

This additive package is pre-reveal and unfrozen. It does not authorize execution until independent acceptance. The executor is disqualified from independent Phase 4 review. Preserve `27 manifest-listed artifacts`, `benchmarks/m15b-phase3/phase3_freeze_manifest.json`, and therefore `28 frozen files in total`; no frozen bytes are edited or regenerated.

Before opening evidence, verify the frozen merge `1f8d258030f1330e022dec34bab608fef46b54c9`, tree `772aba695aac5726df4c0b8193ba0bad5dbab24f`, parent order, and all 28 frozen files; then record `M15B PHASE 4 PRE-REVEAL LOCK: ESTABLISHED`.

## Controlled delivery and media type

Apply `M15B_PHASE4_SEALED_DELIVERY_CONTRACT.json` only. `M15B_SEALED_ROOT` is a controller-supplied exact absolute existing directory path; never discover it by search or enumerate its parent or neighbors. Inspect the root, every path component below the filesystem or volume root, and each exact registered entry with OS-native no-follow metadata. A symlink, junction, reparse point, redirect, mount redirect, special-file entry, or inability to prove their absence is a hard stop before payload reading. Canonicalization occurs only after no-follow acceptance and cannot cure a rejected path. Compare the canonical root with canonical prohibited roots by path-component relationships and native case semantics; textual-prefix containment is prohibited. Enumerate only the verified root's immediate entries and require the exact registered filename set with no case variant, alias, duplicate, missing, or unexpected entry.

Each registered filename is a single exact component. Its no-follow metadata must prove a non-reparse regular file, and its canonical parent and available parent identity must equal the retained canonical root and root identity exactly; immediate-child containment is canonical-parent equality, never `StartsWith`, substring, or another textual-prefix test. Retain a stable no-follow opened-object identity through metadata validation and the one raw-byte read, or use an equivalent single-read identity check that fails on any replacement or change. Hash, length-check, media-check, and strictly decode the same verified byte buffer without closing and reopening the pathname. All root, entry, containment, identity, length, SHA-256, and media-byte gates must pass for all four payloads before any decode, rendering, comparison, evidence interpretation, receipt completion, or reveal opening. No payload content, absolute sealed path, credential, source copy, or secret is printed, committed, or pasted into chat.

## Normative comparison-unit inventory

The required inventory is version `3.0` and uses exactly these four frozen repository-relative paths, with no dynamic or later-added source:

1. `cases/m15b-case-a/10_claim_ledger.yml`
2. `cases/m15b-case-a/11_engineering_memory_entry.md`
3. `exports/m15b-case-a-phase3/decision_board_preview.json`
4. `exports/m15b-case-a-phase3/triage_result.json`

### Claim-ledger units

The claim ledger contributes exactly two units: `claim_id:CLM-001` and `claim_id:CLM-002`. The executor verifies that both exact claim IDs exist in the already hash-verified frozen file. It does not derive units through YAML parser interpretation. The YAML document title, status, note, claim text, nested fields, and all other YAML nodes are not units. Source count: `2`.

### Engineering-memory units

The engineering memory contributes exactly these seven canonical locators: `heading:Lesson`, `heading:Source Artifact`, `heading:Reusable Pattern`, `heading:Failed Assumption`, `heading:Validated Assumption`, `heading:Future Use`, and `heading:Draft Safety Note`. Source count: `7`.

For the frozen UTF-8/LF text, a captured line begins with exactly the three ASCII bytes for `## `. The locator is `heading:` followed by the remainder of that exact line. Apply no trimming, case folding, Unicode normalization, slugification, or Markdown-anchor conversion. The seven captured heading strings must be unique. Exclude the level-1 title `# Engineering Memory Entry`, `heading:Engineering Memory Entry`, metadata lines, section body paragraphs, blank lines, and every heading level other than level 2. The excluded title would have ID `M15B-P4-CAU-71a60b23fc2b28aaf7d81e88950d52e6b548a99defb3bf168030d958c05296d58`; that ID must not occur in the required inventory.

### JSON scalar-leaf units and decoding

For each named JSON file, include all and only scalar leaf values. A scalar leaf has JSON type string, number, `true`, `false`, or `null`. Each scalar array element is included individually. Objects, arrays, empty objects, empty arrays, and object or array containers with scalar descendants are not units. `decision_board_preview.json` contributes exactly `160`; `triage_result.json` contributes exactly `111`. For this frozen protocol, “decision-bearing JSON Pointer” means all and only those scalar leaves and requires no semantic judgment.

Decode strictly as UTF-8 and reject duplicate keys at every object depth. The frozen `triage_result.json` contains one leading UTF-8 BOM: permit and remove exactly one leading U+FEFF from that named file solely before JSON parsing. Reject a second BOM, a BOM anywhere else, and any BOM in `decision_board_preview.json`. Reject comments, trailing non-whitespace content, non-standard numeric values, and duplicate keys. The removed BOM does not participate in pointer construction.

For every JSON scalar leaf, construct the locator with an RFC 6901 JSON Pointer from the document root. Each object member adds `/` and its member name escaped by first replacing `~` with `~0`, then replacing `/` with `~1`. Each array position uses its zero-based base-10 index with no leading zero except index `0`. Do not URI-encode, prefix a fragment `#`, case-fold, or Unicode-normalize the pointer. The canonical locator is `json_pointer:` immediately followed by the pointer. Examples include `json_pointer:/case_id`, `json_pointer:/secondary_classifications/0`, and `json_pointer:/triggered_rules/0/rule_id`. Object source order does not affect the inventory because canonical ordering is defined separately.

### Identifier, ordering, and digest bytes

For every unit, use the exact repository-relative path and canonical locator. Construct the unit-ID preimage as `path.encode("utf-8") + bytes([0x0A]) + locator.encode("utf-8")`. The separator is exactly one actual LF byte `0x0A`, never the two literal bytes backslash plus `n`. The preimage has no CR, BOM, surrounding whitespace, or terminal LF and undergoes no Unicode normalization or locale transformation. The identifier is `M15B-P4-CAU-` plus the lowercase hexadecimal SHA-256 of that preimage.

Sort ascending first by exact UTF-8 path bytes and then by exact UTF-8 canonical-locator bytes, using unsigned bytewise lexicographic comparison. Do not use locale-aware, natural-number, case-insensitive, filesystem, YAML/JSON source, or unit-ID ordering. Every Case A comparison record and leakage assessment follows this identical canonical order.

After ordering, construct the required-unit digest preimage as `bytes([0x0A]).join(comparison_unit_id.encode("ascii") for comparison_unit_id in canonically_ordered_ids)`. For 280 complete IDs it contains exactly 279 actual `0x0A` separator bytes, no leading or trailing LF, no CR or BOM, and no literal backslash-plus-`n` separator. The required-unit-set SHA-256 is lowercase hexadecimal.

The frozen golden inventory is:

- Claim-ledger units: `2`
- Engineering-memory units: `7`
- Decision Board JSON units: `160`
- Triage JSON units: `111`
- Total required units: `280`
- Required-unit-set SHA-256: `4a1d9fab7154166a5c1daa5bcdbfe88aa4f49db41f697dc189a739e546a81bd3`

The first unit is path `cases/m15b-case-a/10_claim_ledger.yml`, locator `claim_id:CLM-001`, ID `M15B-P4-CAU-41f739f2487744226be4b0868f02b2a2718c2de0afe1617075ac1594e9fa6142`. The last unit is path `exports/m15b-case-a-phase3/triage_result.json`, locator `json_pointer:/validation_note`, ID `M15B-P4-CAU-83e3f4a4040fd5b4f956480bd4211e92a4247fd88097a814ec8d1c5ca1d5194f`.

Each unit has exactly one Case A record; multiple evidence references belong inside it. The same ordered inventory is assessed exactly once for leakage. The semantic validator binds every path, locator, and ID to the exact frozen inventory, enforces exact per-source and total counts, both golden digests, canonical order, H1 exclusion, scalar-only JSON selection, container exclusion, duplicate-key/BOM rules, and identical Case A/leakage inventories. Leakage assessment IDs are exactly `M15B-P4-LK-00000001` through `M15B-P4-LK-00000280`, with sequence position equal to canonical unit position.

## Comparison semantics and disclosure

Case A uses structured findings, no new numeric score. `not_evidenced` is not contradiction; a correct result does not validate unsupported reasoning; immaterial wording is not material failure. Schema plus mandatory semantic validation enforce relationship consistency, material downstream effect, concise disclosure-minimized prose, and no Phase 4 implementation authorization. Evidence uses concise paraphrase only; prohibit full sources, long extracts, URLs, local paths, temporary paths, credentials, and unrelated evidence.

Case B is separate: schema fields are applicability status and handling compliance, validated only against the frozen Case B contract and hash. It cannot hold evidence identifiers/locators, quotations, score, Case A finding, or engineering outcome. Leakage distinguishes authorized input, generic overlap, distinctive evidence-specific overlap, unsupported evidence-specific detail, and indeterminate overlap; correct blind output alone is insufficient.

## Determinism, artifacts, and lifecycle

All JSON is UTF-8 without BOM, LF-final, canonical two-space/lexicographic-key JSON. Capture one RFC 3339 UTC `Z` timestamp once per run and inject that exact value into both generation runs. All seven output artifacts must then reproduce byte-for-byte; no clock call occurs during either generation. The package manifest covers exactly nine other package files, sorted by repository-relative path, and excludes itself.

The Case A Markdown report is a deterministic rendering of validated Case A JSON: exact headings in output-contract order; finding-ID ascending; fixed Markdown table columns; escaped `|`, backslash, CR/LF; empty values rendered as an em dash; final LF; no timestamp, appendix, or text not traceable to source JSON/fixed text. The executor handoff is similarly a deterministic rendering of manifest pre-commit gates, fixed stops, independence boundary, and fixed external commit/push transition.

The immutable execution manifest records only `ready_for_commit_not_frozen` and exactly the pre-commit gates. Commit/push verification is an external transition reported only in the executor response and later review/freeze records; it is never asserted by the committed artifact. Statuses remain: `M15B PHASE 4 EVIDENCE REVEAL: OPENED`; `M15B PHASE 4 EVIDENCE REVEAL: COMPLETED — BRANCH PUSHED, NOT FROZEN`; `M15B PHASE 4 EVIDENCE REVEAL: BLOCKED — <exact requirement>`; `M15B PHASE 4 EVIDENCE REVEAL: FAILED — <exact gate>`.

## Validation and test accounting

Validate each schema against Draft 2020-12 with format checking, all IDs/refs, valid synthetic instances, and invalid fixtures for every listed negative case in the output contract. Inventory fixtures must reject H1-title inclusion, containers and empty arrays, missing scalar array elements, wrong RFC 6901 escape order, leading-zero indexes, locale/natural and unit-ID sorting, a terminal LF in the digest, literal backslash-plus-`n` separators, wrong source counts or allocation, count/digest mismatch, and locator/identifier mismatch. Fixtures live only in the temporary root and are removed.

Test reports must state run, passed, failed, errored, skipped, skip names/reasons, and whether skips are expected platform-conditional. Compare complete-suite values and exact skip names/reasons with an isolated no-hardlinks temporary clone of frozen parent; new, remediated, or unrelated skips block. Do not call skipped tests passed.
