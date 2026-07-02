# Next Best Action: Example Incomplete GaN RF PA

## Purpose

Select the lowest-risk next step that improves decision quality.

## When To Use

Use after red flags are identified.

## Required Fields

- Case ID: example-incomplete-gan-rf-pa
- Recommended action: create bounded thermal assumptions before expensive simulation
- Why now: top uncertainties can reverse the preferred architecture
- Inputs required: heat source bounds, package stack, interface assumptions, cooling boundary
- Expected output: narrowed decision board and validation-ready model boundary
- Decision it enables: whether to evaluate package-level, submount-level, die-near, or system-cooling routes first
- Cost/risk level: low

## Recommendation

Recommended action:

Collect and bound the minimum thermal architecture inputs before selecting a diamond route or launching detailed simulation.

Rationale:

The current problem is under-specified. Interface thermal resistance and cooling boundary conditions are likely to determine whether conventional package improvement, diamond heat spreading, submount changes, die-near diamond integration, or cooling-system changes should be prioritized.

## Requested Inputs

- Approximate heat source size or bounded range.
- Current package stack and thermal path.
- Die attach, submount, TIM, and heat sink interface assumptions.
- Cooling boundary and temperature reference.
- Mechanical/RF constraints that affect double-side cooling or submount changes.

## Review Checklist

- [x] The action is bounded and practical.
- [x] The action reduces top uncertainty.
- [x] The action does not require unsupported claims.

## Confidentiality Note

Inputs should be sanitized or handled under the correct confidentiality level.

## Claim Safety Note

This action defines how claims will be validated; it does not assume the validation result.
