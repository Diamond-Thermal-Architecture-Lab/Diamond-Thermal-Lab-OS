# Vapor Chamber Package Upgrade

## Pattern ID
PAT-VAPOR-PKG-001

## Pattern Name
Vapor chamber package upgrade

## Problem Type Addressed
Package-level spreading and boundary improvement.

## Typical Use Cases
- Heat must be spread across a package or module base.
- System volume and orientation allow vapor chamber integration.
- Heat flux and operating range are within supplier limits.

## Architecture Genome Mapping
- heat source: package or module-level hot spot
- substrate: existing device substrate
- bonding interface: package-to-vapor-chamber and vapor-chamber-to-heat-sink interfaces
- heat spreader: vapor chamber or heat pipe structure
- package path: package base to vapor chamber to heat sink
- cooling boundary: heat sink, airflow, or cold plate
- manufacturing route: package or module base redesign
- validation method: operating envelope review and package-level thermal test
- risk profile: orientation limits, heat flux limits, integration volume, and interface uncertainty

## When To Use
Use when boundary and spreading limits are package-level and a passive two-phase element fits the system.

## When Not To Use
Do not use when heat flux, orientation, reliability, or volume constraints are incompatible.

## Critical Assumptions
- Operating envelope is within supplier guidance.
- Interfaces to the package and heat sink are bounded.
- Orientation and mechanical constraints are known.

## Main Red Flags
- Supplier data lacks orientation or heat flux limits.
- Boundary condition remains undefined.
- Added interfaces are ignored.

## Required Input Data
- Heat source map and total power.
- Package footprint and volume.
- Orientation and operating temperature range.
- Interface stack and mounting conditions.

## Validation Path
Review supplier operating envelope and run package-level thermal testing under representative boundary conditions.

## Falsification Criterion
If operating envelope or integration volume is incompatible, reject the pattern.

## Supplier Data Request
Request heat transport limits, orientation limits, working fluid compatibility, dimensions, and test method.

## Claim Safety Guidance
Do not claim module temperature reduction until tested under the case boundary.

## Public-Safe Summary
Vapor chambers can improve package-level spreading when the operating envelope and integration constraints fit.

## Internal Notes Placeholder
TODO: Add case-specific reviewed notes only.

## Related Patterns
- PAT-CONV-PKG-001
- PAT-CUDIA-001
- PAT-DOUBLE-COOL-001
