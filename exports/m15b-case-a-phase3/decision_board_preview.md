# Decision Board Preview

This review package contains a deterministic decision preview, not an approved engineering decision.

Decision Board Preview: m15b-case-a

Board status:
HOLD_FOR_DATA

Decision state:
deferred

Current decision:
Defer architecture selection until critical thermal inputs are defined.

Decision basis:
- Critical input is incomplete: heat_source_geometry.
- Critical input is incomplete: power_or_power_density.
- Critical input is incomplete: cooling_boundary.
- Cooling boundary is not defined.
- Interface resistance remains unbounded in an interface-sensitive context.
- Thermomechanical material-property evidence is incomplete for elevated-temperature layer integration.
- The deposited-layer route lacks a resolved process thermal history for thermomechanical screening.
- Residual-stress or bow/warpage context is not sufficient to advance the membrane integration route.
- The integrated layer interface lacks a stated adhesion or mechanical-integrity basis for thermomechanical screening.
- The applicable process lacks a resolved fixture, carrier, or reactor thermal-boundary basis.

Critical missing data:
- heat_source_geometry
- power_or_power_density
- cooling_boundary

Top uncertainties:
- heat_source_geometry
- power_or_power_density
- cooling_boundary
- interface thermal resistance

Candidate routes:
- none; no approved pattern candidate has been selected.

Deferred routes:
- none

Next actions:
1. Define heat_source_geometry.
2. Bound interface thermal resistance for the relevant thermal stack.
3. Define supplier or test acceptance criteria before external engagement.

Hold points:
- Do not start detailed FEM before defining heat source geometry and cooling boundary.
- Do not advance elevated-temperature membrane integration without the stated thermomechanical evidence.
- Do not optimize diamond thickness before interface resistance is bounded.
- Do not make customer-facing thermal claims before measurement or validation.

Claim guardrails:
- Screening output is not a validated thermal conclusion.
- Pattern selection is not a final recommendation.
- Measured and simulated evidence must be clearly distinguished.
- Supplier-stated properties must not be treated as system-level performance.
- Customer-facing performance claims remain blocked until the stated evidence gap is closed.

Triggered rules:
TRIAGE-DATA-HEAT_SOURCE_GEOMETRY, TRIAGE-DATA-POWER_OR_POWER_DENSITY, TRIAGE-DATA-COOLING_BOUNDARY, TRIAGE-BOUNDARY-001, TRIAGE-INTERFACE-001, TRIAGE-THERMOMECH-001, TRIAGE-THERMOMECH-002, TRIAGE-THERMOMECH-003, TRIAGE-THERMOMECH-004, TRIAGE-THERMOMECH-005, BOARD-STATUS-001, BOARD-ROUTE-002, BOARD-HOLD-001, BOARD-CLAIM-001, BOARD-ACTION-001

Validation note:
This is a deterministic decision preview, not an approved engineering decision.
