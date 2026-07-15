# Gold Case Assessment

## Case Identity and Source

- Case ID: `literature-arxiv-2305-thermal-sio2-released-membrane`
- Source: C. Malhaire et al., "Determination of compressive stress in thin films using micro-machined buckled membranes," arXiv:2305.15794, 2023.
- Assessment status: `benchmark_candidate`
- Confidentiality: public
- Evaluation mode: repository-level blind-to-outcome benchmark.

This is not a prospective double-blind experimental trial. It is not a certified Gold Case, has not been accepted for automatic calibration, and has not been promoted to engineering memory. Structural validator PASS or WARN results do not prove engineering correctness.

## Blind-to-Outcome Methodology

The blind input was committed before Evidence Objects, Measurement References, or outcome values were added. The frozen phase-one baseline commit is `9a9f3af3001b947226484f48b8db99f428556428` (`test: freeze M15 independent Gold Case baseline`). The source table was separated by column: material, approximately 1.5 um thickness, and membrane side length were admitted as blind inputs; measured profile values, estimated residual-stress values, and result-derived explanations were excluded until evidence reveal.

The frozen export is historical evidence. It must not be rewritten to make the earlier rule set appear stronger. The source uses square membrane side length; this assessment intentionally does not relabel it as membrane diameter.

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

## Actual Blind Baseline Behavior

The frozen deterministic result was `READY_FOR_SCREENING`, with primary classification `design_space_unclear`, secondary classification `interface_limited_candidate`, and low confidence. It triggered `TRIAGE-INTERFACE-001` and `TRIAGE-DESIGN-001`. It did not approve a route, make a customer claim, predict numerical deflection, or predict numerical stress.

M14 thermomechanical screening returned `not_applicable`; none of `TRIAGE-THERMOMECH-001` through `TRIAGE-THERMOMECH-007` triggered. The next action remained a generic architecture comparison rather than a request for thermomechanical evidence.

## What M14 Correctly Identified

- The baseline remained conservative: no route was approved and no customer-ready claim was produced.
- The deterministic result retained low confidence and did not invent stress, deflection, cracking, or failure predictions.
- It preserved a separation between screening and evidence-based decision making.
- It exposed an interface-sensitive classification from the existing general triage engine, which is useful as an observable diagnostic even though it was not well matched to the final released-membrane structure.

## What M14 Failed to Identify

- The high-temperature wet-oxidation and released-membrane context was not recognized as thermomechanically applicable.
- Temperature-dependent property data and a stress-free reference temperature were not requested.
- Oxidation dwell, exposure, and cooling-route history were not requested.
- Residual-stress evidence, initial/post-release profile comparison, and case-specific bow or warpage acceptance criteria were not requested.
- The three membrane side lengths were not recognized as a geometry-scaling context.
- High-temperature reactor thermal boundaries and the distinct KOH release-holder mechanical constraint were not separated or requested.

These are benchmark observations, not a basis for silently changing M14 in this PR.

## Irrelevant or Questionable Baseline Finding

`TRIAGE-INTERFACE-001` was triggered by the blind case text despite the target being a released single-material SiO2 membrane, not a retained film/substrate thermal interface. The existing generic interface context is therefore a probable false positive for this case. The source-faithful case text is not being rewritten to avoid it. A later rule-focused change would require an independent review and test.

## Revealed Experimental Evidence

The evidence reveal is represented by `EVD-001` (literature source), `EVD-002` (source-documented measurement-derived evidence), `MSR-001` through `MSR-006`, and `PRL-001`.

- The source reports central deflections of approximately -11.3 +/- 0.1 um, -14.2 +/- 0.1 um, and -20.9 +/- 0.1 um for reported square membrane side lengths of approximately 256.7 +/- 2.0 um, 340.5 +/- 2.0 um, and 506.7 +/- 2.0 um.
- The source reports simulation-inferred residual-stress estimates of approximately -319 MPa, -320 MPa, and -323 MPa, with a reported average of approximately -321 MPa. These are not direct independent stress measurements.
- The source attributes the residual stress mainly to thermal-expansion mismatch between thermally grown SiO2 and silicon and estimates its stress-evaluation method's relative error below approximately 5 percent.
- The source reports that approximately 250 nm SiO2 membranes were strongly and irregularly deformed and unsuitable for its reported fitting method. This qualitative observation is not converted into a fabricated numeric Measurement Reference.
- The KOH release holder constrained the observed deformation direction. That is a process-mechanical boundary observation, not proof of a high-temperature reactor thermal boundary.

All sidecars remain source documented and pending human review. They are not independently reproduced Diamond Thermal Lab measurements and are not accepted for automatic calibration.

## Prediction-Versus-Reality Comparison

`PRL-001` binds to phase-one commit `9a9f3af3001b947226484f48b8db99f428556428` and `baseline_manifest.json`. The baseline did not produce a numerical deflection or stress prediction, so signed, absolute, and relative numerical errors remain null. A null prediction must not be replaced with an invented value.

The missing comparable numerical prediction, together with M14 applicability non-activation, is a valid benchmark result. It does not establish that the source behavior is predictable from the baseline, and it does not approve any architecture or process.

## Rule-by-Rule Assessment

| Rule | Frozen result | Assessment |
| --- | --- | --- |
| `TRIAGE-THERMOMECH-001` | Did not trigger | Missed missing temperature-dependent property and reference-temperature evidence because the family was not applicable. |
| `TRIAGE-THERMOMECH-002` | Did not trigger | Missed incomplete oxidation dwell, exposure, and cooling-route history. |
| `TRIAGE-THERMOMECH-003` | Did not trigger | Missed residual-stress, profile, and acceptance-criteria evidence requests. |
| `TRIAGE-THERMOMECH-004` | Did not trigger | No retained film/substrate interface was asserted after release; this rule may be less relevant than the other guards for this final structure. |
| `TRIAGE-THERMOMECH-005` | Did not trigger | Missed high-temperature reactor boundary definition and did not distinguish it from the release-holder mechanical constraint. |
| `TRIAGE-THERMOMECH-006` | Did not trigger | Missed the side-length scaling context and absence of a cross-size deformation comparison. |
| `TRIAGE-THERMOMECH-007` | Did not trigger | No explicit downstream application context made this non-trigger less diagnostic; no downstream requirement is inferred from the paper alone. |

## Generalization Assessment

Scorecard:

| Category | Maximum | Score |
| --- | ---: | ---: |
| Applicability recognition | 2 | 0 |
| Process and material-property gaps | 2 | 0 |
| Stress and warpage evidence recognition | 2 | 0 |
| Geometry-scaling recognition | 2 | 0 |
| Boundary relevance and false-positive control | 2 | 0 |
| Total | 10 | 0 |

Disposition: `generalization_not_supported` for this case formulation. The score measures the frozen M14 thermomechanical screening result, not the usefulness of conservative governance elsewhere in the system. One additional literature case still cannot validate or invalidate the full rule family.

## What Must Not Be Generalized

- No numerical stress, deflection, bow, warpage, or failure threshold may be learned from this paper.
- The reported stress estimates are simulation-inferred from measured profiles and must not be treated as universally transferable direct measurements.
- The release-holder observation must not be generalized into a reactor thermal-boundary claim.
- The source's geometry, oxide thickness, silicon frame, process history, and fitting approach must not be generalized to other materials or released membranes.
- This benchmark does not prove that all high-temperature membrane cases will have the same screening gap.

## Recommended Follow-Up

1. Review the observed applicability, side-length, boundary-taxonomy, and interface false-positive findings in a separate rule-focused PR.
2. Keep any M14 correction qualitative, reusable, and independently tested; do not add source-specific wording or numerical thresholds.
3. Test any correction against a third independent Gold Case with different material, geometry, and process context.
4. Require human evidence review before any calibration, pattern update, engineering-memory promotion, or canonical decision action.
