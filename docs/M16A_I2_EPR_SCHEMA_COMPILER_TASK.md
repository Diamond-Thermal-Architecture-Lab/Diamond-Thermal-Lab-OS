# Task Brief: M16A-I2 Engineering Problem Representation Schema and Model-Independent Compiler

## Document Control

- Layer: L1 implementation contract / L4 schema and compiler specification
- Status: Ready for implementation gate review
- Objective: M16A-I2 — Engineering Problem Representation Schema and Model-Independent Compiler Contract
- Implementation starting commit: `24540dd22fa552f26a98e2d85427a43cd352195a`
- Starting tree: `45c79d38f13e22229471eae1e6c2932d58683ead`
- Architecture: `docs/M16A_ENGINEERING_PROBLEM_COMPILER.md`
- Architecture disposition: `FINAL M16A ARCHITECTURE REVIEW: APPROVE`
- I1 basis: merged quantity registry `m16a-unit-registry-1.0` and serializer `m16a-canonical-json-1.0`
- Confidentiality: Public-safe; synthetic fixtures only
- Deliverable for this preparation task: this task brief only

The starting commit is an implementation starting state after merged M16A-I1. It is not an M15B baseline and creates no historical authority.

## 1. Objective and Authority Boundary

Implement one versioned, provenance-bearing, unit-normalized, deterministic, immutable, and content-addressed Engineering Problem Representation (EPR) from explicit case and engineering inputs.

The authority split is exact:

| Contract | Question answered |
| --- | --- |
| EPR | What is the engineering problem? |
| Evaluation Plan | How will the immutable problem be evaluated? |
| EER | What happened during evaluation? |

I2 owns only the EPR, its schema/runtime identity, model-independent compilation, complete candidate resolution, and an optional safe persistence edge. I2 evaluates no thermal model.

The EPR must not persist selected/requested model, model version, model applicability, evaluation objective, sweep, sensitivity request, evaluation-instance assumption acknowledgement, solver result/status, or candidate rank. Those fields would change evaluation authority without changing the problem and therefore belong later.

## 2. Repository Findings and Reuse Decisions

| Area inspected | Repository finding | I2 decision |
| --- | --- | --- |
| Schema contracts | JSON sidecars use Draft 2020-12, stable `$id`, required fields, nested `additionalProperties: false`, exact versions, enums, and conditional rules. Runtime validation is feature-local and standard-library-only. | Use the same JSON Schema dialect and closed-object posture; mirror cross-field rules in `problem.py` without adding a schema dependency. |
| I1 quantities | `QuantifiedValue` is immutable and reconstructs its exact canonical value/unit/conversion record; all external values are decimal strings. | Wrap, do not reimplement, `QuantifiedValue`; use all 11 existing quantity kinds and no new units. |
| I1 serialization | `canonical_json_bytes` is compact UTF-8, sorted-key, LF-terminated and filters nothing. | Artifact owners construct explicit identity projections and call `canonical_sha256`. |
| Evidence Objects | `EVD-###`, exact `1.0`, evidence status/level, source reference/hash, measurement links, confidentiality, and human review are existing authority. | Reference and validate EVD sidecars; do not copy their evidence system or promote their status. |
| Measurement References | `MSR-###` links one EVD, has planned/completed/reviewed/rejected status, controlled raw-data reference/hash, and qualitative/numeric uncertainty. | Pin the referenced MSR sidecar by exact-byte hash and validate its EVD linkage; do not migrate legacy numeric storage. |
| Confidentiality | Vocabulary is `public`, `internal`, `customer-confidential`, `restricted`; absolute paths and credential-like strings are unsafe. | Reuse the vocabulary and reference checks; store only sanitized summaries/opaque references. |
| Canonical case IDs | Case generator uses `^[a-z0-9_-]+$`, rejects path separators, traversal, and absolute paths; `00_problem_intake.yml` binds the folder ID. | Reuse exact shape and require folder, intake `case_id`, and EPR `case_id` equality. |
| Canonical files | The authoritative set is the 12 root-level files `00_...` through `11_...` in `REQUIRED_CASE_FILES`; sidecars are outside that set. | Only those names are eligible sources; record only eligible files actually read. |
| Source hashes | Review packages use filename-to-lowercase-SHA256 maps over exact bytes; canonical proposals compare maps for staleness. | Preserve map and exact-byte conventions, but do not reuse the all-numbered-files collector unchanged. |
| Safe paths | Evidence writers constrain a JSON file to one case-local sidecar directory; benchmark code rejects symlinks, non-regular files, absolute paths, backslashes, and dot/traversal components. | Apply both containment and non-symlink checks to reads and writes. |
| Findings | Evidence/decision validators use stable family rule IDs and structured severity/finding/evidence/action records; triage models sort deterministic outputs. | Use versioned `M16A-EPR-<FAMILY>-###` IDs and deterministic finding order. |
| Candidate artifacts | `03_architecture_genomes.yml` contains qualitative `route_id`/`pattern_id` candidates and no quantitative complete stack. | It may seed labels only; EPR uses new `CND-###` identities and explicit resolved engineering content. |
| Case CLI/reports | `scripts/labos_case.py` is the single case CLI; reports are human-readable projections and writers are atomic where overwrite risk matters. | Add no I2 CLI/report. Keep compiler pure, with one thin optional atomic writer. |

New to M16A-I2 are the EPR schema/version, complete quantity envelope, EPR provenance disposition, immutable problem runtime, exact-files-read binding, EPR/candidate identity projections, candidate materializer, model-independent findings/outcomes, and safe EPR writer.

## 3. Recommended Implementation Boundary and Delivery Split

Use two PRs because schema/identity review and transformation/rule review have different failure modes. I2A freezes the persisted contract before I2B writes compilation behavior against it.

### I2A — EPR schema, runtime representation, and identity

- Add the closed Draft 2020-12 EPR schema and all local `$defs`.
- Add immutable runtime reconstruction, cross-field persisted validation, structural provenance validation, I1 quantity adaptation, canonical ordering, candidate/EPR projections, and hashes.
- Require no case or sidecar filesystem access to reconstruct or validate a persisted EPR value.
- Use inline public-safe synthetic test data; add no case artifact.

### I2B — Model-independent compiler, resolution, and safe writer

- Always read/bind `00_problem_intake.yml`; read other explicitly selected canonical files and explicit structured engineering input.
- Resolve EVD/MSR repository reality, safe paths, exact bytes, linkage, status, and staleness.
- Resolve baseline plus overrides into independent complete candidates.
- Emit deterministic findings, unknowns, outcome, hashes, and canonical EPR bytes.
- Add the idempotent case-local writer; do not add a CLI.

### Exact future file set

| Change | File | Owner |
| --- | --- | --- |
| Add | `labos/schemas/engineering_problem.schema.json` | Persisted EPR contract and local `$defs` |
| Add | `labos/engineering/problem.py` | Immutable EPR records, validation, ordering, identity projections |
| Add | `labos/engineering/compiler.py` | Source reader, compiler, rules, candidate resolution, optional writer |
| Modify | `labos/engineering/__init__.py` | Small reviewed public exports and version constants |
| Add | `tests/test_m16a_epr_schema.py` | Schema/runtime/quantity/provenance/identity acceptance tests |
| Add | `tests/test_m16a_compiler.py` | Compiler/source/candidate/safety/outcome acceptance tests |

Do not add `provenance.py`, a quantity schema, fixtures, reports, a CLI module, dependencies, or a thermal package in I2. If the implementation cannot remain within this set, stop for scope review.

## 4. Persisted EPR Contract

Use schema `$id` `labos/engineering_problem.schema.json` and exact `problem_format_version` `m16a-engineering-problem-1.0`. A change to required fields, meanings, canonical ordering, or identity projection requires a new problem format version.

Every top-level field below is required and `additionalProperties` is false at every object boundary.

| Field | Exact I2 meaning |
| --- | --- |
| `problem_format_version` | Constant `m16a-engineering-problem-1.0`. |
| `problem_id` | Case-local `^EPR-[0-9]{3}$`; filename must equal `<problem_id>.json`. |
| `case_id` | Existing safe canonical case ID, equal to case folder and intake ID. |
| `title` | Non-empty public-safe problem label. |
| `purpose` | Non-empty statement of intended engineering use, not evaluation objective. |
| `source_case_sha256` | Non-empty exact-byte hash map that always contains `00_problem_intake.yml` and only other canonical files actually read. |
| `requirements` | Non-empty, unique, ordered `REQ-###` requirement records. |
| `heat_sources` | Non-empty, unique, ordered `HSR-###` engineering source facts. |
| `geometry` | Authoring baseline ordered stack and source-to-sink orientation. |
| `materials` | Case-local explicit material/property records; no lookup authority. |
| `interfaces` | Baseline adjacent-layer interface records with one representation each. |
| `boundary_conditions` | Baseline source-side and downstream representations. |
| `constraints` | Stable quantitative or review-only constraint records. |
| `candidates` | Resolved complete `CND-###` views with exactly one `candidate_role: baseline` and one or more `variant` roles; no persisted overrides. |
| `unknowns` | Stable machine-readable gaps and assumption/evidence states. |
| `compilation` | Versioned model-independent outcome, findings, warnings, and assumption paths. |
| `confidentiality_level` | Existing four-value Lab OS vocabulary. |
| `compiled_content_sha256` | Lowercase SHA256 of the explicit EPR identity projection. |

Canonical collection order is requirements/source/material/constraint by ID, the baseline candidate first then variants by ID, layers by integer order then ID, interfaces by upstream layer order then ID, unknowns by field path/state/ID, changed paths lexically, source-hash keys by POSIX path, and findings by rule ID/field paths/message. Duplicate IDs or non-canonical persisted order fail validation.

## 5. Quantified Value Envelope

Define `$defs.quantified_value_envelope`, `$defs.i1_conversion_record`, and non-provenance uncertainty quantity helpers inside the EPR schema. Do not create a standalone quantity schema.

Each physical field contains exactly:

- `value`: canonical SI decimal string, or `null` only for `status: missing`;
- `unit`: the canonical I1 unit for `quantity_kind`, including on a missing expected value;
- `quantity_kind`: exact I1 `QuantityKind` string;
- `provenance`: the I2 structure in Section 6;
- `uncertainty`: one closed variant in Section 7;
- `confidence`: `unknown`, `low`, `medium`, `high`, or `not_applicable`;
- `status`: `provided`, `assumed`, `missing`, `conflicting`, or `evidence_required`; and
- `conversion`: exact I1 `ConversionRecord`, or `null` only when status is `missing`.

For every non-missing envelope, adapt `value`/`unit` to I1 `canonical_value`/`canonical_unit`, reconstruct `QuantifiedValue.from_dict()`, and require exact agreement with `conversion`. This makes persisted decimal strings canonical while retaining original lexical value/unit and conversion rule/version. There is one original-to-canonical conversion record, not a mutable multi-step conversion log.

Rules are:

- A physical value supplied as JSON number, float, integer, boolean, NaN, infinity, or free-text numeric is invalid.
- `status: missing` requires `value: null`, `conversion: null`, `confidence: unknown`, and `uncertainty.kind: not_provided`.
- Every other status requires a valid I1 quantity; `conflicting` preserves a submitted value but cannot be evaluated or treated as selected truth.
- `assumed` requires non-empty provenance `reference` and `rationale`; its exact envelope path is acknowledgement-required later.
- `evidence_required` means the value is structurally usable but its evidence disposition blocks readiness; it is not an assumption.
- `not_provided` uncertainty is unknown uncertainty and emits a warning; it never means zero.
- Confidence never replaces provenance or numeric uncertainty and has no probabilistic meaning.
- Field-specific sign/range checks are compiler rules, not changes to I1 parsing.

## 6. Provenance Contract

Every envelope has one closed provenance object with `source_type`, `reference`, `evidence_object_ids`, `measurement_reference_ids`, `source_sha256`, `review_status`, and `rationale`.

Allowed source types are exactly `requirement`, `evidence_object`, `measurement_reference`, `literature`, `supplier`, `expert_judgment`, `assumption`, and `synthetic_fixture`.

`reference` is a non-empty sanitized case/repository-relative path or opaque controlled reference. `source_sha256` is lowercase SHA256 or null. It proves the bytes identified by the reference, not engineering truth, applicability, correctness, approval, or review.

To keep the first envelope unambiguous, each ID array is unique, sorted, and has at most one member:

- `evidence_object`: exactly one `EVD-###`, no MSR; reference/hash pin that EVD sidecar's exact bytes.
- `measurement_reference`: exactly one `MSR-###` and its one owning `EVD-###`; reference/hash pin the MSR sidecar's exact bytes.
- all other source types: both arrays empty; the reference identifies the requirement, publication, supplier record, judgment record, assumption basis, or fixture.

I2A validates only persisted provenance structure: source-type vocabulary; EVD/MSR ID syntax, cardinality, and allowed array combinations; SHA256 lexical shape; review-status vocabulary; rationale/status cross-field rules; and sanitized reference lexical/safety shape that needs no repository resolution. Its tests use synthetic inline objects only.

I2B validates repository reality: the referenced sidecar exists at a safe case-local/repository-safe non-symlink path; its existing EVD/MSR validator accepts it; its `case_id` matches; actual status supports the EPR disposition; MSR `evidence_id` equals the declared EVD ID; exact sidecar bytes match `source_sha256`; and neither source nor hash became stale. Measurement quantity/unit mapping uses I1 explicitly rather than copying legacy JSON numeric identity.

`review_status` is the reduced EPR disposition `unverified`, `source_documented`, `reviewed`, `rejected`, or `not_applicable`. I2A validates this vocabulary only. In I2B, it may not overstate a linked sidecar: `reviewed` requires linked status `reviewed`; `source_documented` may reflect documented but not reviewed evidence. The EPR never edits or upgrades EVD/MSR status.

`rationale` is non-empty for `status: assumed` and otherwise string or null. `source_type: assumption` requires `status: assumed`; synthetic or expert sources may also be explicitly assumed. A rejected source produces `evidence_required` or `conflicting` disposition, never silent acceptance.

## 7. Uncertainty Semantics

`uncertainty` is a `oneOf` closed object and always has non-empty `basis`:

| Kind | Required numeric fields | Validation |
| --- | --- | --- |
| `not_provided` | none | Warning; does not supply a zero bound. |
| `not_applicable` | none | Explicit claim that numeric uncertainty is inapplicable; no probability implied. |
| `absolute` | `amount` | Non-negative I1 quantity; same kind as value except absolute temperature uses temperature difference. |
| `relative` | `fraction` | Non-negative physical-dimensionless I1 quantity with unit `1`. |
| `interval` | `lower`, `upper` | Same kind/unit as value; lower <= upper and, for usable central value, lower <= value <= upper. |

Uncertainty helper quantities contain only canonical `value`, `unit`, `quantity_kind`, and I1 `conversion`; they do not recursively carry provenance/status/confidence. Interval endpoints and uncertainty amounts are descriptive bounds, not distributions, confidence intervals, or probabilistic propagation instructions.

## 8. Domain Structures

### Requirements and heat sources

A requirement contains `requirement_id`, `description`, `target_path`, optional target envelope, and provenance. Quantitative targets use the full envelope. Qualitative requirements remain text and are never converted into scores.

A heat source contains `source_id`, `source_location`, `total_power`, `heat_flux`, `footprint`, `heated_area`, `spatial_profile`, `operating_mode`, and nullable `duty_cycle` metadata. `source_location` names a layer and `source_side`/`sink_side` face for surface injection, or named layer regions for volumetric/distributed generation.

`footprint` has a declared shape, explicit dimensions, and optional descriptive profile reference; `heated_area` is always an area envelope, never silently taken from text. `spatial_profile` permits `uniform_surface`, `nonuniform_surface`, `volumetric`, `distributed`, or `other`. `operating_mode` permits `steady_state`, `transient`, `pulsed`, or `other`. Duty cycle, when present, is physical-dimensionless with unit `1` and remains metadata.

At least one of power or flux must be non-missing for readiness. Multiple sources, unequal footprints, nonuniform profiles, distributed/volumetric generation, and non-steady modes are representable facts and are not generic EPR failures.

If power, flux, and area are all usable, I2 checks `P = q'' * A` under policy `m16a-heat-source-consistency-1.0`: exact Decimal arithmetic; both zero is consistent; otherwise `abs(P-qA) / max(abs(P),abs(qA)) <= 0.001`. The policy ID is persisted in `compilation`; mismatch is a conflicting structural finding and `FAIL`. I2 does not populate an absent authoritative power/flux field from this equation.

### Geometry and materials

`geometry` contains `stack_id`, `source_to_sink_direction`, and non-empty `layers`. Each layer has unique `LYR-###`, contiguous zero-based `order`, role, `MAT-###` reference, thickness envelope, declared footprint dimensions/area, and orientation.

Orientation records stack-normal axis and an optional public-safe rotation description. Unequal layer/source areas and arbitrary orientation are preserved; only inconsistent dimension/area declarations or broken IDs are generic failures.

Each material has unique `MAT-###`, case-local label/class, `anisotropy_representation`, and explicit `thermal_properties`. Properties have `property_id`, component (`isotropic`, `x`, `y`, `z`, cross-component, or `other`), thermal-conductivity envelope, temperature basis, and condition basis. Rotated tensors and temperature-dependent facts may be represented through the declared representation/basis even though a later model may reject them.

A label such as `diamond`, `copper`, or `SiC` supplies no value. Missing conductivity remains missing; there is no material database fallback, implicit grade, inferred normal component, or reserved density/heat-capacity field in I2.

### Interfaces

Each interface has unique `IFC-###`, upstream/downstream adjacent layer IDs, one `representation_type`, one value envelope, effective-area envelope, and condition basis. Representation is exactly one of `area_normalized_resistance`, `absolute_resistance`, `area_normalized_conductance`, or `ideal_zero`.

The value kind must respectively be area thermal resistance, absolute thermal resistance, area thermal conductance, or area thermal resistance with canonical value `0`. Parallel authoritative representations fail. Missing interface/effective-area input holds readiness; I2 never calculates resistance, inverts conductance, infers TBR, or hides an omitted interface.

### Boundary conditions

`boundary_conditions` contains one source-side record and one downstream record. Source-side data includes a heat-flow-fraction envelope and explicit path disposition such as `adiabatic_other_paths`, `declared_parallel_paths`, or `unknown`.

Downstream representation is `fixed_temperature`, `absolute_resistance`, `direct_convection`, or `other`. Closed conditional fields require terminal plane/reference temperature; or absolute `K/W` value/reference temperature/operating basis; or `h`, boundary area, ambient temperature, and operating basis. Unsupported `other` remains representable with description and missing/evidence states.

I2 validates kinds, references, and completeness only. It does not calculate `1/(h*A)`, require convection area to equal stack area, require heat-flow fraction one, or decide whether a boundary is valid for strict 1D.

## 9. Constraints and Unknowns

A constraint contains unique `CON-###`, exact target JSON Pointer, operator, nullable threshold envelope, severity, provenance, and evaluation disposition. Operators are `lt`, `le`, `eq`, `ge`, `gt`, `in`, `not_in`, or `review_only`; dispositions are `machine_evaluable`, `review_required`, or `not_evaluable_in_epr`.

Quantitative operators require a dimensionally compatible threshold. `review_only` requires no numeric threshold. I2 validates representation but does not evaluate constraints or turn manufacturing/material judgments into numeric scores.

An unknown contains `UNK-###`, exact JSON Pointer, state (`missing`, `assumed`, `conflicting`, `evidence_required`), reason, consequence, structural-readiness impact (`blocking`, `requires_later_acknowledgement`, `non_blocking`), and next evidence action.

Compiler-generated unknowns are sorted by pointer/state/rule ID and assigned sequential IDs, so identical normalized input produces identical paths, IDs, and bytes. Paths address the final persisted EPR, use RFC 6901 escaping, and must resolve to the affected field. User-authored duplicate/conflicting unknown entries fail; the compiler may deterministically coalesce identical entries.

## 10. Candidate Resolution Contract

Authoring input may contain one validated baseline plus candidate override lists. Overrides are transient compiler input and never persist in the EPR.

Override resolution uses this exact sequence:

```text
raw structured baseline
  -> structural normalization
  -> canonical collection ordering by approved stable IDs/order
  -> immutable normalized baseline
  -> RFC 6901 override resolution against that baseline
  -> lexical-order non-overlapping replacement
  -> revalidation, canonicalization, and candidate hash
```

Each override is a replace-only RFC 6901 pointer plus explicit structured value. Allowed roots are `/geometry`, `/materials`, `/interfaces`, and `/boundary_conditions`. The target must already exist in the immutable normalized baseline. Raw authoring array order has no pointer authority. Array insertion/removal, wildcard selection, implicit merge, path creation, and free-text value extraction are prohibited; replacing a whole canonical array is the explicit way to change membership.

Duplicate paths, ancestor/descendant path overlap, missing targets, unsafe pointers, invalid replacement shape, or duplicate IDs after replacement cause `FAIL`. Non-overlapping overrides apply in lexical pointer order. Pointers and `changed_field_paths` use the same post-normalization canonical pointer namespace and are persisted only after normalization. Semantically equivalent raw baselines with different collection order therefore resolve the same semantic override to identical candidate content.

Each persisted candidate contains `candidate_id`, `candidate_role` (`baseline` or `variant`), label, `parent_requirement_id`, complete geometry/stack, complete materials, complete interfaces, complete boundary conditions, sorted `changed_field_paths`, sorted applicable constraint IDs, sorted assumption paths, sorted evidence-required paths, and `resolved_content_sha256`.

Exactly one candidate has baseline role and at least one other candidate has variant role. Top-level `geometry`, `materials`, `interfaces`, and `boundary_conditions` are the sole normalized baseline authority; the baseline candidate is their derived complete mirror. Those four structures must be canonical-content equivalent and its `changed_field_paths` must be exactly empty. A mismatch is structural `FAIL`, so the candidate cannot silently become a second baseline authority. Variant changed paths are always relative to that normalized baseline.

No persisted candidate refers to its baseline or requires calculation-time patch inheritance. Runtime structures are deep-frozen and separately reconstructed so mutating authoring input or one candidate cannot affect another. Each candidate is independently checked for layer/material/interface references, adjacency, boundary completeness, assumptions, and evidence gaps. I2 does not rank candidates.

Candidate hash uses `m16a-candidate-content-identity-1.0` and an explicit projection of every persisted candidate field except `resolved_content_sha256`. Role, label, changed paths, constraints, assumptions, and evidence states are authoritative and therefore included.

## 11. Compiler Contract, Findings, and Lifecycle

The pure compiler accepts already-decoded explicit structured authoring input plus a safe source-reader interface. It returns an immutable EPR value and canonical bytes, or deterministic fatal diagnostics when no schema-valid EPR can be emitted.

Compilation stages are: safely read/hash mandatory intake and bind its case ID; read/hash selected additional sources; validate IDs/confidentiality/input shape; normalize through I1; canonicalize/freeze the baseline; resolve pointers and candidates; verify the persisted baseline candidate is equivalent to top-level baseline; run structural rules; generate unknowns/findings; choose outcome; build candidate hashes; build EPR hash; revalidate final schema/runtime invariants.

`compilation` contains exactly `compiler_policy_version`, `unit_registry_version`, `canonical_json_version`, `heat_source_consistency_policy_version`, `outcome`, `blocking_findings`, `non_blocking_findings`, `warnings`, `assumptions_present`, and `assumptions_requiring_later_acknowledgement`.

Use compiler policy `m16a-epr-compiler-1.0`. Findings contain `rule_id`, classification `STRUCTURAL_MODEL_INDEPENDENT`, exact sorted field paths, message, and required action. Rule IDs follow `M16A-EPR-<SCHEMA|ID|QTY|PROV|UNC|REF|SOURCE|HEAT|GEOM|MAT|IFC|BC|CND|UNKNOWN|CONF>-###` and never encode array position.

Outcome precedence is deterministic:

1. Any malformed, unsafe, dimensionally invalid, conflicting, or unresolved-override blocking finding -> `FAIL`.
2. Otherwise, any required missing or `evidence_required` input -> `HOLD_FOR_INPUT`.
3. Otherwise, any assumed path -> `READY_WITH_ASSUMPTIONS`.
4. Otherwise -> `READY`.

Warnings such as `not_provided` uncertainty do not change outcome. Assumption lists remain populated even when a higher-precedence failure/hold exists. Evaluation-instance acknowledgement is never written.

Use `compilation.outcome` as the sole persisted lifecycle truth in format 1.0. Derived UI lifecycle is `FAIL -> blocked`, `HOLD_FOR_INPUT -> blocked`, `READY_WITH_ASSUMPTIONS -> ready_with_assumptions`, and `READY -> ready`. `draft` describes uncompiled authoring input and is not a persisted compiled-EPR state. This explicit simplification requires gate confirmation; do not add a duplicate `lifecycle_state` silently.

## 12. Rule Classification Matrix

| Planned check | I2 classification/result |
| --- | --- |
| Schema/version/required fields/unknown fields | Structural; invalid shape `FAIL` |
| ID shape, duplicates, case binding, broken pointers/references | Structural; `FAIL` |
| I1 reconstruction, canonical unit/kind, dimensions, status envelope | Structural; `FAIL` or missing `HOLD_FOR_INPUT` |
| Provenance/EVD/MSR linkage/hash/review overclaim | Structural; `FAIL` or evidence gap hold |
| Uncertainty variant, bounds, central-value containment | Structural; malformed/conflicting `FAIL`; absent numeric uncertainty warns |
| Layer order/material links/interface adjacency/one representation | Structural; malformed `FAIL`; required missing input holds |
| Explicit power-flux-area consistency | Structural under versioned tolerance; mismatch `FAIL` |
| Candidate override and complete independent resolution | Structural; unresolved/invalid candidate `FAIL` |
| Baseline role count, top-level equivalence, empty baseline changes | Structural; mismatch or role error `FAIL` |
| Unsafe source/write path, symlink, stale source | Structural safety; abort/no emit |
| Unequal source/layer/downstream footprints | Deferred model applicability; valid EPR fact |
| Multiple sources, nonuniform/volumetric/distributed generation | Deferred model applicability; valid EPR fact |
| Pulsed/transient operating mode or duty-cycle use | Deferred model applicability/evaluation; valid EPR fact |
| Rotated anisotropy, tensor alignment, temperature dependence | Deferred model applicability; valid EPR fact |
| Parallel heat paths or heat-flow fraction not equal to one | Deferred model applicability; preserve explicit metadata |
| Direct-convection area versus stack area | Deferred model applicability; no generic failure |
| Constant-area strict-1D assumptions and supported boundary selection | Deferred model applicability |
| Thermal resistance/TBR/convection/source-temperature equations | Out of I2; no calculation |
| Objective, constraints evaluation, ranking, sweep, sensitivity | Evaluation Plan/EER authority; absent from I2 |

The compiler rejects contradictory representation, not physics merely unsupported by M16A-I4. A schema-valid EPR with any deferred feature can still be `READY`; a later selected model may return `not_applicable`.

## 13. Source-Case and Content Identity

`00_problem_intake.yml` is the mandatory minimum source: I2B always reads it, hashes its exact persisted bytes, and records it in `source_case_sha256`. The case directory name, intake `case_id`, and EPR `case_id` must match; absence, unreadability, unsafe type/path, or mismatch is structural `FAIL` with no emit.

Only other existing root-level canonical names in `REQUIRED_CASE_FILES` are eligible additions. The caller explicitly selects which are consumed; the compiler parses from the same byte buffers it hashes and records only those files. The other 11 files are not mandatory merely because they exist.

Map keys are case-relative POSIX basenames; values are lowercase SHA256 over exact persisted bytes, with no newline, encoding, or YAML normalization. The minimum map is `00_problem_intake.yml -> <lowercase exact-byte SHA256>`. Keys are unique and canonical serializer ordering supplies deterministic map order. Evidence/measurement sidecars are pinned in provenance, not added to this numbered-case map. Unread canonical and unrelated repository files cannot affect it.

Before each read, require a real non-symlink regular file whose resolved parent is the exact canonical case directory. Reject absolute caller references, backslashes, dot/traversal components, directories, alternate names, and paths that escape through symlinks. Reuse SHA256 primitives and path-safety principles, not the existing broader all-numbered-file helper unchanged.

Retain the first read map with the immutable compiler result. Immediately before persistence, re-read and hash every recorded source path using the same safety checks. A missing/replaced/type-changed/symlinked/hash-changed file raises `M16A-EPR-SOURCE-004`, aborts the write, and emits no EPR. Do not call this a baseline and do not hash files never consumed.

EPR identity policy is `m16a-epr-content-identity-1.0`. The owner constructs an explicit dictionary allowlisting, in schema order, every top-level field from `problem_format_version` through `confidentiality_level`; only `compiled_content_sha256` is excluded. `canonical_sha256` then hashes I1 canonical bytes.

Persisted compilation findings, warnings, outcomes, assumption paths, source hashes, and candidate hashes are authoritative EPR content and are included. Changing any semantic field or compiler policy changes identity. Key insertion order does not.

Timestamps, usernames, hostname, absolute local paths, process IDs, Git working directory, and display metadata are neither schema fields nor identity inputs. Transient compiler context may contain them but the allowlist cannot. `canonical_json_bytes` must not be modified to filter metadata.

## 14. Persistence and Side-Effect Boundary

Keep compile, validation, canonical serialization, and persistence separable. The only I2 filesystem mutation is an explicitly called thin writer for `cases/<case_id>/engineering/problems/<problem_id>.json`.

The writer validates case/folder/problem IDs, exact parent containment, `.json` suffix, no symlink in the existing path chain, final source hashes, final EPR identity, and canonical bytes. It creates only `engineering/problems/` as needed and writes atomically with UTF-8/LF bytes.

If the target exists with identical bytes, return idempotent success. If different bytes exist at the same immutable problem ID, fail and require a new ID; do not expose force-overwrite. Never modify numbered files, Decision Board, Claim Ledger, engineering memory, canonical decisions, evidence/measurement/Prediction-Reality records, or historical artifacts.

No I2 command is added to `scripts/labos_case.py`. A later authorized task may expose the pure compiler/writer through that existing CLI.

## 15. Free-Text Boundary

Free text may populate only title, purpose, descriptions, labels, bases, reasons, consequences, warnings, and evidence-gap actions. It may not create an authoritative numeric value, unit, area, property, boundary, heat split, tolerance, or override value.

All physical values enter through the explicit structured envelope and I1 parser with provenance. Numeric-looking text remains text and produces a deterministic missing/evidence gap where a structured field is required. I2 contains no regex/LLM numeric extraction, no generative property estimator, and no confirmation UI.

## 16. Acceptance Test Matrix

| ID | Test | Required result |
| --- | --- | --- |
| SCH-01 | Valid minimal complete EPR | Schema/runtime accept; exact format version |
| SCH-02 | Missing required field, invalid EPR/case/domain ID | Deterministic failure |
| SCH-03 | Unknown top-level or nested field | Rejected by closed contract |
| SCH-04 | Wrong problem format version or filename/ID mismatch | Rejected |
| QTY-01 | I1 quantity with equivalent authoring units | Canonical decimal strings and exact conversion retained |
| QTY-02 | Invalid unit/kind, JSON number, forged conversion | Rejected through I1 reconstruction |
| QTY-03 | Missing status/null value rules | Only exact missing variant accepted |
| QTY-04 | Assumed value without source/rationale | Rejected; valid assumption path listed |
| UNC-01 | All five uncertainty variants | Exact variant validation; no probability semantics |
| UNC-02 | Negative amount/fraction, reversed interval, outside central value | Rejected |
| UNC-03 | `not_provided` | Warning, never treated as zero |
| PROV-01 | Inline provenance shapes and combinations (I2A) | Accepted/rejected without filesystem access |
| PROV-02 | Actual EVD/MSR resolution, validation, case/status/link/hash (I2B) | Repository reality verified |
| PROV-03 | Missing/duplicate/wrong-case/stale sidecar or review overclaim (I2B) | Blocking finding |
| HASH-01 | Repeated EPR, reordered mapping keys | Byte-identical canonical bytes/hash |
| HASH-02 | Self-hash or transient host/user/path/time differs | Explicit projection unchanged |
| HASH-03 | Any allowlisted semantic field/finding changes | EPR hash changes |
| SRC-01 | Minimum compilation | Intake is read and is the minimum exact path-to-byte-hash map |
| SRC-02 | Source changes between compile and write | Stale-source failure; no emit |
| SRC-03 | Unread numbered/unrelated file changes | Source map and EPR identity unchanged |
| SRC-04 | Symlink, traversal, absolute/backslash reference | Rejected |
| SRC-05 | Missing intake or folder/intake/EPR case-ID mismatch | Structural `FAIL`; no emit |
| CMP-01 | Required input missing | `HOLD_FOR_INPUT` and deterministic unknown path |
| CMP-02 | Conflicting representation or arithmetic | `FAIL` with stable rule ID |
| CMP-03 | Complete input with assumptions | `READY_WITH_ASSUMPTIONS` and exact paths |
| CMP-04 | Complete evidence-disposed problem | `READY` |
| SEP-01 | Unequal footprints | Valid EPR; no strict-1D rejection |
| SEP-02 | Volumetric/distributed or multiple source | Valid EPR; applicability deferred |
| SEP-03 | Rotated anisotropy or direct-convection area mismatch | Valid EPR; applicability deferred |
| CND-01 | Baseline plus non-overlapping overrides | Deterministic complete resolved view/hash |
| CND-02 | Candidate roles/top-level baseline equivalence/baseline changed paths | Exactly one equivalent unchanged baseline; mismatch `FAIL` |
| CND-03 | Missing/duplicate/overlapping override target | `FAIL` |
| CND-04 | Candidate baseline mutation after compile | No resolved candidate changes |
| CND-05 | Inherited assumption/evidence gap | Explicit candidate path; cannot be hidden |
| CND-06 | Reordered equivalent raw baseline plus same semantic override | Same canonical pointer, changed paths, bytes, and hash |
| SAFE-01 | Material label/property text only | No value default or extraction; hold |
| SAFE-02 | Existing different EPR at same ID | Refuse overwrite |
| SAFE-03 | Compile/write operation | No numbered/canonical/historical mutation |
| REG-01 | I1 quantity/serialization suites | Remain passing unchanged |
| REG-02 | Prediction-Reality suite/artifacts/schema | Remain unchanged and passing |
| REG-03 | Historical M15B files and dispositions | Byte-untouched; no reinterpretation |
| REG-04 | Full repository test suite | Pass; raw test count is not completion evidence |

## 17. Out of Scope

- Evaluation Plan implementation, EER, and Prediction-Reality adapter.
- Thermal model registry, strict-1D applicability engine, or any model selection.
- Thermal resistance, TBR, convection, source-temperature, or constraint calculations.
- Candidate ranking, objective selection, sweeps, sensitivity, FEA, CFD, or CAD.
- Material-property database, hidden defaults, calibration, or probabilistic uncertainty.
- MPCVD modeling or proprietary growth/bonding/process knowledge.
- LLM extraction, agent runtime, API automation, or paid actions.
- Automatic Evidence review, canonical decision, Claim Ledger/Decision Board/memory change.
- ROADMAP, approved M16A architecture, M16A-I1, benchmarks, frozen protocols, or historical reassessment.

## 18. Historical Boundary

I2 starts from commit `24540dd22fa552f26a98e2d85427a43cd352195a` only as its implementation starting state. It must not modify, replace, reopen, or reinterpret Phase 0.5C, the M15B execution baseline, frozen protocols, historical benchmark evidence, historical P3 = `PARTIAL`, scientific disposition `in_scope_generalization_supported`, or governance disposition `governance_pass`.

## 19. Future Exit Criteria

- The persisted EPR schema and exact version exist and reject unknown structure.
- I1 decimal, unit, conversion, and canonical serialization primitives are reused unchanged.
- Provenance, uncertainty, confidence, status, source linkage, and assumption semantics are explicit.
- Exact-files-read source hashes and stale-source checks are deterministic and safe.
- Candidate and EPR explicit projections produce deterministic hashes without self/host metadata.
- Model-independent outcomes follow precedence and stable rule IDs.
- Physics unsupported by I4 remains representable and is not rejected merely for applicability.
- Every candidate is complete, independently valid, immutable, and free of hidden inheritance.
- No numeric text extraction, property fallback, silent derivation, evaluation authority, or approval leakage exists.
- Writer scope is case-local and historical/canonical artifacts remain untouched.
- Acceptance matrix and full regression pass; test count alone is not an exit criterion.

## 20. Gate Questions and Proposed Resolutions

| Question | Proposed resolution |
| --- | --- |
| One PR or two? | Two: I2A schema/runtime/identity, then I2B compiler/resolution/writer. |
| Standalone quantity schema? | No; use EPR-local `$defs` around I1 runtime primitives. |
| Separate provenance module? | No; keep the small EPR-owned contract in `problem.py`. |
| Persist lifecycle plus outcome? | No; outcome is sole persisted truth and lifecycle is derived. |
| Include compilation findings in EPR identity? | Yes; they are persisted authoritative EPR content. |
| Heat consistency tolerance in I2? | Yes; it is model-independent, versioned, symmetric, Decimal, and recorded by policy ID. |
| Writer in I2? | Yes, only as a thin explicit idempotent case-local edge after the pure compiler. |
| Reuse current source hash helper directly? | No; reuse conventions, but track only safe eligible files actually read. |

No unresolved technical question blocks implementation if the gate accepts these explicit resolutions. Changing the status model, tolerance, hash projection, override operations, version strings, or future file set requires review before coding.

## 21. Recommended Next Step

Authorize I2A only first. Minimum scope is the schema, immutable runtime, identity projections, focused exports, and schema tests. Acceptance is SCH/QTY/UNC/PROV/HASH coverage without compiler/writer behavior or historical changes. Primary risk is freezing an ambiguous persisted contract; independent review should therefore verify authority separation and model-applicability deferral before I2B.

Recommended execution: continue this project task for I2A implementation with a capable coding model at high reasoning. Open a separate independent-review task before merging I2A; do not reuse author self-check as independent review.
