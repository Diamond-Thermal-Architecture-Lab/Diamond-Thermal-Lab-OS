# Engineering Memory Entry: Example Incomplete GaN RF PA

## Purpose

Capture reusable lessons from this reviewed example without exposing confidential details.

## When To Use

Use after the case reaches a reviewed decision point.

## Required Fields

- Memory ID: MEM-EXAMPLE-GAN-RF-PA-001
- Source case: example-incomplete-gan-rf-pa
- Problem pattern: customer asks whether diamond is needed for overheating GaN RF PA
- Reusable assumptions: heat source, interface, and cooling boundary are often decision-critical
- Decision pattern: compare package, spreader, submount, die-near, and system cooling routes before final recommendation
- Red flags: unknown interface resistance and cooling boundary
- Validation lessons: use bounded assumptions before expensive simulation
- Supplier/spec lessons: start with information request, not final spec
- Customer language lessons: conservative, preliminary, no performance promise
- Confidentiality level: public

## Entry

When a GaN RF PA customer asks whether diamond is needed, the first useful output is not a final architecture recommendation. The reusable pattern is to structure the missing inputs, compare diamond and non-diamond routes neutrally, identify interface and boundary risks, and recommend bounded assumptions before costly simulation or supplier commitment.

Direct GaN-on-Diamond should remain a candidate route, but not the default first step unless the evidence shows that package-level, submount-level, spreading, or cooling-boundary improvements are insufficient.

## Review Checklist

- [x] The entry is reusable across future cases.
- [x] It does not expose customer-confidential details.
- [x] It links back to claims and validation status.

## Confidentiality Note

This is a generalized public-safe example.

## Claim Safety Note

This entry does not turn one provisional case into a universal rule.
