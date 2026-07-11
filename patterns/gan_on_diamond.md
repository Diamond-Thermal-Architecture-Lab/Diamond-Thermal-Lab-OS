# GaN-on-Diamond

## Pattern ID
PAT-GAN-DIA-001

## Pattern Name
GaN-on-Diamond or GaN bonded to diamond

## Problem Type Addressed
Die-near thermal path limitation where a high-potential integrated diamond route may be justified.

## Typical Use Cases
- Package-level and submount routes are insufficient under bounded assumptions.
- Die-near thermal resistance dominates the case.
- Schedule, qualification, and process integration risk are acceptable.

## Architecture Genome Mapping
- heat source: GaN active region
- substrate: GaN device integrated with diamond route
- bonding interface: GaN/diamond or process-dependent transition interface
- heat spreader: diamond substrate or carrier
- package path: die-near path to package base and cooling system
- cooling boundary: package and system boundary must still be defined
- manufacturing route: bonding, transfer, or direct integration route
- validation method: interface characterization, die-level thermal validation, and reliability screening
- risk profile: high potential with higher integration, bonding, process, and qualification risk

## When To Use
Use as a later-stage route when evidence shows die-near resistance dominates and simpler routes are not enough.

## When Not To Use
Do not use as the default first step for an overheating GaN device without validation basis.

## Critical Assumptions
- GaN/diamond interface TBR is bounded.
- Bonding quality is controlled and inspectable.
- Device performance and reliability are not compromised.
- Package and cooling boundary do not dominate.

## Main Red Flags
- Direct GaN-on-Diamond proposed before geometry and boundary are known.
- Interface TBR omitted from comparison.
- Process feasibility treated as solved without evidence.

## Required Input Data
- Die layout and heat source map.
- Existing substrate and package path.
- Candidate integration route and interface data.
- Reliability, RF, and qualification constraints.

## Validation Path
Characterize interface TBR, compare die-level thermal response, and define reliability screening before commitment.

## Falsification Criterion
If interface TBR, process risk, or qualification burden is unacceptable, keep this route out of the near-term recommendation.

## Supplier Data Request
Request integration route, interface characterization basis, sample structure, inspection method, and reliability evidence.

## Claim Safety Guidance
Frame as high-potential and high-integration-risk. Do not state it is required without case-specific evidence.

## Public-Safe Summary
GaN-on-Diamond can be high potential, but it is not the default first step and depends strongly on interface and integration risk.

## Internal Notes Placeholder
TODO: Add case-specific reviewed notes only.

## Related Patterns
- PAT-DIA-SUBMOUNT-001
- PAT-DIA-SPREADER-001
- PAT-CONV-PKG-001
