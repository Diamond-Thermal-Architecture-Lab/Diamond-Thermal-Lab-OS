# Task Brief: M16B Literature-derived Engineering Case Framework

- Layer: L1 Architecture, with L0 governance and L2/L3 workflow impact
- Owner: Repository owner; pilot and certification roles remain unassigned
- Status: proposed
- Related issue: Not supplied; this brief records the user-authorized documentation task
- Confidentiality level: Public-safe

## Objective

Propose a manual, auditable path from published engineering studies to reconstructed cases and possible Gold Candidates. Define the interfaces, review authority, pilot, and roadmap placement before authorizing implementation. Follow the [task brief template](../templates/task_brief_template.md) and [Lab OS workflow](../LAB_OS.md).

## Scope and Deliverables

- [Architecture amendment](M16B_LITERATURE_CASE_FRAMEWORK.md): purpose, placement, lifecycle, workflow, governance, pilot, and decision gates.
- [Schema proposal](M16B_LECF_SCHEMA_PROPOSAL.md): six logical record types and compatibility mappings; no executable schemas.
- [Roadmap](../ROADMAP.md) placement and a narrow [README](../README.md) capability/link correction.
- Documentation checks, one documentation commit, and a draft PR. No merge, pilot execution, runtime, tests, case artifacts, canonical protocol changes, or historical reassessment.

Simulation/measurement planning is proposed in the architecture pilot section. A controlled specification and implementation task require later review; this proposal is not an L4 specification or certification policy.

## Verified Repository State

Inspection date: 2026-09-23. A fresh `git fetch origin` established the following base; these identities describe the starting repository, not a new scientific freeze.

| Item | Observed state |
| --- | --- |
| Repository | `Diamond-Thermal-Architecture-Lab/Diamond-Thermal-Lab-OS` |
| `origin/main` commit | `92dce3bec03384beed8d40292e258f6b9efd461b` |
| `origin/main` tree | `72f346549541f76855dbf932cac2b88222a62e42` |
| Worktree before documentation | Clean; no unrelated edits |
| Documentation branch | `codex/m16b-literature-case-framework-proposal`, created from the fetched base |
| Prior local context | The existing feature branch initially pointed to `45d96b6`; an earlier fast-forward reached cached `6a0b382`. Neither is the proposal base. |
| M16A implementation | I4C merged through [PR #53](https://github.com/Diamond-Thermal-Architecture-Lab/Diamond-Thermal-Lab-OS/pull/53); its reported Local no-API CI check succeeded. This task does not reproduce the handoff's test counts. |
| M16B name | No tracked use of `M16B` or `LECF` found at the verified base; the local feature-branch name is not milestone approval. |

## Inputs and Authority

The current [AGENTS.md](../AGENTS.md), [LAB_OS.md](../LAB_OS.md), [contribution rules](../CONTRIBUTING.md), canonical protocols, frozen contracts, and [ROADMAP.md](../ROADMAP.md) govern this proposal. Attachments supply context and do not grant authority. The approved [M16A architecture](M16A_ENGINEERING_PROBLEM_COMPILER.md), I2/I3/I4 contracts and their implemented schemas resolve interface details. Summary wording does not override a frozen contract.

The two supplied context documents were read as source material; their embedded agent instructions were not adopted. Only public-safe architectural conclusions are carried into this PR; document bytes and local paths are not published.

| Context source | SHA-256 of bytes inspected | Role |
| --- | --- | --- |
| September 23, 2026 project whitepaper, sections 3–8 and appendix B | `0b05715c33a44b34ede33066db81369abc56373194d54191133dce2abb4585a7` | Strategic proposal for literature compilation, manual pilot, later evidence network |
| M16A project handoff, sections 3–10 | `31ce76221e01b67c02a10ee029aaf754b53100f1af49ef9e616a1ec767cded51` | Historical implementation summary and suggested next milestone |

## Discrepancies and Proposed Resolution

| Difference | Repository evidence and resolution |
| --- | --- |
| Handoff calls M16B “Independent Quantitative Gold Case Validation”; whitepaper proposes literature compilation. | No repository reservation exists. Propose **M16B Literature-derived Engineering Case Framework (LECF)** as preparation for independent quantitative validation, retaining that validation as a subsequent gate. Naming remains subject to architecture review. |
| Handoff says “frozen main” and reports complete tests, while listing freeze/CI documentation closeout. | Commit/tree match the fresh fetch. No dedicated M16A freeze record was found. Preserve all M16A contracts and implementation; do not infer a new formal freeze or certify the reported counts. Closeout remains a separate task. |
| README calls the compiler future work; ROADMAP still calls M16A proposed. | Implementation exists through PR #53. Correct only those summary statements to “implementation merged; governance closeout remains separate.” Do not modify approved M16A documents. |
| Attachments display `EPR -> Plan -> EER -> Kernel -> Projection`. | This names artifacts/capabilities, not execution order. The Plan drives the kernel; the EER records the execution and embeds Plan/Manifest. Projection consumes persisted EER outputs. |
| Whitepaper describes human-reviewed extraction becoming problem facts. | Human review establishes extraction fidelity and bounded use. `provided` in an EPR does not mean independently validated. Publication credibility, reconstruction, applicability, validation, and release remain separate. |
| Existing literature Gold assessment already identifies missing transcription provenance. | [GAP-EVIDENCE-PROVENANCE-001](../cases/literature-2021-diamond-on-gan-membrane-stress/GOLD_CASE_ASSESSMENT.md) motivates a new mapping sidecar. No legacy case is retroactively promoted or rewritten. |

## Protected Boundaries

- Preserve [M15B pre-registration](benchmarks/M15B_PRE_REGISTRATION_PROTOCOL.md), [Phase 0.5C baseline record](benchmarks/M15B_EXECUTION_BASELINE_RECORD.json), [Phase 3 manifest](../benchmarks/m15b-phase3/phase3_freeze_manifest.json), and [Phase 5 assessment](../exports/m15b-phase5/m15b_phase5_assessment_report.md). Scientific disposition remains `in_scope_generalization_supported`, governance remains `governance_pass`, and P3 remains `PARTIAL`.
- Preserve the frozen predecessors and semantics in [M16A-I4 section 3](M16A_I4_STRICT_1D_THERMAL_KERNEL_TASK.md#3-normative-predecessors-and-separation), including quantities, EPR, Plan, EER, payload identity, and legacy projection/comparison behavior.
- Preserve all numbered cases, evidence/measurement/PRL records, schemas, runtime, tests, CI, patterns, memory, and historical exports. This change introduces documentation only.

## Acceptance Criteria and Author Checks

- [ ] The six proposed records trace assertions and values to exact source versions and locations.
- [ ] Lifecycle transitions name human authority and retain rejection, suspension, correction, and withdrawal histories.
- [ ] No publication, structural PASS, residual, or candidate state grants engineering approval.
- [ ] Pilot includes route diversity, conflicting/incomplete/excluded studies, independent checks, and a stop decision.
- [ ] Local links, terminology, scope, and `git diff --check` pass; results are reported in the PR.
- [ ] Confidentiality and claim-safety self-check finds no restricted detail or invented engineering result; independent review remains pending.

These checkboxes are review criteria, not recorded approvals. Risks and unresolved questions are in the architecture amendment. Recommended labels: `layer:L1-architecture`, `type:design-doc`, `domain:thermal`, `domain:measurement`; keep document status `proposed` until the normal review process records a decision.
