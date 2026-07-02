# Red Flags: Example Incomplete GaN RF PA

## Purpose

Identify conditions that could invalidate a thermal architecture recommendation.

## When To Use

Use before selecting next best action or drafting customer language.

## Required Fields

- Case ID: example-incomplete-gan-rf-pa
- Red flag:
- Why it matters:
- Evidence status:
- Severity:
- Mitigation:
- Owner:

## Red Flags

| ID | Red Flag | Why It Matters | Severity | Mitigation | Status |
| --- | --- | --- | --- | --- | --- |
| RF-001 | Interface thermal resistance is unknown | A poor interface can dominate the thermal path and reduce benefit from high-conductivity materials | High | Bound die attach, spreader, submount, TIM, and package interfaces | Open |
| RF-002 | Cooling boundary is uncertain | Package improvements may fail if the heat sink or ambient boundary is limiting | High | Define heat sink, mounting, flow, and temperature reference | Open |
| RF-003 | Heat source geometry is incomplete | Lateral spreading value depends strongly on heat source size and location | High | Request sanitized heat map or bounded dimensions | Open |
| RF-004 | Direct GaN-on-Diamond may be over-scoped | It may add cost and process risk before proving simpler routes are insufficient | Medium | Treat as later option after bounding analysis | Open |
| RF-005 | Customer-facing language may overstate diamond need | Premature claims can create cost and expectation risk | Medium | Use conservative memo language and claim ledger review | Open |

## Review Checklist

- [x] Missing inputs are treated as risks.
- [x] Interface and boundary-condition risks are checked.
- [x] Red flags are linked to next actions.

## Confidentiality Note

This file describes generic risks only.

## Claim Safety Note

No red flag is presented as a confirmed failure mechanism.
