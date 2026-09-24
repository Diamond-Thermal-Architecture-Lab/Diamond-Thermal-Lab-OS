# M16B LECF Schema and Interface Proposal

- Status: proposed
- Layer: L1 Architecture with L2/L3 data interfaces
- Related design: [Literature-derived Engineering Case Framework](M16B_LITERATURE_CASE_FRAMEWORK.md)
- Related task: [M16B task brief](M16B_LECF_TASK_BRIEF.md)
- Confidentiality level: Public-safe

## Scope and Representation

These are proposed logical contracts for a manual pilot, not executable JSON schemas or changes to current runtime validation. Manual Markdown tables can carry them initially. A later schema-first task must resolve serialization and validation details with reviewed fixtures before introducing JSON persistence. No new field or enum is added to an existing EVD, MSR, PRL, Claim Ledger, EPR, Plan or EER.

Use six record types rather than a general evidence graph:

| Record | Proposed ID prefix | Authority |
| --- | --- | --- |
| Literature Metadata | `LIT-###` | Identity, version, access, rights, discovery and screening of one source |
| Evidence Mapping | `LEM-###` | Located assertions and explicit links to existing evidence/claims |
| Engineering Parameter Extraction | `LPE-###` | Source values, methods, conditions, transformations and review of each parameter |
| Case Reconstruction | `LCR-###` | A bounded reconstruction and mappings into a case/EPR |
| Validation Status | `LVS-###` | Exact validation scope, dataset independence, protocol, findings and human review |
| Gold Candidate Status | `LGC-###` | Human candidacy/certification disposition for an exact case revision and intended use |

Proposed working area: `literature/<literature_case_id>/`, outside `cases/` until a canonical Engineering Case is warranted. A `literature_case_id` is a stable lowercase slug; it is not a replacement for canonical `case_id`. Each record has its own revision. IDs are unique within that workspace and never reused. Fully qualified links include workspace, record ID, revision and content identity; case-local EVD/MSR/PRL/CLM references additionally include `case_id` and artifact identity. A paper can be cited in several workspaces, using the same source/version and dataset-family identities.

No proposed directories are created by this documentation task. Future case artifacts retain the canonical 12-file structure and existing `engineering/problems`, `engineering/evaluations`, `evidence`, `measurements`, and `prediction_reality` sidecar locations. LECF references these locations externally. There is no `engineering/plans` directory.

The six types are stage-dependent rather than six mandatory records per paper. A registration or exclusion may use only LIT; LEM/LPE exist only for attempted extraction; LCR exists only for a reconstruction; LVS is activity-specific and may have pre-execution and post-execution revisions; and LGC exists only for an actual nomination or disposition. Do not create empty downstream records to satisfy a count.

## Shared Required Fields and Rules

For future JSON, all six records require the fields below. “Required” means the field must be present; a null value is allowed only where stated and must carry a reason. Empty strings cannot disguise missing information. The manual Markdown pilot follows the identity exception below and may mark a stage-dependent value `pending` only with reason, responsible owner and resolution gate. A pending field grants no review, freeze, use or transition authority; every field required by the pre-execution freeze must be resolved before execution.

| Field | Proposed type and rule |
| --- | --- |
| `record_type`, `format_version` | Closed record-type token; provisional version `lecf-proposal-0.1`. A later approved schema receives its own version without relabelling older records. |
| `record_id`, `revision`, `literature_case_id` | Prefix ID, positive integer revision, workspace slug. Exact `(workspace, ID, revision)` is immutable once reviewed. |
| `case_id` | Canonical case slug or null before association; every non-null external case link is separately checked. |
| `owner`, `created_at` | Human owner identifier and ISO-8601 UTC timestamp; accountability metadata, not a solver input. |
| `confidentiality_level` | Existing `public`, `internal`, `customer-confidential`, `restricted` vocabulary; higher sensitivity requires controlled storage/sanitized references. |
| `supersedes` | Prior revision reference or null. Correction preserves the old record and explains the change. |
| `input_refs` | List of exact source/artifact references used; hashes and hash authority are explicit. |
| `record_content_sha256` | Lowercase SHA-256 for a future canonical JSON record excluding only this self-hash. Includes governance metadata; distinct from M16A reproducibility identities. A manual Markdown record does not populate or claim this future identity. For each bound manual dependency, the LECF validation-freeze manifest records its exact Git commit, repository-relative path, Git blob OID with algorithm, and exact file SHA-256. The manifest does not self-identify inside its own content: the later reviewer attestation names the authoritative LVS revision's exact Git/file identity, avoiding a recursive hash. |
| `review_events` | Initially empty list. Each event records event ID, subject revision/hash, action, previous/new state, human actor/role, UTC date, rationale, evidence refs, unresolved objections, and independence/conflict declaration. |

A reference requires `namespace`, `id`, `revision_or_version`, `reference`, `hash_authority`, `sha256`, and `availability`. References are public-safe relative paths, bibliographic locators or opaque controlled identifiers, never credentials or private absolute paths. `sha256` may be null only with `unavailable_reason`; a DOI/URL establishes a locator, not exact byte identity. Hash authority distinguishes exact file bytes, committed Git blob content and canonical record content. Different authorities are never silently substituted. No source bytes need to be uploaded to establish a controlled hash reference.

### Manual Repository-Global Family Register

The pilot maintains one repository-global family register shared by every literature workspace; it is not a seventh per-study record. Source-family IDs use globally qualified form `lecf:source-family:SRCF-######`; dataset-family IDs use `lecf:dataset-family:DSF-######`. Workspaces store those complete identifiers, never workspace-local substitutes.

Each family entry records canonical ID, known aliases, member source/assets/datasets, and append-only identity assertions. Each assertion names the compared identities, disposition `same`, `distinct`, or `unresolved`, evidence references, rationale, conflicts, accountable lineage steward, independent reviewer, decision event and any superseded assertion. The lineage steward may propose an alias, merge or split, but it becomes effective only after review by a person independent of the affected extraction/reconstruction. A correction appends a superseding assertion and impact event; it never rewrites earlier family history. Competing, conflicting or insufficient assertions remain `unresolved`. Any affected LVS must then keep `independence_assessment: unresolved`, and neither independent-accuracy nor Gold-accuracy use may advance.

For future JSON, use the existing M16A canonical serialization behavior with an explicit record-owned hash projection; do not change its algorithm or EPR/EER projections. For source documents use exact acquired-byte hashes and version metadata. A file change creates a new revision and invalidates dependent review for new use until assessed. Hashes prove identity, not truth. Future machine checks may report holds/findings; they cannot synthesize human review events or approve transitions.

Proposed event actions cover register, screen, submit, accept-for-stated-use, request-evidence, reject, suspend, correct, supersede, withdraw and reopen. A review event binds an already captured subject revision/hash and is recorded in a later revision; it never references the enclosing record's own hash recursively. Its disposition applies only to that subject snapshot. Adding review metadata can preserve that disposition by linking the unchanged subject; changing evidence, inputs or scope requires a new review. Competing events require human resolution. Ordinary drafts may change before review, but no previously bound revision or frozen snapshot is overwritten. A self-entered human name is not an authenticated signature.

## 1. Literature Metadata

| Required field | Content and constraints |
| --- | --- |
| `citation` | Title, authors, venue, year, DOI or stable URL, language and source type. Missing bibliographic facts remain null with reason; identity uncertainty blocks parameter use. |
| `source_version` | Publisher/preprint version label, publication/revision date, repository-global `source_family_id`, related versions and their relationships. IDs and aliases resolve through the family register. Do not merge preprint, accepted manuscript, final article and supplement asset identities. |
| `publication_status` | `peer_reviewed`, `preprint`, `other`, or `unverified`, plus verification locator/date/reviewer. Journal reputation/citation count does not set evidence reliability. |
| `integrity_status` | `no_notice_found`, `corrected`, `expression_of_concern`, `retracted`, or `unchecked`; checked authority/location/date and linked notices. No notice found is bounded to the recorded check, not a continuing guarantee. |
| `source_assets` | Article/supplement/data/code assets, each with asset ID, version, controlled reference, byte hash or unavailable reason, access date and access state (`accessed`, `metadata_only`, `inaccessible`). Missing supplements are individually recorded. |
| `rights_access` | License/rights statement locator or `unknown`, access basis, storage/redistribution permissions for text/figures/data, allowed use, restrictions and review owner/date. Access permission and publication permission are independent. |
| `discovery` | Engineering question, search scope, database/catalogue, query, search date, selection rationale and known search limitations. |
| `screening` | Each design credibility dimension with finding/reasons/references; intended use; disposition (`reconstruct`, `background_only`, `hold`, `exclude`); explicit exclusion reasons and reviewer event. |
| `dataset_families` | Repository-global experiment/dataset-family IDs, related reports and reuse evidence, or an `unresolved` register assertion plus investigation action. Different DOIs are not independence evidence. |
| `update_events` | Correction/retraction/access/rights notices with source locator, date, affected assertion IDs and impact-review reference. |

Peer review is metadata. A retracted finding cannot support new engineering use; retain its record and impact history. A corrected version requires renewed assertion checking. Source screening can retain scientifically credible but irrelevant work as background.

## 2. Evidence Mapping

`assertions` and `relations` are required lists. An assertion requires:

- `assertion_id` (`AST-###`), narrow `statement`, and `assertion_kind`: `reported_measurement`, `reported_simulation`, `fitted_parameter`, `author_inference`, `qualitative_observation`, or `reconstruction_assumption`.
- `source_ref` and `locator`: exact asset/version and page plus figure/panel/table/row/equation/section/supplement identifier as available. A DOI alone is insufficient. A reconstruction assumption instead needs explicit rationale and author; it cannot claim a paper locator supports a value absent from that paper.
- `sample_ref`, `dataset_ref`, `method`, `operating_conditions`, `uncertainty_summary`, and `applicability_limits`; use explicit unresolved records when the paper omits them.
- `observation_polarity`: positive, negative, null, mixed or unspecified; `alternative_explanations`, `contradiction_refs`, and `missing_context`. Never translate “not reported” into a negative outcome.
- `extraction_method`: manual, OCR-assisted, AI-assisted or digitized, with tool/version when used and exact source-check review event. Tool output begins unreviewed.

A relation requires `relation_id`, fully qualified `from_ref`/`to_ref`, `relation_type`, `scope`, and `basis`. Proposed types are `transcribed_from`, `derived_from`, `supports`, `contradicts`, `background_for`, `conflicts_with`, `unknown_relation`, `same_dataset_as`, and `supersedes`. A workspace-level `same_dataset_as` relation cites the effective repository-global family-register assertion; it cannot create, merge or split a family locally. Preserve all conflicting assertions; do not average them or elect a winner silently. Cross-record derivation cycles reject the mapping.

The `legacy_bindings` list names exact case/EVD/MSR/PRL/claim artifact hashes, assertion IDs, relationship and review basis. The current EVD can express support/contradiction of existing Claim Ledger IDs. The richer relationships stay here. A new public-safe measurement EVD must explicitly map `transcribed_from` the source literature EVD/assertion; this is the proposed solution to the existing provenance gap, not a new evidence type.

## 3. Engineering Parameter Extraction

`parameters` is a required list of parameter records. Each requires:

| Field | Meaning |
| --- | --- |
| `parameter_id`, `assertion_refs`, `quantity_label` | `PAR-###`, exact assertion revisions, and physical observable/property definition including reference plane or normalization basis. |
| `source_value` | Original lexical number/unit, table/figure locator and reported precision. Numeric values are finite decimal strings. Qualitative values, ranges, censored limits and absent values retain their original form; no fabricated midpoint or point estimate. |
| `origin` | Directly measured, author-fitted, author-simulated, source-inferred, reconstruction-derived or assumed; origin does not change after review. |
| `sample` and `dataset_ref` | Paper sample/series label, sanitized local sample alias, count or missing reason, specimen state and repository-global dataset-family identity or unresolved register assertion. Never combine different specimens or process stages silently. |
| `method` and `conditions` | Measurement/fit method, calibration/reference basis if reported, operating/material/process state, geometry, temperature basis and boundary conditions. Missing details are explicit. |
| `uncertainty` | Reported uncertainty form, value/bounds and unit where supplied, basis, coverage factor/confidence level if reported, sample versus measurement variation, and digitization/conversion uncertainty separately. Missing uncertainty is `not_provided`, never zero. |
| `normalization` | Quantity kind, canonical decimal/unit, original-to-canonical conversion rule and registry version, or blocked/unsupported reason. Preserve absolute temperature versus difference and area-normalized versus absolute resistance. |
| `derivation` | Formula/method identifier, dependency parameter refs, operation order, assumptions and reproducible calculation reference; null for direct transcription. Fitting history and target datasets are mandatory when fitted. |
| `disposition` | `provided`, `assumed`, `missing`, `conflicting`, or `evidence_required`, with rationale and evidence action. Source-reported presence is not engineering validity. |
| `conflict_group` | Related inconsistent records and proposed resolution, or null; conflicting originals remain accessible. |
| `use_roles`, `review_event_refs` | Intended input/fit/select/target/control roles and exact human checks. Decision-relevant values need independent source checking. |

If digitization is later authorized, record axis scale, image asset/version, calibration points, extraction method, estimated resolution and independent check; digits extracted from a plot do not increase the publication's precision. This task performs no digitization.

For M16A input, construct its existing complete `QuantifiedValue` envelope using the public quantity APIs. An unsupported unit/kind remains a LECF gap; no new registry token is added. Confidence is retained separately from numeric uncertainty. An interval without a reported central value cannot silently become a scalar input.

## 4. Case Reconstruction

| Required field | Meaning |
| --- | --- |
| `question`, `intended_use`, `route_scope` | Bounded engineering question, target decision/test, diamond and non-diamond comparator rationale and exclusions. |
| `source_refs`, `assertion_refs`, `parameter_refs` | Exact reviewed revisions; mixed-source constructions explicitly identify every origin. |
| `physical_system` | Source/power/profile, geometry/stack, material state/orientation, interfaces, thermal and mechanical boundaries, process sequence, sample state and measured observables/reference planes. Each item maps to a parameter/assertion or a declared gap. |
| `reconstruction_changes` | Reductions, inferred geometry, equivalent boundaries and counterfactual variants distinguished from source facts, with rationale, assumptions and limits. |
| `gaps`, `conflicts` | Stable IDs, affected field paths, missing/conflicting basis, consequence for intended use, blocking status and next evidence action. |
| `completeness` | Per-field/use completeness findings; no universal completeness score. |
| `canonical_bindings` | Case ID and hashes of canonical files read/created through the existing reviewed workflow, or explicit pending status before case creation. |
| `epr_mapping` | Two-way mapping between every non-missing literature-derived or reconstruction-derived EPR envelope path and its parameter record. Each exact candidate/global EPR path maps once to reviewed `direct`, `converted`, `derived`, `fitted`, or `assumed` provenance; transformation, intended envelope status, all dependency parameter/source-asset refs and review refs are explicit. Binding includes persisted EPR reference, `compiled_content_sha256`, exact file hash and version when available; otherwise pending and ineligible for freeze. |
| `intended_input_paths` | Canonically ordered selected-candidate/global path inventory intended for the evaluation, with each path linked to its `epr_mapping` entry or declared non-literature source. It is frozen before execution and later compared with actual model `consumed_input_paths`. |
| `validation_plan_ref`, `review_event_refs` | Intended independent checks and human reconstruction acceptance; null with reason while drafting. |

EPR provenance mapping must obey its current closed contract: `source_type: literature` carries no EVD/MSR IDs; `evidence_object` carries one EVD; `measurement_reference` carries one EVD and one MSR. All use a non-empty safe reference and appropriate source hash/review status. Use the LECF mapping to retain multiple source dependencies; never overfill single-ID fields or smuggle undocumented provenance into the kernel.

The EPR `source_case_sha256` map accepts only numbered canonical files. LECF's source/parameter revision bindings therefore need a separate pre-use check; existing M16A stale-source checking does not automatically detect corrected papers or LECF records. The proposed manual gate checks those bindings before each use. If the source basis changes, hold new use, issue a new reconstruction and explicitly recompile as appropriate. Preserve the original EPR/EER and historical decision.

EPR expresses model-independent problem state. An assumed source value maps as `assumed` with rationale; its exact path must be acknowledged in each Plan that consumes it. Rejected evidence cannot be rescued by relabelling it `provided`. Model selection, sweep/OAT choices, model options and acknowledgements stay in Plan; actual applicability stays in EER. A literature-review event does not authorize changing these contracts.

LCR contains no actual EER, Model Manifest, output, applicability or post-execution consumed-path binding. Once an LCR is named by an authoritative pre-execution freeze, that revision remains unchanged. Actual execution bindings belong only to a later LVS revision referencing the frozen LCR and freeze. Correcting reconstruction evidence, assumptions, scope or mapping requires a new LCR revision, new freeze and new evaluation; an earlier EER cannot be retroactively attached to it.

## 5. Validation Status

| Required field | Meaning |
| --- | --- |
| `scope` | Exact reconstruction/case revisions, intended use, observable/reference plane, operating envelope and limits. A computational activity always names the unchanged frozen LCR revision. |
| `validation_kind` | `extraction_check`, `reconstruction_check`, `analytic_verification`, `published_result_reproduction`, or `independent_empirical_validation`. Use separate records for distinct activities. |
| `protocol_ref` | Version/hash of predeclared targets, metrics, uncertainty treatment, case-specific acceptance basis, exclusions, failure rules, controls and reveal sequence. Null before planning. |
| `dataset_lineage` | Dataset-family/sample-group/partition refs, shared-source or shared-fit relationships, roles (input/calibration/model-selection/validation-target/control), known dependence and unresolved lineage. |
| `independence_assessment` | `not_assessed`, `dependent`, `unresolved`, or `independent_for_stated_use`, with evidence, reviewer and conflicts/exposure declaration. Different author/reviewer/DOI alone is insufficient. |
| `freeze_role` | `none`, `authoritative_pre_execution_freeze`, or `post_execution_assessment`. Exactly one immutable LVS revision per computational activity uses `authoritative_pre_execution_freeze`. |
| `pre_execution_freeze` | Null for a non-computational check. For the authoritative freeze, contains the LECF validation-freeze manifest: exact LIT/LEM/LPE/LCR revisions and manual/future content identities; exact source-asset versions and byte hashes; EPR reference, `compiled_content_sha256` and exact file SHA-256; complete canonical Evaluation Plan snapshot and recomputed `evaluation_plan_sha256`; intended Model Manifest identity or deterministic predeclared selection rule; intended selected-candidate/global input-path inventory; target sample/dataset partitions and roles; and freeze reviewer evidence. A post-execution revision references this exact freeze identity without changing it. |
| `exposure_and_freeze` | Executor/custodian roles, prior outcome access, visibility, freeze/reveal events, and retrospective/blind classification with evidence. All freeze-required fields are resolved in the authoritative pre-execution revision; no invented blind baseline. |
| `execution_bindings` | Empty in the authoritative pre-execution freeze. A post-execution LVS revision records exact EER file/content identities, embedded Plan and Manifest hashes, `evaluation_input_sha256`, candidate/output identities, pointers to actual applicability findings and actual `consumed_input_paths`; it also names the unchanged frozen LCR revision and exact freeze identity. No duplicate editable Plan or EER. |
| `measurement_refs`, `comparison_refs` | Exact EVD/MSR/PRL references and target bindings. Record empty lists for non-computational checks. |
| `comparability` | Quantity definition/label, unit, sample state, measurement plane, time/operating/thermal boundary matching; allowed transformation and reviewed basis or non-comparable reason. |
| `findings` | Planned versus observed checks, residuals where comparable, failures, adverse results, uncertainty limitations and possible error sources. No residual for absent/non-comparable predictions. |
| `status` | `not_started`, `planned`, `in_review`, `supported_for_scope`, `inconclusive`, `failed`, `suspended`, or `withdrawn`, with human event and unresolved actions. |
| `impact_register` | Affected downstream artifact revision/hash, issue/notice, owner, new-use hold, correction/review action and closure evidence. Empty only when no known impact exists. |

The one authoritative pre-execution LVS revision is immutable after its exact record/file identity is registered. Before outcome reveal, an independent reviewer resolves and checks every frozen reference and source-asset byte identity; reconstructs EPR content and file identities; reconstructs the complete Plan with the existing M16A canonical identity implementation and recomputes its hash; resolves the declared Model Manifest identity or deterministic selection rule; and checks intended paths, target partitions/roles, custodian/executor separation and exposure declarations. The reviewer event identifies that exact LVS revision and identity. A missing, pending or mismatched freeze field blocks execution under this protocol.

The complete Plan snapshot is registration evidence embedded in the LECF freeze, not a standalone primary M16A Plan sidecar and never an `engineering/plans` artifact. The eventual EER must embed a Plan canonically identical to the frozen snapshot and carry the same `evaluation_plan_sha256`; its embedded Model Manifest must match the frozen identity or the result of the frozen deterministic selection rule. A mismatch means the execution was not the predeclared run. The post-execution LVS revision preserves the freeze and LCR references while adding actual execution bindings; it never edits or substitutes them.

After execution, compare every actual model `consumed_input_paths` entry with the frozen inventory and inverse LCR mapping. Each consumed non-missing literature-derived or reconstruction-derived envelope must resolve to exactly one reviewed mapping with all declared dependencies. An extra, missing, ambiguous or unmapped consumed path invalidates a claim of complete source-to-output traceability even if the calculation itself is structurally valid.

`supported_for_scope` in an extraction check means faithful transcription. It cannot be interpreted as physical validation. Independence is assessed per target/use; a dataset consumed for parameter fitting or model selection cannot be marked independent for validating that same result. Unresolved dependence blocks an independent-validation claim. Holdout partitions require justified separation and disclosure of shared systematic errors.

Legacy mapping uses numeric JSON MSRs/PRLs without altering schemas. A future explicit mapping must preserve value identity through their decode domain; refuse unsupported precision or semantics rather than round to fit. Keep full source precision in LPE. Use M16A's existing projection for EER predictions, including exact label and registered-unit checks. Physical comparability and independent validation require this additional review; passing the adapter alone is insufficient.

The existing PRL comparator retains `signed_error = reality - prediction`; relative error is absent when reality is zero. Any different metric belongs to the separately declared validation protocol/report. Do not rewrite the comparator or describe reproduction residuals as a calibrated accuracy claim.

## 6. Gold Candidate Status

| Required field | Meaning |
| --- | --- |
| `subject_refs`, `intended_gold_use` | Exact case/reconstruction/validation revisions and proposed scope: regression, independent physical accuracy, or case-specific validation. These uses are never silently substituted. |
| `status` | `not_nominated`, `proposed_candidate`, `gold_candidate`, `certified_gold`, `rejected`, `suspended`, `withdrawn`, or `superseded`. Vocabulary is proposed; no certificates are created here. |
| `policy_ref` | Previously approved certification/eligibility policy identity, scope and responsible authority; null means certification cannot proceed. No policy is invented by this proposal. |
| `gate_findings` | Source integrity, fidelity, reconstruction, applicability, independence, control coverage, uncertainty, objections and unresolved actions, each bound to evidence and reviewer. |
| `validation_refs` | Completed checks and outstanding independent evidence/measurement requirements; candidacy may precede their completion. |
| `decision` | Human actor/role, independence/conflict declaration, date, rationale, previous/new state and review/PR reference; null until a human acts. |
| `certificate` | Null unless a separately authorized certification occurs; then exact certified revisions, authority, policy, validation scope, limitations, issue date and re-review/expiry triggers. |
| `permitted_uses`, `prohibited_uses` | Explicit applicability boundary. Calibration, memory, specification and customer release each need their existing separate review; none follows from candidacy alone. |
| `customer_release_ref` | Existing release decision for the exact artifact/claim or null. Neither a certificate nor `public` confidentiality implies release permission. |
| `impact_register`, `review_event_refs` | Suspension/correction/withdrawal dependencies and accountable history. |

No boolean such as `is_gold` replaces the gate findings. Certification is unavailable until an independently reviewed policy defines its evidentiary requirements and authority. Physical-accuracy certification requires independent empirical evidence for its stated scope; transcription checks, analytic fixtures and same-paper reconstruction alone cannot satisfy it. Machine validation may check required references, but only an authorized human decision can advance candidacy or certification.

## Proposed Cross-Record Checks for Review

These acceptance examples describe later manual/schema checks; they are not new automated tests.

| Input condition | Required disposition |
| --- | --- |
| DOI resolves but source/supplement cannot be inspected | Metadata/background or hold; no unverifiable parameter acceptance. |
| Peer-reviewed source has unknown measurement uncertainty | Preserve `not_provided`; review its consequence. No inference of zero error or certification. |
| Published temperature and fitted TBR share a dataset | Preserve fit lineage; reproducing temperature is dependent evidence. |
| Two studies disagree under unresolved conditions | Preserve both assertions and a conflict; no automatic average or ranking. |
| Source/dataset-family assertions conflict or remain unresolved | Keep the global family and validation independence `unresolved`; block independent-accuracy and Gold-accuracy claims. |
| Quantitative field lacks source locator, sample mapping or needed condition | Hold that use or explicitly hypothesize a separate assumption for permitted screening; no validated-input promotion. |
| Lateral spreading or unequal direct-convection area is material | Place a manual pre-execution **do not run** hold as needed; if attempted under strict 1D the M16A disposition is `not_applicable`. More data alone cannot make that physics applicable. |
| Required in-model input or acknowledgement is missing/unusable | EPR may remain `HOLD_FOR_INPUT` before evaluation; an otherwise valid attempted strict-1D scenario is `blocked`, not `not_applicable`. |
| Explicit sweep/OAT request is invalid | Preserve the M16A scenario disposition `invalid`; do not relabel it `blocked` or `not_applicable`. |
| Actual `consumed_input_paths` contains an unmapped literature/reconstruction value | Preserve the calculation record but invalidate the complete source-to-output traceability claim and require a new reviewed mapping/freeze/evaluation cycle. |
| Source value cannot survive legacy numeric projection | Refuse projection, retain source value and diagnostic. |
| Corrected paper changes a parameter after EER creation | Record dependency impact, hold new use and issue reviewed revisions; preserve prior EER bytes. |
| Final record requests `certified_gold` without policy/authority/independent scope evidence | Reject transition; no automatic approval or fabricated attestations. |

## Open Contract Decisions

Independent architecture review must confirm the specified global-family authority, stage-dependent six-record burden, one-freeze/LCR immutability rule, input-path closure, rights handling and certification vocabulary before a manual pilot. Executable schema/serialization design, safe writers, review-package extensions and enforcement of these gates require a separately authorized implementation task. Existing validators do not enforce the proposed LECF lifecycle, family register, freeze checks or correction propagation.
