# Diamond Submount

## Pattern ID
PAT-DIA-SUBMOUNT-001

## Pattern Name
Diamond submount

## Problem Type Addressed
Die-near thermal spreading and conduction through a submount path.

## Typical Use Cases
- Existing submount or carrier may limit heat spreading.
- Moving high-conductivity material closer to the die is plausible.
- Mechanical and attach constraints can be reviewed.

## Architecture Genome Mapping
- heat source: semiconductor die or active region
- substrate: existing die with submount or carrier
- bonding interface: die-to-submount attach and submount-to-package attach
- heat spreader: diamond submount
- package path: die to submount to baseplate or heat sink
- cooling boundary: package and heat sink boundary remain relevant
- manufacturing route: replace or evaluate submount material
- validation method: attach resistance review and stress-informed thermal comparison
- risk profile: attach TBR, bonding quality, and thermomechanical mismatch

## When To Use
Use when die-near submount resistance is plausible and integration constraints are acceptable.

## When Not To Use
Do not use before bounding die attach, submount attach, CTE, and assembly constraints.

## Critical Assumptions
- Interface thermal resistance is bounded for both sides of the submount.
- Bonding quality can be inspected.
- Mechanical stress does not create unacceptable reliability risk.

## Main Red Flags
- Submount material compared without attach data.
- No CTE or reliability review.
- Package boundary left undefined.

## Required Input Data
- Die size, heat source geometry, and power.
- Current submount material and attach stack.
- Candidate diamond dimensions and metallization.
- Mechanical and reliability constraints.

## Validation Path
Compare stack resistance, inspect attach quality, and run reliability-relevant thermal cycling or power cycling when needed.

## Falsification Criterion
If attach or stress risk dominates the route, do not treat the submount as the near-term answer.

## Supplier Data Request
Request diamond submount dimensions, surface finish, metallization, flatness, attach compatibility, and inspection criteria.

## Claim Safety Guidance
Keep claims conditional on interface and reliability review.

## Public-Safe Summary
A diamond submount can be useful near the die, but attach resistance and mechanical integration are central risks.

## Internal Notes Placeholder
TODO: Add case-specific reviewed notes only.

## Related Patterns
- PAT-DIA-SPREADER-001
- PAT-GAN-DIA-001
- PAT-SIC-ALN-001
