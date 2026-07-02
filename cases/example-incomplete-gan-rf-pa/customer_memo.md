# Customer Memo: Example Incomplete GaN RF PA

## Purpose

Provide a conservative customer-facing summary of the current decision state.

## When To Use

Use after the decision board, red flags, next best action, and claim ledger are reviewed.

## Required Fields

- Case ID: example-incomplete-gan-rf-pa
- Audience: technical customer stakeholder
- Customer question: whether diamond or another thermal architecture is needed
- Current understanding: overheating GaN RF PA with incomplete stack, heat source, interface, and cooling-boundary information
- Preliminary comparison: multiple routes remain plausible
- Red flags: interface resistance and cooling boundary
- Recommended next action: bound assumptions before expensive simulation or supplier commitment
- Claims allowed for release: preliminary, public-safe only

## Memo Draft

Based on the information currently available, it is too early to select a single thermal architecture. Diamond-based routes may be relevant, but the first decision should not automatically be direct GaN-on-Diamond. Conventional package improvement, diamond heat spreading, diamond submounts, Cu-diamond composites, double-side cooling, and cooling-boundary improvements should be compared under the same assumptions.

The most important missing inputs are the heat source geometry, interface thermal resistance, and package-to-heat-sink boundary condition. These factors can change which architecture has the strongest practical benefit.

Recommended next step: define bounded assumptions for the heat source, stack, interfaces, and cooling boundary. With those inputs, the team can narrow the architecture routes and decide what level of simulation or supplier engagement is justified.

These conclusions are preliminary and should not be treated as validated thermal performance claims.

## Review Checklist

- [x] Language is clear and conservative.
- [x] No unsupported performance promise is made.
- [x] Confidential information is removed.
- [x] Next action and validation path are explicit.

## Confidentiality Note

This memo is public-safe example language.

## Claim Safety Note

Only preliminary claims from the claim ledger are used.
