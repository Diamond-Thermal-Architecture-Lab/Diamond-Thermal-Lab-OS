# M15B Phase 4 Executor Handoff

## Entry conditions

Enter only after independent acceptance; verify the frozen anchors and 27-listed-plus-manifest/28-file freeze, establish the lock, and block if controlled delivery is absent. Follow the sealed-delivery contract; do not search or substitute evidence.

## Completed gates

| gate | status |
| --- | --- |
| frozen_phase3_anchor_verification | passed |
| pre_reveal_lock | passed |
| sealed_root_resolution | passed |
| sealed_byte_provenance | passed |
| reveal_opening | passed |
| authorized_evidence_scope | passed |
| case_a_comparison | passed |
| case_b_disposition | passed |
| leakage_assessment | passed |
| schema_validation | passed |
| deterministic_validation | passed |
| disclosure_audit | passed |
| targeted_tests | passed |
| complete_tests | passed |
| baseline_verifiers | passed |
| protected_surface_audit | passed |

## Stop conditions

Missing authority/delivery is `M15B PHASE 4 EVIDENCE REVEAL: BLOCKED — <exact requirement>`; integrity, schema, disclosure, test, baseline, or preservation failure is `M15B PHASE 4 EVIDENCE REVEAL: FAILED — <exact gate>`. No Phase 3 rewrite, numeric score, fabricated Case B evidence, or source reproduction is permitted.

## Independent-review boundary

The executor cannot independently review, approve, freeze, merge, or begin later phases. Commit and normal push verification are external transition checks after immutable artifact creation and are reported outside it; successful external push is `M15B PHASE 4 EVIDENCE REVEAL: COMPLETED — BRANCH PUSHED, NOT FROZEN`.
