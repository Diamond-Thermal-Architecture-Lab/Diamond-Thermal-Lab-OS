# M15B Phase 4 Evidence-Reveal Protocol

## Status and authority

This normative, pre-reveal package is additive to the Phase 3 freeze. It is not a Phase 4 execution, assessment, approval, or freeze. The executor may open registered evidence only after independent acceptance and is disqualified from independent Phase 4 review. Frozen anchors are commit `1f8d258030f1330e022dec34bab608fef46b54c9`, tree `772aba695aac5726df4c0b8193ba0bad5dbab24f`, parents `2b45c63128dad6793dd753ca9300538769af8c53` and `61753ff5e3398f30f983682b59c04fc4ad0449f1`, and the 28 entries in `benchmarks/m15b-phase3/phase3_freeze_manifest.json`. No Phase 3 file is edited, regenerated, or rewritten.

## Output surface and controlled delivery

`M15B_PHASE4_OUTPUT_CONTRACT.json` is the sole output inventory. Adding, renaming, omitting, or adding an artifact requires an accepted pre-reveal protocol amendment. JSON validates against named local Draft 2020-12 schemas; Markdown contains its stated required sections.

Before reveal, verify every frozen anchor and manifest hash, record the receipt, and emit `M15B PHASE 4 PRE-REVEAL LOCK: ESTABLISHED`. Apply `M15B_PHASE4_SEALED_DELIVERY_CONTRACT.json`: the controller supplies absolute `M15B_SEALED_ROOT`; it is never searched for. It must exist, be a real non-reparse directory outside the Git repository and all Role D, review, protocol-author, and execution workspaces. Do not enumerate a parent or neighbor. Inspect only immediate contract entries; resolve each payload by exact relative filename; verify strict containment, regular-file type, raw bytes, SHA-256, and media type before decoding. Extra sibling, link/reparse redirect, absent file/root, containment error, type mismatch, digest mismatch, or substitute source is a hard stop. Never paste a secret in chat. Plaintext/rendered temporary material stays only below the executor temporary root and is removed after validation. Payload bytes are not committed. Then emit `M15B PHASE 4 EVIDENCE REVEAL: OPENED`.

## Case A, Case B, leakage, disclosure

Case A uses structured findings, not a newly invented numeric score. Required fields are frozen artifact path, blind locator, registered evidence ID, evidence locator, relationship, materiality, discrepancy category, three downstream effects, concise rationale, uncertainty, lesson, and recommendation status. Relationships are `supported`, `partially_supported`, `contradicted`, `not_evidenced`, `not_assessable`; `not_evidenced` is not contradiction, a correct answer does not validate unsupported reasoning, and immaterial wording is not material failure. Evidence locators are mandatory for evidence conclusions, quotes are minimal, and frozen artifacts remain frozen.

Case B records only its authorized applicability disposition and cannot carry evidence locators, comparison findings, quotations, scores, or engineering outcomes. Leakage records authorized-input provenance plus generic overlap, distinctive evidence-specific overlap, unsupported evidence-specific detail, or indeterminate overlap. A correct blind conclusion alone is never leakage. Use minimum necessary paraphrase: no full source, long extract, credentials, local paths, temporary paths, unrelated evidence, source copy, or binary payload. Over-disclosure is a hard failure.

## Determinism and gates

JSON is UTF-8 without BOM, LF-final, RFC 8259, two-space indentation, lexicographic object keys; arrays use output-contract sort keys. IDs are `M15B-P4-CA-` plus an eight-digit ordinal after sorting by frozen path, blind locator, evidence ID, and locator. Numbers have at most six fractional digits. Only receipt/execution `generated_at_utc` are volatile RFC 3339 UTC values; all other timestamps are absent. Generate each deterministic artifact twice and compare raw SHA-256. Validate schemas, references, cross-file IDs, ordering, disclosure, and integrity. The package manifest covers every package file except itself; independent review hashes it.

Gate order: anchors; lock; root; provenance; reveal; scope; Case A; Case B; leakage; schema; determinism; disclosure; targeted tests; complete tests; baseline verifiers; protected-surface audit; commit/push; handoff. Missing authority/delivery emits `M15B PHASE 4 EVIDENCE REVEAL: BLOCKED — <exact requirement>`; failure emits `M15B PHASE 4 EVIDENCE REVEAL: FAILED — <exact gate>`; successful push emits `M15B PHASE 4 EVIDENCE REVEAL: COMPLETED — BRANCH PUSHED, NOT FROZEN`. Stop after push: no merge, freeze, later phase, or correction planning.
