# Microchannel Diamond Hybrid

## Pattern ID
PAT-MICRO-DIA-001

## Pattern Name
Microchannel diamond hybrid

## Problem Type Addressed
High heat load where active cooling and high-conductivity spreading may both be considered.

## Typical Use Cases
- System allows liquid cooling complexity.
- Boundary condition is dominant or severe.
- Reliability and service constraints can be addressed.

## Architecture Genome Mapping
- heat source: die, package, or module-level heat load
- substrate: existing or modified package stack
- bonding interface: cooler-to-package and possible diamond interfaces
- heat spreader: diamond element and/or microchannel cold plate
- package path: heat source to liquid cooling boundary
- cooling boundary: active liquid cooling loop
- manufacturing route: package/cooler integration
- validation method: thermal-fluid test, pressure-drop review, and reliability plan
- risk profile: fluidics, sealing, maintenance, and interface risk

## When To Use
Use when system-level cooling complexity is acceptable and simpler boundary improvements are insufficient.

## When Not To Use
Do not use when liquid cooling, maintenance, reliability, or sealing constraints are unacceptable.

## Critical Assumptions
- Coolant flow, pressure drop, and thermal boundary are defined.
- Interfaces to the cooler are bounded.
- Reliability plan covers leakage, corrosion, and service conditions.

## Main Red Flags
- Microchannel modeled without pressure drop or reliability.
- Diamond included without interface TBR.
- Cooling loop constraints missing.

## Required Input Data
- Heat load and allowable pressure drop.
- Coolant, flow, inlet temperature, and service constraints.
- Package/cooler interface.
- Reliability requirements.

## Validation Path
Run thermal-fluid testing on a representative fixture and inspect interface and sealing quality.

## Falsification Criterion
If pressure drop, reliability, or maintenance burden is unacceptable, do not advance the pattern.

## Supplier Data Request
Request flow limits, pressure drop, materials compatibility, sealing method, and test conditions.

## Claim Safety Guidance
Avoid presenting hybrid cooling as a material-only benefit.

## Public-Safe Summary
Microchannel hybrids can help severe thermal boundaries but add system complexity and validation burden.

## Internal Notes Placeholder
TODO: Add case-specific reviewed notes only.

## Related Patterns
- PAT-DOUBLE-COOL-001
- PAT-DIA-SPREADER-001
- PAT-CONV-PKG-001
