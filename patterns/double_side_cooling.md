# Double-Side Cooling

## Pattern ID
PAT-DOUBLE-COOL-001

## Pattern Name
Double-side cooling

## Problem Type Addressed
Single-path package cooling limitation where a second heat path may reduce thermal resistance.

## Typical Use Cases
- Package layout permits top and bottom heat extraction.
- Electrical, RF, or optical access is compatible.
- Boundary conditions on both sides can be defined.

## Architecture Genome Mapping
- heat source: semiconductor die or module hot spot
- substrate: existing or modified stack
- bonding interface: top-side and bottom-side interfaces
- heat spreader: package-dependent spreaders or cold plates
- package path: parallel top and bottom heat paths
- cooling boundary: two defined cooling surfaces
- manufacturing route: package and assembly redesign
- validation method: dual-boundary model and package feasibility test
- risk profile: mechanical complexity, access constraints, and boundary uncertainty

## When To Use
Use when a second heat path is feasible and boundary definition is strong enough for comparison.

## When Not To Use
Do not use when RF, mechanical, service, or electrical constraints block top-side access.

## Critical Assumptions
- Both cooling boundaries are real and maintainable.
- Interfaces on both paths can be controlled.
- Package complexity is acceptable.

## Main Red Flags
- One cooling side modeled as ideal.
- Missing mechanical keep-out review.
- Added cooling path conflicts with RF or interconnect needs.

## Required Input Data
- Package layout and keep-out zones.
- Heat source map and power.
- Top and bottom boundary conditions.
- Interface materials and mechanical constraints.

## Validation Path
Run dual-boundary sensitivity and validate with a fixture that represents both paths.

## Falsification Criterion
If the second path cannot be physically or electrically integrated, reject the pattern for the case.

## Supplier Data Request
Request fixture constraints, interface materials, clamping requirements, and reliability limits.

## Claim Safety Guidance
Discuss as a package architecture option, not a simple material substitution.

## Public-Safe Summary
Double-side cooling may add thermal path capacity when package access and boundaries allow it.

## Internal Notes Placeholder
TODO: Add case-specific reviewed notes only.

## Related Patterns
- PAT-CONV-PKG-001
- PAT-MICRO-DIA-001
- PAT-VAPOR-PKG-001
