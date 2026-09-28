# Draft Decision: M16B Stage 1 Public Bibliographic Metadata Search and Screening

> **DRAFT — NOT AUTHORIZED — NO HUMAN ATTESTATION.** This document is a review draft, not a signed approval. It grants no permission to begin Stage 1 or any later stage. Every `pending` field is unresolved and blocks the affected activity.

- Lab OS layer: L0 governance, limited to the proposed Stage 1 boundary of the M16B LECF workflow
- Artifact type: authorization decision draft
- Prepared date: 2026-09-28
- Current decision: **NOT AUTHORIZED**
- Pilot status: not started
- Confidentiality level: public-safe draft; no specific literature source or source content is included
- Related issue: `pending`

## 1. Fixed Basis and Evidence Status

This draft is stacked on the exact reviewed head of PR #56. It does not update, reinterpret or extend that head.

| Item | Status | Basis |
| --- | --- | --- |
| PR #56 fixed head | Verified | `336e47166c3d1f9897125464823cbba0b8f54855` |
| PR #56 base | Verified | PR #54 reviewed head `21dcb835854a5f961293b9ddaa5023d7788b392f` |
| PR #56 human review | Verified | [Shuo / `@shuo9917Dang`, review `5336867319`](https://github.com/Diamond-Thermal-Architecture-Lab/Diamond-Thermal-Lab-OS/pull/56#pullrequestreview-5336867319), submitted 2026-09-28 against the fixed head |
| PR #56 proposal disposition | Verified | **ACCEPT PROPOSAL** |
| PR #56 actual-activity disposition | Verified | **NOT AUTHORIZED** |
| Project lead | User-provided operating fact; not independently verified here | Daniel |
| Proposed independent authorization reviewer | User-provided proposal; appointment and Stage 1 independence attestation `pending` | Shuo |
| Stage 1 registrar | User-provided operating fact; acceptance and account identity `pending` | Shuo |
| Proposed authorization duration | User-provided operating fact | Six months; effective and expiry timestamps `pending` |

The PR #56 review accepted the task brief as a suitable proposal only. It expressly did not authorize pilot activity. Its independence statement concerned review of PR #56 and must not be treated as a prospective independence attestation for this draft or for Stage 1 operations.

The named people, duration and other operating facts supplied outside the repository are recorded as such. This draft does not invent supporting evidence, signatures, organizational authority or acceptance of appointment.

## 2. Decision Requested and Current Disposition

The only decision this draft is designed to support is whether to authorize a six-month Stage 1 activity limited to reproducible retrieval and screening of **public bibliographic metadata** under an approved search boundary and log plan.

Current disposition: **NOT AUTHORIZED**.

A later decision can change that disposition only if:

1. Daniel's decision authority and acceptance of the project-lead obligations are recorded;
2. the registrar appointment is accepted;
3. the reviewer/registrar independence issue in Section 5 is resolved and attested by a human;
4. every required search, access, logging, retention and timing field is resolved;
5. the decision identifies the exact Git revision reviewed; and
6. Daniel and an eligible independent authorization reviewer explicitly record an authorization outcome outside this unsigned draft.

Merge, review, comment, checkbox completion or passage of time does not by itself authorize activity.

## 3. Stage 1 Boundary: Metadata Hit Is Not Source Selection

| State | Meaning in this draft | Authority consequence |
| --- | --- | --- |
| Search query | A predeclared query submitted to an approved bibliographic search interface | May be run only after final Stage 1 authorization |
| Retrieval hit | A result returned by that query containing public bibliographic metadata | It is not an included, approved, acquired or selected source |
| Logged hit | A retrieval hit recorded for reproducibility, duplicate handling, metadata-level exclusion or later hold | Logging does not create rights to obtain, open, copy, extract or use the source |
| Metadata exclusion | A metadata-only reason that the hit is outside the approved search boundary | It is negative screening evidence, not a technical judgment on source contents |
| Hold for later source-selection review | A hit whose metadata may justify a later, separately authorized selection decision | It remains unselected and cannot cross into source-specific activity |
| Selected specific source | An affirmative inclusion/registration decision that would trigger source-specific rights, access, storage and checking duties | **Excluded from Stage 1 and prohibited by this draft** |
| Source content | Abstract text, full text, supplements, figures, tables, datasets, parameters or other substantive contents | **Excluded from Stage 1 and prohibited by this draft** |

Titles, authors, venue, publication year, document type, language, persistent identifier and the search-interface result URL are treated as candidate minimal bibliographic metadata. Abstracts and author/publisher keywords are excluded under the current default even if a search interface displays them. The exact metadata allow-list remains `pending` until the choice in Section 9 is made.

No Stage 1 label may use `selected`, `included`, `accepted source`, `registered source`, `evidence source` or equivalent wording. Permitted states are limited to `metadata_hit`, `metadata_excluded`, `hold_for_later_selection` and `unresolved_duplicate`, subject to final review.

## 4. Candidate Permitted Activities — Effective Only After Authorization

The activities below are proposed, not presently permitted.

| ID | Candidate activity | Named responsibility | Required record |
| --- | --- | --- | --- |
| A1 | Freeze approved search questions, strings, filters, date/language bounds and interface allow-list before the first query | Daniel approves scope; Shuo registers it | Versioned search-boundary entry |
| A2 | Manually submit frozen queries only to approved interfaces that expose public bibliographic metadata under reviewed access terms | Shuo performs; Daniel owns scope compliance | Query, interface, timestamp, filters and result count |
| A3 | Record only approved minimal metadata for each returned hit | Shuo | Hit ID, query ID, rank/page, allowed fields and capture timestamp |
| A4 | Apply only the four Stage 1 states defined in Section 3, with a concise metadata-level reason | Shuo; Daniel resolves scope ambiguity | State, reason and actor/date |
| A5 | Mark exact-identifier duplicates and retain unresolved identity conflicts without inferring dataset-family sameness | Shuo | Compared identifiers and `exact_duplicate` or `unresolved_duplicate` |
| A6 | Preserve zero-result queries, inaccessible results, conflicting metadata, exclusions and holds as negative or incomplete search evidence | Shuo | Outcome and reason; no source-content substitute |
| A7 | Stop the affected activity immediately when a Section 8 condition occurs and notify the project lead | Shuo stops and reports; Daniel owns disposition | Stop-event entry and follow-up status |
| A8 | Perform project-lead review of log completeness and continued scope fitness without converting hits into selected sources | Daniel | Dated review note and any narrower boundary |

No quantitative target is an acceptance threshold. The PR #56 planning estimate of 8–12 screened studies is not carried forward as a quota because Stage 1 does not select studies and standards must not be relaxed to reach a count.

## 5. Named Roles and Independence

| Role | Named person | Current status | Responsibility and limitation |
| --- | --- | --- | --- |
| Project lead | Daniel | Named by the user; acceptance and decision authority `pending` | Owns scope, resources, stop disposition and expiry; cannot replace independent authorization review |
| Stage 1 registrar | Shuo | Named by the user; acceptance and exact account identity `pending` | Runs approved metadata searches and maintains the append-only log; cannot independently audit their own operational entries |
| Independent authorization reviewer | Shuo | Proposed only; eligibility and acceptance `pending` | May authorize only if the role overlap is explicitly assessed as compatible for the exact decision; the PR #56 attestation is insufficient |
| Rights/access owner for search interfaces | `pending` | Unresolved | Confirms access terms and allowed metadata handling before an interface is used |
| Log custodian / storage administrator | `pending` | Unresolved | Implements approved storage, access, retention and expiry controls |
| Drafting support | Codex | Non-accountable | Prepared this draft; cannot accept a role, attest independence, sign, approve or authorize activity |

### Independence statement

No Stage 1 independence conclusion has been made. Shuo is both the proposed independent authorization reviewer and the named Stage 1 registrar. That overlap creates a prospective operational conflict that must be resolved before authorization; silence is not a waiver.

Choose and document one of these models:

- **I1 — recommended:** Shuo remains registrar; a different named human performs the independent authorization review and any later independent log review.
- **I2:** Shuo remains the independent authorization reviewer; a different named human becomes registrar before authorization.
- **I3:** Shuo performs a pre-start scope review and later acts as registrar, but the decision does not claim Shuo is operationally independent; a different named human gives the final authorization and reviews Stage 1 records.

For any model, the eligible independent reviewer must state authorship, operational, financial, source-ownership and decision conflicts for the exact reviewed revision. A self-check by Daniel, Shuo or Codex is not an independent review of that person's own work.

## 6. Prohibited Activities

Daniel is accountable for keeping these activities outside the decision scope. Shuo is responsible for not performing them and for recording and reporting any attempted boundary crossing. Neither person is authorized by this draft.

| ID | Prohibited activity | Named enforcement responsibility |
| --- | --- | --- |
| P1 | Selecting, approving, shortlisting or registering a specific literature source | Daniel prevents scope expansion; Shuo stops and reports |
| P2 | Resolving a DOI or result link for the purpose of opening a source landing page, obtaining source bytes or beginning source-specific review | Daniel prevents; Shuo does not proceed |
| P3 | Acquiring, downloading, uploading, copying, storing or redistributing full text, abstracts, supplements, figures, tables or datasets | Daniel prevents; Shuo does not proceed |
| P4 | Reading, quoting, summarizing, extracting, transcribing, digitizing or independently checking source content | Daniel prevents; Shuo does not proceed |
| P5 | Making source/dataset-family lineage assertions beyond exact bibliographic-identifier duplicate flags | Daniel prevents; Shuo records identity as unresolved |
| P6 | Reconstructing a study, model, geometry, boundary condition, parameter set or engineering question | Daniel prevents; Shuo does not proceed |
| P7 | Creating or modifying a case, EPR, Plan, Manifest, EER, LECF extraction/reconstruction record or validation record | Daniel prevents; Shuo does not proceed |
| P8 | Running a kernel, solver, script, calculation, comparison, simulation, validation execution or measurement | Daniel prevents; Shuo does not proceed |
| P9 | Establishing or claiming blindness, outcome independence, dataset independence or validation independence | Daniel prevents; Shuo makes no such claim |
| P10 | Creating, nominating, reviewing or certifying Gold; promoting claims or engineering memory | Daniel prevents; Shuo does not proceed |
| P11 | Producing customer-facing conclusions, performance claims, specifications or release decisions | Daniel prevents; Shuo does not proceed |
| P12 | Using paid actions, unattended automation, bulk scraping or an API not explicitly approved in the final decision | Daniel prevents; Shuo does not proceed |
| P13 | Entering restricted process, customer, supplier, pricing, partner, export-controlled or other non-public information in a query or log | Daniel prevents; Shuo stops and reports |
| P14 | Starting a pilot, creating an operational log or treating this draft/PR/merge as an approval before the final authorization record is effective | Daniel and Shuo both stop |

## 7. Search Boundary and Log Storage

The following fields remain `pending`; therefore Stage 1 remains not authorized.

| Required field | Current state | Minimum resolution |
| --- | --- | --- |
| Engineering search question | `pending` | Neutral, bounded question that does not presume diamond superiority |
| Route coverage | `pending` | Diamond and plausible non-diamond routes, or a documented narrower reason |
| Search-interface allow-list | `pending` | Exact interface names, access method, terms basis and credential rule |
| Query set and change control | `pending` | Frozen initial strings; Daniel approval and append-only rationale for changes |
| Publication date range | `pending` | Explicit inclusive dates or a documented no-lower-bound rule |
| Language scope | `pending` | Included languages and treatment of untranslated metadata |
| Document types | `pending` | Included/excluded publication types at metadata level |
| Minimal metadata allow-list | `pending` | Exact fields; default excludes abstracts and keywords |
| Duplicate rule | `pending` | Exact identifiers only; non-exact relationships remain unresolved |
| Search stopping rule | `pending` | Query/run/time or saturation rule that is not a source-selection quota |
| Operational log path | `pending` | Exact approved location; no source bytes or content |
| Log format and required columns | `pending` | Append-only, reviewable and versioned representation |
| Log access control | `pending` | Named writers/readers and public-safe review rule |
| Retention and expiry handling | `pending` | Read-only retention, deletion or archive rule after authority expires |
| Incident/stop notification channel | `pending` | Exact channel and expected response owner |

Until the storage field is resolved, no operational search log may be created. This governance draft is not the operational log.

## 8. Validity and Stop Conditions

Proposed duration: six months from an explicit `effective_at` timestamp. Both `effective_at` and `expires_at` are `pending`. The draft date, PR creation date, review date and merge date are not effective dates. Authorization does not renew automatically.

If later authorized, new Stage 1 activity must stop at the earliest of the expiry timestamp, a project-lead stop, an independent-review withdrawal or any condition below:

- the PR #56 fixed head or its human-review disposition is changed, withdrawn or superseded without impact review;
- a named role is unaccepted, unavailable, conflicted or no longer satisfies the chosen independence model;
- an access term, metadata-use right, interface allow-list entry, credential rule or log-storage control is unknown, changed, denied or expired;
- a query, filter, language, date, document type or interface falls outside the approved boundary;
- the next action would select a specific source or open, obtain, copy, store, read or extract source content;
- abstracts, keywords, full text, parameters, figures, tables, datasets or restricted information enter the log;
- a record would require fabrication, silent correction, non-exact deduplication or a stronger evidence label than metadata supports;
- the approved append-only log cannot be written, reviewed or preserved without loss of provenance;
- search volume, access burden, ambiguity or confidentiality risk becomes disproportionate to the stated Stage 1 value;
- any P1–P14 activity is requested, attempted or observed; or
- the six-month authorization expires.

On stop: cease new queries and metadata classification, preserve the approved log read-only, record the reason and time, notify Daniel through the approved channel, and do not resume without a new or amended human authorization bound to an exact revision. Stopping does not authorize investigation using source content.

## 9. Choices Required From the Owner

The recommended choices are designed to keep Stage 1 narrow. No choice is made merely by appearing in this draft.

| Topic | Options | Recommendation |
| --- | --- | --- |
| Independence model | I1, I2 or I3 from Section 5 | **I1**: Shuo as registrar; different independent reviewer |
| Interface scope | S1: exact allow-list of public/no-account bibliographic interfaces; S2: S1 plus named licensed indexes after terms review; S3: named custom set | **S1** for the first authorization |
| Metadata scope | M1: title/authors/venue/year/type/language/ID/result URL only; M2: M1 plus abstract/keywords after separate terms review; M3: custom allow-list | **M1**; M2 would require revising the current content exclusion |
| Route scope | R1: neutral diamond and non-diamond terms; R2: GaN-on-diamond only with documented bias limitation; R3: custom bounded comparison | **R1** |
| Date range | D1: no lower bound through the effective date; D2: fixed recent-year window; D3: custom dates | **D1**, with result-volume stop rule |
| Language scope | L1: English metadata only; L2: named additional languages with a qualified registrar; L3: all returned languages but untranslated items held | **L1** unless named capability supports L2 |
| Log storage | G1: version-controlled public-safe repository log; G2: approved access-controlled external log with repository hash/summary; G3: dual record with defined authority | **G1** if all fields are public-safe; otherwise **G2** |
| Post-expiry handling | E1: freeze read-only for a defined retention period; E2: archive in approved storage; E3: reviewed deletion with a tombstone record | **E1**, retention period `pending` |
| Review cadence | C1: review after every query batch; C2: weekly; C3: fixed hit-count intervals | **C1** for the first two batches, then reassess |

## 10. Preconditions for a Later Authorization Record

- [ ] Daniel's full identity, role acceptance and decision authority are recorded.
- [ ] Shuo's full identity, registrar acceptance and account identity are recorded.
- [ ] One independence model is selected and the eligible reviewer records an exact-revision conflict statement.
- [ ] Rights/access owner and log custodian are named and accept their roles.
- [ ] Every Section 7 field is resolved with evidence appropriate to the affected interface and storage system.
- [ ] `effective_at` and `expires_at` are explicit and exactly six months apart under the chosen calendar rule.
- [ ] The final record states Stage 1 only and reproduces P1–P14 without weakening them.
- [ ] Daniel and the eligible independent reviewer record explicit human dispositions for the exact Git revision.
- [ ] The final record states that review or merge does not start the activity; a separate start notice is required.

Decision field: `pending`

Operational authorization: **NOT AUTHORIZED**

Human attestations: `pending`

Pilot start: **prohibited**

## 11. Confidentiality and Claim Safety

- No specific source was selected, named, acquired or inspected for this draft.
- No source content, proprietary process detail, customer/supplier information, restricted parameter, internal measurement or performance metric is included.
- No API or paid action was used for engineering-source discovery; GitHub CLI/API use was limited to verifying PR #56 metadata/review state and preparing the draft PR workflow.
- No extraction, reconstruction, case/EPR/EER, calculation, blindness or Gold activity is authorized or represented as completed.
- Unknown facts remain `pending`; this file contains no signature image, digital signature, human attestation or apparent approval.

## 12. Required Next Human Decision

Daniel should select the Section 9 options and provide the missing Section 7 facts. An eligible independent reviewer should then review an exact revised Git head and record either **NOT AUTHORIZED** or **AUTHORIZED FOR STAGE 1 PUBLIC BIBLIOGRAPHIC METADATA SEARCH AND SCREENING ONLY**. Any broader wording requires a new scope and is outside this draft.
