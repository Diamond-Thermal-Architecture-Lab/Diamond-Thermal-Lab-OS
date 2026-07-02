# Decision Board: Example Incomplete GaN RF PA

## Purpose

Convert incomplete inputs into decision options, blockers, and next actions.

## When To Use

Use after the intake and thermal design passport.

## Required Fields

- Decision needed: Which thermal architecture routes deserve evaluation first?
- Candidate routes: conventional package improvement, diamond heat spreader, diamond submount, GaN bonded to diamond, direct GaN-on-Diamond, Cu-diamond composite, double-side cooling, microchannel hybrid
- Decision criteria: thermal leverage, interface risk, integration burden, validation cost, schedule risk
- Top uncertainties: interface thermal resistance and cooling boundary
- Decision status: pending

## Decision Options

| Option | Why Consider | Key Uncertainty | Evidence Needed | Status |
| --- | --- | --- | --- | --- |
| Conventional package improvement | May address package-level bottleneck with lower integration disruption | Whether bottleneck is package/cooling rather than die substrate | Package stack and boundary characterization | Candidate |
| Diamond heat spreader | May improve lateral spreading near package level | Interface resistance may erase benefit | Interface stack and heat source dimensions | Candidate |
| Diamond submount | May improve heat spreading closer to die | Die attach and CTE/integration constraints | Mechanical and thermal interface assumptions | Candidate |
| GaN bonded to diamond | May place diamond closer to active region than package-level routes | Bond/interface quality and process compatibility | Feasibility and interface bounds | Candidate |
| Direct GaN-on-Diamond | Potentially high thermal leverage if die-level bottleneck dominates | Highest process and integration burden | Strong evidence that simpler routes are insufficient | Hold |
| Cu-diamond composite | May improve package or baseplate spreading | Composite properties and interface stack | Supplier capability and package model | Candidate |
| Double-side cooling | May add a parallel heat path | RF/package accessibility and mechanical feasibility | Package layout and cooling constraints | Candidate |
| Microchannel hybrid | May improve boundary condition strongly | Complexity, reliability, fluid integration | System-level cooling constraints | Candidate |

## Current Decision

Decision: Pending. Do not select direct GaN-on-Diamond as the first step.

Rationale:

The highest uncertainties are interface thermal resistance and the package-to-heat-sink boundary. These uncertainties can dominate the outcome regardless of whether diamond is used. The next action should bound the heat source, interface stack, and cooling boundary before expensive simulation or supplier commitment.

## Review Checklist

- [x] Diamond and non-diamond routes are compared neutrally.
- [x] The board identifies what must be learned next.
- [x] The decision is not stronger than the evidence.

## Confidentiality Note

This example contains no customer-specific dimensions or partner information.

## Claim Safety Note

All routes are candidate or hold states, not validated recommendations.
