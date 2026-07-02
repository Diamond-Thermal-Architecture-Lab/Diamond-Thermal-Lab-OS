# Claim Ledger: Example Incomplete GaN RF PA

## Purpose

Track every technical claim that may influence the decision, supplier specification, or customer memo.

## When To Use

Use throughout the case and review before any customer-facing language.

## Required Fields

- claim_id
- claim
- basis
- assumptions
- confidence
- validation_required
- status
- public_release
- confidentiality_level

## Claims

| claim_id | claim | basis | assumptions | confidence | validation_required | status | public_release | confidentiality_level |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CLM-001 | The case is under-specified for selecting a final architecture. | Intake review | Heat source, interface, and boundary inputs are incomplete | High | Confirm missing input list | Proposed | Yes | public |
| CLM-002 | Interface thermal resistance is a top uncertainty. | Thermal path reasoning | Interfaces are present and not yet characterized | Medium | Bound interface stack and sensitivity | Proposed | Yes | public |
| CLM-003 | Package-to-heat-sink boundary may change route ranking. | Thermal resistance reasoning | Boundary condition is currently unknown | Medium | Define cooling boundary and run bounded comparison | Proposed | Yes | public |
| CLM-004 | Direct GaN-on-Diamond should not be the default first recommendation. | Architecture risk review | Simpler routes have not been ruled out | Medium | Compare routes under bounded assumptions | Proposed | Yes | public |
| CLM-005 | Diamond heat spreader, diamond submount, Cu-diamond composite, package upgrade, double-side cooling, and microchannel hybrid are plausible candidates. | Option screening | Integration constraints are not yet known | Low | Screen routes against constraints and validation plan | Proposed | Yes | public |

## Review Checklist

- [x] Each claim is narrow and testable.
- [x] Each claim has basis and assumptions.
- [x] Customer-facing claims are marked for release.

## Confidentiality Note

No restricted source content is included.

## Claim Safety Note

All claims are proposed and preliminary, not validated results.
