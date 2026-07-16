# M15B Pre-Registration Protocol

## 1. Protocol Status

* Protocol version: `1.0`
* Milestone: `M15B`
* Status: `ready_for_protocol_freeze`
* Repository baseline at protocol design: `226a6f678b105e7310543b71ca441d698b217fea`
* Execution baseline: a separately recorded commit created after this protocol
  is merged and after any independently reviewed generic benchmark
  infrastructure is complete, but before candidate screening begins. Once
  recorded, that execution baseline is immutable for M15B.
* Governing rule family: frozen M14 `TRIAGE-THERMOMECH-001` through `TRIAGE-THERMOMECH-007`
* Final primary literature case: not selected
* M14 rule modification permitted during benchmark: no

This protocol must be merged before final candidate selection, Blind Input Packet construction, or phase-one execution.

## 2. Objective

M15B evaluates whether the frozen M14 thermomechanical triage rule family can recognize relevant qualitative evidence gaps in a new, clearly in-scope membrane or suspended-structure integration case without:

* outcome leakage;
* source-specific rule tuning;
* post-result applicability changes;
* post-result scoring changes;
* rewriting frozen phase-one artifacts.

M15B is a case-level generalization benchmark. It is not general validation of M14 across all materials, structures or processes.

## 3. Primary Research Question

Can the frozen M14 rule family activate on an independent, source-faithful, strictly in-scope case and request the relevant thermomechanical evidence before the published outcomes are revealed?

The following are secondary observations and must not be folded into the primary conclusion:

* generic triage classifications;
* candidate-route generation;
* Decision Board coherence;
* numerical prediction capability;
* adjacent-scope transfer;
* automatic learning or calibration.

## 4. Non-Goals

M15B does not:

* calculate stress, curvature, bow or warpage;
* estimate cracking, delamination or failure probability;
* validate numerical thresholds;
* approve a material, process or architecture;
* produce customer-facing performance claims;
* modify M14 rules;
* add source-specific keywords;
* tune applicability after viewing outcomes;
* update patterns or engineering memory;
* perform automatic calibration;
* demonstrate general thermomechanical reliability from one case.

## 5. Frozen M14 Applicability Contract

The primary case must receive a human pre-screen verdict of `in_scope` before phase-one construction.

All five gates below must pass.

### 5.1 Structural-State Gate

Before or during the thermally significant integration step, the relevant structure must already be:

* a membrane;
* a suspended region;
* a released thin structure;
* or a mechanically compliant thin structural region whose stress or shape may be affected by the integration process.

A structure that becomes suspended only after the thermally significant integration step fails this gate for the primary case.

### 5.2 Integration Gate

A layer, coating, bonded interface or transferred structure must be integrated through:

* deposition;
* direct growth;
* coating;
* bonding;
* transfer and bonding;
* or an equivalent retained integration process.

The integrated relationship must remain relevant in the post-process structure.

Background material mentions, removed sacrificial layers and unrelated annealing do not satisfy this gate.

### 5.3 Thermal-Significance Gate

The integration process must contain a thermal cycle, process temperature or cooling route that makes at least one of the following legitimately relevant:

* temperature-dependent material properties;
* stress-free reference condition;
* residual stress;
* curvature, bow or warpage;
* interface mechanical integrity;
* fixture or reactor boundary;
* downstream dimensional compatibility.

No universal temperature threshold is predeclared.

### 5.4 Source-Sufficiency Gate

The source must provide enough pre-outcome information to construct a meaningful case without using measured outcomes.

At minimum, the source must support:

* structural state before integration;
* integration process;
* process order;
* material stack;
* stated geometry;
* relevant process temperature or thermal condition;
* retained post-process relationship.

### 5.5 Independence Gate

The source must not have been:

* used to design M14;
* used to tune M14;
* used in the first diamond-on-GaN benchmark;
* used as the M15A SiO2 boundary case;
* or selected because it contains exact phrases already known to trigger M14.

### 5.6 Scope Verdicts

Each candidate receives one verdict before phase one:

* `in_scope`
* `out_of_scope`
* `ambiguous_scope`

Only `in_scope` may be the primary case.

`out_of_scope` may be a boundary or negative control.

`ambiguous_scope` must be rejected unless resolved from source process facts before the Blind Input Packet is created.

### 5.7 Execution-Baseline Gate

Before candidate screening begins, the project must record one M15B execution
baseline commit.

That commit must:

* descend from the merged protocol commit;
* include any reusable benchmark infrastructure approved without knowledge of
  the final candidate;
* preserve M14 applicability and rule semantics;
* contain no candidate-specific terms, source-specific parser, threshold or
  rule tuning;
* have successful exact-head CI.

After it is recorded:

* candidate screening must not cause production-code changes;
* the phase-one branch must be created from that exact execution baseline;
* files under `labos/`, `scripts/`, `.github/workflows/`, schema paths and
  dependency manifests must remain byte-identical throughout the benchmark PR;
* any required semantic production-code change cancels the current benchmark
  run and requires a new protocol review or a later separate milestone.

## 6. Candidate Inclusion Criteria

The primary candidate must:

1. Pass all five applicability gates.
2. Use a material or process family meaningfully different from the first diamond-on-GaN case.
3. Use natural source terminology.
4. Provide a separable set of pre-outcome facts.
5. Provide independent revealed evidence after phase one.
6. Have a traceable primary source.
7. Allow source identity to be withheld without destroying engineering meaning.
8. Pre-register at least three applicable P2–P8 dimensions, including at least
   two genuine source-faithful missing or unresolved evidence needs. No evidence
   gap may be manufactured by deleting or withholding a source-provided
   pre-outcome fact that is admissible under this protocol.
9. Remain public-safe.
10. Not require proprietary process or customer information.

## 7. Hard Exclusion Criteria

Reject a candidate as the primary case when:

* the structure becomes a membrane only after high-temperature integration;
* process order cannot be established;
* source identity cannot be removed without revealing the outcome;
* geometry and outcomes cannot be separated;
* the relevant integrated layer is removed before the final structural state;
* only an abstract is available;
* the source is a review without a traceable primary experiment;
* the source was used during M14 development;
* M14 activation requires rewriting natural terms into known rule vocabulary;
* the source lacks an independent evidence reveal;
* source facts are insufficient to distinguish supported and released states;
* the Phase-One Builder has already seen the full source;
* the candidate can only be judged in scope by using measured outcomes;
* the candidate requires confidential data;
* the candidate is a near-duplicate of the first Gold Case.

## 8. Soft-Risk Flags

The following do not automatically exclude a candidate but must be recorded:

* geometry selected after preliminary testing;
* exact dimensions reported only in result tables;
* incomplete cooling history;
* stress inferred from deformation rather than directly measured;
* mixed experiment and simulation;
* incomplete fixture description;
* selective sample reporting;
* unavailable raw data;
* qualitative rather than numerical failure observations;
* post hoc causal interpretation;
* multiple sample families with unclear selection rationale.

A soft-risk flag cannot be hidden by rewriting the Blind Input Packet.

## 9. Three-Case Benchmark Set

### 9.1 Primary In-Scope Case

Purpose:

Test case-level generalization of frozen M14 on a new, strictly in-scope material/process/geometry combination.

Expected applicability:

`applicable`

No exact triggered-rule list is supplied to the Phase-One Builder.

### 9.2 Boundary Control

Default control:

The merged M15A thermal-SiO2 release-after-growth benchmark.

Purpose:

Preserve the distinction between:

* integration performed while the structure is already a membrane; and
* integration performed on a supported wafer followed by later release.

Expected strict-scope interpretation:

`generalization_not_evaluable`

Its frozen files and outputs must not change in M15B.

### 9.3 Negative Control

Purpose:

Test M14 applicability false-positive control.

The negative control must be a credible engineering case with related vocabulary but clearly lacking at least one required applicability gate.

Suitable forms include:

* a bulk supported substrate;
* a membrane mentioned only in background;
* deposition without a suspended structure;
* a suspended structure without a thermally significant integration step;
* a high-temperature process without a retained layer/interface relationship.

Expected applicability:

`not_applicable`

The final negative control is selected only after protocol freeze.

## 10. Knowledge-Isolation Roles

Role separation is informational. One person may perform more than one judgment role, but the Phase-One Builder must remain isolated from prohibited information.

### Role A — Protocol Owner

Responsible for:

* this protocol;
* applicability definitions;
* scoring rules;
* invalidation rules.

Role A must freeze the protocol before final source selection.

### Role B — Candidate Researcher

Responsible for:

* primary-literature research;
* candidate dossiers;
* inclusion/exclusion judgments;
* full-source review.

Role B may know source identity and outcomes.

Role B must not build phase-one Canonical Case files.

### Role C — Information Firewall Editor

Responsible for:

* constructing the Blind Input Packet;
* separating input fields from outcomes;
* producing the sealed relevance registration;
* conducting a leakage audit.

Role C may know the full source but must not communicate prohibited information to the Phase-One Builder.

### Role D — Phase-One Builder

Tool role:

A fresh Codex execution session.

Role D receives only:

* this protocol;
* the approved Blind Input Packet;
* public repository state;
* explicit phase-one implementation instructions.

Role D must not receive or independently retrieve the full source.

Role D builds, runs, freezes, commits and stops.

### Role E — Evidence Author and Assessor

Judgment responsibility remains with the assistant.

Role E:

* reviews the full source after phase one;
* defines exact Evidence, Measurement and PRL content;
* applies the frozen scoring contract.

A separate Codex session may perform only the repository file implementation specified by Role E.

### Role F — Independent Reviewer

A fresh assistant review context checks:

* scope;
* leakage;
* hashes;
* source fidelity;
* scoring;
* output coherence;
* CI state.

Role F does not repair implementation in the benchmark PR.

## 11. Information-Flow Matrix

| Information                |                         A |                   B |               C |                   D |                     E |               F |
| -------------------------- | ------------------------: | ------------------: | --------------: | ------------------: | --------------------: | --------------: |
| M14 design and rules       |                       yes |                 yes |             yes |                 yes |                   yes |             yes |
| M15A findings              |                       yes |                 yes |             yes | protocol-level only |                   yes |             yes |
| Candidate source identity  | no before protocol freeze |                 yes |             yes |                  no |                   yes |             yes |
| Full paper                 | no before protocol freeze |                 yes |             yes |                  no |                   yes |             yes |
| Measured outcomes          | no before protocol freeze |                 yes |             yes |                  no |                   yes |             yes |
| Blind Input Packet         |            after approval |                 yes |             yes |                 yes |                   yes |             yes |
| Expected rule IDs          |                        no |                  no |     sealed only |                  no |          after freeze |             yes |
| Relevance/N/A registration |          sealed hash only |                 yes |             yes |                  no | revealed after freeze |             yes |
| Phase-one outputs          |           after execution |     after execution | after execution |                 yes |                   yes |             yes |
| Rule-fix recommendations   |           after benchmark | no during phase one |              no |                  no |       documented only | documented only |

Separate Git commits alone do not constitute knowledge isolation.

## 12. Blind Input Packet Contract

The packet must be source-faithful, public-safe and sufficient to build the 12 Canonical Case files.

### 12.1 Allowed Information

* anonymized case ID;
* material categories needed for interpretation;
* natural structural terminology;
* state before, during and after integration;
* process sequence;
* integration method;
* stated process temperature or thermal condition;
* layer thickness;
* lateral dimensions;
* support geometry;
* pre-outcome fixture or boundary facts;
* predeclared downstream requirements;
* explicitly stated unknowns;
* assumptions not derived from results.

### 12.2 Allowed With Retrospective-Risk Flag

* geometry appearing in a mixed results table;
* geometry selected after preliminary testing;
* supplier nominal stress or material-property values;
* process-development facts that do not disclose final outcomes;
* fixture details later found to affect results.

The packet must label why the field is retained and what hindsight risk remains.

### 12.3 Prohibited Until Evidence Reveal

* paper title;
* authors;
* DOI, journal or arXiv identifier;
* measured or inferred stress;
* deflection, bow, curvature or warpage results;
* cracking, rupture or delamination outcomes;
* successful/failed sample labels;
* causal conclusions from results;
* result-derived CTE mismatch conclusions;
* geometry rankings;
* expected M14 status;
* expected rule IDs;
* benchmark score;
* known false positives or false negatives;
* proposed rule fixes;
* rewritten terminology intended to trigger M14.

### 12.4 Required Packet Files

* `BLIND_INPUT_PACKET.yml`
* `BLIND_INPUT_MANIFEST.md`
* `ROLE_D_INFORMATION_RECEIPT.md`

The receipt must declare exactly which files and facts Role D received.

## 13. Source-Fidelity Rules

The benchmark must preserve:

* process order;
* supported versus released state;
* source terms such as side length, span, width, window or released area;
* deposition versus annealing;
* retained versus sacrificial interfaces;
* thermal boundary versus mechanical holder constraints;
* direct measurement versus simulation inference;
* source facts versus benchmark assumptions.

Permitted normalization:

* unit conversion;
* spelling normalization;
* formatting;
* anonymization;
* removal of source identity.

Prohibited rewriting:

* replacing side length or span with diameter;
* adding known M14 trigger phrases absent from the source;
* converting an unknown into a missing-evidence conclusion;
* converting a result-derived explanation into a pre-outcome fact;
* reordering process steps;
* describing a supported structure as already released.

## 14. Sealed Pre-Registration Artifacts

Before Role D begins, Role C must prepare:

* `SOURCE_DOSSIER.md`
* `SCOPE_REGISTRATION.md`
* `RELEVANCE_REGISTRATION.md`
* `SCORING_REGISTRATION.md`

These files are not provided to Role D.

Before phase-one freeze, the four sealed documents must remain outside the Git
repository, outside the benchmark working tree, and outside every file path,
attachment, conversation or execution context accessible to Role D.

They must not be:

* committed or staged;
* included in the benchmark branch or pull request;
* placed in a repository-local temporary directory;
* uploaded to the Role D session;
* quoted or summarized in the Role D prompt.

Only `SEALED_REGISTRATION_MANIFEST.json` is committed before reveal. The manifest
records each sealed filename, SHA256, byte length, registration timestamp and
protocol version. It must not contain source identity, outcome values, expected
applicability status, expected rule IDs, expected scores or result-derived
explanations.

Role C retains the exact sealed bytes in controlled storage inaccessible to Role
D. The sealed bytes are released only to Roles E and F after the phase-one
commit and all frozen phase-one hashes exist.

Their SHA256 hashes are committed in:

`SEALED_REGISTRATION_MANIFEST.json`

The sealed documents are revealed only after phase-one freeze. Their revealed bytes must match the precommitted hashes.

`RELEVANCE_REGISTRATION.md` must predeclare which scoring dimensions are:

* applicable;
* not applicable;
* conditionally applicable.

No N/A classification may be changed after seeing phase-one output.

## 15. Pre-Registered Scoring Contract

M15B uses a categorical matrix, not a total numerical score.

Allowed results:

* `PASS`
* `PARTIAL`
* `FAIL`
* `N/A`
* `INVALID`

### 15.1 Validity Gate

The benchmark is evaluated only when all are true:

* strict scope was pre-registered;
* source identity and outcomes did not reach Role D;
* frozen files and hashes are intact;
* natural terminology was preserved;
* no M14 rule changed;
* revealed sealed files match their hashes.

Failure of this gate invalidates the benchmark rather than scoring M14.

### 15.2 Primary Dimensions

| ID | Dimension                                           | Primary conclusion relevance   |
| -- | --------------------------------------------------- | ------------------------------ |
| P1 | Applicability recognition                           | mandatory                      |
| P2 | Material-property and reference-temperature gaps    | when pre-registered applicable |
| P3 | Integration thermal-history gaps                    | when applicable                |
| P4 | Stress and shape-response evidence                  | when applicable                |
| P5 | Thermal/process boundary evidence                   | when applicable                |
| P6 | Geometry and scale-comparison evidence              | when applicable                |
| P7 | Retained-interface or mechanical-integrity evidence | when applicable                |
| P8 | Downstream compatibility evidence                   | when applicable                |

### 15.3 Control and Governance Dimensions

| ID | Dimension                                  | Treatment             |
| -- | ------------------------------------------ | --------------------- |
| C1 | M15A boundary control                      | required control      |
| C2 | Negative-control applicability             | required control      |
| G1 | No fabricated prediction or route approval | separate governance result |
| S1 | Generic triage coherence                   | secondary observation |
| S2 | Decision Board coherence                   | secondary observation |

G1 is reported separately as `governance_pass` or `governance_blocked`. It does
not change the P1–P8 scientific disposition. A governance blocker prevents route
approval, automatic learning, calibration, engineering-memory promotion and
customer-facing use, but it does not relabel otherwise valid M14 evidence-gap
observations.

S1 and S2 must be reported but do not alter the primary M14 thermomechanical
conclusion.

### 15.4 Result Definitions

`PASS`

The output identifies the pre-registered evidence gap with appropriate evidence boundaries and no relevant false assertion.

`PARTIAL`

The output identifies the correct evidence family but omits an important subcomponent, conflates two subcomponents, or provides a materially weaker action.

`FAIL`

The output misses a pre-registered relevant evidence family, treats mention as proof, requests irrelevant evidence, or activates incorrectly.

`N/A`

The sealed relevance registration declared the dimension irrelevant before phase one.

`INVALID`

The dimension cannot be evaluated because benchmark validity was compromised.

### 15.5 Control Pass Criteria

`C1` passes only when:

* all M15A frozen bytes and hashes remain unchanged;
* its deterministic output remains identical to its frozen baseline;
* its strict-scope interpretation remains `generalization_not_evaluable`.

`C2` passes only when:

* the negative control returns
  `thermomechanical_screening.status = not_applicable`;
* it emits none of `TRIAGE-THERMOMECH-001` through
  `TRIAGE-THERMOMECH-007`.

A control fails when any required condition above is not met.

## 16. Final Dispositions

Scientific disposition is assigned only after the validity gate passes. If a
benchmark-invalid or source-insufficiency disposition applies, do not assign
`in_scope_generalization_supported`,
`partial_in_scope_generalization`, or
`in_scope_generalization_not_supported`.

For the scientific dispositions below, let `N` be the number of applicable
P2–P8 dimensions. The candidate-inclusion contract requires `N >= 3`.

### `in_scope_generalization_supported`

Requires:

* the validity gate passes;
* P1 is `PASS`;
* C1 and C2 pass;
* no applicable P2–P8 dimension is `FAIL`;
* at least `ceil(N / 2)` applicable P2–P8 dimensions are `PASS`;
* every remaining applicable P2–P8 dimension is `PARTIAL`.

This supports generalization only for the tested case class.

### `partial_in_scope_generalization`

Requires:

* the validity gate passes;
* the criteria for `in_scope_generalization_not_supported` do not apply;
* the criteria for `in_scope_generalization_supported` are not all satisfied;
* P1 is `PASS` or `PARTIAL`;
* at least one applicable P2–P8 dimension is `PASS` or `PARTIAL`;
* C1 and C2 do not both fail.

This disposition includes, without limitation:

* fewer than `ceil(N / 2)` applicable dimensions being `PASS`;
* one or more applicable dimensions being `FAIL` while the complete applicable
  set is not all `FAIL`;
* all applicable dimensions being `PARTIAL`;
* exactly one control failing;
* P1 being `PARTIAL` rather than `PASS`.

### `in_scope_generalization_not_supported`

Applies when the validity gate passes and at least one of the following is true:

* a human-verified in-scope primary case returns
  `thermomechanical_screening.status = not_applicable`;
* P1 is `FAIL`;
* every applicable P2–P8 dimension is `FAIL`;
* C1 and C2 both fail.

### Scientific Disposition Precedence

Apply scientific outcomes in this order:

1. benchmark invalidity or source insufficiency;
2. `in_scope_generalization_not_supported`;
3. `in_scope_generalization_supported`;
4. `partial_in_scope_generalization`.

The conditions are intended to produce exactly one primary scientific
disposition for every valid and sufficiently evidenced benchmark.

### Governance Disposition

`governance_pass`

No numerical prediction, route approval, customer-facing performance claim,
automatic calibration, automatic learning or engineering-memory promotion was
fabricated from the benchmark output.

`governance_blocked`

At least one prohibited governance action or claim appeared.

The final assessment must report both:

* one primary scientific disposition;
* one governance disposition.

`governance_blocked` is not benchmark invalidity and does not rewrite the
primary M14 scientific disposition. It blocks all downstream approval, learning,
calibration, promotion and customer-facing use until addressed in a separate
reviewed PR.

### `benchmark_invalid_due_to_leakage`

Outcome, source identity, expected status or expected rule information reached Role D.

### `benchmark_invalid_due_to_scope_mismatch`

The primary candidate is later shown not to satisfy the frozen strict-scope contract.

### `benchmark_invalid_due_to_frozen_history_change`

A frozen input, export, sealed artifact or phase-one commit was rewritten or replaced.

### `benchmark_inconclusive_due_to_source_insufficiency`

The source cannot support a reliable reveal or scoring comparison despite valid isolation.

## 17. Stop and Invalidation Conditions

### 17.1 Stop Before Phase One

Stop when:

* scope is ambiguous;
* process order is unresolved;
* blind inputs cannot be separated;
* Role D has seen the full source;
* scoring changed after source-outcome inspection;
* the source was used to tune M14;
* no independent reveal is possible;
* the sealed registration cannot be completed.
* the generic benchmark infrastructure was not frozen before candidate
  screening;
* the M15B execution baseline commit was not recorded before candidate
  screening;
* the recorded execution baseline contains an unreviewed M14 semantic change;
* the phase-one working tree does not match the recorded execution baseline for
  production code, workflows, schemas or dependency manifests;

### 17.2 Invalidate After Phase One

Invalidate when:

* source identity appears in phase-one files;
* outcome values leak;
* expected rules are supplied to Role D;
* source terminology is rewritten to force activation;
* frozen artifacts are regenerated or replaced;
* the phase-one commit is squashed away;
* M14 changes before evidence reveal;
* sealed files do not match precommitted hashes;
* the primary case is later found out of scope.
* production code, workflows, schemas or dependency manifests differ from the
  recorded execution baseline;

### 17.3 Recoverable Defects

Recoverable only before phase-one freeze:

* spelling errors;
* formatting errors;
* missing non-semantic confidentiality marker;
* export packaging errors that do not alter case bytes or triage output.

After freeze, semantic changes require cancellation and a new benchmark run.

## 18. Frozen Artifacts and Hashing

Phase one must freeze:

* the 12 numbered Canonical Case files;
* Blind Input Packet;
* Blind Input Manifest;
* Role D Information Receipt;
* Sealed Registration Manifest;
* triage JSON and Markdown;
* Decision Board JSON and Markdown;
* review manifest;
* human-review checklist;
* ruleset version;
* M14 source hash;
* schema-tree hash;
* dependency-manifest hashes;
* main baseline commit;
* phase-one commit;
* protocol merge commit SHA;
* M15B execution baseline commit SHA;
* deterministic production-code tree hash;
* workflow tree hash;
* SHA256 of every frozen artifact.

The baseline manifest must not hash itself unless a second-level manifest is explicitly used.

Hash tests must work:

* without network;
* without `.git`;
* in a shallow checkout;
* using the Python standard library.

A hash mismatch is a benchmark blocker, not a warning.

## 19. Benchmark PR Boundary

The M15B benchmark PR may contain:

* approved primary case;
* phase-one frozen exports;
* control regression checks;
* Evidence Objects;
* Measurement References;
* PRL records;
* Gold Case assessment;
* benchmark-specific tests;
* methodology documentation.

It may not contain:

* M14 rule changes;
* applicability changes;
* new trigger keywords;
* new thresholds;
* generic triage fixes;
* Decision Board fixes;
* pattern changes;
* engineering-memory promotion;
* automatic calibration;
* source-specific parsing;
* unrelated refactoring.

All discovered implementation defects are documented and deferred to later PRs.

## 20. Candidate-Screening Dossier

For every candidate, Role B records:

* candidate alias;
* full source identity;
* primary-source type;
* material system;
* structural state before integration;
* structural state during integration;
* structural state after integration;
* integration method;
* thermal significance;
* retained relationship;
* process sequence;
* available pre-outcome facts;
* available outcomes;
* direct versus inferred measurements;
* raw-data availability;
* scope verdict;
* hard-exclusion results;
* soft-risk flags;
* blind separability;
* similarity to prior benchmarks;
* terminology risks;
* recommended role:

  * primary;
  * boundary;
  * negative control;
  * reject.

At least three plausible primary candidates must be compared before selection.

## 21. Execution Sequence

### Phase 0 — Protocol Freeze

Owner: Role A

Output:

* merged protocol document;
* protocol commit SHA.

No final source selection occurs before this phase completes.

### Phase 0.5 — Generic Benchmark Infrastructure Freeze

Owner:

Assistant for design and review; Codex only for approved repository
implementation.

Allowed work:

* reusable deterministic hashing;
* sealed-manifest validation;
* source-identity and outcome-leakage test helpers;
* execution-baseline verification;
* generic no-`.git` and shallow-checkout test support.

Prohibited work:

* candidate-specific strings;
* candidate facts;
* source-specific parsing;
* M14 applicability or rule changes;
* result-specific scoring logic.

Output:

* independently reviewed infrastructure PR;
* successful exact-head CI;
* recorded immutable M15B execution baseline commit and hashes.

Gate:

This phase must complete before candidate literature screening begins.

### Phase 1 — Candidate Screening

Owner: Role B

Output:

* candidate dossiers;
* comparison matrix;
* proposed primary and negative control.

Gate:

Independent scope review by the assistant.

### Phase 2 — Sealed Registration and Blind Packet

Owner: Role C

Output:

* Blind Input Packet;
* Blind Input Manifest;
* sealed registration documents;
* sealed hash manifest;
* leakage-audit report.

Gate:

No prohibited information in Role D packet.

### Phase 3 — Blind Phase-One Construction

Owner: Role D, fresh Codex session

Output:

* 12 Canonical Case files;
* deterministic outputs;
* frozen baseline manifest;
* phase-one commit.

Role D stops after push.

### Phase 4 — Evidence Reveal

Judgment owner: Role E

Implementation:

A separate Codex session receives exact approved file contents.

Output:

* source identity;
* Evidence Objects;
* Measurement References;
* PRL record.

No phase-one file changes.

### Phase 5 — Assessment

Owner: Role E

Output:

* source-fidelity audit;
* sealed-file reveal verification;
* categorical scoring matrix;
* final disposition;
* secondary coherence findings.

### Phase 6 — Independent Review

Owner: Role F

Output:

* merge/no-merge decision;
* blocking findings;
* exact-head CI confirmation.

### Phase 7 — Merge

Implementation:

Luna Low merge-only Codex task after approval.

### Phase 8 — Separate Correction Planning

Owner:

Assistant.

Any rule or Decision Board correction becomes a separate milestone and PR.

## 22. Required Automated Tests

### Generic Infrastructure Tests

* deterministic tree hashing;
* hash verification without `.git`;
* canonical versus public-text scope isolation;
* metadata cannot alter triage;
* public metadata remains claim-safety scanned;
* public metadata remains confidentiality scanned;
* sidecar reciprocal linkage;
* exact-head deterministic JSON;
* unchanged M13/M14/M15A frozen baselines.
* sealed source documents are absent from the repository and Role D packet
  before reveal;
* the production-code tree matches the recorded execution baseline;
* workflow, schema and dependency hashes match the recorded execution baseline;
* primary scientific and governance dispositions are represented separately;

Generic infrastructure must be frozen before candidate literature screening
begins.

### Benchmark-Specific Tests

* exact 12-file set;
* canonical hashes;
* Blind Input Packet and Manifest hashes;
* source identity absent before reveal;
* outcome values absent before reveal;
* causal conclusions absent before reveal;
* natural terminology preserved;
* Role D receipt present;
* sealed registration hashes verified after reveal;
* relevance/N/A mapping unchanged;
* primary triage deterministic;
* M15A boundary control unchanged;
* negative control remains not applicable;
* Evidence and PRL cannot alter phase-one triage;
* PRL null prediction preserved when no numerical prediction exists;
* no M14 source change;
* no schema change;
* no dependency change;
* no network dependency;
* no Git-history dependency.
* at least three P2–P8 dimensions were pre-registered as applicable;
* at least two genuine source-faithful evidence gaps were pre-registered;
* no evidence gap was manufactured by deleting admissible source-provided facts;
* sealed source documents remain absent until reveal;
* the final assessment reports separate scientific and governance dispositions;

## 23. Independent Review Gate

Merge requires all of:

* exact reviewed head;
* successful exact-head CI;
* no unresolved review threads;
* valid strict-scope registration;
* valid leakage audit;
* intact frozen hashes;
* revealed sealed files matching hashes;
* source-fidelity audit pass;
* scoring contract applied without post-result revision;
* no M14, schema or dependency change;
* no phase-one rewrite.

## 24. Model Routing

* Protocol design and review: assistant
* Candidate literature research and selection: assistant
* Blind Input Packet and leakage judgment: assistant
* Phase-one repository construction: GPT-5.6 Terra, Medium
* Evidence interpretation and scoring: assistant
* Structured sidecar implementation: GPT-5.6 Terra, Medium
* Cross-module implementation, only when later approved: GPT-5.6 Terra, High
* Independent architecture and benchmark audit: assistant
* Merge-only execution: GPT-5.6 Luna, Low

Sol High is reserved for unresolved core-scope or scoring-contract conflicts.

Terra High is reserved for approved cross-module implementation with substantial compatibility risk.

## 25. Open Questions

No unresolved decision blocks protocol freeze.

The following remain intentionally deferred until after protocol merge:

* final primary source;
* final negative control;
* candidate-specific relevance/N/A registration;
* candidate-specific Blind Input Packet;
* any later M14 correction.

## 26. Recommendation

`READY TO FREEZE PROTOCOL`
