# M16A-I3 — Evaluation Plan, Engineering Evaluation Result, and Reproducibility Identity

## Document Control

| Item | Normative value |
| --- | --- |
| Layer | L1 quantitative engineering infrastructure / L4 contract |
| Starting commit | `a5b40135f2d781f1c42f0973d21d540bb183b358` |
| Starting tree | `51b72c864b2bacf23e935ef7d4ac42e41861dbfd` |
| Architecture | `docs/M16A_ENGINEERING_PROBLEM_COMPILER.md` |
| I2 task contract | `docs/M16A_I2_EPR_SCHEMA_COMPILER_TASK.md` |
| Status | Task-brief preparation only; implementation requires separate independent authorization. |
| Deliverable | This task brief only |
| Confidentiality | Public-safe contract; synthetic examples only |

This document is normative for the proposed M16A-I3 implementation boundary. “Must,” “must not,” “required,” and “reject” define acceptance requirements. It does not authorize implementation.

### Historical boundary

M15B remains unchanged:

- P3 = `PARTIAL`;
- scientific = `in_scope_generalization_supported`;
- governance = `governance_pass`; and
- Phase 0.5C is not restarted.

Nothing in I3 may reinterpret, rewrite, regenerate, or weaken frozen M15/M15B artifacts, tests, outcomes, or review authority.

## 1. Objective and Authority Chain

I3 defines how an immutable Engineering Problem Representation (EPR) is bound to an evaluation request, how the attempted evaluation is recorded in an Engineering Evaluation Result (EER), and how reproducibility identities are reconstructed. It also defines a typed adapter boundary from a valid persisted EER to the unchanged Prediction–Reality 1.0 contract.

The authority chain is exact:

| Artifact | Authoritative question |
| --- | --- |
| EPR | **WHAT IS THE ENGINEERING PROBLEM?** |
| Evaluation Plan | **HOW DO WE INTEND TO EVALUATE THAT IMMUTABLE PROBLEM?** |
| EER | **WHAT ACTUALLY HAPPENED WHEN THAT EVALUATION WAS ATTEMPTED?** |

I3 owns:

- the Evaluation Plan contract;
- the per-evaluation assumption acknowledgement contract;
- exact EPR binding;
- the Model Manifest snapshot contract;
- the EER envelope;
- EER reproducibility identities;
- model-result payload binding;
- safe immutable EER persistence; and
- the typed M16A-to-legacy Prediction–Reality projection contract.

I3 does not own thermal equations, resistance or source-temperature calculations, TBR or convection equations, model-applicability physics, candidate-ranking execution, parameter-sweep execution, sensitivity arithmetic, material-property lookup, optimization, FEA, or spreading correlations. Those computational capabilities begin in I4 or later.

## 2. Repository Findings and Compatibility Decisions

The following findings are from the required starting tree. I3 must reuse or preserve them; this preparation task changes none of them.

| Area inspected | Existing repository behavior | I3 compatibility decision |
| --- | --- | --- |
| I2 public API | `labos.engineering` exports `EngineeringProblem`, `EngineeringProblemValidationError`, EPR/candidate identity functions and version constants, `CompiledEngineeringProblem`, `CompilationFailure`, `compile_engineering_problem`, and `write_engineering_problem`, alongside I1 quantities and serialization. | Reconstruct persisted EPRs through `EngineeringProblem.from_dict`; reuse I1 serialization and quantity behavior; do not change I2 exports or semantics in this brief. |
| EPR identity and outcomes | `EngineeringProblem` validates closed canonical content and reconstructs `compiled_content_sha256`. I2 compilation outcomes are `FAIL`, `HOLD_FOR_INPUT`, `READY_WITH_ASSUMPTIONS`, and `READY`. Candidate views carry resolved content identities and candidate-specific assumption paths. | Bind evaluation to `compiled_content_sha256`. Preserve I2 outcome meanings. Do not put plan choices into EPR or mutate EPR acknowledgement state. |
| Canonical decimal behavior | I1 accepts physical numeric input only as bounded, finite base-10 strings; canonical text is exact plain decimal with normalized zeros. `float` is not an accepted M16A physical input. | All M16A plan values, manifest-related physical values, result values, and prediction outputs follow I1 decimal-string and quantity-kind rules where physical quantities occur. |
| Canonical JSON | `canonical_json_bytes` recursively accepts only null, exact bool/string/int, `Decimal`, mappings with string keys, and lists/tuples; it emits compact sorted-key UTF-8 JSON plus one LF. `canonical_sha256` hashes exactly those bytes. | Every I3 identity uses an explicit allowlisted projection and the existing canonical serializer; no implicit filtering, timestamps, host data, or path normalization may affect hashes. |
| Prediction–Reality 1.0 schema | The closed Draft 2020-12 schema requires `prediction_reality_format_version: "1.0"`; prediction `value`, `lower_bound`, and `upper_bound` are JSON number or null, with model and input metadata. | Do not alter the schema. The adapter must bridge M16A decimal strings to the legacy JSON-number domain only after exact unit conversion and representability checks. |
| Legacy comparator | The comparator requires exact quantity-string equality and exact unit-string equality, performs no unit conversion, and derives numeric values as `Decimal(str(decoded_json_number))`. Unit mismatch is non-comparable. | Keep the comparator untouched. Perform closed-registry conversion before producing a projection, then require exact survival through legacy JSON decoding. |
| Evidence validator | Evidence Objects use format `1.0`, `EVD-###`, human review fields, controlled source reference/hash, the four confidentiality levels, and an `evidence_type` vocabulary that includes `simulation`. Simulation evidence is warned when its source/method does not identify model and input basis. | An EER remains an unreviewed calculation artifact. A later explicit workflow may create a simulation EVD bound to the immutable EER and its exact hash. I3 creates no EVD. |
| Measurement validator | Measurement References use format `1.0`, `MSR-###`, bind an EVD, require case identity, validate completed/reviewed numeric values and units, controlled raw-data reference/hash, anonymized sample IDs, uncertainty, confidentiality, and human review. | The adapter accepts only an existing Measurement Reference that passes repository validation and matches case, explicit quantity label, and compatible registered unit. It does not edit the measurement. |
| Existing sidecar safety | The I2 EPR writer revalidates the immutable object and source snapshots, constrains output to `engineering/problems`, rejects unsafe/symlink parents and targets, emits canonical bytes, uses a same-directory temporary file plus atomic creation, returns success for identical bytes, and rejects different bytes at the same ID. | The later EER writer must apply the same principles to `engineering/evaluations`, plus exact persisted-EPR first-read/second-read stale-source protection. No overwrite or force mode is permitted. |
| No-API CI | CI checks required repository paths, runs the public example case checker in normal and expected-WARN strict modes, then runs `python -m unittest discover -s tests`. | A later implementation must remain standard-library/no-API compatible. This docs-only preparation runs the same relevant repository checks and the full unittest suite. |

## 3. Primary Persistence and Schema Decisions

There are exactly two primary persisted M16A engineering artifacts:

1. EPR; and
2. EER.

The Evaluation Plan is not a third sidecar. The canonical plan is embedded in its EER and bound by `evaluation_plan_sha256`. A plan must not be persisted at `cases/<case_id>/engineering/plans/...` or any equivalent sidecar location.

The exact Model Manifest snapshot used is also embedded in the EER and bound by `model_manifest_sha256`. There is no standalone persisted Model Manifest sidecar.

The approved EER location is:

```text
cases/<case_id>/engineering/evaluations/EER-001.json
```

I3 will eventually own one new persisted schema only:

```text
labos/schemas/engineering_evaluation_result.schema.json
```

That closed schema will define the Evaluation Plan, Model Manifest, result envelope, prediction outputs, and findings through internal `$defs`. I3 must not create `evaluation_plan.schema.json` or `model_manifest.schema.json`. This task creates no schema.

## 4. Frozen Proposed v1 Versions and IDs

| Purpose | Exact identifier |
| --- | --- |
| Evaluation Plan format | `m16a-evaluation-plan-1.0` |
| Engineering Evaluation Result format | `m16a-engineering-evaluation-result-1.0` |
| Model Manifest format | `m16a-model-manifest-1.0` |
| Evaluation Plan content identity | `m16a-evaluation-plan-content-identity-1.0` |
| Model Manifest content identity | `m16a-model-manifest-content-identity-1.0` |
| Evaluation input identity | `m16a-evaluation-input-identity-1.0` |
| EER content identity | `m16a-eer-content-identity-1.0` |
| Prediction–Reality adapter | `m16a-prediction-reality-adapter-1.0` |

EER IDs are sequential case-local identifiers `EER-001`, `EER-002`, and so on, matching `^EER-[0-9]{3}$`. Timestamps and random UUIDs must not be used as EER identity.

All version fields are authoritative content. Changing a frozen contract incompatibly requires an explicitly reviewed new version rather than silent reinterpretation.

## 5. Exact EPR Binding

Every Evaluation Plan and EER binds to exactly one persisted EPR with:

- `case_id`;
- `problem_id`; and
- `epr_compiled_content_sha256`.

The EER additionally records:

- `epr_reference`, exactly `engineering/problems/<problem_id>.json`; and
- `epr_file_sha256`, SHA-256 over the exact persisted canonical EPR file bytes.

The semantic evaluation identity uses `epr_compiled_content_sha256`, not a mutable path or file hash. `epr_file_sha256` records repository reality and enables stale-source detection. The plan must not mutate, copy, or recompile the EPR.

Changing the requested model or version, selected candidates, objective, constraint rule, sweep, sensitivity request, assumption acknowledgements, or model options must not change the EPR `compiled_content_sha256`. Such changes produce a different plan identity while the problem remains the same.

## 6. Evaluation Plan Contract

The canonical Evaluation Plan is an immutable, closed, canonical-JSON-compatible object. Every field below is required unless an internal closed sub-contract explicitly permits null or an empty array.

| Field | Normative meaning |
| --- | --- |
| `evaluation_plan_format_version` | Exact `m16a-evaluation-plan-1.0`. |
| `case_id` | Must equal the bound EPR case. |
| `problem_id` | Must equal the bound EPR problem ID. |
| `epr_compiled_content_sha256` | Must equal the reconstructed persisted EPR content identity. |
| `model_request` | Explicit requested `model_id` and `model_version`. |
| `selected_candidate_ids` | Non-empty canonical selection of EPR candidate IDs. |
| `objective` | Closed explicit metric/direction/reference contract. |
| `constraint_handling` | One declared deterministic rule. |
| `parameter_sweeps` | Canonically ordered zero-or-more scenario requests. |
| `sensitivity_request` | Null or one closed OAT request. |
| `assumption_acknowledgements` | Exact, canonical, structured per-evaluation acknowledgements. |
| `model_options` | Closed canonical-JSON-compatible model-request options defined by the requested model contract; no unregistered physics defaults. |
| `maximum_requested_combination_count` | Explicit positive integer plan ceiling covering the requested sweep combination count. |

The plan does not contain reviewer name, approval status, timestamp, hostname, absolute path, EER ID, or a self-hash. The enclosing EER owns `evaluation_plan_sha256`.

### 6.1 Plan content identity

`evaluation_plan_sha256` is `canonical_sha256` over an explicit object containing exactly:

```text
evaluation_plan_identity_version
evaluation_plan
```

`evaluation_plan_identity_version` is `m16a-evaluation-plan-content-identity-1.0`, and `evaluation_plan` is the complete canonical plan object. The version is identity-domain separation and need not be duplicated inside the plan. The same logical plan must reconstruct byte-identically and hash identically; changing any authoritative plan field must change its hash.

### 6.2 Explicit model request

I3 v1 requires `model_request` to contain exactly non-empty `model_id` and `model_version`. There is no automatic model-selection engine in I3. A future version may define deterministic selection rules, but v1 selects one requested model explicitly.

The EER records the actual embedded Model Manifest used. Its `model_id` and `model_version` must exactly equal the request. A mismatch rejects the EER; it is not a warning and must not be silently rebound.

### 6.3 Candidate selection

`selected_candidate_ids` must be non-empty, unique, and sorted lexically. Every selected ID must exist in the bound EPR. A comparison plan with multiple candidates must require all selected candidates to have the same EPR `parent_requirement_id` required for that comparison.

The plan must not embed candidate geometry, material, interface, boundary-condition, or other resolved-content copies. The candidate content in the EPR remains authoritative.

### 6.4 Objective

`objective` is a closed object containing exactly:

- `metric`;
- `direction`; and
- `reference_requirement_id`.

Initial metrics reserved for I4 are:

| Metric | Required direction | Reference rule |
| --- | --- | --- |
| `source_temperature` | `minimize` | `reference_requirement_id` may be null unless the model contract requires one. |
| `total_thermal_resistance` | `minimize` | `reference_requirement_id` may be null unless the model contract requires one. |
| `temperature_margin` | `maximize` | A non-null compatible EPR requirement ID is required. |

I3 validates structure, vocabulary, direction consistency, reference existence, and the explicit compatibility requirement for `temperature_margin`. It calculates no objective.

### 6.5 Constraint handling

`constraint_handling` declares exactly one deterministic rule from:

- `exclude_violating_from_rank`; or
- `report_only`.

I3 validates only the declaration. It must not execute constraints, apply weighted penalties, hide a scoring function, or aggregate manufacturing text into numerical scores. I4 later evaluates constraints and applies the declared rule.

## 7. Per-Evaluation Assumption Acknowledgement

Acknowledgement is per evaluation and is not engineering approval. It creates no reviewer authority, modifies no source status, and must never be written back into the EPR.

An acknowledgement is one of two closed structured forms:

| Scope | Required fields | Path authority |
| --- | --- | --- |
| Candidate | `scope: "candidate"`, `candidate_id: "CND-###"`, `field_path` | RFC 6901 path relative to the selected resolved candidate view. |
| Global | `scope: "global"`, `candidate_id: null`, `field_path` | RFC 6901 path in global EPR authority. |

Candidate-domain fields are `geometry`, `materials`, `interfaces`, and `boundary_conditions`. Required candidate-domain acknowledgements are derived from each selected candidate's own `assumption_paths`, not from the authoring baseline and not from another candidate. This prevents an assumption inherited by `CND-001` but replaced by a provided value in `CND-002` from being falsely required for `CND-002`.

Applicable structured assumptions outside the candidate-domain view are global, including assumptions in `requirements`, `heat_sources`, and `constraints`.

Validation must deterministically:

1. reconstruct the exact bound EPR;
2. resolve each selected candidate independently;
3. determine which assumed fields the requested evaluation declares it will use, without inventing model-specific physics requirements in I3;
4. build exact required candidate-scoped and global acknowledgement records;
5. canonicalize records by scope, candidate ID with null first, then RFC 6901 path;
6. require exact set equality between required and supplied acknowledgements; and
7. resolve every supplied record to an actual `status: assumed` field under its declared authority.

Reject a missing required acknowledgement, an extra acknowledgement, an unknown path, acknowledgement of a provided or otherwise non-assumed value, acknowledgement for an unselected candidate, a duplicate, or a non-canonical list. `reviewed_by` is neither required nor permitted.

Every required assumed field used by the requested evaluation must be acknowledged. I3 must not silently acknowledge an assumption or invent a missing value.

## 8. Representation, Hold, Failure, and Execution Boundary

Representation validity and evaluation execution are separate.

| Condition | Required behavior |
| --- | --- |
| Invalid plan structure or identity | Reject before execution; no EER. |
| EPR `compilation.outcome = FAIL` | Evaluation execution is forbidden; no attempted calculation. |
| EPR `HOLD_FOR_INPUT` | Do not globally fill gaps. A later evaluator may mark a selected candidate `blocked` when its required inputs are unavailable; other selected candidates may still be evaluated in the same EER. |
| EPR `READY_WITH_ASSUMPTIONS` | Arithmetic is allowed only after all exact acknowledgements required by the requested evaluation are present. |
| EPR `READY` | No acknowledgement is required unless a selected candidate actually contains an assumed field used by the evaluation. |

I3 validates the representation and binding. It does not determine model-specific required physics inputs. A software/runtime structural failure that prevents a truthful result must produce no EER, not an EER containing an arbitrary exception trace.

## 9. Parameter-Sweep Contract

Sweeps are evaluation scenarios. They do not create EPR candidates and do not change candidate hashes.

Each sweep is a closed object containing `sweep_id`, `candidate_id`, `field_path`, and exactly one value specification:

- explicit grid: a non-empty canonical list of explicit typed values; or
- range: exact `start`, `stop`, and `step` values plus an explicit endpoint policy.

The endpoint policy must be declared; it must not be inferred from arithmetic coincidence. Sweep IDs must be stable, unique, and canonically ordered. The target candidate must be selected, and `field_path` must resolve to an existing quantified-value field within that candidate.

Every physical sweep point uses the target QuantityKind and a registered dimensionally compatible unit. A sweep may replace only the numeric value of the existing quantified field for an evaluation scenario. It must not alter provenance, uncertainty, confidence, status, quantity kind, unit identity, geometry membership, material membership, or interface membership. There are no JSON Patch semantics and no hidden candidate mutation.

The plan's `maximum_requested_combination_count` must be explicit and must be at least the deterministically calculated requested combination count. Later execution-policy hard ceilings are separately versioned policy and must not be silently inferred or represented as plan intent.

Every requested sweep point must eventually have an explicit EER result disposition, including invalid, blocked, or not-applicable points. I3 does not execute sweeps.

## 10. OAT Sensitivity Request

The first sensitivity method is exactly `oat`. There is no automatic percentage perturbation.

A non-null sensitivity request is a closed object containing:

- `method: "oat"`;
- `baseline_candidate_id` referencing one selected candidate;
- `output_metric` using an explicitly supported metric; and
- a non-empty canonical parameter list.

Each parameter declares `candidate_id`, `field_path`, `minus_value`, and `plus_value`. Both perturbations must have the same QuantityKind as the resolved target field and use compatible registered units. I3 validates the request only.

A zero reference, invalid point, or unsupported metric is an explicit I4 result finding. The evaluator must not silently alter the method, substitute a denominator, or choose a different metric.

## 11. Model Manifest Snapshot

I3 defines the snapshot contract. I4 later supplies the real strict-1D manifest.

The embedded closed Model Manifest contains at minimum:

- `model_manifest_format_version`;
- `model_id`;
- `model_version`;
- `equation_set_version`;
- `implementation_version`;
- `applicability_policy_version`;
- `numerical_policy_version`;
- `result_payload_schema_id`;
- `result_payload_schema_version`;
- `accepted_quantity_kinds`;
- `canonical_units`;
- `known_limitations`;
- `source_references`; and
- `implementation_git_commit`.

`model_manifest_format_version` is `m16a-model-manifest-1.0`. Collections must be unique and canonically ordered. `canonical_units` must bind accepted I1 kinds to exact registry canonical units. Known limitations and source references must be public-safe, deterministic content without credentials or local paths.

`implementation_git_commit` may be null when unavailable. If present, it must be a lowercase Git commit identifier. Timestamp, hostname, user name, and local filesystem path are forbidden.

`model_manifest_sha256` is `canonical_sha256` over an explicit object containing exactly:

```text
model_manifest_identity_version
model_manifest
```

The identity version is `m16a-model-manifest-content-identity-1.0`; `model_manifest` is the complete embedded snapshot. Changes to equations, validity/applicability rules, numerical policy, result contract, or implementation identity must change an appropriate version/content field and therefore the manifest identity.

## 12. Evaluation Input Reproducibility Identity

`evaluation_input_sha256` is the canonical SHA-256 over an explicit allowlisted object containing exactly:

```text
evaluation_input_identity_version
epr_compiled_content_sha256
evaluation_plan_sha256
model_manifest_sha256
```

`evaluation_input_identity_version` is `m16a-evaluation-input-identity-1.0`.

The projection excludes EER ID, EER filename/path, result values, timestamps, reviewers, hostname, absolute paths, and display strings. Therefore:

```text
same EPR + same Evaluation Plan + same Model Manifest
    -> same evaluation_input_sha256
```

This remains true independently of the EER ID or filename. The identity states that inputs and declared model contract are the same; it does not assert that execution completed, that results match, or that human review occurred.

## 13. EER Core Contract

The future EER is a closed, immutable canonical object with at least these top-level fields:

| Field | Normative meaning |
| --- | --- |
| `engineering_evaluation_result_format_version` | Exact `m16a-engineering-evaluation-result-1.0`. |
| `evaluation_id` | Case-local `EER-###`, matching the filename. |
| `case_id` / `problem_id` | Exact bound EPR identity. |
| `epr_reference` | Exact case-local `engineering/problems/<problem_id>.json`. |
| `epr_compiled_content_sha256` | Semantic EPR content identity. |
| `epr_file_sha256` | SHA-256 of exact persisted EPR bytes read for evaluation. |
| `evaluation_plan` / `evaluation_plan_sha256` | Complete embedded plan and reconstructed hash. |
| `model_manifest` / `model_manifest_sha256` | Complete actual manifest snapshot and reconstructed hash. |
| `evaluation_input_sha256` | Reconstructed input identity. |
| `execution_outcome` | `completed`, `partial`, or `not_evaluated`. |
| `candidate_execution` | Exactly one execution record per selected candidate. |
| `assumptions_used` | Acknowledgements actually consumed during evaluated execution. |
| `result_payload` | Null only in the permitted no-evaluation case; otherwise the model-specific wrapper. |
| `prediction_outputs` | Normalized typed numerical outputs for legacy-independent consumption. |
| `findings` / `warnings` | Deterministic public-safe structured result diagnostics. |
| `confidentiality_level` | Deterministic non-downgraded level. |
| `eer_content_sha256` | Reconstructed EER authoritative-content identity. |

An EER has no `reviewed_by`, approval, canonical decision, timestamp, user name, host name, or absolute path. Human review remains outside the calculation artifact.

### 13.1 Execution outcome

Derive `execution_outcome` only from the selected-candidate execution records:

| Candidate result set | Outcome |
| --- | --- |
| All selected candidates successfully evaluated | `completed` |
| At least one evaluated and at least one blocked or not applicable | `partial` |
| No selected candidate evaluated | `not_evaluated` |

The persisted value must equal the derivation. Arbitrary exception traces are not engineering findings and must not be persisted.

### 13.2 Candidate execution envelope

Each selected candidate receives exactly one record, in `selected_candidate_ids` order, containing:

- `candidate_id`;
- `execution_status`: `evaluated`, `blocked`, or `not_applicable`;
- `applicability_status`: `applicable`, `applicable_with_warnings`, `not_applicable`, or `not_evaluated`;
- `applicability_findings`;
- `assumption_acknowledgements_used`; and
- `result_presence`.

Candidate IDs must be unique and exactly equal the plan selection. Status combinations and `result_presence` must be internally consistent. A blocked or not-applicable candidate receives no numerical rank and must not generate a fabricated numerical output.

I3 validates structure and identity only. It does not calculate applicability. I4 supplies actual applicability findings.

### 13.3 Model-specific result payload

Strict-1D result fields must not be hard-coded into the EER core schema. A non-null `result_payload` is a closed versioned wrapper:

```text
schema_id
schema_version
content
content_sha256
```

The embedded manifest declares the exact `result_payload_schema_id` and `result_payload_schema_version`; both must equal the wrapper values. `content` must be canonical-JSON-compatible. `content_sha256` is the canonical SHA-256 over an explicit domain-separated projection containing the exact schema ID, schema version, and content. The future implementation must freeze the payload-content identity version with the model-specific schema rather than infer hashing behavior.

I3 validates wrapper shape, canonical compatibility, schema-identity match, and `content_sha256`. I3 does not validate strict-1D physics inside `content`; I4 owns the model-specific schema and validation. This wrapper is the extension point for strict 1D, spreading-resistance, FEA, and other separately validated models without redesigning EER core identity.

`result_payload` may be null only when `execution_outcome = not_evaluated`, no candidate is `evaluated`, every `result_presence` is false, and `prediction_outputs` is empty.

### 13.4 Actual assumptions used

`assumptions_used` contains the canonical acknowledgement records actually consumed by evaluated execution. It must be a subset of the embedded plan's acknowledgements. Each candidate execution record's `assumption_acknowledgements_used` must also be consistent with the top-level set and its candidate/global scope.

An assumption must not be claimed as used for a blocked or non-executed candidate unless the model explicitly consumed it before reaching that status and its versioned execution contract records that behavior. EPR assumption status is never modified.

### 13.5 Prediction outputs

Prediction–Reality consumers must not depend on model-specific payload internals. The EER therefore exposes a normalized typed `prediction_outputs` array. Each output contains exactly:

- `output_id`;
- `candidate_id`;
- `quantity_label`;
- `quantity_kind`;
- `value`;
- `unit`;
- `lower_bound`;
- `upper_bound`; and
- `result_pointer`.

`output_id` uses `^EER-[0-9]{3}-OUT-[0-9]{3}$`; its EER prefix must equal `evaluation_id`, and IDs are unique and canonically ordered by numeric output suffix. This is a stable case-local EER-output identity; it uses neither time nor randomness.

`quantity_label` is the exact semantic label used for later Prediction–Reality matching, for example `junction_temperature`. `quantity_kind` is an I1 physical kind, for example `absolute_temperature`. `value` and `unit` use canonical M16A decimal-string and canonical-unit semantics. Bounds may be null; when present, they use the same kind and canonical unit as `value`, and `lower_bound <= value <= upper_bound` under exact Decimal comparison.

`result_pointer` is an RFC 6901 pointer into `result_payload.content` and must resolve to the corresponding model-specific result. Only genuinely evaluated numerical outputs may appear. The candidate must be `evaluated` with result presence. Blocked and not-applicable candidates have no fabricated prediction output.

### 13.6 EER content identity

`eer_content_sha256` is `canonical_sha256` over an explicit object containing:

- `eer_identity_version: "m16a-eer-content-identity-1.0"`; and
- every authoritative EER top-level field except `eer_content_sha256` itself.

The allowlist therefore includes EER format and ID; EPR binding and exact file hash; the embedded plan and plan hash; embedded manifest and manifest hash; evaluation-input identity; execution outcome; candidate execution records; actual assumptions used; result payload; prediction outputs; findings and warnings; and confidentiality level.

Only the self-hash is excluded. Because time, user, host, reviewer, approval, and absolute-path fields are absent, the same authoritative EER content must yield byte-identical canonical JSON and the same hash.

## 14. EPR Stale-Source and Safe EER Writer Contract

The later I3 writer writes only:

```text
cases/<case_id>/engineering/evaluations/<evaluation_id>.json
```

Before evaluation, the I3B boundary must safely read the case-local EPR, retain its exact bytes and file hash, reconstruct `EngineeringProblem`, and validate case ID, problem ID, content hash, canonical path, and non-symlink containment.

Immediately before EER persistence, the writer must re-read that same persisted EPR and require:

- exact case identity;
- exact problem ID;
- successful `EngineeringProblem` reconstruction;
- `compiled_content_sha256` equal to the plan and EER binding;
- exact EPR file SHA-256 equal to the first-read snapshot; and
- the path still safe, canonical, case-local, and non-symlinked.

If the EPR changed between planning/evaluation and persistence, persistence must abort. The writer must not silently rebind, recompile, re-evaluate, or modify the EPR.

The writer also must enforce:

- a case-local resolved path under `engineering/evaluations`;
- no symlink case/parent/target and no non-regular target;
- a validated `EER-###` ID and exact `<evaluation_id>.json` filename;
- complete EER reconstruction and identity checks immediately before writing;
- canonical UTF-8/LF bytes;
- a same-directory temporary file, flush/fsync, and atomic no-clobber publication;
- second stale-EPR verification immediately before publication;
- identical existing bytes produce idempotent success; and
- different existing bytes at the same EER ID fail.

There is no overwrite flag, force mode, or automatic next-ID selection. A failed write must leave no partial target and must not alter existing artifacts.

## 15. Typed M16A-to-Legacy Prediction Projection

The I3 adapter sits before the existing Prediction–Reality record and comparator.

Inputs are:

- one persisted valid EER whose exact file bytes and `eer_content_sha256` have been verified;
- one selected `prediction_output`; and
- one existing Measurement Reference that passes repository validation.

Output is a typed projection object suitable for explicit insertion into a new or separately managed Prediction–Reality 1.0 record. The adapter does not write a PRL record, choose `record_id`, choose status, mark anything reviewed, choose `learning_disposition`, invent evidence IDs, modify a measurement, or call calibration.

The projection binds:

| Legacy field | Exact source |
| --- | --- |
| `quantity` | `measurement.quantity`, after exact label-match validation |
| `prediction.value` | EER output converted exactly to `measurement.unit`, then legacy-number checked |
| `prediction.unit` | Exact `measurement.unit` token |
| `prediction.lower_bound` / `upper_bound` | Each bound independently converted and checked when present |
| `prediction.model_name` | `model_manifest.model_id` |
| `prediction.model_version` | `model_manifest.model_version` |
| `prediction.input_reference` | Case-local `engineering/evaluations/<evaluation_id>.json` |
| `prediction.input_sha256` | SHA-256 over the exact persisted EER file bytes |

The projection type should also carry `prediction_reality_adapter_version: "m16a-prediction-reality-adapter-1.0"` and source output identity for caller-side traceability, but only the existing legacy fields may be inserted into the closed Prediction–Reality object.

### 15.1 Measurement matching

The adapter requires all of the following:

- EER `case_id` equals Measurement Reference `case_id`;
- `prediction_output.quantity_label` exactly equals `measurement.quantity`;
- `measurement.unit` is registered for the output's exact I1 QuantityKind; and
- repository validation of the Measurement Reference passes, including its EVD linkage and case binding.

No semantic aliasing is inferred. `junction_temperature` does not silently equal `source_temperature`. The mapping must be explicit in the EER output.

### 15.2 Exact legacy unit projection

The old comparator must never be modified to add conversions. The adapter converts before projection using exact `Decimal` and the closed I1 registry; float is forbidden.

I1 converts a target-unit input `x` to canonical value `c` as:

```text
c = x * scale + offset
```

For a canonical EER value, the adapter derives the exact target-unit value as:

```text
x = (c - offset) / scale
```

The operation must use the I1 exact Decimal context and reject inexact arithmetic. The target unit must be registered for the same QuantityKind. The adapter must then round-trip the derived target value and target token through I1 `convert_quantity` and require exact numeric identity with the canonical EER quantity. Absolute temperature and temperature difference remain distinct kinds.

Example: canonical absolute temperature `323.15 K` converts to exact target value `50 degC`. This does not authorize treating an absolute temperature as a temperature difference.

### 15.3 Legacy JSON-number representability

Prediction–Reality 1.0 stores JSON numbers rather than M16A decimal strings. After exact target-unit conversion, apply this compatibility check independently to value, lower bound, and upper bound:

1. create one standards-compliant JSON numeric token from the exact canonical Decimal text;
2. decode it through the same standard JSON-number domain used by existing Prediction–Reality loading;
3. reject bool, null, or non-number output;
4. calculate `Decimal(str(decoded_value))`; and
5. require numeric identity with the intended exact target Decimal.

If identity changes, projection fails. This check is compatibility validation, not unit conversion, and it does not preserve or claim M16A lexical identity. A high-precision value such as `0.12345678901234567890123456789` that cannot survive the legacy decode path unchanged must be refused rather than rounded.

## 16. Evidence, Review, and Confidentiality Boundaries

An EER is a calculation record, not automatically a reviewed Evidence Object. I3 must not automatically create EVD, MSR, or PRL artifacts; update the Claim Ledger or Decision Board; update engineering memory; approve a candidate; or assert human review.

The current evidence vocabulary supports `evidence_type: simulation`. A later explicitly authorized workflow may create a simulation EVD whose controlled source references the immutable EER and exact persisted file hash. That later Evidence Object carries review authority. Calculation alone does not.

EER confidentiality must never be less restrictive than its EPR. Use the existing ordered vocabulary:

```text
public < internal < customer-confidential < restricted
```

The deterministic rule is:

```text
eer_confidentiality_rank >= epr_confidentiality_rank
```

If later model/result input introduces a more restrictive declared level, EER confidentiality is the maximum rank across the EPR and all declared authoritative inputs. A caller may explicitly choose a more restrictive level but never a less restrictive one. Unknown tokens reject the EER.

No finding, warning, source reference, manifest field, payload field, or adapter projection may leak credentials, user/host names, absolute filesystem paths, restricted process details, or debug traces. Synthetic fixtures must be public-safe and must not encode proprietary growth, bonding, substrate-preparation, chamber, customer, supplier-pricing, or unreleased measurement information.

## 17. Synthetic Public-Safe Architecture Example

All identifiers, hashes, values, statuses, and references in this subsection are synthetic and illustrative. They are not engineering measurements, model results, or performance claims. This is an abridged architecture sketch, not a complete persisted EER instance. Repeated-character hashes are visibly non-authoritative placeholders; future tests must calculate real hashes from fixture bytes.

```json
{
  "epr": {
    "case_id": "synthetic-m16a-i3-case",
    "problem_id": "EPR-001",
    "compiled_content_sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
  },
  "evaluation_plan": {
    "evaluation_plan_format_version": "m16a-evaluation-plan-1.0",
    "case_id": "synthetic-m16a-i3-case",
    "problem_id": "EPR-001",
    "epr_compiled_content_sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
    "model_request": {
      "model_id": "m16a-strict-1d",
      "model_version": "1.0"
    },
    "selected_candidate_ids": ["CND-001", "CND-002"],
    "objective": {
      "metric": "source_temperature",
      "direction": "minimize",
      "reference_requirement_id": null
    },
    "constraint_handling": "exclude_violating_from_rank",
    "parameter_sweeps": [],
    "sensitivity_request": null,
    "assumption_acknowledgements": [
      {
        "scope": "candidate",
        "candidate_id": "CND-001",
        "field_path": "/materials/0/thermal_properties/0/value"
      }
    ],
    "model_options": {},
    "maximum_requested_combination_count": 1
  },
  "evaluation_plan_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "model_manifest": {
    "model_manifest_format_version": "m16a-model-manifest-1.0",
    "model_id": "m16a-strict-1d",
    "model_version": "1.0",
    "equation_set_version": "synthetic-equations-1.0",
    "implementation_version": "synthetic-implementation-1.0",
    "applicability_policy_version": "synthetic-applicability-1.0",
    "numerical_policy_version": "synthetic-numerical-1.0",
    "result_payload_schema_id": "synthetic-strict-1d-result",
    "result_payload_schema_version": "1.0",
    "accepted_quantity_kinds": ["absolute_temperature"],
    "canonical_units": {"absolute_temperature": "K"},
    "known_limitations": ["Synthetic fixture only."],
    "source_references": ["public-synthetic-reference"],
    "implementation_git_commit": null
  },
  "model_manifest_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "eer": {
    "evaluation_id": "EER-001",
    "candidate_execution": [
      {
        "candidate_id": "CND-001",
        "execution_status": "evaluated",
        "applicability_status": "applicable_with_warnings"
      },
      {
        "candidate_id": "CND-002",
        "execution_status": "not_applicable",
        "applicability_status": "not_applicable"
      }
    ],
    "result_payload": {
      "schema_id": "synthetic-strict-1d-result",
      "schema_version": "1.0",
      "content": {"synthetic_result": "not an engineering claim"},
      "content_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
    },
    "prediction_outputs": [
      {
        "output_id": "EER-001-OUT-001",
        "candidate_id": "CND-001",
        "quantity_label": "junction_temperature",
        "quantity_kind": "absolute_temperature",
        "value": "323.15",
        "unit": "K",
        "lower_bound": null,
        "upper_bound": null,
        "result_pointer": "/candidate_results/0/junction_temperature"
      }
    ]
  },
  "synthetic_legacy_projection": {
    "measurement_id": "MSR-001",
    "quantity": "junction_temperature",
    "measurement_unit": "degC",
    "prediction_value": 50,
    "prediction_unit": "degC"
  }
}
```

The example demonstrates two selected candidates, candidate-specific acknowledgement, explicit model request, objective direction, per-candidate applicability status, embedded plan and manifest identities, a model-specific payload identity, a normalized `323.15 K` absolute-temperature output, and exact projection to synthetic `50 degC`. It does not demonstrate executed physics.

## 18. Implementation Decomposition — Future Authorization Required

The work must remain split. Do not collapse I3A, I3B, and I4.

### M16A-I3A — Evaluation Plan, Model Manifest, and EER schema/runtime/identity

Purpose: define and reconstruct a valid Evaluation Plan/EER and its plan, manifest, input, payload-binding, and EER hashes.

I3A may later propose approximately:

- `labos/schemas/engineering_evaluation_result.schema.json`;
- `labos/engineering/evaluation.py`;
- a small reviewed update to `labos/engineering/__init__.py`; and
- `tests/test_m16a_evaluation_schema.py`.

I3A has no filesystem planning, writer, Prediction–Reality adapter, solver, model applicability, or thermal arithmetic. The final file set requires a separate independent implementation gate.

### M16A-I3B — EPR-bound validation/compiler, safe EER writer, and projection adapter

I3B later owns focused modules for:

- EPR-bound plan validation/compiler;
- stale-source-safe EER persistence; and
- the typed Prediction–Reality projection adapter.

I3B has no solver. It should not freeze unnecessary framework abstractions. No CLI is required in I3A; a CLI remains deferred unless separately reviewed for I3B.

### M16A-I4 — strict-1D implementation

I4 later owns:

- the strict steady-state constant-area 1D Model Manifest;
- model applicability;
- thermal equations;
- candidate evaluation and ranking;
- constraint execution;
- sweep execution;
- OAT sensitivity execution; and
- the model-specific result payload schema/content.

## 19. Acceptance Matrix

All tests use synthetic/public-safe fixtures. Test names may add descriptive suffixes but must preserve these stable IDs.

| ID | Acceptance condition | Expected result |
| --- | --- | --- |
| PLAN-01 | Reconstruct the same logical plan from independently built equivalent inputs. | Canonical plan bytes and `evaluation_plan_sha256` are identical. |
| PLAN-02 | Change model/version, selected candidate, objective, sweep, or acknowledgement independently. | Each authoritative change produces a different plan hash. |
| PLAN-03 | Create multiple plans against one EPR. | Plan changes do not change EPR bytes or `compiled_content_sha256`. |
| PLAN-04 | Select an unknown candidate or reference an unselected candidate from a sweep/sensitivity/acknowledgement. | Reject; no executable plan/EER. |
| ACK-01 | Supply all exact used assumption records for every selected candidate/global field. | Acknowledgement validation passes. |
| ACK-02 | Omit one required acknowledgement. | Execution is blocked or plan rejected according to the validation stage; no silent assumption. |
| ACK-03 | Add extra, provided-value, unknown-path, duplicate, or wrong-scope acknowledgement. | Reject. |
| ACK-04 | Candidate `CND-002` replaces an assumed baseline field with a provided value. | No false acknowledgement is required for `CND-002`; `CND-001` remains candidate-scoped. |
| MAN-01 | Reconstruct the same logical manifest. | Canonical manifest bytes and hash are identical. |
| MAN-02 | Change model/equation/implementation/applicability/numerical/result-schema identity. | Manifest hash changes. |
| RID-01 | Reuse the same EPR content identity, plan hash, and manifest hash. | `evaluation_input_sha256` is identical. |
| RID-02 | Change EER ID or case-local EER filename only. | `evaluation_input_sha256` remains identical. |
| EER-01 | Reconstruct the same authoritative EER content. | Canonical EER bytes and `eer_content_sha256` are identical. |
| EER-02 | Change model-specific payload content. | Payload `content_sha256` and EER hash change. |
| EER-03 | Alter embedded plan without its hash or supply a wrong plan hash. | Reject. |
| EER-04 | Alter embedded manifest without its hash or supply a wrong manifest hash. | Reject. |
| EER-05 | Represent no evaluated candidate with `execution_outcome: not_evaluated`. | Null payload, false result presence, and empty prediction outputs are accepted. |
| EER-06 | Represent an evaluated numerical result. | Bound non-null payload, evaluated candidate record, resolving result pointer, and consistent typed prediction output are required. |
| SRC-01 | Read a persisted EPR at the canonical case-local path. | Exact bytes/hash, case/problem identity, canonical reconstruction, and content hash are verified. |
| SRC-02 | Change the EPR bytes after evaluation snapshot and before EER write. | Stale-source failure; no EER write. |
| SAFE-01 | Write the same canonical EER bytes twice to the same valid target. | Second write is idempotent success. |
| SAFE-02 | Place different bytes at the same EER ID. | Reject without overwrite. |
| SAFE-03 | Use a symlink parent or target, including a race substitution. | Reject; no unsafe write. |
| PRJ-01 | Project synthetic absolute temperature `323.15 K` to a matching MSR in `degC`. | Legacy numeric prediction is exactly `50`, unit `degC`. |
| PRJ-02 | Convert between equivalent registered units and round-trip through I1. | Exact M16A numeric identity is preserved before legacy-number conversion. |
| PRJ-03 | Use a different measurement quantity label. | Reject; no inferred semantic alias. |
| PRJ-04 | Use a target unit registered for a different QuantityKind or not registered. | Reject. |
| PRJ-05 | Project a high-precision Decimal that changes through the legacy JSON-number decode path. | Reject; no rounding or float approximation. |
| PRJ-06 | Compare baseline files/tests before and after adapter implementation. | Old comparator, schema, and `tests/test_evidence_reality.py` are unchanged. |
| SEP-01 | Represent a not-applicable selected candidate. | Explicit status/findings are valid and no numerical rank/output is present. |
| SEP-02 | Search EER schema/runtime and fixture output for approval/reviewer authority. | EER contains no approval or reviewer semantics. |
| SEP-03 | Inspect I3 modules and run arithmetic-boundary tests. | No solver, applicability physics, ranking, sweep execution, or sensitivity calculation exists in I3. |
| HIST-01 | Compare frozen M15/M15B content against authorized baseline. | No change. |
| HIST-02 | Run legacy Prediction–Reality regression. | Historical JSON-number, exact-label/unit, no-conversion, and Decimal comparison behavior is unchanged. |

Additional implementation tests must cover closed-object rejection, version mismatch, non-canonical ordering, duplicate IDs, manifest/request mismatch, outcome derivation, confidentiality non-downgrade, unsafe reference rejection, malformed RFC 6901 pointers, output-to-payload binding, range endpoint policy, explicit combination count, and no partial target after a failed write.

## 20. Explicit Non-Goals

I3 does not:

- implement thermal equations;
- implement strict-1D applicability;
- calculate resistance;
- calculate temperature;
- calculate TBR;
- rank candidates;
- execute constraints;
- execute sweeps;
- calculate sensitivity;
- select materials;
- infer properties;
- modify an EPR;
- modify Prediction–Reality 1.0;
- automatically create Evidence;
- approve engineering decisions; or
- reopen M15B.

I3 also does not create a plan sidecar, Model Manifest sidecar, automatic model selector, optimizer, FEA integration, spreading correlation, paid/API automation, or new scientific claim.

## 21. Preparation and Future Delivery Controls

This task is documentation execution only. It creates exactly this file and no implementation, schema, test, fixture, CLI, or case artifact. The preparation commit must contain only:

```text
docs/M16A_I3_EVALUATION_PLAN_EER_REPRODUCIBILITY_TASK.md
```

Before committing this brief, verify:

- starting main commit and tree match Document Control;
- `git diff --check` passes;
- repository required paths exist;
- the public example case checker completes without FAIL;
- strict example checking returns PASS or its documented expected WARN, never FAIL;
- `python -m unittest discover -s tests` completes with zero failures and zero errors; and
- the exact file SHA-256 is recorded in the PR body.

The preparation PR must state its one-file docs-only scope, starting SHA, task-brief SHA-256, no implementation, no schema, no solver, no Prediction–Reality mutation, no M15B mutation, and actual validation results. It must target `main`, use head `codex/m16a-i3-task-brief`, and must not be merged by the documentation executor.

## 22. Authorization Gate and Recommended Next Step

Implementation remains unauthorized. The minimum next step is independent architecture review of this one-file contract against the M16A architecture, merged I1/I2 behavior, identity boundaries, legacy compatibility, and acceptance matrix.

Acceptance for that review is an explicit disposition on I3A scope and frozen contract semantics, with any required corrections made before a separate implementation authorization. Principal risks are accidental third-artifact persistence, plan-to-EPR authority leakage, false assumption acknowledgement, hash projection ambiguity, model-specific EER coupling, stale-source writes, decimal loss at the legacy boundary, and inadvertent creation of review authority.

No development should begin until the repository owner separately authorizes I3A after independent review.
