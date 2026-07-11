# SiC Or AlN Substrate Upgrade

## Pattern ID
PAT-SIC-ALN-001

## Pattern Name
SiC or AlN substrate/carrier upgrade

## Problem Type Addressed
Neutral non-diamond substrate, carrier, or package material improvement.

## Typical Use Cases
- Existing substrate or carrier is a plausible bottleneck.
- A lower-integration-risk non-diamond route is attractive.
- Supplier and reliability data are available.

## Architecture Genome Mapping
- heat source: semiconductor die or package hot spot
- substrate: SiC, AlN, or related carrier/substrate route
- bonding interface: die attach and substrate/package interfaces
- heat spreader: substrate or carrier acts as spreading path
- package path: die to carrier/substrate to package
- cooling boundary: package and heat sink remain important
- manufacturing route: substrate, carrier, or package material upgrade
- validation method: stack resistance comparison and mechanical compatibility review
- risk profile: interface dominance, supplier variation, and CTE mismatch

## When To Use
Use when a non-diamond material route could meet needs with lower integration risk.

## When Not To Use
Do not use when interface or boundary resistance dominates and substrate change has little leverage.

## Critical Assumptions
- Material property range is supplier-specific.
- Interfaces are bounded.
- Mechanical constraints are acceptable.

## Main Red Flags
- Treating material conductivity as the full stack result.
- Missing attach data.
- No reliability review.

## Required Input Data
- Candidate material grade and thickness.
- Interface stack.
- Heat source geometry and power.
- Mechanical and reliability constraints.

## Validation Path
Compare stack resistance, review supplier data, and validate with fixture or package test where needed.

## Falsification Criterion
If stack analysis shows boundary or interface dominance, deprioritize substrate change.

## Supplier Data Request
Request material grade, thermal properties, CTE, surface finish, tolerances, and inspection basis.

## Claim Safety Guidance
Frame as a comparative route, not a universal substitute for diamond or copper.

## Public-Safe Summary
SiC and AlN routes can be valid non-diamond options when the stack supports them.

## Internal Notes Placeholder
TODO: Add case-specific reviewed notes only.

## Related Patterns
- PAT-CONV-PKG-001
- PAT-DIA-SUBMOUNT-001
- PAT-CUDIA-001
