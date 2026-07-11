# Conventional Package Upgrade

## Pattern ID
PAT-CONV-PKG-001

## Pattern Name
Conventional package upgrade

## Problem Type Addressed
Package, attach, TIM, baseplate, or heat-sink boundary resistance may dominate the thermal path.

## Typical Use Cases
- Incomplete cases where the package stack is not yet partitioned.
- Near-term improvement path before advanced materials are justified.
- Cases where the cooling boundary may dominate junction temperature.

## Architecture Genome Mapping
- heat source: semiconductor die or module hot spot
- substrate: existing device substrate
- bonding interface: die attach, package attach, TIM, and mounting interfaces
- heat spreader: existing or improved package spreader/baseplate
- package path: die to package to heat sink
- cooling boundary: heat sink, cold plate, airflow, or fixture boundary
- manufacturing route: package stack, attach, mounting, or TIM update
- validation method: thermal resistance partition and boundary sensitivity
- risk profile: may miss die-near bottlenecks if interface data is incomplete

## When To Use
Use when package stack, mounting, or boundary resistance is plausible and a near-term route is needed.

## When Not To Use
Do not rely on it alone if evidence shows the dominant resistance is inside the die-near stack.

## Critical Assumptions
- Package stack and mounting boundary can be described.
- Interface thermal resistance is not ignored.
- Electrical, RF, and mechanical constraints remain acceptable.

## Main Red Flags
- Ideal contact assumptions.
- Missing package-to-heat-sink boundary.
- Supplier TIM claims without test conditions.

## Required Input Data
- Package stack and thicknesses.
- Interface materials and process notes.
- Heat source geometry and power.
- Boundary condition and target margin.

## Validation Path
Partition thermal resistance, run sensitivity checks, and compare with package-level thermal test data.

## Falsification Criterion
If die-near resistance dominates after bounded analysis, package-only improvements are not sufficient.

## Supplier Data Request
Request TIM, attach, baseplate, flatness, mounting, and test-condition data.

## Claim Safety Guidance
Describe this as a near-term route candidate, not a guaranteed fix.

## Public-Safe Summary
Conventional package upgrades can be a valid first route when package and boundary uncertainties are large.

## Internal Notes Placeholder
TODO: Add case-specific reviewed notes only.

## Related Patterns
- PAT-SIC-ALN-001
- PAT-VAPOR-PKG-001
- PAT-CUDIA-001
