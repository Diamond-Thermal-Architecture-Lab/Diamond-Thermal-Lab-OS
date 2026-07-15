# Gold Case Assessment

## Case Identity

- Case ID: literature-2021-diamond-on-gan-membrane-stress
- Source-paper reference: arXiv:2102.09664; Cuenca et al.; Thermal stress modelling of diamond on GaN/III-Nitride membranes; 2021
- Blind-baseline commit SHA: ce9520deb1216610b8226626fcbaa51b19621b6c
- Evidence commit SHA: c19a7d5cfdcc99057ce20e0cd1774108a988ee3f
- Assessment status: benchmark_candidate
- Confidentiality: public
- Evaluation mode: blind baseline followed by evidence reveal

This is a Gold Case benchmark candidate. It is not yet a certified Gold Case. It has not been accepted for automatic calibration or engineering-memory promotion. Validator PASS/WARN states do not prove technical correctness.

## Test Objective

This test evaluates whether Diamond Thermal Lab OS can recognize that direct CVD diamond growth on thin GaN/III-N membranes is governed not only by thermal conductivity and interface resistance, but also by thermomechanical stress, membrane deformation, process-fixture boundaries, and manufacturability.

## Blind Baseline Inputs

The blind baseline used only pre-reveal case information:

- 0.5 mm, 2 mm, and 5 mm membrane diameters.
- Approximately 1.7 um GaN.
- Approximately 3.6 um remaining III-N layers.
- Approximately 75 um residual silicon support.
- Approximately 38 to 57 um CVD diamond.
- Approximately 720 to 750 degrees Celsius growth process.
- Spatially nonuniform process heating.
- Possible membrane movement toward the plasma.
- Unknown interface thermal resistance.
- Unknown allowable bow, stress, fracture, and delamination limits.

## Blind Baseline Result

The deterministic blind baseline produced:

- status: READY_FOR_SCREENING
- primary classification: design_space_unclear
- secondary classifications:
  - interface_limited_candidate
  - package_limited_candidate
- confidence: low
- direct GaN-on-Diamond retained as a higher-integration-risk screening candidate.
- no route was automatically approved.
- interface thermal resistance was identified as unbounded.
- detailed material optimization was held.
- customer-facing claims remained blocked.

## Revealed Experimental Reality

The later source-documented evidence is recorded in `EVD-001`, `EVD-002`, `MSR-001` through `MSR-005`, and `PRL-001`; those sidecars remain the controlled source for the individual literature-transcribed values and limitations. In aggregate, they show increasing reported deformation with membrane diameter, reported residual tensile stress in the source membranes, and severe thermally coupled deformation and damage in the reported 5 mm membrane.

These are literature-transcribed results, not independently reproduced Diamond Thermal Lab measurements. The evidence reveal does not validate every direct GaN-on-Diamond architecture or provide a general process window.

## Scoring

| Category                                      | Maximum | Score |
| --------------------------------------------- | ------: | ----: |
| Conservative decision governance              |       2 |     2 |
| Interface-risk recognition                    |       2 |     2 |
| Integration and manufacturability caution     |       2 |     2 |
| Thermomechanical-risk recognition             |       2 |     0 |
| Size-scaling and process-feedback recognition |       2 |     0 |
| Total                                         |      10 |     6 |

Conservative decision governance scored 2 because the baseline kept the result in screening, did not approve a route, and preserved claim guardrails. Interface-risk recognition scored 2 because unbounded interface thermal resistance was explicit. Integration and manufacturability caution scored 2 because direct GaN-on-Diamond remained a higher-integration-risk screening candidate rather than an automatic first route. Thermomechanical-risk recognition scored 0 because CTE mismatch, residual stress, bow, warpage, buckling, fracture, and delamination were not transformed into focused deterministic findings or hold points. Size-scaling and process-feedback recognition scored 0 because membrane diameter, nonlinear deformation, movement toward the plasma, and possible heating feedback were not treated as explicit decision drivers.

## What The System Did Correctly

- Did not recommend direct GaN-on-Diamond automatically.
- Preserved neutral alternatives.
- Identified interface uncertainty.
- Recognized higher integration and manufacturability risk.
- Kept confidence low.
- Prevented unsupported customer claims.
- Preserved the distinction between screening, measurement, and human-reviewed decision.

## What The System Missed

- Coefficient-of-thermal-expansion mismatch.
- Residual thermal stress.
- Membrane bow and warpage.
- Buckling, fracture, and delamination mechanisms.
- Strong membrane-diameter scaling.
- Nonlinear geometry effects.
- Membrane displacement toward the plasma.
- Positive thermal-process feedback.
- Contact-lithography flatness constraints.
- Wafer handling and downstream-process compatibility.
- Need for coupled thermal-structural modelling.
- Need to compare initial membrane curvature with post-growth curvature.

These risks were present in the blind input but were not transformed into explicit deterministic findings or hold points.

## Quantitative Prediction Gap

The baseline did not produce a numerical membrane-bow prediction. PRL-001 therefore cannot calculate signed, absolute, or relative numerical error. A null prediction must not be replaced with an invented value. The inability to generate a comparable prediction is itself a valid Gold Case finding. The present case should not be marked accepted_for_calibration.

## Boundary-Taxonomy False Positive

The probable false positive is:

- The triage classified the case as package_limited_candidate.
- This case is primarily governed by a process-fixture and reactor thermal boundary, not a conventional package-to-heat-sink boundary.
- Generic mounting and package placeholder language may have contributed to the trigger.
- The system needs separate boundary concepts for:
  - device package boundary;
  - die-attach boundary;
  - process fixture boundary;
  - wafer carrier boundary;
  - reactor boundary;
  - coolant boundary;
  - ambient and radiative boundary.

Do not claim the rule is conclusively defective until a focused unit test reproduces the trigger.

## Evidence-Model Finding

A literature Evidence Object could not directly serve as the parent of Measurement References under the current contract. The case required:

- EVD-001 as literature source evidence;
- EVD-002 as a source-documented measurement-derived evidence object;
- MSR-001 through MSR-005 linked to EVD-002.

This solution is structurally valid under the present validator. The phrase literature-transcribed measurement is not yet represented as a dedicated provenance relationship. This should be reviewed as a future evidence-graph improvement, not silently changed in this case.

## Capability Gaps

### GAP-THERMOMECH-001

The deterministic triage lacks focused thermomechanical rules for CTE mismatch, residual stress, warpage, bow, buckling, fracture, and delamination.

### GAP-PROCESS-BOUNDARY-001

The boundary taxonomy does not distinguish semiconductor packaging from process fixtures and reactor thermal boundaries.

### GAP-SCALE-FEEDBACK-001

The system does not explicitly reason about membrane-size scaling, nonlinear deformation, or displacement-driven plasma-heating feedback.

### GAP-PREDICTION-001

The system lacks a bounded numerical or categorical prediction contract for membrane bow and process-induced deformation.

### GAP-EVIDENCE-PROVENANCE-001

The evidence model lacks an explicit relationship for measurements transcribed from a literature source.

## M14 Rule Coverage

M14 addresses the screening gaps with reusable qualitative guardrails:

- `TRIAGE-THERMOMECH-001` requests a temperature-dependent material-property and reference-temperature basis when elevated-temperature layer integration is in scope.
- `TRIAGE-THERMOMECH-003` keeps residual-stress and bow/warpage evidence separate from case-specific acceptance criteria and human review.
- `TRIAGE-THERMOMECH-004` requests an adhesion or mechanical-integrity evidence basis without predicting delamination or cracking.
- `TRIAGE-THERMOMECH-005` distinguishes a process fixture, carrier, or reactor boundary from a conventional package boundary.
- `TRIAGE-THERMOMECH-006` requests geometry, thickness, curvature, and boundary comparison evidence before scale-up extrapolation.
- `TRIAGE-THERMOMECH-007` requests downstream flatness, handling, lithography, packaging, or fabrication compatibility criteria where those constraints are relevant.

These rules are qualitative screening guardrails, not validated stress or warpage models. They do not calculate numerical bow, infer failure, select a route, or add an unsupported numerical threshold from this paper.

## Recommended Improvement Order

1. Add process and thermomechanical boundary taxonomy.
2. Add conservative thermomechanical triage rules.
3. Add focused unit tests using this Gold Case.
4. Add categorical prediction output before attempting numerical prediction.
5. Add literature-transcribed measurement provenance.
6. Rerun the blind baseline from an unchanged input snapshot.
7. Compare the improved output against this baseline.

Categorical prediction should precede numerical prediction. Useful categorical examples include low bow risk, moderate bow risk, high bow risk, thermomechanical hold required, and unsupported without coupled FEM. The system should not fabricate a precise bow value from rules alone.

## Rerun Acceptance Criteria

The improved system should, without seeing the measured results:

- Trigger a thermomechanical-risk classification.
- Identify CTE mismatch and residual stress.
- Identify membrane diameter as a scaling variable.
- Identify possible plasma-proximity feedback.
- Add a hold point before scaling to the 5 mm membrane.
- Request initial and post-growth profilometry.
- Request Raman stress mapping.
- Recommend coupled thermal-structural modelling.
- Distinguish process-fixture boundaries from package boundaries.
- Keep direct GaN-on-Diamond unapproved until validation.
- Preserve non-diamond comparison routes.
- Avoid generating unsupported numerical bow claims.

## Learning Disposition

- Current disposition: pending_review.
- Not accepted for calibration.
- Not promoted to engineering memory.
- Suitable as a regression benchmark candidate.
- Human review is required after rules are improved and the blind test is rerun.

## Generalization Boundary And M15 Test

One literature case does not validate this rule family. The frozen blind-baseline export remains historical evidence and must not be rewritten to incorporate the later findings. A second independent Gold Case should test whether the guardrails remain useful for a different material pair, thermal process, membrane geometry, fixture boundary, and downstream constraint set, while also checking that ordinary bulk-package cases do not receive irrelevant thermomechanical warnings.

No numerical stress, bow, warpage, adhesion, or scale-up threshold may be learned from this source alone. M15 should compare an unchanged blind input snapshot with independently sourced evidence and should evaluate both missed-risk and false-positive behavior.

## Final Assessment

Diamond Thermal Lab OS passed the governance and traceability portion of the test but did not yet pass the core thermomechanical reasoning portion. The case demonstrates that the system is useful as a conservative decision framework, while also showing that its deterministic intelligence is currently too centered on interface, material, and package resistance for process-induced thin-film and membrane deformation problems.
