# Diamond Heat Spreader

## Pattern ID
PAT-DIA-SPREADER-001

## Pattern Name
Diamond heat spreader

## Problem Type Addressed
Localized heat spreading near a high heat flux source.

## Typical Use Cases
- Lateral spreading is likely limiting.
- A package-level or near-die spreader can be integrated without changing the device process.
- Interface and bonding quality can be bounded.

## Architecture Genome Mapping
- heat source: localized semiconductor active region or die hot spot
- substrate: existing device substrate
- bonding interface: spreader attach or die attach interface
- heat spreader: diamond heat spreader
- package path: die/substrate to spreader to package/cooling boundary
- cooling boundary: heat sink or cold plate must still be defined
- manufacturing route: attach or integrate diamond spreader in package path
- validation method: interface sensitivity, spreading model, attach inspection
- risk profile: benefit can be limited by interface thermal resistance and bonding quality

## When To Use
Use when geometry supports spreading benefit and the added interface can be controlled or bounded.

## When Not To Use
Do not use when cooling boundary dominates or when the diamond interface is unknown and likely poor.

## Critical Assumptions
- Interface thermal resistance is bounded.
- Bonding quality is inspectable.
- Heat source size and location are known enough for spreading estimates.

## Main Red Flags
- Bulk diamond conductivity used without interface discussion.
- Missing attach thickness or void information.
- Supplier data lacks boundary conditions.

## Required Input Data
- Heat source dimensions and power.
- Existing stack and spreader location.
- Attach material, thickness, void tolerance, and surface requirements.
- Cooling boundary.

## Validation Path
Run interface sensitivity, inspect attach quality, and validate with package-level or coupon thermal data.

## Falsification Criterion
If interface resistance consumes the expected spreading benefit, do not advance the pattern.

## Supplier Data Request
Request diamond grade, thickness, surface finish, metallization, attach guidance, and thermal test basis.

## Claim Safety Guidance
Say "candidate heat spreading route" until validation supports stronger language.

## Public-Safe Summary
Diamond heat spreaders may help localized heat spreading, but interface quality controls much of the value.

## Internal Notes Placeholder
TODO: Add case-specific reviewed notes only.

## Related Patterns
- PAT-DIA-SUBMOUNT-001
- PAT-CUDIA-001
- PAT-CONV-PKG-001
