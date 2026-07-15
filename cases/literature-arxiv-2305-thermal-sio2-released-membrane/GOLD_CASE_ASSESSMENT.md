# Gold Case Assessment

## Case Identity and Source

- Case ID: `literature-arxiv-2305-thermal-sio2-released-membrane`
- Source: C. Malhaire et al., "Determination of compressive stress in thin films using micro-machined buckled membranes," arXiv:2305.15794, 2023.
- Assessment status: `benchmark_candidate`
- Confidentiality: public
- Benchmark type: artifact-separated retrospective, outcome-value-withheld, adjacent-scope boundary benchmark.
- Declared-scope applicability: outside the strict M14 process-sequence contract.
- In-scope generalization disposition: `generalization_not_evaluable`
- Adjacent-scope transfer disposition: `adjacent_scope_transfer_not_supported`

This is M15A, a retrospective thermomechanical scope-boundary benchmark. It is not a certified Gold Case, is not accepted for automatic calibration, and is not promoted to engineering memory. Validator PASS or WARN states check structure and traceability; they do not prove engineering correctness.

## Blind-to-Outcome Methodology

The phase-one baseline commit preceded Evidence Objects, Measurement References, Prediction-Reality sidecars, the source title, and revealed outcome values. The frozen phase-one baseline commit is `9a9f3af3001b947226484f48b8db99f428556428` (`test: freeze M15 independent Gold Case baseline`).

The source table was separated by column for the frozen baseline: material, approximately 1.5 um thickness, and membrane side length were admitted as blind inputs; measured central deflection, simulation-inferred stress, and result-derived explanations were withheld until evidence reveal. The source uses square membrane side length; this assessment intentionally does not relabel it as membrane diameter.

The frozen export is historical evidence. It must not be rewritten to make the earlier rule set appear stronger or weaker.

## Process-Sequence Scope

Thermal SiO2 was formed on a supported silicon wafer. The self-supporting membrane was created later by backside KOH removal. The membrane was not already present during the approximately 1130 degC oxide formation process.

M14 applicability requires the conjunction of:

- membrane, suspended, or thin structural context;
- deposited, bonded, or directly grown layer integration;
- thermally significant integration process.

This case therefore does not cleanly exercise M14 within its strict declared process-sequence scope. `thermomechanical_screening.status = not_applicable` must not be scored automatically as an in-scope rule-family failure. The current implementation also does not model temporal process state, so this result is not proof of deliberate sequence-aware reasoning.

## Blindness and Retrospective Limitations

Artifact chronology is valid: the phase-one baseline commit came before the evidence sidecars and outcome values. Agent knowledge isolation was not valid: the same implementation context knew the source, measured outcomes, and assessment questions before constructing phase one.

The 12 numbered Canonical Case files contain expert-targeted missing-evidence language, including stress-free reference temperature, residual-stress evidence, bow or warpage acceptance criteria, initial/post-release profile comparison, geometry-dependent comparison, reactor boundary, and release-fixture constraints. Exact membrane side lengths reflect as-fabricated geometry, but they also carry retrospective process-development knowledge from the source table.

This is not a prospective double-blind test and not a cognitively isolated agent-blind test. It withholds explicit measured outcome values from frozen artifacts, but remains vulnerable to hindsight bias. `BENCHMARK_AUDIT_QUALIFICATION.md` records this post-freeze qualification without rewriting phase-one history.

## Frozen Baseline Artifact Hashes

| Artifact | SHA256 |
| --- | --- |
| `decision_board_preview.json` | `6a18fadcbdef0295a0cfd9ddbe43f4e99e11ea9bb6a4e9112e9f610ff718bc2e` |
| `decision_board_preview.md` | `80912cdd40b32c5a8d2f8159c9d9c1c55cd7719c15e6c38c4c6625f766c9f488` |
| `human_review_checklist.md` | `6ee1ac064f30208361f5d445581b853515505f7d46fb9e230d04137815a2d58c` |
| `review_manifest.json` | `f00ce5370270c0984bd0023acb886014ccb72ce89028b61c9315b2069cbcdcfb` |
| `triage_report.md` | `a8f35bc5765f03807da8f0074e533086f034edf407861fd60f8f6db7cc53f248` |
| `triage_result.json` | `d99a8d6490d64c37736aae8426adeb72b896a009b9f65cc4b6444d3c5dca2b64` |

`baseline_manifest.json` records the same mapping and intentionally does not hash itself.

## Actual Frozen Baseline Behavior

The frozen deterministic result was `READY_FOR_SCREENING`, with primary classification `design_space_unclear`, secondary classification `interface_limited_candidate`, and low confidence. It triggered `TRIAGE-INTERFACE-001` and `TRIAGE-DESIGN-001`. It did not approve a route, make a customer claim, predict numerical deflection, or predict numerical stress.

M14 thermomechanical screening returned `not_applicable`; none of `TRIAGE-THERMOMECH-001` through `TRIAGE-THERMOMECH-007` triggered. The next action remained a generic architecture comparison rather than a request for thermomechanical evidence.

## Frozen Decision Board Coherence Findings

These are immutable observations of the frozen phase-one output. They are not repaired in this PR.

| Finding | Classification | Assessment |
| --- | --- | --- |
| `candidate_routes` is empty while the board says to proceed with comparative screening of identified candidates. | Internally contradictory output | The board status and instruction do not match candidate availability. |
| The board requests comparison of two or three architectures although the Canonical Case contains one process path. | Decision Board template leakage | Generic architecture-comparison language leaked into a single-path process benchmark. |
| `TRIAGE-DESIGN-001` states that multiple routes remain plausible despite the single-path formulation. | Generic triage false positive | The design-space default overstated route multiplicity for this case. |
| Two diamond-thickness hold points appear in a non-diamond SiO2 case. | Cross-domain state contamination | Diamond-specific wording from the generic triage context is inappropriate historical output. |
| The diamond-thickness hold point is duplicated in different wording. | Decision Board template leakage | The duplicate wording makes the frozen review package noisier. |
| Interface-limited classification is questionable for the final released single-material membrane. | Generic triage false positive | The retained-interface concept is not a clean match for the final released SiO2 membrane. |
| A generic architecture-comparison action displaced the case-specific thermomechanical evidence need. | Prioritization defect | The strongest missing evidence was not surfaced because M14 applicability did not activate. |
| `READY_FOR_ARCHITECTURE_SCREENING` is internally questionable with zero candidate routes. | Internally contradictory output | Conservative governance was retained, but the status does not align with the empty candidate list. |

The governance result remains conservative because no route was approved and no customer-facing performance claim was made.

## Revealed Experimental Evidence

The evidence reveal is represented by `EVD-001` (literature source), `EVD-002` (source-documented measurement-derived evidence), `MSR-001` through `MSR-006`, and `PRL-001`.

- The source reports central deflections of approximately -11.3 +/- 0.1 um, -14.2 +/- 0.1 um, and -20.9 +/- 0.1 um for reported square membrane side lengths of approximately 256.7 +/- 2.0 um, 340.5 +/- 2.0 um, and 506.7 +/- 2.0 um.
- The source reports simulation-inferred residual-stress estimates of approximately -319 MPa, -320 MPa, and -323 MPa, with a reported average of approximately -321 MPa. These are not direct independent stress measurements.
- The source attributes the residual stress mainly to thermal-expansion mismatch between thermally grown SiO2 and silicon and estimates its stress-evaluation method relative error below approximately 5 percent.
- The source reports that approximately 250 nm SiO2 membranes were strongly and irregularly deformed and unsuitable for its reported fitting method. This qualitative observation is not converted into a fabricated numeric Measurement Reference.
- The KOH release holder constrained the observed deformation direction. That is a process-mechanical boundary observation, not proof of a high-temperature reactor thermal boundary.

All sidecars remain source documented and pending human review. They are not independently reproduced Diamond Thermal Lab measurements and are not accepted for automatic calibration.

## Prediction-Versus-Reality Comparison

`PRL-001` binds to phase-one commit `9a9f3af3001b947226484f48b8db99f428556428` and `baseline_manifest.json`. The baseline did not produce a numerical deflection or stress prediction, so signed, absolute, and relative numerical errors remain null. A null prediction must not be replaced with an invented value.

The missing comparable numerical prediction is a valid benchmark result. It does not establish that the source behavior is predictable from the baseline, and it does not approve any architecture or process.

## Rule-by-Rule Assessment

| Rule | Frozen result | Scope-boundary assessment |
| --- | --- | --- |
| `TRIAGE-THERMOMECH-001` | Did not trigger | Non-diagnostic for strict in-scope generalization because applicability did not activate. Missing material-property and reference-temperature questions remain visible as adjacent-scope needs. |
| `TRIAGE-THERMOMECH-002` | Did not trigger | Non-diagnostic for strict in-scope generalization. Oxidation dwell, exposure, and cooling-route history remain adjacent-scope needs. |
| `TRIAGE-THERMOMECH-003` | Did not trigger | Non-diagnostic for strict in-scope generalization. Residual-stress, profile, and acceptance-criteria evidence remain adjacent-scope needs. |
| `TRIAGE-THERMOMECH-004` | Did not trigger | Less relevant to the final released single-material structure than to a retained film/substrate interface. |
| `TRIAGE-THERMOMECH-005` | Did not trigger | Non-diagnostic for strict in-scope generalization. It records a missed adjacent-scope separation between high-temperature reactor boundaries and KOH release-holder mechanical constraints. |
| `TRIAGE-THERMOMECH-006` | Did not trigger | Non-diagnostic for strict in-scope generalization. The case exposes a possible future need for side-length scale reasoning. |
| `TRIAGE-THERMOMECH-007` | Did not trigger | Not strongly diagnostic because no explicit downstream application context was supplied. |

## Scope-Separated Assessment

The earlier draft headline `0/10` score is construct-invalid and superseded because applicability never activated and the case does not cleanly satisfy the strict M14 process-sequence contract. The dimensions below are deliberately not combined into a total score.

| Dimension | Assessment |
| --- | --- |
| Conservative governance | Retained: no route approval, customer claim, calibration, or numerical prediction was fabricated. |
| Strict declared-scope fit | Outside strict M14 process-sequence scope. |
| In-scope generalization evaluability | `generalization_not_evaluable` for M14's declared scope. |
| Adjacent-scope transfer | `adjacent_scope_transfer_not_supported` by the frozen output. |
| Generic triage coherence | Defects found: route multiplicity, interface context, and generic next-action leakage. |
| Decision Board coherence | Defects found: empty route list paired with comparative-screening status and cross-domain hold points. |
| Quantitative prediction capability | Absent and correctly not fabricated. |

## Value and Future Use

This case remains valuable as:

- an M14 declared-scope boundary case;
- an adjacent-domain transfer test;
- a generic triage false-positive case;
- a Decision Board contamination regression;
- a future negative or boundary control for M15B.

It is not the primary independent in-scope generalization case. One additional literature case still cannot establish broad professional reliability, and no numerical threshold may be learned from this source.

## What Must Not Be Generalized

- No numerical stress, deflection, bow, warpage, or failure threshold may be learned from this paper.
- The reported stress estimates are simulation-inferred from measured profiles and must not be treated as universally transferable direct measurements.
- The release-holder observation must not be generalized into a reactor thermal-boundary claim.
- The source geometry, oxide thickness, silicon frame, process history, and fitting approach must not be generalized to other materials or released membranes.
- This benchmark does not prove that all high-temperature membrane cases will have the same screening gap.

## Recommended Follow-Up

1. Treat this PR as M15A and keep the frozen output as historical evidence.
2. Use a separate rule-focused PR to investigate generic triage and Decision Board coherence defects.
3. Run M15B as a knowledge-isolated, in-scope generalization benchmark with predeclared applicability and scoring.
4. Include an independent negative or boundary control; this SiO2 case can serve that role.
5. Require human evidence review before any calibration, pattern update, engineering-memory promotion, or canonical decision action.
