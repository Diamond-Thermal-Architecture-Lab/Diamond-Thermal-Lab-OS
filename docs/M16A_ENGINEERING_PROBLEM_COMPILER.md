# M16A Architecture Specification: Engineering Problem Compiler and Quantitative Thermal Core

## Document Control

- Layer: L1 Architecture / L4 Specification
- Status: Architecture approved; schema-first implementation task preparation authorized after the architecture PR is merged; implementation execution requires separate authorization
- Initial vertical: GaN/high-power device to diamond heat-spreader layer to interface/TBR to downstream cooling
- Confidentiality: Public-safe; synthetic parameters only
- Related task brief: Not provided
- Decision: FINAL M16A ARCHITECTURE REVIEW: APPROVE
- Independent-review basis: Reviewed specification SHA-256 `47e35ca8bc630abfca754a1c39ca6d568b0fc01b8b243cef78011ffd4e4040c2`; blocking findings: none
- Approval boundary: Architecture approval does not authorize merge, implementation execution, or any change to an M15B historical record

## 1. Purpose and Problem Statement

M16A defines the first deterministic quantitative engineering loop in Diamond Thermal Lab OS:

```text
requirement
  -> Engineering Problem Representation (EPR)
  -> compilation and readiness checks
  -> Evaluation Plan
  -> quantitative thermal evaluation
  -> candidate comparison
  -> sensitivity and evidence-gap analysis
  -> evidence-bound recommendation
  -> human review
```

Architectural authority is separated as follows:

| Artifact/contract | Authority |
| --- | --- |
| Engineering Problem Representation | What is the engineering problem? |
| Evaluation Plan | How will that immutable problem be evaluated? |
| Engineering Evaluation Result | What happened during that evaluation? |

The initial capability addresses layered thermal stacks containing a high-power device, a diamond or non-diamond thermal layer, interfaces, and a downstream cooling boundary. It converts incomplete, provenance-bearing requirements into an auditable calculation request and result. It does not implement a solver in this architecture task and does not approve an engineering route.

### Design goals

- Represent the heat source, geometry, materials, interfaces, boundaries, constraints, unknowns, and candidate variants without free-text ambiguity at the calculation boundary.
- Require a value, unit, provenance, and uncertainty/confidence disposition for every quantitative input.
- Detect missing or conflicting inputs before evaluation.
- Define a deterministic steady-state 1D thermal core with explicit equations and validity limits.
- Compare multiple candidates on a declared objective and common basis.
- Produce reproducible results, sensitivity rankings, evidence gaps, and applicability warnings.
- Reuse the canonical case, evidence, review, decision, and hash infrastructure without changing their authority.

### Non-goals

- Establishing validated material properties or interface values.
- Claiming that a 1D model quantifies lateral heat spreading.
- Replacing simulation, measurement, technical review, or approval.
- Reopening any historical benchmark or governance conclusion.

## 2. Historical Boundary

Merged PR #37 at repository commit `9672df5a02f81fb8a3e1850bbd142aa891086f63` is the repository starting state for M16A architecture work. This starting-point identity is not an M15B baseline and does not create, replace, update, or reinterpret:

- the M15B execution baseline;
- any M15B assessment baseline;
- any M15B frozen artifact;
- the M15B scientific or governance disposition;
- historical P3 = `PARTIAL`;
- the frozen protocol;
- the historical Phase 0.5C execution baseline.

Phase 0.5C is not restarted. M16A artifacts require new format versions, identities, examples, and review records. They must not create, replace, update, or reinterpret any frozen historical record, be represented as new M15B evidence, or be written under `docs/benchmarks/`.

## 3. Architectural Principles

1. **No silent quantitative assumptions.** A missing property remains missing unless an explicit assumption with provenance and a use disposition is supplied.
2. **Dimensioned quantities at every boundary.** Bare physical numbers are invalid in an EPR, evaluation plan, or result.
3. **Facts, assumptions, and calculations remain distinct.** Provenance classification is preserved in the result and recommendation.
4. **Applicability precedes arithmetic.** A numerically executable problem may still be outside a model's validity boundary.
5. **One immutable input identity per evaluation.** Normalized input, evaluation plan, and model manifest are content-addressed.
6. **Comparison is conditional.** Rankings apply only to the declared objective, candidates, model, inputs, constraints, and uncertainty scenarios.
7. **Calculation is not approval.** No solver status or candidate rank creates a canonical decision, customer claim, or engineering-memory update.
8. **Diamond is one candidate, not the default conclusion.** Conventional material, interface, package, and cooling-boundary changes remain comparable where physically meaningful.

## 4. Engineering Problem Representation

### 4.1 Identity and lifecycle

The canonical machine-readable EPR should use a versioned JSON schema and contain:

| Field | Requirement |
| --- | --- |
| `problem_format_version` | Exact schema/serialization version. |
| `problem_id` | Case-local stable ID, proposed form `EPR-001`. |
| `case_id` | Existing canonical case ID. |
| `title` and `purpose` | Public-safe engineering question and intended use. |
| `source_case_sha256` | Hash map for the numbered canonical case files used by compilation. |
| `requirements` | Named engineering requirements and target quantities with provenance. |
| `heat_sources` | Power/flux, footprint, profile, operating mode, and source-plane identity. |
| `geometry` | Ordered layer stack, dimensions, orientation, and source-to-sink direction. |
| `materials` | Case-bound properties; a material name alone never implies a property value. |
| `interfaces` | Explicit resistance/conductance representation for every adjacent layer pair. |
| `boundary_conditions` | Explicit source-side and downstream thermal boundaries. |
| `constraints` | Quantitative limits and review-only manufacturing/material constraints. |
| `candidates` | One baseline and one or more explicit candidate variants. |
| `unknowns` | Missing, assumed, conflicting, or evidence-required inputs. |
| `compilation` | Versioned outcome, model-independent findings, warnings, and assumptions present/requiring later acknowledgement. |
| `confidentiality_level` | Existing Lab OS confidentiality vocabulary. |
| `compiled_content_sha256` | SHA256 over canonical content, excluding this self-hash field. |

Proposed lifecycle states are `draft`, `blocked`, `ready_with_assumptions`, and `ready`. `ready_with_assumptions` means the EPR contains named assumed fields that a later Evaluation Plan must explicitly acknowledge before arithmetic may run. The EPR records assumption status, rationale, source, and required acknowledgement paths, but never records evaluation-instance acknowledgement. A named human reviewer is not required at compiler time for non-canonical screening calculations. Evaluation-plan acknowledgement is not engineering approval; existing human review remains mandatory before any reviewed or canonical decision path.

### 4.2 Quantity envelope

All physical inputs use one `QuantifiedValue` envelope. Canonical decimal values should be serialized as base-10 strings to avoid platform-dependent binary-float text.

```yaml
value: "1000"
unit: W/(m*K)
quantity_kind: thermal_conductivity
provenance:
  source_type: synthetic_fixture
  reference: docs/M16A_ENGINEERING_PROBLEM_COMPILER.md#92-synthetic-input-set
  evidence_object_ids: []
  source_sha256: null
  review_status: unverified
uncertainty:
  kind: interval
  lower: {value: "800", unit: W/(m*K)}
  upper: {value: "1500", unit: W/(m*K)}
  basis: synthetic sensitivity interval; not a material claim
confidence: not_applicable
status: assumed
```

Required rules:

- `value` is finite and has a recognized dimensionally compatible `unit`; `null` is permitted only when `status: missing`.
- `provenance.source_type` is one of `requirement`, `evidence_object`, `measurement_reference`, `literature`, `supplier`, `expert_judgment`, `assumption`, or `synthetic_fixture`.
- A controlled source may carry a lowercase SHA256 and/or existing `EVD-*` or `MSR-*` references. A hash proves identity, not technical validity.
- `uncertainty.kind` is `not_provided`, `not_applicable`, `absolute`, `relative`, or `interval`. M16A does not attach probabilistic meaning to these forms.
- `confidence` is `unknown`, `low`, `medium`, `high`, or `not_applicable`; it never substitutes for numeric uncertainty.
- `status` is `provided`, `assumed`, `missing`, `conflicting`, or `evidence_required`.
- `assumed` requires a rationale and source. The EPR compilation block lists its exact field path as requiring acknowledgement by any Evaluation Plan that uses it. `not_provided` uncertainty creates an evidence-gap warning rather than silently meaning zero uncertainty.
- Conversion history records original value/unit, canonical SI value/unit, conversion rule ID, and unit-registry version.

Dimensionless control values such as format versions, enumerations, IDs, and sweep counts are not physical quantities and do not use this envelope.

Physical dimensionless inputs, including heat-flow fraction or duty cycle, still use the quantity envelope with unit `1`.

Canonical units for the first model are:

| Quantity kind | Canonical unit |
| --- | --- |
| Power | `W` |
| Heat flux | `W/m^2` |
| Length | `m` |
| Area | `m^2` |
| Thermal conductivity | `W/(m*K)` |
| Area-normalized thermal resistance/TBR | `m^2*K/W` |
| Absolute thermal resistance | `K/W` |
| Area-normalized conductance / convection coefficient | `W/(m^2*K)` |
| Absolute temperature | `K` internally; degree Celsius accepted and preserved for display |
| Temperature difference | `K` |

Every accepted authoring alias and scale conversion belongs to a versioned unit registry. Unknown or ambiguous unit strings fail compilation.

### 4.3 Heat source

The heat-source object contains:

- source ID and source-plane location;
- total power and/or heat flux;
- footprint shape and dimensions;
- heated area derived from explicit dimensions;
- spatial profile, initially only `uniform`;
- operating mode, initially only steady-state;
- optional duty-cycle metadata preserved but not applied by the steady-state model.

At least one of power or heat flux is required. If both are supplied, the compiler checks `power = heat_flux * heated_area` using a declared consistency tolerance. A mismatch is `conflicting` and blocks evaluation. Arbitrary heat maps, nonuniform generation, multiple interacting sources, and transient pulses are not accepted by the first model.

The EPR must identify the source/injection plane. The first model treats heat input as power injected at that plane into a one-dimensional series thermal path. It does not model volumetric or distributed internal heat generation within a finite-thickness layer. If that physics is required, strict 1D is `not_applicable` unless a separately reviewed equivalent-source reduction is explicitly supplied with its assumptions and provenance.

### 4.4 Geometry and layer stack

Each ordered layer contains:

- `layer_id`, role, order, and material ID;
- thickness;
- declared cross-sectional dimensions and areas;
- orientation of the layer normal relative to material axes;
- optional manufacturing constraints expressed as facts or requirements, not process recipes.

The stack declares its source-to-sink direction and every area transition. The 1D model requires a constant effective cross-section. A lateral size change or source/spreader area mismatch is not silently averaged: it triggers `not_applicable` for strict 1D evaluation or requires a separately selected spreading/constriction model.

### 4.5 Materials

Each material contains a public-safe name or case-local opaque ID and property records:

- isotropic thermal conductivity, or principal values `k_x`, `k_y`, and `k_z`;
- material orientation relative to the layer normal;
- property temperature and condition basis when known;
- provenance, uncertainty, confidence, and review status per property;
- density and heat capacity only as reserved optional fields for a later transient model; the M16A steady-state core must ignore them and report that they were unused.

The first 1D model may use only the conductivity component normal to the layer. It supports anisotropy only when a principal material axis is aligned with the stack normal. Rotated tensors, off-diagonal terms, temperature-dependent conductivity, and phase changes are outside the model.

There is no implicit material database fallback. A friendly material label such as `diamond` is not a property value.

### 4.6 Interfaces

Every adjacent layer pair has an explicit interface record, including explicit zero resistance when that is the intended synthetic idealization. Supported representations are:

- area-normalized thermal boundary/contact resistance `R''` in `m^2*K/W`, converted by `R_interface = R'' / A`;
- absolute contact resistance in `K/W`, used directly; or
- area-normalized conductance in `W/(m^2*K)`, converted by `R'' = 1 / G`.

The representation type, effective area, source, uncertainty, confidence, and evidence status are mandatory. Only one representation is authoritative per interface. Conflicting parallel representations block compilation. Contact pressure, roughness, bond quality, and process dependence may be captured as evidence gaps but are not inferred.

### 4.7 Boundary conditions

The initial single downstream heat-flow path supports:

- fixed temperature `T_base` at an explicit terminal plane;
- provenance-bearing absolute downstream thermal resistance `R_boundary` in `K/W` plus its ambient/base reference temperature and operating-condition basis; or
- direct convection defined by `h`, boundary area, and ambient temperature, with `R_convection = 1 / (h*A_boundary)`.

A fixed-temperature boundary defines the terminal temperature plane and contributes no hidden thermal resistance. Any resistance upstream of that plane must be an explicit layer, interface, or resistance element.

An absolute `R_boundary` may represent an externally characterized downstream subsystem. The strict 1D model uses that value as a black-box boundary condition; it does not claim to model the subsystem's internal geometry, spreading, convection, fluid flow, or other physics. Its provenance, applicability, and operating-condition basis are required.

For direct convection, `A_boundary` must equal the common 1D cross-sectional area. A larger or smaller geometric convection area must not silently represent spreading, area enlargement, fins, cold plates, or other multidimensional heat-flow effects. If `A_boundary` differs from the common area, strict 1D is `not_applicable`.

The source-side boundary and the fraction of total power entering the modeled path must be explicit. The heat-flow fraction is a provenance-bearing dimensionless quantity with unit `1`. The first model requires its value to be `1` and all other source-side paths to be explicitly adiabatic. Radiation, coupled convection, parallel heat paths, fluid temperature rise, and spatially varying sink temperature are outside the model.

Absolute temperature and temperature difference are different quantity kinds. Celsius-to-kelvin offsets apply to absolute temperatures; temperature differences use equivalent degree increments without an offset.

### 4.8 Engineering constraints

Constraints are machine-evaluable where possible and otherwise preserved as review requirements. Initial quantitative constraints include:

- maximum temperature at a named node;
- maximum total stack or candidate-layer thickness;
- maximum footprint dimensions;
- allowed material classes;
- allowed candidate/manufacturing-route categories.

Each constraint has an ID, operator, threshold quantity, source, severity, and evaluation disposition. Non-quantitative manufacturing constraints cannot be converted into scores by the solver.

### 4.9 Unknowns and evidence gaps

Each unknown contains a stable ID, exact field path, state, reason, consequence, structural-readiness impact, and next evidence action. States are `missing`, `assumed`, `conflicting`, and `evidence_required`.

Examples include an unknown interface TBR, unspecified normal conductivity, unbounded cooling resistance, missing footprint dimension, or a material value whose source does not apply at the intended temperature. The compiler emits these gaps even when a later Evaluation Plan may acknowledge an assumed value for screening arithmetic.

### 4.10 Candidate representation

A candidate is a complete resolved view, not an unordered patch applied during calculation. Authoring files may express a candidate as a baseline plus overrides, but compilation must materialize the full candidate, validate it independently, and hash its resolved content. Each candidate declares:

- stable candidate ID and public-safe label;
- parent requirement ID;
- complete stack, interfaces, and boundary;
- changed field paths relative to the baseline;
- applicable engineering constraints;
- unresolved evidence and assumption states.

This prevents inherited or candidate-specific assumptions from being hidden.

## 5. Engineering Problem Compiler

The compiler is a deterministic transformation and validation boundary, not a generative property estimator.

### 5.1 Inputs

- Selected fields from existing `00_problem_intake.yml`, `01_thermal_design_passport.yml`, candidate artifacts, and case metadata.
- Explicit quantitative authoring input supplied for problem compilation.
- Optional Evidence Object and Measurement Reference IDs.
- A versioned, model-independent compilation policy.

Free text from canonical artifacts may prefill descriptive fields and unknowns. It must not be parsed into authoritative numeric quantities without explicit confirmation and provenance.

### 5.2 Compilation stages

1. Bind the source case and hash every numbered canonical artifact read.
2. Validate identifiers, confidentiality status, schema, and quantity envelope completeness.
3. Normalize units to canonical SI while preserving original lexical values and conversions.
4. Resolve each candidate into a complete immutable problem view.
5. Check dimensional compatibility, sign/range rules, duplicate IDs, interface adjacency, and heat-source consistency.
6. Classify missing, assumed, conflicting, and evidence-required fields.
7. Run model-independent structural readiness checks without selecting or evaluating a model.
8. Emit a canonical EPR containing the versioned `compilation` block and content hash.

### 5.3 Compiler outcomes

| Outcome | Meaning | Evaluation behavior |
| --- | --- | --- |
| `FAIL` | Malformed, dimensionally invalid, conflicting, or unsafe input. | No evaluation. |
| `HOLD_FOR_INPUT` | Required quantitative input is missing. | No evaluation for affected candidate/model. |
| `READY_WITH_ASSUMPTIONS` | Required inputs exist, but named assumptions are present. | Evaluation may proceed only when its plan acknowledges the exact paths; result remains provisional. |
| `READY` | Required inputs and provenance dispositions are complete. | Model applicability still controls execution. |

The EPR `compilation` block must list the outcome, every model-independent blocking and non-blocking finding by stable rule ID, warnings, assumptions present, and assumptions requiring later acknowledgement. It must not contain evaluation-instance acknowledgements, requested-model state, or model-specific applicability findings. It must never insert a default material conductivity, TBR, geometry, heat split, or boundary condition. No separate compilation-report sidecar is proposed.

### 5.4 Evaluation Plan authority

The Evaluation Plan is the hash-bound evaluation-request contract. It references the immutable EPR and controls how that problem is evaluated without changing EPR identity. It contains:

- plan format/version and stable plan identity;
- EPR reference and EPR content hash;
- requested model and version, or an explicit deterministic model-selection rule;
- candidate IDs to evaluate;
- evaluation objective and constraint-handling rule;
- requested parameter sweeps;
- requested OAT sensitivity analysis;
- exact assumed-field paths acknowledged for this evaluation; and
- any other deterministic execution options accepted by the selected model.

Plan validation requires every acknowledged path to identify an `assumed` EPR field and every assumed field used by the selected candidates to be acknowledged. Missing acknowledgements block execution; unknown or extra acknowledgement paths fail plan validation. Model applicability is checked only after the plan selects a model. The EER records the selected model and actual applicability findings, including a non-evaluated result when the model is `not_applicable`.

The Evaluation Plan does not require a third primary sidecar. The exact canonical plan is embedded in the EER as `evaluation_plan`, bound by `evaluation_plan_sha256`, and included in the reproducibility identity. A request may hold the plan transiently before execution, but the persisted record of what was requested is the plan embedded in the EER.

## 6. Quantitative Thermal Core

### 6.1 Model registry and identity

Every model is registered with:

- model ID, semantic version, equation-set version, and implementation version;
- accepted quantity kinds and canonical units;
- required and prohibited input features;
- applicability checks and warning/error rule IDs;
- rounding/serialization policy;
- source references for any non-fundamental correlation;
- validation fixtures and known limitations.

An evaluation result identifies the exact model manifest and code Git commit when available. Changing equations, unit conversions, validity rules, or rounding requires a model or registry version change.

### 6.2 First model: steady-state 1D series conduction

For a constant cross-sectional area `A`, positive source power `P`, layer thickness `t_i`, and normal conductivity `k_i`:

```text
R_layer_i     = t_i / (k_i * A)
R_interface_j = TBR_j / A                 for area-normalized TBR
R_convection  = 1 / (h * A_boundary)      when convection is selected
A_boundary    = A                          direct-convection validity requirement
R_total       = sum(R_layer_i) + sum(R_interface_j) + R_boundary
delta_T       = P * R_total
T_source      = T_reference + delta_T
```

In these equations, the boundary contribution is zero for a direct fixed-temperature terminal plane, the supplied absolute `K/W` value for a black-box resistance boundary, or `R_convection` for direct convection. Any explicit resistance upstream of a fixed-temperature plane remains a separate resistance-budget element.

Node temperatures are calculated from cumulative downstream resistance. The resistance budget reports every layer, interface, and boundary contribution in `K/W` and as a percentage of `R_total`.

For heat-flux input, the compiler derives `P = q'' * A` before the model runs. The derivation and source identities remain in the result.

### 6.3 Determinism and numerical policy

- Convert canonical decimal strings to decimal arithmetic; do not use locale-sensitive parsing.
- Use a fixed operation order defined by the model version and stable ordering by layer/interface ID.
- Reject NaN, infinity, non-positive area, non-positive thickness, non-positive conductivity, negative TBR, and non-physical convection coefficients. Explicit zero TBR is allowed and retained in the budget.
- Keep full working precision set by the model manifest and round only at serialized output fields using a declared rule.
- Serialize canonical JSON as UTF-8, LF line endings, stable key ordering, and stable decimal notation; exclude timestamps, usernames, hostnames, and absolute paths from reproducibility hashes.

### 6.4 Candidate comparison

Candidate comparison operates on resolved candidates that share a requirement and declared objective. Initial objectives are minimum source temperature, minimum total thermal resistance, and maximum temperature margin.

The result separates:

- applicable and constraint-feasible candidates;
- applicable candidates with constraint violations;
- candidates evaluated with acknowledged assumptions;
- not-applicable or blocked candidates, which receive no numerical rank.

Ranking uses the declared objective, then stable candidate ID for exact ties. Constraint feasibility and assumption status remain visible; a numerical rank is not a recommendation or approval.

### 6.5 Parameter sweeps

A sweep plan names exact field paths and explicit value grids or start/stop/step quantities. Candidate order, parameter order, endpoint inclusion, and maximum combination count are part of the plan. Every point receives a deterministic status and result. Invalid or not-applicable points are retained with findings rather than silently omitted.

### 6.6 Sensitivity analysis

The first sensitivity method is deterministic one-at-a-time local sensitivity around a named baseline:

```text
S_i = ((y_plus - y_minus) / y_ref) / ((x_plus - x_minus) / x_ref)
```

The evaluation plan provides the perturbation fraction or explicit plus/minus values. Central difference is used when both points are valid; otherwise a declared one-sided method may be used and flagged. If `x_ref` or `y_ref` is zero, only a dimensional finite-difference derivative is reported and no normalized rank is implied.

Normalized sensitivity is preferred for outputs with meaningful ratio semantics, including total thermal resistance, temperature rise, and resistance contribution. For absolute temperature, a dimensional derivative may be reported, but the first implementation must not imply a normalized sensitivity ranking by default because the numeric ratio depends on the temperature-scale zero. Any exception requires an explicit definition and interpretation in the evaluation plan.

Sensitivity ranking sorts by descending `abs(S_i)` and then stable field path. The result includes sign, method, points, units, and invalid points. M16A may also report output envelopes from explicit uncertainty-bound sweeps, but it must not describe them as confidence intervals or probabilistic uncertainty propagation.

### 6.7 Model-validity boundary

The 1D model is applicable only when all of the following are explicitly asserted or established by geometry:

- steady state;
- power injected at an explicit source/injection plane, with no volumetric or distributed internal generation;
- one series heat-flow path carrying the declared full power;
- uniform heat flux over a constant cross-sectional area;
- layer properties are constant over the evaluated temperature range;
- interface resistance is represented over the same effective area;
- direct convection, when selected, uses a boundary area equal to the common 1D cross-sectional area;
- an absolute downstream resistance, when selected, has provenance, applicability, and operating-condition basis and is treated only as a black-box boundary;
- a fixed-temperature boundary identifies the explicit terminal plane and adds no hidden resistance;
- the selected conductivity component is aligned with the stack normal;
- a supported downstream boundary is present.

The model is not applicable to directly modeling lateral spreading/constriction, materially different layer footprints, multiple heat sources, parallel heat paths, nonlinear or temperature-dependent properties, transient response, phase change, radiation, fluid flow, or coupled thermomechanics. An externally characterized absolute boundary resistance may encapsulate such downstream physics only as a provenance-bearing black box; the M16A model makes no claim about its internals. Applicability status is `applicable`, `applicable_with_warnings`, or `not_applicable`. `not_applicable` blocks ranking for that model.

### 6.8 Reduced-order spreading resistance

No spreading-resistance correlation is selected for the M16A first implementation. The term “heat spreader” describes the candidate component, not a claim that the 1D model quantifies its lateral benefit. Under strict 1D, a diamond layer may be compared only as a same-area through-plane conduction layer, and the result must warn that real spreading benefit and thickness optimization are unresolved.

The architecture reserves a later `spreading_resistance` model adapter. Adding one requires, before implementation:

- a named, source-backed correlation and exact equation-set version;
- supported source/spreader shapes and centering;
- required source, spreader, and sink dimensions;
- conductivity/isotropy requirements and boundary assumptions;
- published or independently reviewed dimensionless applicability ranges;
- limiting-case and reference-data tests;
- defined behavior outside the validity range;
- a rule preventing double-counting with 1D layer resistance.

Until those conditions are reviewed, lateral area changes produce `not_applicable`, not an estimated spreading angle or hidden empirical factor.

## 7. Engineering Evaluation Result

The proposed `EngineeringEvaluationResult` is a versioned, immutable JSON sidecar containing at least:

```text
result_format_version
evaluation_id
case_id
problem_id
input_reference + input_sha256
evaluation_plan + evaluation_plan_sha256
model_identity
unit_registry_version
applicability_status + applicability_findings
assumptions_used
inputs_used_with_original_and_SI_values
calculated_quantities
node_temperatures
resistance_budget
constraint_results
candidate_results + candidate_ranking
sweep_results
sensitivity_results + sensitivity_ranking
uncertainty_scenarios
missing_evidence
warnings
provenance_references
reproducibility_identity
result_content_sha256
calculation_not_approval_notice
```

Required semantics:

- `evaluation_plan` is the exact canonical plan embedded in the result; `evaluation_plan_sha256` binds it independently of the EPR.
- `model_identity` includes model ID/version, equation-set version, implementation version, and code revision when available.
- `assumptions_used` contains exact EPR field paths, values, sources, rationales, and matching acknowledgements from the embedded Evaluation Plan.
- `applicability_status` and `applicability_findings` record the actual result for the selected model; `not_applicable` produces no thermal calculation or candidate rank.
- `resistance_budget` preserves zero and small contributions rather than rounding them away.
- `constraint_results` records pass, fail, or not-evaluable with margin and source constraint ID.
- `candidate_ranking` includes objective, tie rule, exclusions, and conditionality statement.
- `missing_evidence` distinguishes evaluation-blocking gaps from recommendation-limiting gaps.
- `reproducibility_identity` is the SHA256 of normalized EPR hash, evaluation-plan hash, model-manifest hash, unit-registry version, and deterministic runtime policy.
- The result content hash excludes its own hash field and non-reproducible display metadata.
- The mandatory notice states: “This is a model result, not validation, approval, or a canonical engineering decision.”

## 8. Existing Lab OS Integration

M16A adds quantitative sidecars and does not replace the canonical 12-file case structure.

| Existing Lab OS layer | M16A reuse | Authority boundary |
| --- | --- | --- |
| Canonical case artifacts | Supply requirement context, candidates, constraints, and source hashes. | Compiler reads; it does not rewrite numbered files. |
| Triage | Missing-input and route context can seed compiler gaps. | Triage remains qualitative screening and does not supply numeric defaults. |
| Evidence Objects | Referenced as provenance for properties or used to register a reviewed calculation artifact as `simulation` evidence. | A calculation result begins as unverified/draft and is not validated merely by being linked. |
| Measurement References | Supply reviewed measured quantities where applicable. | The EPR stores IDs/hashes, not raw controlled data. |
| Prediction-Reality Records | Bind a selected result quantity/model/input hash to later measurement evidence. | Comparison does not auto-calibrate a model or change a decision. |
| Decision Board | May display evaluation status, candidate comparison, gaps, and conditional recommendation. | Result ingestion remains read-only preview behavior. |
| Decision Review Package | A future versioned extension may include EPR/result references and hashes. | Export remains separate and non-approving. |
| Human Decision Record | Captures the human disposition after reviewing calculations and evidence. | Solver output cannot populate human attestations or approval fields. |
| Canonical Decision Proposal | May cite an eligible reviewed calculation through a bound Human Decision Record. | Proposal remains unapplied; canonical write remains a separate PR. |
| Hash/provenance infrastructure | Reuse lowercase SHA256, relative paths, source hash maps, and stale-input detection. | Hashes establish identity and traceability, not truth. |
| Engineering memory | May receive a later reviewed reusable lesson. | No automatic memory modification or promotion. |

### Proposed sidecar locations

```text
cases/<case_id>/engineering/problems/EPR-001.json
cases/<case_id>/engineering/evaluations/EER-001.json
```

These locations are accepted for the M16A architecture specification. They remain implementation proposals until M16A implementation is authorized, are not added by this specification task, and stay outside the numbered canonical set like the existing evidence, measurement, and prediction-reality sidecars.

### Approval sequence

```text
canonical case + quantitative authoring inputs
  -> compiled EPR with compilation outcome and findings
  -> Evaluation Plan bound to the EPR hash
  -> Engineering Evaluation Result embedding the plan and its hash
  -> optional draft Evidence Object reference
  -> Decision Board preview
  -> Decision Review Package
  -> Human Decision Record
  -> Canonical Decision Proposal
  -> explicit PR-based canonical application
```

At no point before the final explicit PR application may a calculation modify `02_decision_board.md`, a Claim Ledger state, or engineering memory.

## 9. First Canonical Engineering Workflow

### 9.1 Synthetic requirement

Evaluate a public-safe, synthetic 10 W steady-state heat source over a 2 mm by 2 mm footprint. Compare same-area through-plane diamond and copper thermal-layer candidates above a downstream cooling resistance. Determine whether the modeled source temperature stays at or below a synthetic 75 degrees Celsius limit and identify which uncertain input most affects total resistance.

This is an analytic fixture, not a device-performance claim, material qualification, or recommendation for a real product.

### 9.2 Synthetic input set

| Input | Baseline value | Provenance and uncertainty disposition |
| --- | --- | --- |
| Power | 10 W | Synthetic fixture; exact for test purpose. |
| Footprint | 2 mm x 2 mm | Synthetic fixture; exact for test purpose. |
| Device layer | 100 micrometers, `k_z = 160 W/(m*K)` | Synthetic assumption; unverified; vary if used beyond invariant test. |
| Interface TBR | `5e-9 m^2*K/W` | Synthetic assumption; sweep `2e-9` to `10e-9 m^2*K/W`. |
| Diamond candidate | 300 micrometers, `k_z = 1000 W/(m*K)` | Synthetic assumption; sweep 800 to 1500 `W/(m*K)`. |
| Copper candidate | 300 micrometers, `k_z = 400 W/(m*K)` | Synthetic assumption; no claim about grade or condition. |
| Downstream boundary | 1.5 K/W at 50 degrees Celsius | Synthetic assumption; sweep 0.5 to 2.5 K/W. |
| Temperature limit | 75 degrees Celsius at source plane | Synthetic requirement. |

Each row is encoded as a full quantity envelope; the compact table does not waive that requirement.

### 9.3 Missing-input detection

Before an Evaluation Plan acknowledges the synthetic assumptions, a realistic intake would be held for at least:

- reviewed power and footprint under the intended operating condition;
- normal conductivity values with temperature/grade applicability;
- interface TBR and effective contact area;
- downstream resistance or a supported boundary condition;
- confirmation that the full power follows one constant-area path;
- evidence that 1D is adequate for the decision being asked.

For the synthetic fixture, the evaluation request explicitly acknowledges all synthetic assumptions. The result remains `provisional_synthetic` and retains the same gaps as requirements for any real-case recommendation.

### 9.4 Deterministic baseline evaluation

The area is `4e-6 m^2` and the derived heat flux is `2.5e6 W/m^2`. For the diamond candidate:

| Contribution | Resistance |
| --- | ---: |
| Device layer | 0.15625 K/W |
| Interface | 0.00125 K/W |
| Diamond layer | 0.075 K/W |
| Downstream boundary | 1.5 K/W |
| **Total** | **1.7325 K/W** |

The analytic temperature rise is 17.325 K and the modeled source temperature is 67.325 degrees Celsius. The synthetic baseline passes the 75 degrees Celsius constraint with a 7.675 K margin.

For the same-area 300 micrometer copper candidate, total resistance is 1.845 K/W and modeled source temperature is 68.45 degrees Celsius. Under only these 1D assumptions, the diamond candidate is 1.125 K lower. This delta is a fixture result, not a general diamond performance claim.

### 9.5 Thickness, material, interface, and boundary alternatives

- Diamond thicknesses of 200, 300, and 500 micrometers produce modeled source temperatures of 67.075, 67.325, and 67.825 degrees Celsius under strict constant-area 1D.
- Interface TBR from `2e-9` to `10e-9 m^2*K/W` produces 67.3175 to 67.3375 degrees Celsius for the 300 micrometer diamond candidate.
- Diamond conductivity from 800 to 1500 `W/(m*K)` produces 67.5125 to 67.075 degrees Celsius.
- Downstream resistance from 0.5 to 2.5 K/W produces 57.325 to 77.325 degrees Celsius; the upper point violates the synthetic limit by 2.325 K.

The strict 1D thickness trend reflects only through-plane conduction: greater thickness adds resistance. It cannot predict the competing lateral-spreading benefit of a thicker or wider heat spreader. Therefore, it must not be used to select real heat-spreader thickness without a reviewed spreading model or suitable higher-fidelity evidence.

### 9.6 Sensitivity and evidence-bound recommendation

For total resistance, normalized sensitivity magnitudes of the baseline series contributions are approximately:

1. downstream cooling resistance: 0.866;
2. device-layer thickness or inverse conductivity: 0.090;
3. diamond-layer thickness or inverse conductivity: 0.043;
4. interface TBR: 0.00072.

Power has normalized sensitivity 1.0 for temperature rise when treated as an operating input. Exact finite-difference points and signs must be stored in the result.

The evidence-bound recommendation is: under the synthetic constant-area 1D model, the diamond candidate has lower through-plane resistance than the copper candidate, but the downstream cooling boundary controls the result and can determine constraint failure. Characterize the actual boundary and source conditions first. Do not make a real heat-spreader thickness or lateral-spreading claim until a reviewed spreading model or measurement supports it. Retain both diamond and non-diamond routes for human review.

### 9.7 Evidence and human-review record

1. Store the compiled EPR and EER with its embedded Evaluation Plan, hashes, and model applicability warning.
2. If review warrants, create a draft Evidence Object of type `simulation` pointing to the result hash; do not mark it reviewed automatically.
3. Link later measured temperature through a Measurement Reference and Prediction-Reality Record with the exact input/model identity.
4. Present calculation, gaps, constraint status, and conditional ranking in a Decision Board preview.
5. Export a review package and require a Human Decision Record before any Canonical Decision Proposal.
6. Apply no canonical change or memory update without a separate reviewed PR.

## 10. Architectural Gap Analysis and Proposed Modules

The repository currently has structured case schemas, qualitative triage, evidence sidecars, prediction-reality comparison, Decision Board preview, review packages, decision records, canonical proposals, and reusable SHA256 conventions. It does not yet have a dimensioned quantity system, EPR compiler, thermal equation layer, model registry, evaluation result, parameter sweep, or sensitivity engine.

The cleanest fit is two focused packages plus flat schemas, following the repository's existing feature-package pattern:

```text
labos/
  engineering/
    quantities.py        # quantity envelope, dimensions, SI normalization
    provenance.py        # source and uncertainty validation
    problem.py           # EPR domain models
    compiler.py          # case/input -> immutable EPR + findings
    results.py           # evaluation result domain models
    serialization.py     # canonical decimal/JSON and hashes
  thermal/
    registry.py          # model manifests and version selection
    one_dimensional.py   # explicit 1D equations only
    boundaries.py        # fixed-T, resistance, convection adapters
    validity.py          # model applicability rules
    evaluation.py        # deterministic execution and budgets
    comparison.py        # candidate objectives and conditional ranking
    sensitivity.py       # sweeps and OAT sensitivity
labos/schemas/
  engineering_problem.schema.json
  engineering_evaluation_result.schema.json
```

Recommended integration points:

- Extend `scripts/labos_case.py` later with explicit read/compile/evaluate commands rather than creating a second CLI.
- Reuse result/report dataclass patterns and stable rule IDs from `labos.triage` and `labos.evidence` without importing qualitative rules into physics equations.
- Extract or deliberately reuse the existing source-hash convention so review packages, EPRs, and results agree on relative-path SHA256 semantics.
- Keep model equations independent of filesystem and case parsing; the evaluation layer supplies validated SI quantities.
- Add tests beside the existing `tests/` suite and public-safe fixtures under a new, clearly non-canonical fixture directory selected during implementation review.

Do not create a broad `labos/physics/` namespace yet: there is only one approved quantitative domain. Do not create a generic top-level `models/` package because the repository already uses feature-local `models.py` files, and a generic name would obscure ownership. A material-property registry should not be introduced until its provenance, review, and update authority are separately specified.

## 11. M16A Scope

### In scope

- Architecture and schemas for EPR, compilation findings, model manifests, evaluation plans, and results.
- Dimensioned quantity validation and deterministic SI normalization.
- Public-safe steady-state 1D conduction through a constant-area multilayer stack.
- Area-normalized TBR/contact resistance and supported downstream boundaries.
- Resistance budgets, temperature rise, node temperatures, and constraints.
- Multiple-candidate comparison on a declared common basis.
- Explicit parameter sweeps and deterministic one-at-a-time sensitivity.
- Missing-input, provenance, uncertainty, and model-applicability reporting.
- Hash-bound integration with existing case/evidence/review/decision workflows.
- Synthetic analytic fixtures and physically meaningful invariant tests.
- Architecture contract for, but not selection or implementation of, a future reduced-order spreading model.

### Out of scope

- CAD generation.
- Full finite-element analysis (FEA).
- Computational fluid dynamics (CFD).
- A lateral spreading-resistance correlation in the first implementation.
- MPCVD plasma modeling.
- MPCVD recipe optimization or proprietary process modeling.
- Meshing, geometry repair, or solver orchestration.
- Transient, nonlinear, radiative, fluidic, electrical, RF, stress, or coupled multiphysics models.
- Material-property database population or silent lookup/defaults.
- Model calibration and probabilistic uncertainty quantification.
- MES.
- LIMS.
- Instrument control.
- Autonomous laboratory execution.
- Automatic canonical approval.
- Autonomous memory modification.
- Production UI.
- Multi-agent architecture.
- Customer-specific, supplier-confidential, restricted, or proprietary process data.

## 12. M16A Acceptance and Exit Criteria

M16A exits only when implementation is independently reviewed and the following capabilities are demonstrated. Test count alone is not an exit criterion.

### Engineering capability

- The same normalized EPR, evaluation plan, and model manifest produce byte-identical canonical result content and identical hashes across repeated supported runs.
- Equivalent supported units produce equivalent SI results within the declared decimal/rounding policy, including correct handling of absolute temperature versus temperature difference.
- Missing values, bare physical numbers, incompatible dimensions, conflicting power/flux, and unprovenanced material/interface properties block or warn exactly as specified; no default property is inserted.
- Changing the Evaluation Plan, selected model, or per-evaluation assumption acknowledgements does not change the EPR content hash.
- The EER embeds the exact Evaluation Plan and binds its hash; unacknowledged assumed fields and invalid acknowledgement paths prevent execution.
- The analytic single-layer and multilayer/TBR fixtures reproduce hand-calculated resistance and temperature results.
- At least two material candidates and three thickness or interface alternatives are compared with a declared objective, constraints, exclusions, and stable tie behavior.
- A declared sweep returns every requested point, including invalid-point findings.
- Sensitivity output includes points, method, sign, magnitude, stable ranking, and evidence limitations.
- The result identifies all assumptions, missing evidence, constraint violations, provenance, model identity, applicability status, and reproducibility identity.
- A geometry requiring lateral spreading is rejected by strict 1D or explicitly marked not applicable; it is never evaluated through a hidden area approximation.
- A direct-convection boundary whose area differs from the common 1D cross-sectional area is `not_applicable`.
- Fixed-temperature and black-box absolute-resistance boundaries preserve their declared authority without hidden resistance or claims about unmodeled downstream physics.

### Physically meaningful invariants

- Series resistance equals the sum of layer, interface, and boundary contributions.
- For constant properties, temperature rise is linear with power.
- Doubling one layer's thickness doubles that layer's resistance.
- Doubling the common cross-sectional area halves the absolute `K/W` resistance contribution of each constant-property layer and of an interface having a fixed area-normalized TBR.
- Increasing conductivity cannot increase that layer's resistance.
- Decreasing TBR cannot worsen source temperature under the same valid model.
- Positive power and resistance produce a monotonic source-to-sink temperature drop.
- Reordering constant-area series layers preserves total resistance but changes intermediate node temperatures as expected.
- A zero-TBR interface remains explicit and contributes exactly zero.
- A dominant synthetic boundary-resistance sweep can cross a temperature constraint and produces the correct violation margin.

### Lab OS integration and governance

- A compiled EPR records hashes of the exact numbered canonical case inputs and detects stale inputs.
- An evaluation records EPR, plan, model-manifest, unit-registry, and result hashes using relative public-safe references.
- Draft calculation evidence can be linked to existing Evidence Objects and later Prediction-Reality Records without copying raw controlled data.
- Compilation and evaluation are read-only with respect to all numbered canonical artifacts, Decision Board, Claim Ledger, patterns, and memory.
- The Decision Board/review path preserves the sequence from preview to review package to Human Decision Record to Canonical Decision Proposal.
- No result status, constraint pass, rank, or evidence link can automatically approve a route or apply a canonical proposal.
- At least one canonical public-safe example reproduces the analytic fixture in Section 9 and carries the mandatory no-approval and model-applicability warnings.
- Confidentiality and claim-safety review confirms that examples contain no customer data, restricted process parameters, supplier pricing, or unverified external performance claims.

## 13. Alternatives Considered

| Alternative | Rationale | Disposition |
| --- | --- | --- |
| Add numeric fields directly to the current intake/passport schemas | Fewer new artifacts. | Not selected: it mixes incomplete canonical framing with immutable calculation inputs and weakens hash-bound reproducibility. |
| Start with a broad `physics/` platform | Could host future domains. | Deferred: premature abstraction for one approved quantitative vertical. |
| Start with FEA/CFD | Higher geometric fidelity. | Out of scope: larger validation surface, external tool dependence, and poor fit for the first auditable core. |
| Use a hidden material-property library | Faster authoring. | Rejected: violates the no-silent-assumption requirement and obscures applicability. |
| Select a spreading correlation now | More directly models a heat spreader. | Deferred until a source, validity range, and validation fixtures are independently reviewed. |
| Write results directly into the Decision Board | Shorter workflow. | Rejected: calculation must remain separate from approval. |

## 14. Risks and Controls

| Risk | Control |
| --- | --- |
| False precision from uncertain properties | Preserve source/status/uncertainty, sweep explicit ranges, and label provisional results. |
| Misuse of 1D output as heat-spreading proof | Strict applicability checks and mandatory warning; lateral mismatch blocks the model. |
| Candidate rank treated as approval | Calculation-not-approval notice and existing human review chain. |
| Unit or temperature-offset error | Dimensioned quantities, versioned conversions, and invariant fixtures. |
| Stale or changed case inputs | Source-case hash map and reproducibility identity. |
| Property provenance laundering through memory | No automatic registry or memory update; reviewed Evidence Objects remain distinct. |
| Confidential data entering examples/results | Public-safe fixtures, existing confidentiality checks, and relative/opaque references. |
| Over-abstraction before first vertical works | Focused `engineering` and `thermal` packages; no general multiphysics framework. |

## 15. Review Decisions and Final Approval Checks

### Resolved review decisions

- For non-canonical screening, `READY_WITH_ASSUMPTIONS` does not require a named human reviewer at compiler time. The EPR records assumptions present and requiring acknowledgement; the Evaluation Plan provides exact per-evaluation acknowledgement. This does not constitute engineering approval or remove later human review.
- `cases/<case_id>/engineering/problems/` and `cases/<case_id>/engineering/evaluations/` are accepted as the M16A architecture sidecar locations. They remain proposals until implementation authorization.

### Final contract approval checks

- Confirm that immutable EPR authority is separated from per-evaluation plan choices and acknowledgements, with the exact plan embedded and hash-bound in the EER.
- Confirm that direct convection uses only the common 1D area, while fixed-temperature and provenance-bearing absolute-resistance boundaries retain their defined limited authority.

The source-backed spreading correlation and shared hash-helper selection remain later implementation-review questions; they do not expand or block this architecture contract.

## 16. Review and Confidentiality Checklist

- [x] Architecture is limited to a public-safe diamond thermal-management vertical.
- [x] Quantitative examples are explicitly synthetic analytic fixtures.
- [x] No proprietary growth, bonding, substrate-preparation, equipment, customer, supplier-pricing, or schedule data is included.
- [x] No benchmark result, historical disposition, or frozen artifact is modified or reinterpreted.
- [x] Diamond and non-diamond candidates remain comparable.
- [x] Model limitations and evidence gaps are explicit.
- [x] Calculation is kept separate from approval and memory modification.
- [x] Independent review accepted the core architecture subject to the two final contract fixes.
- [x] Final independent review confirms the EPR / Evaluation Plan / EER authority separation.
- [x] Final independent review confirms the downstream-boundary validity contract.

## 17. Recommended Next Step

After the architecture PR is merged, prepare a separate schema-first M16A implementation task brief with acceptance tests. Implementation execution, solver code, new case artifacts, and canonical decision changes require separate authorization.
