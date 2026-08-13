# M15B Phase 4 Executor Handoff

## Entry conditions

Enter only after independent acceptance of this package. Start from the frozen Phase 3 merge, independently verify all anchors and 28 freeze-manifest hashes, preserve Phase 3, use a dedicated temporary root, and establish the pre-reveal lock. `M15B_SEALED_ROOT` may be unset until delivery; that is a block, not permission to search, substitute, or begin reveal.

## Required execution

Apply the sealed-delivery contract exactly, create only the seven output-contract artifacts, follow the protocol gate order, validate every JSON/schema/local reference/cross-reference, repeat deterministic generation and compare hashes, perform the disclosure audit, run the required tests and baseline verifiers, and audit protected surfaces. No new Phase 4 artifact is authorized.

## Stop conditions

For missing controlled delivery or authority, stop with `M15B PHASE 4 EVIDENCE REVEAL: BLOCKED — <exact requirement>`. For an integrity, provenance, schema, determinism, disclosure, test, baseline, or protected-surface failure, stop with `M15B PHASE 4 EVIDENCE REVEAL: FAILED — <exact gate>`. Do not repair Phase 3, alter rules, invent a score, fabricate Case B evidence, expose source text, or continue after a hard stop.

## Independent-review boundary

After a valid push, report `M15B PHASE 4 EVIDENCE REVEAL: COMPLETED — BRANCH PUSHED, NOT FROZEN` and stop. The executor cannot independently review, approve, freeze, merge, or begin later phases.
