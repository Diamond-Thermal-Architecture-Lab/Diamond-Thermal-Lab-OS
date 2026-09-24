# Design Doc: M16B Literature-derived Engineering Case Framework

- Layer: L1 Architecture; L0 governance and L2/L3 workflow interfaces
- Related task brief: [M16B LECF task brief](M16B_LECF_TASK_BRIEF.md)
- Status: proposed
- Confidentiality level: Public-safe
- Decision: Pending; no reviewer approval or implementation authorization recorded

## Problem Statement

Literature can supply engineering questions, observations, counterexamples, and reconstruction candidates when experimental cases are unavailable or confidential. A published result still carries uncertainties in methods, interpretation, sample identity, and applicability. LECF proposes a controlled path from that source to a case whose assumptions, evidence, and independent validation needs can be audited.

The useful unit is an individual assertion under stated conditions, not a paper summary or a paper-level quality score. This design follows the [design doc template](../templates/design_doc_template.md), the [existing case workflow](CASE_WORKFLOW.md), and the authority/reconciliation record in the task brief.

## Design Goals and Non-Goals

Preserve **AI optional, Evidence mandatory, Deterministic first, Human accountable**. Manual registration and reconstruction must remain viable without model services. Every engineering assertion needs a locator or an explicit assumption/gap. Stable identities, dimensional checks, reproducibility, and conflict detection precede automated extraction. Named humans own evidence review, risk acceptance, certification, and release.

The scope is literature acquisition planning, screening, assertion/parameter capture, case reconstruction, validation planning, and possible candidacy. This is neither a paper summarization product nor an AI training-data pipeline. It adds no automatic approval, material-property database, solver physics, runtime code, executable schema, graph database, API automation, or customer certification. No real paper is selected or assigned a performance claim in this proposal.

## Engineering Context and Placement

LECF is an optional input path across L1–L3. L0 retains governance authority; L4 remains the destination for separately reviewed requirements and specifications. The [12 canonical files](CASE_FILE_NAMING_STANDARD.md) retain their roles. A Literature Case may exist before a canonical case is justified, or support an existing engineering case.

```text
Engineering question / evidence gap
  -> bounded literature search and source registration
  -> assertion mapping and parameter extraction
  -> Literature Case reconstruction and human review
  -> Engineering Case / explicit quantitative authoring input
  -> EPR (model-independent problem and provenance)
  -> Evaluation Plan (model, scenarios, acknowledgement)
  -> applicability checks and selected kernel execution
  -> EER (embedded Plan/Manifest, actual applicability and outputs)
  -> optional prediction projection + reviewed measurement comparison
  -> validation assessment and possible Gold candidacy
  -> separate certification decision under an approved policy
```

Published observations also feed evidence/measurement references and validation plans without entering a kernel. A case outside strict 1D can remain valuable for qualitative screening, failure retrieval, or planning independent measurements. The existing preview -> review package -> Human Decision Record -> Canonical Decision Proposal -> explicit PR application chain retains decision authority.

## Credibility Dimensions

Each dimension records a finding, rationale, exact evidence references, limitations, reviewer, and date. Findings are `supported`, `limited`, `unresolved`, or `adverse` for the stated use, with exclusion/hold reasons. They are not a combined score and do not establish fixed numerical acceptance thresholds.

| Dimension | Question and bounded meaning |
| --- | --- |
| Publication credibility | Are identity, version, peer-review status, correction/retraction notices and access basis verifiable? Peer review describes publication process; it does not validate a reconstructed case. |
| Problem relevance | Do device, route, observable, scale, material state, and operating boundaries address this engineering question? |
| Reconstruction completeness | Which geometry, power, interface, material, source/sink, process-sequence and measurement fields can actually be reconstructed? Completeness is assessed per intended use. |
| Evidence reliability | Was the assertion measured, fitted, simulated, inferred, or merely stated? Are method, samples, calibration, uncertainty, confounders and contradictory observations visible? |
| Model applicability | Does the specific EPR/Plan satisfy the selected model's validity conditions? Actual execution findings belong to EER. |
| Independent validation | Is the comparison evidence independent of extraction choices, parameter fitting, model selection and outcome exposure? Independent review alone is not independent measurement. |
| Customer release permission | Has a responsible human approved the exact statement, evidence basis and rights/confidentiality scope through the existing release path? Publication and Gold candidacy grant no permission. |

A peer-reviewed study may be incomplete for thermal reconstruction. A complete reconstruction may be unsuitable for strict 1D. A reproduced published curve may be a useful retrospective check while providing no independent accuracy evidence. Keep all three outcomes explicit.

## Proposed Data and Interface Design

The [schema proposal](M16B_LECF_SCHEMA_PROPOSAL.md) defines six logical records: Literature Metadata, Evidence Mapping, Engineering Parameter Extraction, Case Reconstruction, Validation Status, and Gold Candidate Status. It proposes identifiers and revision bindings without modifying current schemas. The types are stage-dependent, not six mandatory records for every paper: registration or exclusion may stop at Literature Metadata, extraction adds Evidence Mapping and Parameter Extraction only when warranted, reconstruction adds LCR, validation adds one or more activity-specific LVS records, and LGC is created only for an actual nomination or disposition.

Paper/source identity links to specific assertions; assertions link to extracted parameters or observations; reconstruction maps reviewed inputs into a bounded engineering case; validation binds exact case/EPR/EER/measurement identities; candidacy records a separate human disposition. One paper may produce multiple reconstructions. Multiple papers may reuse one dataset and must not be counted as independent evidence.

The manual pilot also maintains one repository-global source/dataset-family register. It is shared infrastructure, not a seventh per-study record. Every workspace uses the register's globally qualified family IDs and declared aliases. Identity assertions remain explicit as `same`, `distinct`, or `unresolved`, with evidence, rationale, accountable lineage steward, independent reviewer and append-only merge/split/correction history. Conflicting or unresolved assertions keep the relationship and the affected validation independence `unresolved`; they block independent-accuracy and Gold-accuracy claims until independently resolved.

| Existing contract | Proposed use and compatibility boundary |
| --- | --- |
| [Evidence Object](../labos/schemas/evidence_object.schema.json) | Register a source as `literature`, initially `draft`/`source_documented` when verified. A paper's measured observation may have a separate `measurement` EVD whose method/source explicitly says literature-transcribed. The new map binds it back to the literature EVD, assertion and source version. Never infer `independently_measured` from publication or transcription review. |
| [Measurement Reference](../labos/schemas/measurement_reference.schema.json) | Preserve `MSR-###`, case binding, anonymized sample, method, conditions and uncertainty. Its parent must be measurement-compatible; a `literature` EVD cannot be its parent. Preserve reciprocal EVD/MSR links. Qualitative failure, author simulation and fitted parameters do not become measured scalar MSRs. If raw data are unavailable, identify the published locator as the available source and state that raw data were not accessed; do not mislabel a paper hash as raw-data identity. |
| [Prediction-Reality Record](../labos/schemas/prediction_reality_record.schema.json) | An eligible published measurement can be a comparison target, explicitly labelled retrospective/source-documented in `comparison_context` and the new validation record. The name “reality” grants no independent-validation status. Preserve exact quantity/unit semantics and the existing error definitions; leave `learning_disposition` as `pending_review` or `information_only` unless separately reviewed. |
| [Claim Ledger](../labos/schemas/claim_ledger.schema.yml) | Keep existing claim types/statuses. A narrow statement that a paper reports X can cite a checked locator; that does not make X a validated engineering performance claim. Support, contradiction, background, conflict and unknown relations live in Evidence Mapping, not new Claim Ledger enums. No automatic `validated`, public release, or memory promotion. |
| [EPR](../labos/schemas/engineering_problem.schema.json) | Supply explicit, reviewed authoring inputs with existing quantity/provenance envelopes. `provided` means supplied, not certified. Preserve unknowns, conflicts, assumption rationale, candidate identities, and source-case hashes. The external reconstruction binds the additional source/parameter hashes; do not extend `source_case_sha256` beyond canonical files. |
| [Evaluation Plan / EER](../labos/schemas/engineering_evaluation_result.schema.json) | Model choice, sweep/OAT settings and per-evaluation assumption acknowledgements stay in Plan. Plan and Manifest remain embedded in EER, never new standalone sidecars. EER binds the exact EPR and records actual applicability/execution. Literature review fields remain outside these immutable calculation artifacts. |
| [M16A projection](M16A_I3_EVALUATION_PLAN_EER_REPRODUCIBILITY_TASK.md#15-typed-m16a-to-legacy-prediction-projection) | Use the existing typed projection after exact EER, case, output-label, registered-unit and legacy-number representability checks. A projection supplies legacy fields; it does not create or approve PRL/EVD/MSR objects or establish data independence. |

The EPR currently requires a baseline and at least one genuine resolved variant. A single-design paper is not padded with a duplicate candidate. It can remain a reconstruction; a separately justified alternative may be authored as an explicit hypothesis with its own provenance, or broader single-candidate support may be proposed later. Neither path changes M16A here.

Strict 1D remains steady-state, one source, one series path, common area, and the frozen boundary/property assumptions. Do not assert away spreading, parallel losses, transient behavior, or temperature-dependent properties to obtain a result. Direct convection requires the common area; a measured absolute downstream resistance requires its applicable conditions. Before execution, LECF may place a manual **do not run** hold on an unsuitable or incomplete reconstruction, and an EPR may remain `HOLD_FOR_INPUT`; neither is an EER applicability outcome. Under the frozen M16A execution contract, out-of-model physics such as lateral spreading or unequal direct-convection area is `not_applicable`; a missing or unusable required in-model input or acknowledgement is `blocked`; and an invalid explicit sweep/OAT request is `invalid`. Supplying more data alone cannot make out-of-model physics applicable. A separately reviewed reduction creates a distinct reconstruction with its assumptions; it does not rewrite the study.

## Proposed Lifecycle and Transition Authority

The high-level lifecycle is **Paper -> Literature Case -> Engineering Case -> Gold Candidate -> Certified Gold Case**. Benchmark candidacy is an optional branch for a specified benchmark purpose. The tokens below are proposed LECF vocabulary only; they neither change legacy statuses nor assert that any record has reached them.

| Transition | Required record and human authority |
| --- | --- |
| Paper -> `source_registered` | Registrar binds source version, identity, access and rights; unavailable metadata remains explicit. Registration alone permits no parameter use. |
| Registration -> `literature_screened` | Domain reviewer records relevance, source integrity, evidence dimensions, search/exclusion history and permitted use: reconstruction, background, hold or exclusion. |
| Screening -> `literature_case_draft` | Extractor creates located assertions, parameters and reconstruction gaps. No numerical defaults from prose or material labels. |
| Draft -> `reviewed_literature_case` | A second person checks decision-relevant extraction against the actual source, including unit, sample, uncertainty and adverse evidence. Disagreements remain visible until resolved; review establishes source fidelity only. |
| Reviewed literature -> `engineering_case` | Engineering owner accepts a stated question, reconstruction scope, known gaps and validation plan through normal case/PR review. Unresolved inputs may block evaluation without erasing the case. |
| Engineering case -> `benchmark_candidate` | Independent benchmark reviewer accepts intended test scope, frozen input/output separation, criteria, controls and exposure/data-lineage declarations. A retrospective regression candidate may qualify for that limited use while remaining ineligible for independent accuracy claims. |
| Engineering case -> `gold_candidate` | Independent reviewer confirms reconstruction and a predeclared independent-validation protocol, data availability plan and eligibility for a specified certification scope. Same-data fitting or unknown lineage blocks this transition for accuracy validation. Pending independent measurements remain pending. Benchmark candidacy alone does not promote a case. |
| Gold Candidate -> `certified_gold` | A separately designated certification authority accepts completed independent validation and adverse findings under a previously approved, versioned certification policy. Certificate binds exact revisions, use, conditions, limitations and re-review triggers. Until that policy and authority exist, certification is blocked. |

Review roles may be held by one team, but the extractor cannot independently check their own reconstruction. Benchmark outcome custodians and blind executors need separate information access. Certification review must be independent of case preparation and calibration; conflicts of interest and involvement with the original study must be declared. AI tools may draft fields but cannot occupy these accountable roles.

An **Engineering Case** denotes a structured question and reconstruction, not a validated design. A **Gold Candidate** denotes eligibility to pursue the declared validation, not a certification. A later certificate must distinguish regression suitability from independent physical accuracy and customer-specific validation; none substitutes for customer release approval.

### Rejection, suspension and correction

Rejected/excluded records retain reasons and useful negative evidence. Unavailable supplementary data are a gap, not contradictory results. `suspended` blocks new use and advancement pending investigation; `withdrawn` records a human decision to stop use; `superseded` points to a reviewed replacement revision. Re-entry requires new evidence and a recorded review, never deletion of the adverse history.

A reported correction, retraction, disputed sample identity, extraction error or rights change starts an impact review. Record the notice and affected assertions first; suspend affected downstream use conservatively while the owner checks dependency scope. Retractions exclude the affected findings from new engineering support; unaffected material requires explicit justification and review. Preserve the old snapshot and decision basis, append the impact event, and create new reconstructions/EPRs/EERs only where needed. A frozen LCR never receives post-outcome edits or bindings. A corrected reconstruction requires a new LCR revision, a new pre-execution freeze and a new evaluation; it cannot be attached retroactively to an earlier EER. No historical or frozen file is overwritten.

## Workflow and Prevention of Circular Validation

1. **Define acquisition scope.** Record question, candidate routes including non-diamond alternatives, databases/catalogues, queries, date, inclusion/exclusion reasons and inaccessible sources. Register versions and related reports before extracting outcomes. Retain failed, null, contradictory and boundary results.
2. **Extract and independently check.** Capture original lexical quantities and locators, methods, sample groups and uncertainty; distinguish directly measured, fitted, simulated and inferred values. Review missing/conflicting fields individually. Human-check optional AI/OCR drafts against source content.
3. **Reconstruct before evaluating.** Bind geometry, material conditions, thermal and mechanical boundaries, process sequence, observables and comparator conditions. Keep original observations separate from reconstructed assumptions and counterfactual variants. For every non-missing literature-derived or reconstruction-derived EPR envelope, record an inverse map from the exact candidate/global EPR path to reviewed direct, converted, derived, fitted or assumed provenance and all dependency parameters/source assets. Freeze the intended selected-candidate/global input-path inventory; a single-reference EPR provenance envelope remains unchanged while LCR carries the complete external dependency map.
4. **Create the one authoritative pre-execution freeze.** For each computational validation activity, an immutable pre-execution LVS revision contains the **LECF validation-freeze manifest**. It binds exact LIT/LEM/LPE/LCR revisions and identities; source-asset versions and byte identities; EPR `compiled_content_sha256` and exact file SHA-256; the complete canonical Evaluation Plan snapshot and its `evaluation_plan_sha256`; either the intended Model Manifest identity or a deterministic predeclared selection rule; the intended selected-candidate/global input-path inventory; target sample/dataset partitions and roles; and executor, custodian, prior-exposure, visibility and reveal information. It also records targets, metrics, fitting/model-selection history, uncertainty treatment, controls, exclusions and invalid-run rules. Numerical tolerances require a case-specific evidence basis and independent review; this proposal supplies none.
5. **Check before reveal, then execute.** Before any executor receives outcomes, an independent reviewer resolves every frozen reference, checks source/file identities, reconstructs the EPR identities, reconstructs the complete Plan through the existing M16A canonical identity implementation, recomputes its hash, and checks the manifest identity or deterministic selection result, target partitions, input roles and exposure declarations. The review event binds the exact immutable LVS revision and must pass before execution/reveal. The Plan snapshot is LECF registration evidence inside the LVS freeze, not a third primary M16A Plan sidecar and not an `engineering/plans` artifact. The existing kernel then executes only a valid bound Plan. The eventual EER's embedded Plan must equal the frozen snapshot canonically and by hash, and its embedded Model Manifest must match the frozen identity or the result of the frozen deterministic selection rule; a mismatch is not a predeclared run. EER records all planned, failed and non-evaluable scenarios.
6. **Bind outcomes without changing the reconstruction.** A later LVS revision references the unchanged frozen LCR revision and exact validation-freeze identity, then binds the actual EER file/content identities, embedded Plan and Manifest hashes, `evaluation_input_sha256`, outputs, applicability findings and actual `consumed_input_paths`. Compare those paths against the frozen inventory and inverse mappings. Any consumed path without a reviewed mapping invalidates the claimed complete source-to-output trace. Project only eligible prediction outputs. Compare with eligible evidence and record residuals and possible parameter/model/boundary/measurement causes without attributing cause from residual alone. The independent reviewer checks scope, lineage, exposure and all adverse findings before considering candidacy. Rule/model/reconstruction changes require a new LCR revision, new freeze and new evaluation.

Data lineage uses the repository-global family register, experiment/dataset families, sample groups and reused-data relations across papers, not DOI uniqueness. Each dataset records roles such as input, calibration, model selection, validation target or control. A lineage steward proposes family aliases and `same`/`distinct`/`unresolved` assertions; a person independent of the affected extraction/reconstruction reviews every merge or split. Conflicting assertions are preserved and append-only corrections supersede rather than delete earlier decisions. If a target influenced TBR fitting, property choice, boundary selection, model choice, thresholds or sensitivity settings, its comparison is reconstruction/calibration evidence and cannot also count as independent validation. An unknown, conflicting or unresolved relationship keeps independence `unresolved`. Merely splitting figures, citations, samples or files does not prove independence; shared fits, apparatus/systematic errors and investigator exposure need assessment.

Separate extraction verification, analytic/software verification, published-result reproduction and independent empirical validation in the validation record. Two people rereading one paper can establish extraction agreement, not a second experiment. A fresh calculation after reading outcomes is retrospective; do not call it blind. For a claimed blind benchmark, use independently controlled input delivery, an exposure receipt, predeclared negative/boundary controls, immutable baseline identities and post-reveal audit under a separately approved protocol informed by [M15B controls](benchmarks/M15B_PRE_REGISTRATION_PROTOCOL.md). LECF creates no new M15B results and does not reuse its historical certification authority.

## Smallest Useful Manual Pilot

Status: proposed; execution requires a separate reviewed task with named human registrar, extractor, independent source checker, reconstruction owner, lineage steward, validation reviewer and rights owner, plus separate outcome custodian/executor where blindness is claimed. Source access and storage/use/redistribution rights must be checked before source selection. Target **8–12 screened studies and 2–3 deeper reconstructions** as a workload estimate only. Stop below that target if access, rights or reconstruction evidence is inadequate; do not relax criteria to reach a quota.

The manual pilot uses Markdown working records. The validation-freeze manifest binds each dependency's exact Git commit/path/blob identity and exact file SHA-256; the later reviewer attestation names the authoritative LVS revision's own exact Git/file identity so the manifest does not recursively self-hash. These records do not pretend to possess the future canonical JSON `record_content_sha256`. Required facts not yet knowable at registration or before execution remain explicitly pending with reason, responsible owner and resolution gate. Pending fields cannot be treated as reviewed, frozen or satisfied, and freeze-required fields must be resolved before execution.

| Coverage target | Purpose |
| --- | --- |
| GaN-on-Diamond integration and diamond heat-spreader studies | Distinguish integration/process context from package-level heat flow and physical observables. |
| Conventional package/copper or other non-diamond route | Exercise neutral route comparison and common-basis limitations. |
| Interface-resistance study | Track direct observation versus inverse-fit parameter and uncertainty. |
| Active cooling or multidimensional study | Exercise strict-1D exclusion and useful validation planning without a forced scalar result. |
| Conflicting findings, incomplete methods and an excluded source | Preserve disagreement, unresolved fields and a reasoned exclusion. These categories may overlap routes. |

Select sources only during the authorized pilot and check their actual contents; no named real study is assigned an outcome here. Source strength varies deliberately: verified primary measurement, model/fitting-dependent evidence, and incomplete or inaccessible support. A registration/exclusion entry is sufficient for a source that must not be used; inaccessible sources are not silently replaced by abstracts.

Required review outputs are a search/screening register, the repository-global source/dataset-family register, assertion/parameter sheets with independent check differences, reconstruction and gap sheets, an authoritative pre-execution LVS/LECF validation-freeze manifest with controls, and a pilot assessment. For a genuinely compatible case, use unchanged EPR/Plan/EER/projection contracts; otherwise produce a specific incompatibility report. Include a draft prior-art brief, neutral comparison, failure/negative-evidence retrieval example, validation plan and internal customer-memo draft. Every statement in that memo must map to a source or be explicitly conditional; it is not released by the pilot.

Two-person checks cover every parameter consumed by a quantitative evaluation, its uncertainty/sample/conditions, targets, dataset independence, and release-relevant claims. Reviewer checks the source independently of the extractor's interpretation and records disagreements before reconciliation. Blind execution additionally requires an outcome custodian separate from the executor; two-person extraction alone does not meet that requirement.

Pilot success requires an auditable source-to-output path for every used assertion/value, reproducible eligible calculations, preserved failures/exclusions, truthful rejection of unsupported physics, no unacknowledged assumed inputs, and an explicit decision about user usefulness. Record extraction error categories, unresolved disagreements, review time, access constraints and correction effort; these observations do not establish a calibrated quality score or statistical coverage.

Pilot failure includes fabricated/defaulted inputs, unresolved decision-relevant transcription differences, lost sample/dataset identity, target leakage described as independent validation, misleading cross-paper rankings, or a need to weaken M16A to obtain results. Unusable sources must be held or excluded. If all sources are unsuitable for quantitative reconstruction, report that outcome and narrow the capability to evidence retrieval and validation planning; the quantitative pilot has not succeeded. No Gold certification is a pilot acceptance criterion.

The repository owner and an independent domain reviewer then choose: continue a bounded manual workflow, revise the contract and repeat a focused check, narrow scope, or stop. Automated PDF extraction needs reviewed manual reference records, a representative error taxonomy, measured review burden and an explicit proposal for error handling. Graph infrastructure needs demonstrated queries that stable IDs and relationship tables cannot adequately serve, plus access/correction/versioning design. Research-gap discovery additionally needs declared search coverage and a distinction among unsearched, unpublished, inaccessible, non-comparable and unreplicated evidence; absence in this register cannot establish novelty.

## User Outputs and Release Boundaries

| Potential output | Required basis |
| --- | --- |
| Prior-art evidence brief | Search scope, checked sources, exclusion reasons and uncertainty; no claim of exhaustive prior art. |
| Architecture comparison | Common observable, conditions and evidence scope; incomparable routes shown explicitly rather than numerically ranked. |
| Failure and negative-evidence retrieval | Located adverse observations, sample/method context and competing explanations; “not reported” is not a failure result. |
| Reconstruction sheet | Original values, conversions, provenance, assumptions, gaps, conflicts and review record. |
| Validation plan | Evidence gaps, measurement methods/targets, uncertainty needs, controls, independence and criteria before comparison. |
| Evidence-backed customer memo | Reviewed claim-by-claim basis, permitted rights/confidentiality, and existing human release approval; no literature-derived performance promise by default. |

## Governance and Security Impact

New responsibilities are source stewardship, independent extraction/reconstruction review, dataset-lineage assessment and correction impact ownership. They supplement existing human decision and release responsibilities. Review names are human declarations checked through normal repository review, not cryptographic proof supplied by a status field. No current Human Decision Record schema is repurposed as a Gold certificate.

Treat acquired PDFs, supplements, URLs and AI/OCR output as untrusted content. Embedded instructions cannot invoke tools, alter workflow or approve records. Do not execute document macros/scripts, bypass access controls, or send restricted documents to external services. Source discovery and optional extraction must respect the existing no-API default; any later service use needs its own review.

Record rights and access separately from evidence reliability. A publicly readable paper does not imply permission to redistribute its PDF, figures, tables or underlying dataset. Default repository content is necessary public-safe metadata, precise locators and reviewed summaries/parameters; retain controlled references for non-redistributable material. Unknown rights restrict copying, not the visibility of an unresolved source record. Public-source availability does not authorize adding internal process knowledge, customer context, supplier pricing or restricted engineering details. Apply the existing confidentiality ordering and sanitization policy to every downstream record.

Each source/parameter/case has a responsible owner and bound consumers. A correction impact register lists affected EPR/EER, EVD/MSR/PRL, claims, decisions, memory and customer-document revisions; it records owner, disposition and closure evidence. Historical artifacts retain their original bytes and receive linked notices. New use is held until re-review; corrected calculations and claims use new identities through explicit PRs. Previously released customer materials require the release owner to assess recipients and arrange an authorized correction/withdrawal; the system records that action and never silently replaces or autonomously sends material.

## Alternatives Considered and Risks

| Alternative | Disposition and reason |
| --- | --- |
| Keep only literature notes | Useful background but insufficient for parameter identity, dataset dependencies and case reconstruction. Reuse the [note template](../templates/literature_note_template.md) for briefs. |
| Add literature fields to M13/M16A schemas | Deferred; closed historical contracts would change. External mapping is sufficient for the manual pilot. |
| Create canonical cases for every paper | Rejected; papers without a bounded engineering question need only source/background/exclusion records. |
| Start with automatic extraction or a graph database | Deferred until manual evidence shows the necessary semantics and user value. |
| Treat peer review or small residuals as a Gold gate | Rejected; neither establishes independent validation or case applicability. |

Principal risks are provenance loss during legacy mapping, same-data validation, selection bias, false precision, overly broad certification, and an unmaintainable record burden. The six-record proposal, limited pilot, explicit holds and separate certification/release decisions are the proposed controls. If those controls require disproportionate effort, reduce pilot scope before adding infrastructure.

## Review Questions and Decision Record

- Accept M16B LECF as the preparatory stage, with independent quantitative validation retained downstream, or allocate a different milestone during review?
- Approve the six logical records and external mapping approach for a manual pilot, including the current single-design-paper limitation?
- Who owns source updates, independent review and later certification policy? What intended Gold use should be considered first?
- Complete the separate M16A freeze/summary closeout before a quantitative pilot claims a formally frozen M16A release. Its absence does not authorize changing current contracts.

Decision: Pending. Reviewer/date: not assigned. All capabilities, lifecycle tokens and file placements introduced here remain proposed. Architecture approval, pilot authorization, schema/runtime implementation, certification policy and customer release are separate decisions.

## Review and Confidentiality Checklist

- [ ] Repository authority and attachment discrepancies are recorded; no frozen contract is changed.
- [ ] Publication, relevance, reconstruction, reliability, applicability, validation and release are distinct.
- [ ] All six interfaces preserve units, source/sample/dataset identity, uncertainty and adverse evidence.
- [ ] Fit/select/validate dependencies and exposure controls prevent circular-validation claims.
- [ ] Named human transitions and correction/withdrawal paths are reviewable; no automatic approval exists.
- [ ] Pilot can succeed at identifying limits and can explicitly fail quantitative reconstruction.
- [ ] No restricted process detail, customer data, supplier pricing or invented performance appears.
- [ ] Certification and automation remain blocked pending their separate evidence and review gates.

Recommended next step: independent architecture review of this amendment and schema proposal. Acceptance is a written disposition on naming, authority, compatibility, lineage and pilot scope. Implementation and pilot execution require separate authorization after review.
