# Cu-Diamond Composite

## Pattern ID
PAT-CUDIA-001

## Pattern Name
Cu-diamond composite spreader or baseplate

## Problem Type Addressed
Package-level spreading, baseplate conduction, and thermal expansion tradeoffs.

## Typical Use Cases
- A package/baseplate route is plausible.
- Supplier composite data is available for review.
- Integration needs a balance of spreading and mechanical compatibility.

## Architecture Genome Mapping
- heat source: package-level heat input or die array
- substrate: existing device substrate
- bonding interface: package attach and composite attach interfaces
- heat spreader: Cu-diamond composite spreader or baseplate
- package path: package base to heat sink
- cooling boundary: heat sink or cold plate
- manufacturing route: supplier composite package element
- validation method: supplier data review, incoming inspection, and package model sensitivity
- risk profile: property variation, interface stack uncertainty, and CTE mismatch

## When To Use
Use when package-level spreading is plausible and supplier data is specific enough for review.

## When Not To Use
Do not use when die-near resistance dominates or supplier data lacks conditions and tolerances.

## Critical Assumptions
- Composite properties match the supplied part, not a generic material.
- Interfaces to package and heat sink are bounded.
- CTE and assembly constraints are acceptable.

## Main Red Flags
- Generic conductivity claims without test method.
- Missing interface and flatness data.
- No incoming inspection plan.

## Required Input Data
- Composite composition or supplier grade.
- Thickness, dimensions, flatness, and surface finish.
- Interface stack and cooling boundary.
- Heat source layout.

## Validation Path
Review supplier data, inspect incoming material, and compare package-level thermal response.

## Falsification Criterion
If supplier data is ambiguous or interfaces dominate, do not advance the route.

## Supplier Data Request
Request thermal property basis, CTE, density, surface finish, tolerances, inspection method, and operating limits.

## Claim Safety Guidance
Do not translate supplier screening values into customer performance claims.

## Public-Safe Summary
Cu-diamond composites can be useful package elements, but supplier data and interfaces must be reviewed.

## Internal Notes Placeholder
TODO: Add case-specific reviewed notes only.

## Related Patterns
- PAT-CONV-PKG-001
- PAT-DIA-SPREADER-001
- PAT-VAPOR-PKG-001
