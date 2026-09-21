# Task Brief: M16A-I4 Strict Constant-Area 1D Thermal Kernel

## Document Control

- Lab OS layer: L2 quantitative evaluation contract
- Status: Ready for independent review
- Confidentiality level: Public-safe
- Authorized deliverable: this task brief only
- Implementation status: not authorized by this task
- Required starting main: `922ed113fba26989784d5ae008f83c5882cf3bce`
- Required starting tree: `d2d6f3721b0dcc807da6bc51fb91bcd2839278c8`

## 1. Purpose and Authority

This brief freezes the implementation contract for M16A-I4, the first strict steady-state, constant-area, one-dimensional quantitative thermal kernel. A later implementation MAY execute this brief without selecting new equations, applicability rules, scenario semantics, assumption rules, ranking rules, or version identities.

This document authorizes no solver, runtime, schema, test, or case-artifact change. It MUST NOT be treated as implementation approval, scientific validation, or approval of any candidate architecture.

The implementation objective is to transform one immutable M16A Engineering Problem Representation (EPR) and one valid I3 Evaluation Plan into a reproducible Engineering Evaluation Result (EER) whose core remains governed by I3 and whose model-specific payload makes every requested core and OAT scenario auditable.

## 2. Scope and Non-Goals

### 2.1 In scope for the later I4 implementation

- one strict, steady-state, single-series-path, constant-area thermal-resistance model;
- deterministic selected-model input binding and exact assumed-field acknowledgement closure;
- single-scenario resistance, temperature, node-temperature, and constraint calculations;
- deterministic sweep Cartesian products and explicit per-scenario dispositions;
- the scenario-to-candidate aggregation contract in Section 10;
- conditional candidate comparison and ranking;
- OAT central-difference sensitivity using only I3-authored points;
- normalized EER prediction outputs only when a unique authorized output scenario exists;
- a closed, versioned strict-1D result payload and manifest;
- synthetic/public-safe analytic, negative, invariant, and determinism tests.

### 2.2 Out of scope

The later implementation MUST NOT add or imply:

- lateral spreading or constriction resistance;
- a spreading angle, contact-area correction, fin efficiency, fluid model, radiation model, transient model, phase-change model, or coupled multiphysics model;
- multiple heat sources, power splitting, parallel paths, or inferred heat-flow fractions;
- temperature-dependent properties, property iteration, material-name lookup, or a hidden material database;
- interpolation, adaptive sweep grids, endpoint tolerance, clipping, optimization, or selection of a best sweep point;
- probabilistic uncertainty propagation or confidence intervals;
- an automatic Evidence Object, Human Decision Record, Canonical Decision Proposal, Decision Board update, Claim Ledger update, or engineering-memory update;
- any approval, recommendation, governance-pass, or validation claim.

## 3. Normative Predecessors and Separation

The following are frozen predecessors:

1. `docs/M16A_ENGINEERING_PROBLEM_COMPILER.md` defines the architecture, fundamental strict-1D equations, model-validity boundary, and synthetic fixture.
2. `docs/M16A_I1_QUANTITIES_UNITS_SERIALIZATION_TASK.md` and its implemented contract define QuantityKinds, canonical units, strict decimal strings, exact unit conversions, and canonical JSON.
3. `docs/M16A_I2_EPR_SCHEMA_COMPILER_TASK.md` and its implemented contract define the immutable EPR, complete resolved candidates, quantity envelopes, provenance/status semantics, and candidate identities.
4. `docs/M16A_I3_EVALUATION_PLAN_EER_REPRODUCIBILITY_TASK.md` and its implemented contract define the Evaluation Plan, Model Manifest envelope, EER core, reproducibility identities, assumption acknowledgements, sweep requests, OAT requests, normalized prediction outputs, and Prediction-Reality projection.

I4 MUST NOT change I1 canonical quantity semantics, I2 candidate/EPR semantics, the I3 Evaluation Plan, the I3 EER core status vocabulary, EER identity, model-manifest identity, evaluation-input identity, or historical Prediction-Reality behavior. In particular, I4 MUST NOT add a candidate `partial` execution status. Scenario truth belongs in the I4 payload.

If a structurally invalid Plan, failed EPR, stale EPR, manifest mismatch, unsafe persistence target, or untruthful EER would be rejected by I3, I4 MUST preserve that rejection. Such a failure MUST NOT be converted into a scenario result or arbitrary exception diagnostic.

## 4. Frozen Version and Identity Proposals

The first implementation SHALL use these exact values:

| Identity | Exact value |
| --- | --- |
| `model_manifest_format_version` | `m16a-model-manifest-1.0` |
| `model_id` | `m16a-strict-1d-thermal` |
| `model_version` | `1.0.0` |
| `equation_set_version` | `m16a-strict-1d-equations-1.0` |
| `implementation_version` | `m16a-strict-1d-runtime-1.0` |
| `applicability_policy_version` | `m16a-strict-1d-applicability-1.0` |
| `numerical_policy_version` | `m16a-strict-1d-decimal-1.0` |
| `input_binding_policy_version` | `m16a-strict-1d-input-binding-1.0` |
| `serialization_policy_version` | `m16a-canonical-json-1.0` |
| `result_payload_schema_id` | `m16a-strict-1d-result` |
| `result_payload_schema_version` | `1.0` |
| payload-content identity authority | The exact pair `result_payload_schema_id = m16a-strict-1d-result` and `result_payload_schema_version = 1.0` inside the unchanged I3 result-payload hash projection. |
| scenario/aggregation policy | `m16a-strict-1d-scenario-aggregation-1.0` |
| constraint policy | `m16a-strict-1d-constraints-1.0` |
| comparison/ranking policy | `m16a-strict-1d-ranking-1.0` |
| OAT policy | `m16a-strict-1d-oat-1.0` |

An incompatible change to equations, operation order, working precision, applicability, input binding, scenario enumeration, aggregation, constraint evaluation, ranking, OAT arithmetic, prediction-output selection, or payload meaning MUST change the owning version. A code-only change that can change authoritative output MUST change `implementation_version`. `implementation_git_commit` SHALL be the later implementation commit when known and otherwise null, exactly as I3 permits.

The strict-1D model-specific payload contract is versioned by the exact result-payload schema ID/version declared in the Model Manifest. No additional wrapper hash field is introduced.

## 5. Model Manifest Contract

### 5.1 Applicability rule IDs

`applicability_rule_ids` SHALL be the following lexically ordered values:

```text
I4-APP-CONSTANT-AREA
I4-APP-CONSTANT-PROPERTIES
I4-APP-CONVECTION-COMMON-AREA
I4-APP-EXPLICIT-SOURCE-PLANE
I4-APP-FULL-POWER-PATH
I4-APP-INTERFACE-COMMON-AREA
I4-APP-NO-COUPLED-PHYSICS
I4-APP-NO-DISTRIBUTED-GENERATION
I4-APP-NO-LATERAL-MISMATCH
I4-APP-NO-TEMPERATURE-LAW
I4-APP-NORMAL-CONDUCTIVITY
I4-APP-SINGLE-HEAT-SOURCE
I4-APP-SINGLE-SERIES-PATH
I4-APP-STEADY-STATE
I4-APP-SUPPORTED-BOUNDARY
I4-APP-SUPPORTED-INTERFACE
I4-APP-UNIFORM-SURFACE-SOURCE
```

### 5.2 Required and prohibited feature vocabulary

Manifest feature strings are semantic feature identifiers, not substitute EPR values. Arrays MUST be unique and lexically ordered.

`required_input_features` SHALL contain:

```text
candidate.boundary.downstream.supported
candidate.boundary.source_side.full_power_single_path
candidate.geometry.constant_area_ordered_stack
candidate.interfaces.same_area_tbr
candidate.materials.explicit_normal_constant_conductivity
global.constraints.explicit_applicable_set
global.heat_source.single_uniform_steady_surface_source
global.model_options.strict_1d_validity_assertions
global.objective.explicit_metric_direction_reference
```

`prohibited_input_features` SHALL contain:

```text
candidate.boundary.hidden_area_or_fin_correction
candidate.geometry.lateral_spreading_or_constriction
candidate.interfaces.unsupported_representation
candidate.materials.rotated_tensor_or_temperature_law
global.heat_source.distributed_or_multiple
global.physics.coupled
global.physics.fluid_or_radiation
global.physics.parallel_path_or_power_split
global.physics.transient
```

### 5.3 Quantity kinds and canonical units

`accepted_quantity_kinds` SHALL contain these lexically ordered I1 kinds, and `canonical_units` SHALL map them exactly as shown:

| QuantityKind | Canonical unit |
| --- | --- |
| `absolute_temperature` | `K` |
| `absolute_thermal_resistance` | `K/W` |
| `area` | `m^2` |
| `area_thermal_conductance` | `W/(m^2*K)` |
| `area_thermal_resistance` | `m^2*K/W` |
| `length` | `m` |
| `physical_dimensionless` | `1` |
| `power` | `W` |
| `temperature_difference` | `K` |
| `thermal_conductivity` | `W/(m*K)` |

Heat flux is not a model input in v1. The model SHALL consume the EPR `total_power`; it MUST NOT substitute or rederive power from heat flux.

### 5.4 Known limitations and references

`known_limitations` SHALL contain these exact lexically ordered strings:

```text
Black-box absolute boundary resistance is consumed without a claim about its internal physics.
Calculation is not validation, approval, recommendation, or a canonical engineering decision.
The model cannot quantify coupled physics, fluid flow, lateral spreading or constriction, phase change, radiation, spatially varying sink temperature, or transient response.
The model requires one steady-state source, one full-power series path, one constant area, and constant layer properties.
```

`source_references` SHALL contain only these lexically ordered internal references:

```text
docs/M16A_ENGINEERING_PROBLEM_COMPILER.md#6.2
internal-normative-reference:steady-state-fourier-conduction-and-series-energy-balance
```

No spreading or empirical-correlation source SHALL appear because no such correlation is implemented.

## 6. Exact Equations and Boundary Semantics

For common area `A`, source power `P`, layer thickness `t_i`, normal conductivity `k_i`, interface area-normalized thermal boundary resistance `TBR_j`, direct-convection coefficient `h`, and boundary area `A_boundary`, the equation set is exactly:

```text
R_layer_i     = t_i / (k_i * A)
R_interface_j = TBR_j / A
R_convection  = 1 / (h * A_boundary)
A_boundary    = A                         when direct convection is selected
R_total       = sum(R_layer_i)
              + sum(R_interface_j)
              + R_boundary
delta_T       = P * R_total
T_source      = T_reference + delta_T
```

`R_boundary` is exactly one of:

- zero for `fixed_temperature`, whose explicit terminal-plane temperature is `T_reference`;
- the supplied provenance-bearing `absolute_thermal_resistance` for `absolute_resistance`, with its supplied `reference_temperature` as `T_reference`; or
- `R_convection` for `direct_convection`, with supplied `ambient_temperature` as `T_reference`.

The first implementation supports interface `representation_type` values `area_normalized_resistance` and `ideal_zero` only. `ideal_zero` MUST carry an explicit zero `area_thermal_resistance` value and contributes exact zero. `absolute_resistance` and `area_normalized_conductance` are valid EPR representations but are outside this equation-set version and therefore make the strict-1D scenario `not_applicable`. The evaluator MUST NOT convert them silently.

The ordered series-element chain is each layer in increasing `(order, layer_id)`, followed immediately by the interface whose upstream layer is that layer, with the boundary contribution last. Layer sums and interface sums are nevertheless formed separately in the exact operation order in Section 8.

Node `NODE-000` is the source/injection plane. Each following node is the plane after one ordered series element; the final node is the explicit boundary reference plane. Node temperature before element `j` is `T_reference + P * sum(elements[j:])`, using the reverse-fold order in Section 8. The final node equals `T_reference` exactly. Fixed-temperature boundary resistance remains an explicit zero boundary contribution and does not create a hidden temperature drop.

No other thermal equation or correction is permitted.

## 7. Applicability and Execution Preconditions

### 7.1 Required strict-1D truth

Each scenario is applicable only when all of the following are established by the bound EPR and the exact Plan assertions below:

1. Exactly one EPR heat source exists.
2. Its `operating_mode` is `steady_state` and `spatial_profile` is `uniform_surface`.
3. Its `source_location.location_type` is `source_side`, and its `layer_id` is the first ordered candidate layer.
4. Heat is injected at that explicit plane; generation is not volumetric or distributed.
5. The candidate is one ordered series path and `source_side.path_disposition` is `adiabatic_other_paths`.
6. `source_side.heat_flow_fraction` is exactly `1`.
7. The source heated area, every layer footprint area, every interface effective area, and any direct-convection boundary area equal one positive common area exactly after I1 canonical conversion.
8. The source footprint dimensions and every layer footprint-dimension array have the same length and equal canonical values in the same order. No equal-area-but-different-footprint inference is allowed.
9. Each layer has a positive thickness and one explicit positive conductivity component normal to the stack.
10. Isotropic material uses exactly one `component: isotropic` property. `principal_components` uses exactly one `x`, `y`, or `z` property equal to the layer `stack_normal_axis`, and `rotation_description` is null. `rotated_tensor`, `other`, off-axis, ambiguous, or duplicate normal components are not applicable.
11. Layer properties are constant for the evaluated range; no temperature-dependent law or iteration is required.
12. Each adjacency has exactly one supported same-area interface. No missing adjacency or extra parallel interface exists.
13. The downstream boundary is `fixed_temperature`, provenance-bearing `absolute_resistance`, or same-area `direct_convection`.
14. There are no multiple sources, parallel paths, unmodeled power splits, lateral spreading/constriction requirements, transient effects, phase change, radiation, fluid-temperature rise, fluid solving, spatially varying sink temperature, or coupled physics.

A lateral size mismatch or any requirement for spreading/constriction is `not_applicable`; it MUST NOT be approximated. A direct-convection area mismatch is `not_applicable`. Multiple heat sources, declared parallel paths, temperature-dependent material laws, and prohibited physics are `not_applicable`.

An unsupported downstream `representation_type: other` is `not_applicable`. A supported boundary whose required numeric envelope is missing/conflicting, whose acknowledgement is missing, or whose numerical prerequisite is nonphysical is `blocked`. This distinction is fixed: physics outside the model is `not_applicable`; unavailable or unusable required input inside the model is `blocked`, except that an explicitly requested nonphysical sweep/OAT override is `invalid` under Section 9.4.

### 7.2 Closed model options

I4 v1 SHALL accept exactly this `model_options` shape and no additional key:

```json
{
  "strict_1d_validity_assertions": {
    "constant_layer_properties_over_evaluated_range": true,
    "no_coupled_physics": true,
    "no_fluid_or_radiation_model": true,
    "no_temperature_dependent_material_law": true,
    "no_unrepresented_parallel_paths_or_power_splits": true
  }
}
```

Every value MUST be the JSON boolean `true`. Missing, false, non-boolean, or extra assertion keys block execution before arithmetic. These assertions are calculation-scope declarations bound by Plan identity; they are not evidence, validation, or approval and MUST NOT mutate EPR status.

### 7.3 Numeric preconditions

All required base values MUST be present, finite I1 canonical Decimals of the required QuantityKind and unit. Power, common area, thickness, conductivity, and convection coefficient MUST be greater than zero. TBR and supplied absolute boundary resistance MUST be greater than or equal to zero. Absolute temperature MUST be greater than or equal to zero kelvin. Heat-flow fraction MUST equal one.

No default conductivity, thickness, TBR, area, power, boundary resistance, convection coefficient, temperature, heat split, property orientation, or material property is permitted. Labels and material names have no numeric authority.

## 8. Decimal Numerical Policy

All physics and comparison arithmetic SHALL use `decimal.Decimal`; a `float` MUST NOT enter model arithmetic, fixture construction, conversion, comparison, ranking, or serialization.

The local working context is fixed as:

```text
precision: 50 significant decimal digits
rounding: ROUND_HALF_EVEN
Emin: -999999
Emax: 999999
capitals: 1
clamp: 0
trapped: InvalidOperation, DivisionByZero, Overflow
not trapped: Inexact, Rounded, Subnormal, Underflow
```

Inputs SHALL first be reconstructed from I1 canonical decimal strings. Unit conversion remains I1 authority and MUST occur before the model context is entered. Terminating operations that fit the context remain exact. A non-terminating division is rounded only by the fixed 50-digit working context; there is no quantization, display rounding, or significant-digit trimming of intermediate or authoritative output values.

The exact operation order is:

1. For each layer in canonical layer order, calculate `k_i * A`, then `t_i / product`.
2. For each interface in canonical adjacency order, calculate `TBR_j / A`.
3. For direct convection, calculate `h * A`, then `1 / product`; otherwise bind the exact zero or supplied boundary resistance.
4. Left-fold layer resistance from `Decimal(0)` in layer order.
5. Left-fold interface resistance from `Decimal(0)` in interface order.
6. Calculate `(layer_sum + interface_sum) + boundary_resistance`.
7. Calculate `P * R_total`.
8. Calculate `T_reference + delta_T`.
9. Calculate contribution fractions in series-element order by `R_element / R_total`.
10. Calculate node temperatures by a reverse right-to-left cumulative resistance fold, then `T_reference + P * cumulative_resistance` at each node.
11. Evaluate constraints, objective values, comparison, and sensitivity only after scenario physics is complete.

The scenario result SHALL record `numerical_exactness` as `exact` when no operation set the Decimal `Inexact` or `Rounded` flag and `context_rounded` otherwise. Context rounding is reproducible numerical metadata, not by itself an applicability warning. All authoritative Decimals SHALL serialize through I1 canonical decimal-string rules with their full working value. Negative zero SHALL serialize as canonical zero. No separate display-rounded number is authoritative.

## 9. Input Binding, Paths, and Assumption Closure

### 9.1 Path authority

Each consumed path record is a closed object:

```text
scope: candidate | global
candidate_id: CND-### | null
field_path: RFC 6901 pointer relative to the resolved candidate or global EPR
```

Candidate paths are relative to the selected resolved candidate. Global paths are relative to the EPR root. Records sort by scope with global first, candidate ID with null first, then lexical RFC 6901 path. The same path MUST appear once.

### 9.2 Deterministic consumed paths

Before arithmetic, each scenario SHALL derive its exact `consumed_input_paths`. The set includes the structural discriminator paths inspected and the numeric envelope paths consumed. At minimum it SHALL include:

- global `/heat_sources` cardinality and, for index `0`, `/heat_sources/0/source_location/layer_id`, `/heat_sources/0/source_location/location_type`, `/heat_sources/0/total_power`, `/heat_sources/0/heated_area`, every `/heat_sources/0/footprint/dimensions/<index>`, `/heat_sources/0/spatial_profile`, and `/heat_sources/0/operating_mode`;
- global `/requirements/<index>/target` and `/requirements/<index>/target_path` only when the objective references that exact requirement;
- global `/constraints/<index>` only for IDs in the candidate's `applicable_constraint_ids`;
- candidate `/geometry/layers`, and for each canonical layer index: `/geometry/layers/<index>/layer_id`, `/order`, `/material_id`, `/thickness`, every `/footprint_dimensions/<index>`, `/footprint_area`, `/orientation/stack_normal_axis`, and `/orientation/rotation_description`;
- candidate `/materials`, and for each material/property selected by a layer: `/materials/<index>/material_id`, `/anisotropy_representation`, `/thermal_properties/<index>/property_id`, `/component`, `/thermal_conductivity`, `/temperature_basis`, and `/condition_basis`;
- candidate `/interfaces`, and for each interface: `/interfaces/<index>/interface_id`, `/upstream_layer_id`, `/downstream_layer_id`, `/representation_type`, `/value`, `/effective_area`, and `/condition_basis`;
- candidate `/boundary_conditions/source_side/heat_flow_fraction` and `/boundary_conditions/source_side/path_disposition`;
- candidate `/boundary_conditions/downstream/representation_type` plus the exact fields of the selected variant: `terminal_plane` and `reference_temperature`; or `resistance`, `reference_temperature`, and `operating_basis`; or `heat_transfer_coefficient`, `boundary_area`, `ambient_temperature`, and `operating_basis`.

The actual numeric indices come from frozen EPR canonical order; dictionary iteration MUST NOT select or order inputs. A sweep or OAT override does not change the consumed path: it changes only that path's numeric value for the scenario.

### 9.3 Envelope status and acknowledgement closure

For each consumed numeric envelope:

- `provided` with a value is executable;
- `assumed` with a value is executable only with an exact matching I3 acknowledgement;
- `evidence_required` with a value is executable with deterministic warning `I4-BIND-EVIDENCE-REQUIRED` and is never acknowledged as assumed;
- `missing` or `conflicting`, or a null required value, blocks the scenario before arithmetic.

For each candidate, derive the required acknowledgement set as every candidate/global consumed envelope path whose bound EPR envelope has `status: assumed`. Scenario overrides retain status and therefore do not remove an acknowledgement requirement. Supplied and required acknowledgement sets MUST be exactly equal at the model-bound closure:

- a missing candidate-scoped acknowledgement blocks that candidate's affected scenarios before arithmetic;
- an extra candidate-scoped acknowledgement blocks that candidate before arithmetic;
- a missing global acknowledgement blocks every scenario that consumes it;
- a supplied global acknowledgement not required by the union of any selected candidate/core/OAT execution blocks the requested evaluation before arithmetic;
- a global acknowledgement required by one candidate but not another is not considered extra for the other candidate.

No blocked scenario may claim an acknowledgement as used merely because closure inspected it. Each evaluated scenario records exactly the acknowledgements for assumed inputs it actually consumed. Candidate `assumption_acknowledgements_used` is the canonical union across its evaluated core and OAT scenarios; top-level EER `assumptions_used` is the canonical union across evaluated candidates, as I3 requires. An extra non-consumed acknowledgement MUST NOT appear in either used set. I4 MUST NOT acknowledge automatically or change the EPR envelope status.

## 10. Scenario Model and Aggregation

### 10.1 Core scenarios

For each selected candidate:

- with no parameter sweep targeting it, the core set is exactly one baseline scenario with no override;
- with one or more parameter sweeps, the core set is exactly the I3 Cartesian product and contains no automatically added baseline;
- a baseline value appears in a swept core set only when explicitly authored as one requested point.

Sweeps for a candidate are ordered by their canonical Plan order. The first sweep is the outermost/slowest-varying dimension and the last is the innermost/fastest-varying dimension. Within each sweep, explicit-grid order or exact I3-generated range order is authoritative. Candidate order is `selected_candidate_ids` order. Every requested combination receives one record and disposition.

Core scenario IDs are `SCN-C<ccc>-K<ssssss>`, where `<ccc>` is the one-based selected-candidate position padded to three digits and `<ssssss>` is the one-based core-scenario position padded to six digits. The unswept baseline is `K000001`. The record also carries the actual `candidate_id`; ordinal IDs MUST NOT replace semantic binding.

### 10.2 Auxiliary OAT scenarios

OAT is evaluated around the baseline candidate's resolved EPR values, not around a sweep point. It does not form a Cartesian product with sweeps. One explicitly represented shared reference scenario and two point scenarios per canonical parameter are requested:

```text
SCN-C<ccc>-O000-REF
SCN-C<ccc>-O<ppp>-MINUS
SCN-C<ccc>-O<ppp>-PLUS
```

`<ppp>` is the one-based position in canonical `field_path` order. Each OAT record carries the exact `field_path` and side; the semantic identity tuple is `(candidate_id, field_path, side)`. Ordering is reference first, then field-path order, minus before plus.

If the candidate has no sweeps and its core baseline is evaluated, the OAT reference record SHALL explicitly point to and reuse that core result without duplicate arithmetic. Otherwise the reference SHALL be an explicitly recorded auxiliary evaluation of the resolved baseline. `requested_oat_points` is exactly `1 + 2 * parameter_count`, including the reference record, and MUST equal the actual OAT scenario-record count.

OAT scenarios belong to the requested analysis but do not establish candidate `result_presence`, do not make a candidate evaluated when no core scenario produced a result, and do not make an ineligible candidate rankable. Incomplete, invalid, not-applicable, or warning-bearing OAT work makes an otherwise evaluated candidate `applicable_with_warnings`.

### 10.3 Scenario dispositions

Every core and OAT scenario SHALL have exactly one disposition:

| Disposition | Exact meaning |
| --- | --- |
| `evaluated` | The strict-1D model is applicable and a complete numerical scenario result exists. |
| `blocked` | A required model-bound input, acknowledgement, numerical prerequisite, assertion, or execution precondition was not satisfied. |
| `not_applicable` | The scenario violates the strict-1D physical validity contract. |
| `invalid` | An explicitly requested sweep/OAT override or mathematical request is itself invalid for execution. |

`invalid` is not `not_applicable`; for candidate aggregation it belongs to the blocked class. A nonphysical bound baseline input is `blocked`. The same nonphysical value introduced by an explicit sweep/OAT override is `invalid`. No requested scenario may be omitted.

### 10.4 Candidate aggregation truth table

Aggregation uses core scenarios only for `execution_status` and `result_presence`:

| Core result set | `execution_status` | `applicability_status` | `result_presence` |
| --- | --- | --- | --- |
| At least one `evaluated`; every core evaluated without applicability warning and all requested OAT complete without applicability/execution warning | `evaluated` | `applicable` | `true` |
| At least one `evaluated`; any other core is blocked, invalid, not applicable, or warning-bearing, or any OAT work is incomplete/invalid/not applicable/warning-bearing | `evaluated` | `applicable_with_warnings` | `true` |
| No evaluated core and all core scenarios `not_applicable` | `not_applicable` | `not_applicable` | `false` |
| No evaluated core and at least one core is `blocked` or `invalid`, regardless of simultaneous `not_applicable` core scenarios | `blocked` | `not_evaluated` | `false` |

Successful numerical results MUST NOT be discarded because another scenario failed. No candidate-level `partial` value exists.

The I3 candidate-execution record SHALL be assembled directly from this table. Its `applicability_findings` is the canonical union of that candidate's scenario applicability findings plus `I4-SCENARIO-PARTIAL-COVERAGE` when required. Its `assumption_acknowledgements_used` is the union defined in Section 9.3. `result_presence` is not inferred from OAT data.

### 10.5 Top-level execution outcome

I4 SHALL preserve I3 derivation, interpreted through the core aggregation above:

- `completed`: every selected candidate has at least one evaluated core scenario;
- `partial`: at least one selected candidate has an evaluated core result and at least one selected candidate has no evaluated core result;
- `not_evaluated`: no selected candidate has an evaluated core result.

`completed` does not mean every core or OAT scenario completed. Whenever an evaluated candidate has a non-evaluated or warning-bearing requested core/OAT scenario, candidate and top-level warnings SHALL include stable rule ID `I4-SCENARIO-PARTIAL-COVERAGE`, pointing to that candidate's coverage summary. This warning is required even when top-level `execution_outcome` is `completed`.

### 10.6 Coverage summary

Each candidate payload SHALL contain:

```text
requested_core_scenarios
evaluated_core_scenarios
blocked_core_scenarios
invalid_core_scenarios
not_applicable_core_scenarios
oat_coverage: null | {
  requested_oat_points
  evaluated_oat_points
  blocked_oat_points
  invalid_oat_points
  not_applicable_oat_points
}
```

Core disposition counts MUST sum to `requested_core_scenarios` and equal the actual core records. OAT counts MUST sum to `requested_oat_points` and equal the actual OAT records. There is no hidden scenario execution and no omitted failed point.

## 11. Sweep Contract

I4 SHALL use the exact I3-expanded points, Plan sweep order, point order, per-candidate Cartesian product, and maximum-combination validation. It MUST NOT sort point values, generate a baseline, interpolate, adapt the grid, clip a point, correct a step sign, snap an endpoint, or apply a tolerance.

A scenario override replaces only the target envelope's numeric `value` for that scenario. It MUST NOT change provenance, uncertainty, confidence, status, QuantityKind, unit authority, conversion authority, candidate structure, candidate hash, or EPR hash. The scenario record SHALL retain `sweep_id`, target `field_path`, canonical point value, and point ordinal for every coordinate.

Structural/non-numeric fields are not valid sweep targets. A value with the wrong QuantityKind/unit is rejected by I3 before execution. A correctly typed but nonphysical explicit point is retained as `invalid` in I4.

## 12. OAT Sensitivity Contract

I4 SHALL use only the I3 `baseline_candidate_id`, `output_metric`, canonical parameter order, and explicit `minus_value`/`plus_value`. It MUST NOT generate a percentage, perturbation, substitute point, or one-sided method.

For each parameter, let `x_ref` be the resolved baseline canonical value, and let `y_ref`, `y_minus`, and `y_plus` be the requested metric from evaluated reference, minus, and plus scenarios. Only when all three scenarios are evaluated and `x_plus != x_minus` SHALL I4 calculate:

```text
dimensional_derivative = (y_plus - y_minus) / (x_plus - x_minus)
normalized_sensitivity = dimensional_derivative * (x_ref / y_ref)
```

The dimensional derivative uses the output unit divided by the parameter unit. It MAY be reported when `x_ref == 0` or `y_ref == 0`, provided the three scenario values and denominator are valid. Normalized sensitivity SHALL be null with an explicit reason when `x_ref == 0` or `y_ref == 0`.

Normalized sensitivity is supported in v1 for `total_thermal_resistance` and `temperature_margin` only. For `source_temperature`, the dimensional derivative MAY be reported, but normalized sensitivity SHALL be null with reason `absolute_temperature_not_normalized`. No absolute-temperature normalized ranking is permitted.

If the reference or either required point is unavailable, both the central derivative and normalized value SHALL be null; the parameter disposition is `incomplete`; the exact unavailable scenario IDs and findings SHALL be recorded. There is no one-sided fallback. A parameter result is `complete` only when the central dimensional derivative exists. OAT ranking contains only complete parameters with defined normalized sensitivity and sorts by descending absolute normalized sensitivity, then lexical canonical field path. An empty eligible set yields `ranking_status: not_performed`.

## 13. Constraint Semantics

Each applicable candidate constraint receives one result in constraint-ID order:

```text
constraint_id
scenario_id
status: pass | fail | not_evaluable
evaluated_quantity: typed quantity | null
limit: typed quantity | null
margin: typed quantity | null
operator
finding_ids
```

I4 v1 machine-evaluates a source-temperature constraint only when:

- `evaluation_disposition` is `machine_evaluable`;
- `target_path` is exactly `/heat_sources/0/source_location`;
- threshold kind is `absolute_temperature`; and
- operator is `lt`, `le`, `eq`, `ge`, or `gt`.

For `le`/`lt`, margin is `limit - evaluated`; for `ge`/`gt`, margin is `evaluated - limit`; for `eq`, margin is `-abs(evaluated - limit)`. Pass/fail follows the exact operator, so equality fails `lt`/`gt` even when margin is zero. Margin kind is `temperature_difference`, unit `K`. Other constraint targets/operators, `review_only`, missing thresholds, or incompatible kinds are `not_evaluable` with a stable finding; they are not silently scored.

A blocked, invalid, or not-applicable scenario MUST report each applicable constraint as `not_evaluable` with null evaluated quantity and margin. It MUST NOT fabricate pass/fail.

For objective `temperature_margin`, `reference_requirement_id` MUST resolve to the exact EPR requirement, its target MUST be a usable `absolute_temperature`, and its `target_path` MUST equal `/heat_sources/0/source_location`. The objective value is `requirement target - source_temperature`, kind `temperature_difference`, unit `K`. Any assumed target participates in acknowledgement closure. No other requirement is substituted.

## 14. Candidate Comparison and Ranking

A candidate is eligible for ranking only when:

1. it is `evaluated` and the exact objective result exists;
2. its ranking-basis scenario is evaluated and applicable;
3. it has an unambiguous, comparable basis; and
4. `exclude_violating_from_rank` does not exclude it for any failed machine-evaluable applicable constraint.

For I3 Plan v1, the sole unswept baseline scenario is the only authorized comparison basis. Any candidate targeted by any sweep is ineligible for candidate-level ranking, even if the Cartesian product has one combination or contains its baseline value, because Plan v1 has no reference-scenario selector. I4 MUST NOT choose a best, first, median, nominal, or baseline-looking sweep point by inference.

Eligible candidates sort by the declared objective direction, then lexical stable `candidate_id` for an exact objective tie. `report_only` retains constraint-violating candidates with visible constraint status. `exclude_violating_from_rank` excludes a candidate when its basis scenario has any failed machine-evaluable applicable constraint, regardless of constraint severity; severity remains visible and is not rewritten. Blocked/not-applicable candidates have no rank. An `applicable_with_warnings` candidate MAY rank when its ranking-basis scenario is valid and comparable; its warnings remain visible.

`candidate_comparison.ranking_status` is `performed` only when at least two candidates are eligible; otherwise it is `not_performed`. Every selected candidate receives an eligibility/exclusion record. Ranking is a conditional calculation, not a recommendation or approval.

## 15. Prediction-Output Basis

Only an EER candidate execution record with `execution_status: evaluated` and `result_presence: true` may own normalized `prediction_outputs`. Each output MUST point to an actual evaluated model-specific numerical value.

For I3 Plan v1, the unique output scenario is the sole unswept baseline core scenario. A swept candidate has no normalized candidate-level prediction output because the Plan cannot identify a unique semantically authorized reference scenario. I4 MUST NOT select a best or baseline-looking sweep point.

For each eligible unswept baseline, emit exactly three outputs in candidate order and this metric order:

1. `source_temperature`, kind `absolute_temperature`, unit `K`;
2. `temperature_rise`, kind `temperature_difference`, unit `K`;
3. `total_thermal_resistance`, kind `absolute_thermal_resistance`, unit `K/W`.

Bounds are null because I4 v1 performs no uncertainty propagation. Output IDs follow I3 numeric suffix order. `result_pointer` SHALL resolve to the corresponding value in that candidate's baseline core scenario. A failed OAT point does not remove valid baseline prediction outputs; a failed/absent baseline does.

## 16. Closed Model-Specific Result Payload

The I3 result-payload wrapper remains unchanged. For strict-1D v1, `schema_id` SHALL equal `m16a-strict-1d-result`, `schema_version` SHALL equal `1.0`, and both values SHALL equal the corresponding Model Manifest values. `content_sha256` SHALL equal the existing frozen I3 `result_payload_content_sha256` projection:

```text
canonical_sha256({
    "schema_id": "m16a-strict-1d-result",
    "schema_version": "1.0",
    "content": <exact strict-1D content object>
})
```

The hash projection MUST NOT include `result_payload_content_identity_version` as a fourth hash-domain field. I4 SHALL reuse the existing I3 wrapper hash semantics unchanged and MUST NOT special-case or modify the I3 validator. The strict-1D model-specific semantic identity/version is carried through the Model Manifest model/version fields, `result_payload_schema_id`, `result_payload_schema_version`, the exact closed `content`, `model_manifest_sha256`, `evaluation_input_sha256`, and EER content identity. This correction does not weaken result reproducibility.

Compatibility invariant: a strict-1D result payload produced by I4 MUST pass the existing frozen I3 `EngineeringEvaluationResult` result-payload hash validation without any modification to I3 runtime. The same payload wrapper passed to the existing public `result_payload_content_sha256(...)` MUST produce exactly the persisted `content_sha256`. No duplicate I4-specific wrapper hash is permitted.

The closed `content` object SHALL contain exactly:

```text
scenario_policy_version
constraint_policy_version
ranking_policy_version
oat_policy_version
candidate_results
candidate_comparison
findings
warnings
```

`candidate_results` follows selected-candidate order. Each record contains exactly:

```text
candidate_id
coverage_summary
core_scenarios
sweep_result
oat_result
findings
warnings
```

`sweep_result` is null for an unswept candidate; otherwise it records ordered sweep IDs, ordered field paths, Cartesian-order declaration, and ordered core scenario IDs without duplicating numerical results. `oat_result` is null when OAT does not target the candidate; otherwise it contains the method, output metric, reference scenario record, parameter results in field-path order, point scenario records, derivative results, normalized-sensitivity disposition, and ranking.

The following closed helper shapes are normative:

```text
result_quantity = {
  value: canonical Decimal string,
  unit: I1 canonical unit,
  quantity_kind: I1 QuantityKind
}

consumed_path = {
  scope: global | candidate,
  candidate_id: null | CND-###,
  field_path: RFC 6901 pointer
}

sweep_coordinate = {
  sweep_id: SWP-###,
  field_path: RFC 6901 pointer,
  point_ordinal: positive one-based integer,
  value: result_quantity
}

input_override = {
  source_kind: sweep | oat,
  source_id: SWP-### | null,
  field_path: RFC 6901 pointer,
  point_ordinal: positive one-based integer,
  side: null | minus | plus,
  value: result_quantity
}

oat_coordinate = null | {
  parameter_ordinal: non-negative integer,
  field_path: null | RFC 6901 pointer,
  side: reference | minus | plus
}
```

An OAT reference uses `parameter_ordinal: 0`, `field_path: null`, and `side: reference`. A core baseline has empty `sweep_coordinates` and `input_overrides`; an OAT reference has empty `input_overrides`. Diagnostics and acknowledgement records reuse the exact I3 closed shapes.

Every scenario record contains exactly:

```text
scenario_id
scenario_kind: core | oat_reference | oat_minus | oat_plus
candidate_id
sweep_coordinates
oat_coordinate
input_overrides
disposition
applicability_status
reused_core_scenario_id
consumed_input_paths
assumption_acknowledgements_used
applicability_findings
execution_findings
constraint_results
numerical_result
```

`applicability_status` uses the I3 values `applicable`, `applicable_with_warnings`, `not_applicable`, and `not_evaluated`. An evaluated scenario is `applicable` unless it has an applicability/execution warning, in which case it is `applicable_with_warnings`; a `not_applicable` scenario is `not_applicable`; and a `blocked` or `invalid` scenario is `not_evaluated`. `reused_core_scenario_id` is null except for an OAT reference that reuses the evaluated unswept core baseline; in that case it equals that core scenario ID and the copied numerical result MUST be byte-equivalent. `numerical_result` is non-null if and only if disposition is `evaluated` and contains exactly:

```text
common_area
source_power
reference_temperature
layer_resistance_contributions
interface_resistance_contributions
boundary_resistance_contribution
total_thermal_resistance
temperature_rise
source_temperature
node_temperatures
numerical_exactness
```

The nested numerical shapes are exactly:

```text
layer_resistance_contribution = {
  layer_id,
  material_id,
  property_id,
  thickness: result_quantity,
  normal_conductivity: result_quantity,
  area: result_quantity,
  resistance: result_quantity,
  fraction_of_total: result_quantity
}

interface_resistance_contribution = {
  interface_id,
  upstream_layer_id,
  downstream_layer_id,
  tbr: result_quantity,
  area: result_quantity,
  resistance: result_quantity,
  fraction_of_total: result_quantity
}

boundary_resistance_contribution = {
  boundary_id: "BND-DOWNSTREAM",
  representation_type: fixed_temperature | absolute_resistance | direct_convection,
  supplied_resistance: null | result_quantity,
  heat_transfer_coefficient: null | result_quantity,
  boundary_area: null | result_quantity,
  resistance: result_quantity,
  fraction_of_total: result_quantity
}

node_temperature = {
  node_id: NODE-<nnn>,
  node_role: source | internal | reference,
  upstream_element_id: null | layer/interface ID | BND-DOWNSTREAM,
  downstream_element_id: null | layer/interface ID | BND-DOWNSTREAM,
  temperature: result_quantity
}

constraint_result = {
  constraint_id,
  scenario_id,
  status: pass | fail | not_evaluable,
  evaluated_quantity: null | result_quantity,
  limit: null | result_quantity,
  margin: null | result_quantity,
  operator,
  finding_ids: ordered unique rule IDs
}
```

`constraint_results` is present on every scenario, including non-evaluated scenarios, so Section 13 `not_evaluable` records never require a fabricated numerical result. `fraction_of_total` is `physical_dimensionless` in unit `1`; resistance fields are `absolute_thermal_resistance` in `K/W`; source/reference/node temperature fields are `absolute_temperature` in `K`; and temperature rise/margin fields are `temperature_difference` in `K`. Layer/interface/node arrays follow Section 17. `NODE-<nnn>` uses a zero-based three-digit ordinal. No free-text node label is authoritative. No bare physical number is permitted.

`coverage_summary` is the exact shape in Section 10.6. `sweep_result` is exactly null or:

```text
{
  sweep_ids: ordered SWP-### array,
  field_paths: ordered RFC 6901 path array,
  enumeration_rule: "first_sweep_outermost_last_sweep_innermost",
  scenario_ids: ordered core scenario ID array
}
```

`oat_result` is exactly null or:

```text
{
  method: "oat",
  output_metric,
  reference_scenario: scenario_record,
  parameters: [oat_parameter_result],
  ranking_status: performed | not_performed,
  sensitivity_ranking: [oat_ranking_entry]
}

oat_parameter_result = {
  parameter_ordinal,
  field_path,
  x_reference: result_quantity,
  minus_scenario: scenario_record,
  plus_scenario: scenario_record,
  disposition: complete | incomplete,
  dimensional_derivative: null | {
    value: canonical Decimal string,
    output_quantity_kind,
    output_unit,
    input_quantity_kind,
    input_unit
  },
  normalized_sensitivity: null | result_quantity,
  normalized_sensitivity_disposition:
    evaluated | incomplete | zero_x_reference | zero_y_reference |
    absolute_temperature_not_normalized,
  finding_ids: ordered unique rule IDs
}

oat_ranking_entry = {
  rank: positive one-based integer,
  field_path,
  normalized_sensitivity: result_quantity
}
```

The derivative's separated numerator/denominator kind and unit fields avoid inventing an I1 compound QuantityKind. Normalized sensitivity is `physical_dimensionless` in unit `1`.

`I4-OAT-NORMALIZED-NOT-DEFINED` is a finding, not an execution warning, when a complete dimensional derivative cannot be normalized solely because the metric is absolute temperature or `x_ref`/`y_ref` is zero. The parameter remains `complete`, and this finding alone does not downgrade candidate applicability. An unavailable reference/minus/plus point uses `I4-OAT-INCOMPLETE`, is warning-bearing, and downgrades an otherwise evaluated candidate.

`candidate_comparison` is exactly:

```text
{
  objective: exact Evaluation Plan objective object,
  comparison_basis_rule: "sole_unswept_baseline_only",
  constraint_handling: exact Evaluation Plan value,
  ranking_status: performed | not_performed,
  candidate_eligibility: [{
    candidate_id,
    eligible: boolean,
    basis_scenario_id: null | scenario ID,
    reason_ids: ordered unique rule IDs
  }],
  ranked_entries: [{
    rank: positive one-based integer,
    candidate_id,
    scenario_id,
    objective_metric,
    objective_value: result_quantity
  }],
  tie_rule: "objective_value_then_candidate_id",
  calculation_notice: "Ranking is a conditional calculation, not a recommendation or approval."
}
```

When fewer than two candidates are eligible, `ranking_status` is `not_performed` and `ranked_entries` is empty; eligibility remains truthful. When ranking is performed, ranked entries include every and only eligible candidate exactly once.

`candidate_comparison` contains the exact objective, comparison-basis rule, constraint-handling rule, ranking status, ranked entries, per-candidate exclusions, exact tie rule `objective_value_then_candidate_id`, and the notice `Ranking is a conditional calculation, not a recommendation or approval.`

Findings and warnings use the I3 diagnostic shape. No complete EER core, EPR candidate copy, timestamp, user, host, absolute path, reviewer, or approval field may be duplicated in the payload. For a valid strict-I4 attempt, the payload SHALL be non-null even when no core scenario evaluates, because it is the authority for explicit scenario dispositions and coverage; every numerical result remains null in that case.

Candidate payload `findings` and `warnings` are canonical unions of their scenario, constraint, coverage, ranking, and OAT diagnostics, separated by whether the diagnostic changes applicability/execution completeness. Payload top-level `findings` and `warnings` are the canonical unions across candidates and comparison. EER top-level `findings` and `warnings` SHALL equal those payload top-level arrays; no diagnostic is invented or dropped during envelope assembly.

## 17. Deterministic Ordering and Diagnostics

The following orders are normative:

- candidates: Plan `selected_candidate_ids` order;
- core scenarios: Section 10.1 Cartesian order;
- OAT: reference, then canonical field path, minus before plus;
- layer contributions: `(order, layer_id)`;
- interfaces: upstream layer order, then `interface_id`;
- constraints: lexical/numeric `constraint_id`;
- consumed paths/acknowledgements: Section 9 canonical order;
- prediction outputs: candidate order, then Section 15 metric order;
- findings/warnings: rule ID, field-path tuple, message, then canonical encoded record;
- comparison ties: objective, then candidate ID;
- sensitivity ties: descending absolute normalized sensitivity, then field path.

No map iteration, timestamp, UUID, randomness, filesystem order, locale, or hash prefix may determine identity or order. The same EPR, Evaluation Plan, Model Manifest, unit registry, and runtime policy MUST produce byte-identical authoritative content.

In addition to the applicability IDs, the implementation SHALL reserve these stable diagnostics:

```text
I4-BIND-ACKNOWLEDGEMENT-CLOSURE
I4-BIND-EVIDENCE-REQUIRED
I4-BIND-MISSING-INPUT
I4-CNS-NOT-EVALUABLE
I4-NUM-NONPHYSICAL-BASE-INPUT
I4-OAT-INCOMPLETE
I4-OAT-NORMALIZED-NOT-DEFINED
I4-RANK-INELIGIBLE-BASIS
I4-SCENARIO-INVALID-OVERRIDE
I4-SCENARIO-PARTIAL-COVERAGE
```

Messages and required actions SHALL be constant templates populated only with stable IDs, canonical paths, and scenario IDs. Raw exceptions MUST NOT be persisted.

## 18. Synthetic Analytic Acceptance Fixture

All values are public-safe synthetic acceptance fixtures, not material claims or real-device predictions.

### 18.1 Baseline diamond candidate

```text
A = 2 mm * 2 mm = 4e-6 m^2
P = 10 W

device:   t = 100 um, k = 160 W/(m*K), R = 0.15625 K/W
interface TBR = 5e-9 m^2*K/W,        R = 0.00125 K/W
diamond:  t = 300 um, k = 1000 W/(m*K), R = 0.075 K/W
boundary: R = 1.5 K/W

R_total = 1.7325 K/W
delta_T = 17.325 K
T_reference = 50 degC = 323.15 K
T_source = 67.325 degC = 340.475 K
```

The 75 degC source constraint passes with exact margin `7.675 K`.

### 18.2 Copper candidate

For `t = 300 um` and `k = 400 W/(m*K)`:

```text
R_total = 1.845 K/W
T_source = 68.45 degC
diamond-to-copper source-temperature difference = 1.125 K
```

### 18.3 Required sweep fixtures

| Sweep | Points | Expected source temperature |
| --- | --- | --- |
| Diamond thickness | `200`, `300`, `500 um` | `67.075`, `67.325`, `67.825 degC` |
| Interface TBR | `2e-9`, `10e-9 m^2*K/W` | `67.3175`, `67.3375 degC` |
| Diamond conductivity | `800`, `1500 W/(m*K)` | `67.5125`, `67.075 degC` |
| Boundary resistance | `0.5`, `2.5 K/W` | `57.325`, `77.325 degC` |

The upper boundary point fails the 75 degC constraint by exact margin `-2.325 K` and is reported as a `2.325 K` violation.

Approximate baseline resistance fractions, used only with an explicit comparison tolerance in tests, are boundary `0.866`, device `0.090`, diamond `0.043`, and interface `0.00072`. Exact payload fractions come from the frozen Decimal policy and MUST NOT be replaced by these rounded display values.

## 19. Required Negative and Invariant Fixtures

The later tests SHALL include:

- lateral area or footprint mismatch -> scenario `not_applicable`;
- direct-convection area mismatch -> `not_applicable`;
- zero/negative bound common area -> `blocked`; zero/negative sweep or OAT area override -> `invalid`;
- nonpositive bound thickness/conductivity -> `blocked`; nonpositive explicit override -> `invalid`;
- negative bound TBR -> `blocked`; negative explicit override -> `invalid`;
- explicit zero TBR -> evaluated with retained zero contribution;
- missing required physical value -> `blocked`;
- unacknowledged consumed assumption -> blocked before arithmetic;
- extra non-consumed acknowledgement -> closure failure and never claimed as used;
- multiple heat sources, parallel paths, volumetric/distributed generation, rotated conductivity, or temperature-dependent law -> `not_applicable`;
- unsupported boundary `other` -> `not_applicable`; missing data for a supported boundary -> `blocked`;
- unsupported interface representation -> `not_applicable`;
- mixed core `evaluated + invalid` -> candidate evaluated, applicable with warnings, result present;
- mixed core `evaluated + not_applicable` -> candidate evaluated, applicable with warnings, result present;
- all core not applicable -> candidate not applicable, result absent;
- core `not_applicable + blocked` with no evaluated core -> candidate blocked/not evaluated, result absent;
- valid core plus OAT failure -> candidate evaluated/applicable with warnings, core result preserved;
- swept candidate -> no inferred candidate-level prediction output or ranking basis;
- no sweep -> exactly one baseline core scenario;
- sweep present -> no hidden baseline scenario;
- fixed-temperature boundary -> exact zero boundary contribution;
- exact node-temperature monotonicity for positive power/resistance;
- layer reordering -> same total resistance and correctly changed intermediate nodes;
- doubling thickness -> doubled layer resistance; doubling common area -> halved layer/TBR resistance; increasing conductivity -> non-increasing layer resistance;
- identical authoritative inputs -> byte-identical payload and EER content.

## 20. Acceptance Matrix

Test names MAY add descriptive suffixes but SHALL preserve these stable IDs.

| ID | Acceptance condition | Expected result |
| --- | --- | --- |
| KERN-01 | Evaluate the baseline analytic stack. | Exact resistance, rise, source temperature, nodes, and contribution budget match Section 18. |
| KERN-02 | Exercise all three supported boundary forms. | Zero, supplied, or convection resistance is applied exactly; no hidden resistance. |
| KERN-03 | Reorder constant-area series layers. | Total is invariant; intermediate nodes follow the new order. |
| KERN-04 | Use explicit zero TBR. | Scenario evaluates and retains an exact zero interface contribution. |
| APP-01 | Introduce lateral footprint/area mismatch. | `not_applicable`; no arithmetic result. |
| APP-02 | Mismatch direct-convection area. | `not_applicable`. |
| APP-03 | Use multiple sources or a parallel path. | `not_applicable`. |
| APP-04 | Use rotated/temperature-dependent property physics. | `not_applicable`. |
| APP-05 | Use unsupported interface or downstream boundary representation. | `not_applicable` with stable rule. |
| BIND-01 | Resolve canonical model inputs. | Exact deterministic consumed-path list is recorded before arithmetic. |
| BIND-02 | Omit one consumed assumed-field acknowledgement. | Affected scenario blocks before arithmetic. |
| BIND-03 | Supply extra candidate/global acknowledgement. | Exact closure fails; it is never claimed as used. |
| BIND-04 | Consume provided, assumed, evidence-required, and missing envelopes. | Behavior matches Section 9.3 exactly. |
| SCN-01 | Execute an unswept candidate. | Exactly one baseline core record `K000001`. |
| SCN-02 | Execute a swept candidate. | Exact Cartesian records; no hidden baseline. |
| SCN-03 | Enumerate candidates, core, and OAT. | IDs and order match Section 10. |
| SCN-04 | Request a nonphysical override. | Record is retained as `invalid`, not `not_applicable`. |
| AGG-01 | Mix evaluated and blocked core records. | Candidate evaluated/applicable with warnings/result present. |
| AGG-02 | Mix evaluated and invalid core records. | Candidate evaluated/applicable with warnings/result present. |
| AGG-03 | Mix evaluated and not-applicable core records. | Candidate evaluated/applicable with warnings/result present. |
| AGG-04 | Make every core not applicable. | Candidate not applicable/not applicable/result absent. |
| AGG-05 | Mix not-applicable and blocked/invalid with no evaluated core. | Candidate blocked/not evaluated/result absent. |
| AGG-06 | Give every candidate one evaluated core but leave another requested point incomplete. | EER outcome completed plus `I4-SCENARIO-PARTIAL-COVERAGE`. |
| AGG-07 | Validate all coverage counts. | Counts equal actual records and sum exactly. |
| SWP-01 | Use multiple sweeps. | First sweep is outermost; Plan point order is preserved. |
| SWP-02 | Exercise range endpoints. | I3 exact expanded points are used without tolerance or synthesis. |
| SWP-03 | Override an assumed field. | Only numeric value changes; acknowledgement remains required. |
| OAT-01 | Execute valid reference/minus/plus points. | Central derivative and permitted normalized sensitivity are exact. |
| OAT-02 | Lose either point or reference. | Incomplete; no one-sided fallback. |
| OAT-03 | Use zero `x_ref` or `y_ref`. | Dimensional derivative when defined; normalized value null with finding. |
| OAT-04 | Request source-temperature sensitivity. | Dimensional derivative only; no normalized rank. |
| OAT-05 | Fail OAT with valid core. | Candidate result remains evaluated and is warning-bearing. |
| CNS-01 | Evaluate the 75 degC source constraint. | Baseline passes; 2.5 K/W boundary point fails by 2.325 K. |
| CNS-02 | Use blocked/not-applicable scenario. | Constraint is `not_evaluable`; no fabricated pass/fail. |
| CNS-03 | Bind temperature-margin objective. | Exact referenced requirement and target path are consumed. |
| RANK-01 | Compare eligible unswept candidates. | Declared objective then candidate ID determines order. |
| RANK-02 | Include blocked/not-applicable candidate. | No rank; explicit exclusion. |
| RANK-03 | Include a swept candidate. | No inferred best-point ranking basis. |
| RANK-04 | Apply each constraint-handling rule. | Exclusion/report behavior matches Section 14. |
| DET-01 | Repeat identical inputs. | Byte-identical payload/EER authoritative content and hashes. |
| DET-02 | Vary insertion/filesystem/locale order. | No authoritative order or value changes. |
| DET-03 | Exercise a non-terminating division. | Fixed context output and `context_rounded` are reproducible. |
| DET-04 | Construct a strict-1D result-payload wrapper with `schema_id = m16a-strict-1d-result`, `schema_version = 1.0`, and closed strict-1D `content`; compute `content_sha256` with the existing I3 public `result_payload_content_sha256` helper. | The exact hash validates through the frozen I3 EER contract; no I3 runtime/schema modification is required; adding an extra `result_payload_content_identity_version` hash component would not be accepted. |
| FIX-01 | Run all Section 18 analytic values. | Exact values match; approximate fractions use declared tolerance only. |
| FIX-02 | Run Section 19 negative fixtures. | Each fixed disposition/status is obtained. |
| SEP-01 | Inspect code and payload. | No spreading, fin, fluid, radiation, transient, or hidden lookup logic. |
| SEP-02 | Inspect EER/payload authority. | No approval, reviewer, decision, memory, timestamp, host, or path fields. |
| SEP-03 | Run historical tests. | I1–I3 and Prediction-Reality behavior remain unchanged. |

## 21. Implementation Decomposition — Future Authorization Required

The implementation SHOULD use three reviewable PRs:

### I4A — manifest, applicability, binding, kernel, and payload foundation

- add the strict-1D manifest and closed result-payload schema/runtime;
- reuse the existing I3 `result_payload_content_sha256` wrapper authority unchanged; the I4-specific schema/runtime validates the `content` semantics and does not redefine the outer I3 wrapper hash;
- implement model options, applicability preflight, consumed paths, exact acknowledgement closure, Decimal policy, one-scenario kernel, nodes, and resistance budget;
- test KERN, APP, BIND, initial DET, and separation cases.

### I4B — deterministic orchestration, sweeps, aggregation, constraints, and ranking

- enumerate core scenarios and Cartesian products;
- implement explicit dispositions, coverage, candidate aggregation, EER outcome integration, constraints, comparison, and ranking;
- test SCN, AGG, SWP, CNS, RANK, and prediction-basis exclusions.

### I4C — OAT, normalized outputs, and end-to-end synthetic fixture

- add reference/minus/plus OAT execution, derivative semantics, sensitivity ranking, normalized EER prediction outputs, and the complete analytic fixture;
- test OAT, FIX, complete determinism, historical regression, and end-to-end identity.

This split keeps the equation/input boundary independently reviewable before orchestration and keeps OAT/projection behavior from obscuring aggregation review. No phase is authorized by this authoring PR.

## 22. Later Validation Commands

The later implementation PRs SHALL run their focused tests and the full existing suite. Expected command families are:

```text
python -m unittest tests.test_m16a_strict_1d_kernel
python -m unittest tests.test_m16a_strict_1d_orchestration
python -m unittest tests.test_m16a_strict_1d_sensitivity
python -m unittest \
  tests.test_m16a_evaluation_schema \
  tests.test_m16a_evaluation_binding \
  tests.test_m16a_prediction_reality_adapter
python -m unittest discover -s tests
git diff --check
```

Exact future filenames MAY follow the repository's reviewed implementation split, but every acceptance ID in Section 20 MUST be directly traceable to an executed test.

## 23. Governance, History, and Confidentiality Boundaries

I4 MUST NOT reopen M15B, P3 PARTIAL, `in_scope_generalization_supported`, `governance_pass`, Phase 0.5C, or historical Prediction-Reality behavior. It MUST NOT rewrite frozen historical results or acceptance expectations.

Calculation is not approval. No result, applicability status, constraint pass, sensitivity, or numerical rank creates an Evidence Object, validation claim, Human Decision Record, Canonical Decision Proposal, customer claim, or reusable engineering-memory entry. Those require their existing independent workflows and authorization.

All implementation fixtures MUST remain synthetic and public-safe. No proprietary growth, bonding, substrate-preparation, equipment, customer, supplier, pricing, schedule, contract, unreleased measurement, failure-analysis, partner-confidential, or export-controlled information may enter code, tests, fixtures, findings, or documentation.

## 24. Risks and Open Questions

No unresolved contract question blocks the decomposed implementation if independent review accepts this brief. Two deliberate v1 limitations remain visible:

- I3 Plan v1 cannot authorize a reference point for swept candidate-level ranking or normalized prediction output, so I4 v1 emits neither for a swept candidate.
- The EPR can represent absolute-resistance or conductance interfaces, but this exact first equation set consumes same-area TBR only; broader interface equations require a reviewed equation-set/version change.

These limitations MUST NOT be removed by inference during implementation.

## 25. Review Checklist

- [ ] Only this task brief changes in the authoring PR.
- [ ] I1, I2, and I3 contracts remain frozen.
- [ ] Equations, applicability, input paths, assumption closure, Decimal policy, and no-default rule are explicit.
- [ ] Core/OAT scenario identity, ordering, dispositions, coverage, and aggregation are closed.
- [ ] Constraint, ranking, prediction-output, sweep, and OAT semantics are deterministic.
- [ ] Synthetic and negative fixtures cover mixed-scenario truth.
- [ ] Acceptance IDs are traceable to the future split.
- [ ] No implementation, schema, tests, case artifacts, API automation, or governance artifacts are added.
- [ ] Confidentiality and claim-safety review is complete.

## 26. Recommended Next Step

Minimum next step: obtain independent architecture/contract review of this brief only. Acceptance is a written finding that the task is implementable without inventing equations, model validity, scenario aggregation, assumption closure, payload meaning, or output-selection semantics. Risk is accidental reopening of I1–I3 or treating a model calculation as approval. Any implementation requires separate explicit authorization, preferably beginning with I4A in a new project task or independent implementation conversation.
