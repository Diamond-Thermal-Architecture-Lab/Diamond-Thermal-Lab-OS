# Task Brief: M16B LECF Manual Pilot Authorization Proposal

- Layer: L1 Architecture, with L0 governance and L2/L3 workflow impact
- Owner: Repository owner; pilot authorization decision pending
- Status: Draft authorization proposal; **not approved for execution**
- Related issue: Not supplied
- Parent architecture: [M16B LECF framework](M16B_LITERATURE_CASE_FRAMEWORK.md) and [schema proposal](M16B_LECF_SCHEMA_PROPOSAL.md)
- Confidentiality level: Public-safe

## Objective and Engineering Question

Provide the minimum reviewable task definition that the project lead and an independent reviewer can use to decide whether to authorize a separate, manual M16B Literature-derived Engineering Case Framework (LECF) pilot.

The engineering question is whether the proposed manual controls can preserve source rights, assertion and parameter provenance, dataset-family lineage, reconstruction assumptions, model applicability, execution identity and adverse findings well enough to support useful literature-derived engineering preparation without confusing reproduction with independent validation or weakening existing M16A contracts.

Completing or merging this task brief does **not** authorize source selection, acquisition, extraction, reconstruction, case creation or execution. Execution requires the explicit authorization decision and every applicable pre-start gate below.

## Authority and Version Basis

Repository and GitHub state was rechecked on 2026-09-28 after a fresh fetch.

| Item | Verified basis |
| --- | --- |
| PR #54 state | Open draft PR; head `21dcb835854a5f961293b9ddaa5023d7788b392f` on `codex/m16b-literature-case-framework-proposal` |
| PR #54 base | `92dce3bec03384beed8d40292e258f6b9efd461b`; this is the PR base, not the prior reviewed head |
| Prior head | `67327516860d19932e2291e81b2eef9c1e2014fd`; this is the comparison base for the final architecture review, not the PR base |
| Reviewed head | `21dcb835854a5f961293b9ddaa5023d7788b392f`; this task brief is based only on that snapshot |
| Human architecture disposition | [Shuo / @shuo9917Dang review](https://github.com/Diamond-Thermal-Architecture-Lab/Diamond-Thermal-Lab-OS/pull/54#pullrequestreview-5336367811), submitted for the reviewed head |

That disposition accepts the specified snapshot as a **proposed architecture document**, closes the architecture questions on the pre-execution LVS freeze and per-scenario `consumed_input_paths` plus `input_overrides` checks, and records no new blocker in the reviewed difference. It expressly does not authorize a pilot, executable schema/runtime work, M16A formal freeze closeout, Gold certification, customer release, merge or later unreviewed SHAs.

If PR #54 moves from the reviewed head, or if the disposition is withdrawn or superseded, work under this proposal must stop until the change is reported and the authorization basis is re-reviewed. Movement of `origin/main` alone does not change the pinned PR base or reviewed head, but any intended rebase or adoption of later main changes requires a new scope and impact review.

## Scope

### In Scope Only After Separate Authorization

- Manually screen an estimated **8–12 studies** and, only where evidence and applicability justify it, attempt **2–3 deeper reconstructions** across diamond and non-diamond routes, including conflicting, incomplete and excluded material.
- Maintain only the stage-appropriate proposed LECF records and review evidence needed for the selected source or activity.
- Test whether the manual gates, role separation and review burden produce useful, auditable decisions and explicit exclusions.
- For a genuinely compatible quantitative reconstruction, use the unchanged M16A EPR, embedded Plan/Manifest, EER and projection contracts only after the execution gates in this brief pass.
- End with a human assessment of usefulness, burden, unresolved risks and the appropriate next scope; a finding that quantitative reconstruction is not supportable is an acceptable result.

The workload figures are planning estimates, not quotas, statistical-coverage claims or acceptance thresholds. Source, rights, evidence, independence and model-applicability standards must not be relaxed to reach them.

### Out of Scope for This Authorization Proposal

- Selecting or naming real papers, acquiring or downloading restricted full text, copying figures/tables, digitizing plots, entering real parameters, or opening source workspaces.
- Creating cases, EPRs, EERs, validation executions, Gold records or customer deliverables.
- Running the M16A kernel or any other solver.
- Creating executable LECF schemas, writers, validators, automation, API workflows or paid actions.
- Changing M16A contracts, strict-1D semantics, canonical case files, frozen history, prior benchmark dispositions or historical results.
- Gold nomination/certification, automatic customer publication, claim-ledger promotion, memory promotion, calibration claims or unapproved performance statements.
- Treating this document, its review, its merge or PR #54's architecture disposition as pilot execution authority.

## Inputs and Protected Boundaries

The controlling inputs are [AGENTS.md](../AGENTS.md), [LAB_OS.md](../LAB_OS.md), [ROADMAP.md](../ROADMAP.md), the reviewed [M16B task brief](M16B_LECF_TASK_BRIEF.md), framework and schema proposal at the exact head above, and the existing M16A contracts they cite.

The pilot must preserve:

- PR #54's reviewed files and branch; this work neither edits nor rebases them.
- M16A EPR, Plan, Manifest, EER, quantity/unit, projection, comparator and strict-1D meanings.
- M15B and other frozen artifacts, numbered cases, evidence/measurement/PRL records, schemas, runtime, tests, exports and historical review records.
- The distinction between verified fact, source report, reconstruction assumption, hypothesis, validation result and release decision.

## Human Roles and Independence

Every accountable role must be held by a named human before the gate shown below. `pending` is not a role assignment and grants no authority. AI may draft or check clerical consistency but cannot hold an accountable role, attest independence, approve a gate or accept risk.

| Role | Named human | Minimum responsibility and independence | Must be resolved by |
| --- | --- | --- | --- |
| Project lead / authorization owner | `pending` | Approves exact pilot scope, resources, stop authority and permitted execution; cannot substitute author self-check for independent review | Authorization decision |
| Registrar | `pending` | Registers exact source/version/access identity and screening history | Before any specific source is selected or acquired |
| Extractor | `pending` | Produces located assertions and parameter records; declares prior exposure and conflicts | Before extraction |
| Independent source checker | `pending` | Checks the actual source independently of the extractor's interpretation and records differences before reconciliation; cannot check their own extraction/reconstruction | Before any extraction is accepted or consumed |
| Reconstruction owner | `pending` | Owns bounded engineering question, mappings, assumptions, gaps and applicability submission | Before reconstruction starts |
| Lineage steward | `pending` | Proposes source/dataset-family identity assertions and impact updates; merge/split decisions require a human reviewer independent of the affected extraction/reconstruction | Before a family assertion is relied upon |
| Validation reviewer | `pending` | Reviews validation scope, data roles, independence, freeze, exposure and adverse findings; for an independent claim, must be independent of case preparation, fitting/calibration and execution | Before freeze attestation or validation disposition |
| Rights owner | `pending` | Determines and records access, use, storage, copying, redistribution and confidentiality basis without inferring permission from public readability | Before any specific source is selected, acquired or stored |
| Outcome custodian, if blindness is claimed | `pending` | Controls outcomes and reveal evidence; must be information-separated from the executor | Before blind protocol approval |
| Executor, if blindness is claimed | `pending` | Receives only the authorized frozen inputs and records exposure receipt; must not act as outcome custodian | Before blind protocol approval |

One human may hold compatible roles only when the independence requirement for the affected record or claim is still met and the overlap is disclosed. If blind separation cannot be established, classify the activity as retrospective/non-blind and do not imply blindness.

## Rights, Access, Storage and Confidentiality Gate

Before selecting, obtaining, opening in a work environment, copying or storing a specific source, the rights owner and registrar must record the items below. No permission is inferred from a DOI, abstract, public URL, institutional access or publication status.

| Required decision | Initial state | Accountable owner | Resolution gate |
| --- | --- | --- | --- |
| Lawful access basis and authorized persons | `pending` | Rights owner | Before source selection/acquisition |
| Allowed research/engineering use, including extraction or digitization | `pending` | Rights owner | Before acquisition or use |
| Approved storage location, retention, access control and deletion/expiry handling | `pending` | Rights owner | Before any bytes are stored |
| Permission to copy or redistribute full text, supplements, figures, tables and datasets | `pending` | Rights owner | Before any copy or repository inclusion |
| Permission for quotations, derived parameters and internal/public summaries | `pending` | Rights owner | Before extraction or publication of a summary |
| Confidentiality, partner, customer, export-control or other handling restrictions | `pending` | Rights owner and project lead | Before source selection/acquisition |
| Repository-safe representation and controlled-reference method | `pending` | Rights owner and registrar | Before registration commit |

An unknown item remains `pending` with reason, responsible human and evidence needed. It blocks the affected action; it must not be converted to an assumed permission. The default repository content is public-safe metadata, exact locators and reviewed summaries/parameters only. Non-redistributable bytes stay in an approved controlled location and are represented here by permitted, non-sensitive identities or references. A rights change triggers an impact review and hold on new use.

## Staged Records, Gates and Deliverables

The proposed six record types are stage-dependent, not a six-record packet required for every paper. An excluded or inaccessible source may stop after Literature Metadata and screening; mapping/extraction exists only when attempted, LCR only for reconstruction, LVS only for a validation activity, and LGC only for a separately authorized nomination or disposition. This pilot does not authorize LGC creation.

| Stage | Required record or output | Checkable gate and failure disposition |
| --- | --- | --- |
| 0. Authorization readiness | This task brief, named roles, rights plan, approved storage, scope and stop authority | Project lead and independent reviewer must record explicit authorization for a fixed revision; otherwise do not start |
| 1. Search and screening | Reproducible search/screening and exclusion log with query/source, date, inclusion basis, exclusion/hold reason and reviewer | Preserve negative, inaccessible, conflicting and excluded results; do not replace unavailable full text with abstract-derived parameters |
| 2. Registration and lineage | Literature Metadata plus one repository-global source/dataset-family register with globally qualified IDs and append-only `same`/`distinct`/`unresolved` assertions | Rights/access gate passed; unresolved family identity stays unresolved and blocks affected independence claims |
| 3. Assertion and parameter extraction, when warranted | Located assertion and parameter sheets, uncertainty/sample/condition context, extractor/checker differences and reconciliation status | Decision-relevant differences, missing locators or unusable precision hold the affected value; no silent defaults or averages |
| 4. Reconstruction, when warranted | Reconstruction and gap record with bounded question, source facts separated from changes/assumptions, two-way EPR mapping proposal, scenario-specific intended paths and Plan-override mappings | Unmapped or unresolved non-missing inputs, sample identity loss or decision-relevant gaps block freeze/execution; no case/EPR is created by this proposal |
| 5. Applicability and validation planning | Explicit strict-1D applicability assessment; separate LVS plans for extraction check, reconstruction check, analytic/software verification, published-result reproduction and any independent empirical validation | A record type or successful reproduction must not be relabelled as a stronger validation kind |
| 6. Pre-execution freeze, only if separately authorized and applicable | One immutable authoritative pre-execution LVS revision containing the complete LECF freeze manifest and an external final reviewer attestation bound to its exact identity | Every freeze-required field and reference must be resolved and independently checked before execution; any pending/mismatch means **do not run** |
| 7. Execution and post-execution check, only if stage 6 passes | Existing EER plus later LVS assessment binding actual execution/reveal facts, identities, applicability, outputs, paths, overrides, failures and adverse findings | A freeze mismatch is not the predeclared run; trace mismatch withholds the affected complete source-to-output claim and may require a new reconstruction/freeze/evaluation cycle |
| 8. Pilot assessment | Workload, access limits, error categories, disagreements, correction effort, exclusions, usefulness and explicit continue/narrow/stop recommendation | No automatic implementation, certification, release or performance claim follows |

Expected pilot-level deliverables are the search/exclusion log, global family register, assertion/parameter check differences, reconstruction/gap records, applicability decisions, validation-plan records and final pilot assessment. An execution freeze and post-execution check are expected only for a qualifying activity that receives explicit execution authorization and passes every prior gate.

## Validation and Execution Controls

### Dataset Lineage and Same-source Use

- Record each dataset family's roles as input, fitting/calibration, model selection, validation target or control, including shared samples, fits, apparatus/systematic errors and outcome exposure.
- Evidence used to fit a parameter, select a model/boundary/threshold or tune a sensitivity setting cannot validate the same result independently. It may support a labelled reproduction or dependent check.
- A different figure, file, DOI, author or held-out row does not by itself establish independence. Unresolved or conflicting lineage remains `unresolved` and blocks independent-accuracy and Gold-accuracy claims.
- Independent empirical validation requires a separately identified dataset and reviewed independence basis for the stated use; it is not supplied by two-person extraction or software verification.

### Outcome Exposure and Blindness

- Record known prior outcome access, planned visibility, reveal sequence and actual reveal events.
- If outcomes or target values were known during reconstruction, parameter choice, model selection or execution preparation, label the activity retrospective; do not claim blindness.
- A blind claim requires named, separated custodian and executor, controlled input delivery, exposure receipt, predeclared controls and immutable baseline identities. If any control fails, suspend the blind claim and classify the activity truthfully before further use.

### Plan/Manifest Freeze and Scenario Trace Checks

For each authorized computational activity, the single authoritative pre-execution LVS revision must bind exact LIT/LEM/LPE/LCR and source-byte identities; exact EPR identity; complete canonical Plan and resolved Manifest snapshots and independently recomputed hashes; unit-registry/runtime-policy versions; target partitions/roles; exposure controls; expected `consumed_input_paths` for each selected candidate/scenario or a frozen derivation rule; and reviewed `epr_mapping` and `plan_override_mapping` dependencies. Manifest selection cannot be deferred to execution.

Before execution, the independent validation reviewer must resolve the references, recompute identities through the existing M16A implementation, check partitions, roles and per-scenario path expectations, and attest the exact frozen LVS identity outside the immutable freeze. A missing, pending or mismatched item blocks execution.

After execution, the post-execution LVS must:

- verify that embedded Plan/Manifest, hashes, registry/policy versions and EER identities equal the freeze;
- compare actual `consumed_input_paths` to the frozen expectation for each candidate/scenario, not only to a union of paths;
- compare every requested sweep/OAT scenario's `input_overrides` item by item with its frozen Plan point and reviewed mapping, including candidate/scenario identity, source kind/ID, field path, point ordinal, OAT side where applicable, canonical value, quantity kind and unit;
- confirm unswept core baselines and OAT references have empty `input_overrides`;
- record missing, extra, mismatched, ambiguous or unmapped values as findings for the affected scenario and withhold its complete source-to-numerical-result traceability claim until resolved; and
- retain `blocked`, `invalid` and `not_applicable` paths/findings without claiming a numerical output path.

Record agreement does not by itself prove the kernel used replacement values arithmetically; that remains governed by the unchanged M16A contract and analytic tests.

### Strict-1D Applicability

Do not force a scalar result by asserting away material lateral spreading, parallel heat loss, unequal direct-convection area, transient behavior or temperature-dependent properties. Place a manual **do not run** hold before execution when the reconstruction is unsuitable or incomplete. Under the existing contract:

- out-of-model physics attempted under strict 1D is `not_applicable`;
- missing or unusable required in-model input/acknowledgement is `blocked`; and
- an invalid explicit sweep/OAT request is `invalid`.

More data alone cannot make inapplicable physics applicable. Any reviewed reduction is a new, explicit reconstruction and cannot rewrite the study or frozen history.

## Validation Categories and Claim Boundaries

Keep separate LVS activities and conclusions for:

1. extraction/source-fidelity checking;
2. reconstruction checking;
3. analytic or software/parser verification;
4. reproduction of a published result; and
5. independent empirical validation.

A source-fidelity check does not validate the physics; software verification does not reproduce a paper; reproduction using the same dataset is dependent evidence; and none substitutes for an independent measurement. The pilot must not produce `gold_candidate` or `certified_gold` status, automatic customer release, an approved specification, or a performance promise. Any external or customer-facing statement requires its existing separate rights, confidentiality, claim and human release review.

## Execution Authorization Decision Checklist

The project lead and an independent reviewer must answer every item for the exact reviewed revision. Unchecked or `pending` means no execution authority.

- [ ] The authorization decision names its human project lead and independent reviewer, exact Git SHA/path scope, date, permitted activities and expiry/re-review triggers.
- [ ] All accountable roles are filled by named humans and incompatible role overlaps are excluded or disclosed.
- [ ] The rights/access/storage/confidentiality plan is approved before any specific source selection or acquisition.
- [ ] The approved storage boundary and repository-safe reference method are operational.
- [ ] Workload targets are accepted as estimates and stop authority overrides quantity targets.
- [ ] Search scope, route diversity, exclusions and negative-evidence retention are reviewable.
- [ ] The global family-register authority, independent merge/split review and correction-impact ownership are accepted.
- [ ] Same-data fitting/model-selection/validation rules and exposure classification are accepted.
- [ ] Any permitted quantitative execution is stated explicitly; absent such wording, the pilot is documentation/reconstruction-only.
- [ ] Pre-execution freeze, reviewer attestation and per-scenario path/override gates are accepted without changes to M16A.
- [ ] Strict-1D do-not-run, `not_applicable`, `blocked` and `invalid` distinctions are accepted.
- [ ] Gold, certification, customer release, schema/runtime implementation and performance claims remain outside authorization.
- [ ] M16A formal freeze closeout and any other dependency are assigned separately rather than implied complete.
- [ ] Immediate and phase-end stop conditions, incident reporting and correction/withdrawal ownership are accepted.

Decision: `pending`. A valid decision must be an explicit human disposition; document approval alone is insufficient unless it states that execution is authorized and resolves this checklist.

## Acceptance and Stop Criteria

### Acceptance Criteria for an Authorized Pilot

- [ ] Every used assertion/value has an auditable source/version/location-to-record path, with unresolved items held rather than defaulted.
- [ ] Every decision-relevant extracted parameter has an independent source check with differences preserved and reconciled or left blocking.
- [ ] Source/dataset identity and fit/select/target/control roles remain traceable through the global register.
- [ ] Reconstruction facts, transformations, assumptions, gaps and model-applicability decisions remain distinct.
- [ ] Any eligible calculation is reproducible under the unchanged M16A identities and has passed the exact freeze and scenario trace checks.
- [ ] Failures, exclusions, inaccessible sources, adverse evidence and non-applicability are preserved.
- [ ] Validation categories and independence claims are accurate; no Gold, release or performance claim is implied.
- [ ] The final assessment records usefulness, review effort, access constraints, correction burden, unresolved risks and a human continue/narrow/stop decision.

Success does not require reaching the workload estimate, producing a quantitative result, nominating Gold or showing favorable diamond performance. A well-supported decision that the material is unsuitable, inaccessible or outside strict 1D can satisfy the pilot's learning purpose.

### Immediate Stop Conditions

Stop affected work and notify the project lead and independent reviewer if any of the following occurs:

- the pinned PR #54 architecture head or governing disposition changes without re-review;
- required access, use, storage, redistribution or confidentiality rights are unknown, denied, expired or contradicted;
- no qualified named human can fill a required accountable or independent role;
- restricted process, customer, supplier, partner, export-controlled or other non-public information would be exposed;
- source bytes, versions, samples or dataset families cannot be identified sufficiently for the intended use;
- decision-relevant transcription differences remain unresolved, inputs would need fabrication/defaulting, or evidence would need to be relabelled to proceed;
- dataset leakage or outcome exposure makes a planned independence/blindness claim false;
- strict-1D applicability would require weakening or changing M16A, or a freeze/identity/path/override gate fails;
- a correction, retraction, rights change or adverse finding invalidates an active dependency; or
- safe review burden becomes disproportionate to expected learning value.

At each stage boundary, the project lead may stop or narrow scope. If all screened sources are unsuitable for quantitative reconstruction, close with an evidence-retrieval/validation-planning assessment; do not lower standards or claim quantitative-pilot success.

## Dependencies and Open Decisions

- **M16A formal freeze/governance closeout remains separate.** This proposal does not establish it or authorize changing current contracts. Complete it before claiming a formally frozen M16A release for a quantitative pilot.
- Project lead, independent authorization reviewer and all operational human role names remain `pending`.
- Source classes, search bounds, storage system, access credentials, retention policy, rights evidence and budget/time allocation remain `pending`; no real source is selected here.
- Whether the first authorization permits quantitative execution or stops at screening/reconstruction must be stated explicitly.
- Blind versus retrospective scope remains `pending`; no blind claim exists without the required roles and controls.
- Certification policy, Gold authority, independent measurement program, customer release and executable schema/runtime work require separate tasks and authorization.

## Risks and Open Questions

- Rights uncertainty may make an apparently relevant source unusable or non-redistributable.
- Dataset reuse and shared systematic errors may prevent independent-validation claims even when citations differ.
- Manual review effort may outweigh useful engineering learning; the response is to narrow or stop, not automate prematurely.
- Strict-1D may reject many published structures; those exclusions are evidence about scope, not reasons to weaken the model.
- Later source corrections or rights changes require append-only impact review, new-use holds and new revisions without overwriting historical artifacts.

## Confidentiality and Claim Safety Check

- [x] No proprietary growth, bonding, substrate-preparation or other MPCVD process know-how is included.
- [x] No restricted process parameters, chamber design, customer/supplier/pricing/contract detail or confidential project data is included.
- [x] No real source, parameter, measurement, validation result or performance metric is selected or invented.
- [x] No pilot, execution, Gold, release, merge or certification authority is claimed.
- [x] Unknown future rights, roles and operational facts are marked `pending` with an owner and gate rather than fabricated.

## Review Record

Recommended labels: `layer:L1-architecture`, `type:task-brief`, `domain:thermal`, `domain:measurement`, `status:ready-for-review`, `priority:P1`.

Required next decision: the repository owner should obtain an independent review of this exact task-brief revision, resolve the authorization checklist and either record **not authorized**, **authorized for screening/reconstruction only**, or **authorized for the stated gated pilot including explicitly permitted execution**. No pilot activity begins before that decision.
