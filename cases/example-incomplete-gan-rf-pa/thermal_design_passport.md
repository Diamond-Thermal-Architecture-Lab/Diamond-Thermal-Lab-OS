# Thermal Design Passport: Example Incomplete GaN RF PA

## Purpose

Summarize the thermal architecture context needed to compare solution routes.

## When To Use

Use after intake and before selecting architecture routes.

## Required Fields

- Case ID: example-incomplete-gan-rf-pa
- Device class: GaN RF PA
- Application: high-power RF / radar-like module
- Heat generation summary: high local heat flux expected, exact geometry unknown
- Stack or package summary: likely GaN-on-SiC or conventional GaN package
- Thermal interfaces: unknown and likely decision-critical
- Cooling boundary: package-to-heat-sink boundary uncertain
- Validation status: no validation data yet

## Passport

| Area | Current Understanding | Confidence | Validation Need |
| --- | --- | --- | --- |
| Heat source | Localized RF PA heat source, geometry incomplete | Low | Obtain die layout or bounded heat-source dimensions |
| Stack | Likely GaN-on-SiC or conventional package | Low | Confirm layer stack and die attach path |
| Interfaces | Interface thermal resistance unknown | Low | Bound die attach, submount, TIM, and package interfaces |
| Cooling boundary | Heat sink boundary uncertain | Low | Define mounting, heat sink, airflow/liquid condition, and temperature reference |
| Constraints | RF, mechanical, cost, and schedule constraints not specified | Low | Collect constraints before narrowing architecture |

## Review Checklist

- [x] The passport separates facts from assumptions.
- [x] Major thermal bottlenecks are listed without overclaiming.
- [x] Boundary conditions are not treated as known when missing.

## Confidentiality Note

All stack descriptions are sanitized and provisional.

## Claim Safety Note

The passport does not claim that any route will meet the thermal target.
