# Memory Policy

## Purpose

The memory layer preserves reusable engineering knowledge without turning preliminary screening information into unsupported claims.

## Public Vs Internal Memory

Public memory must avoid customer names, restricted process details, confidential supplier pricing, proprietary recipes, and unreleased measured results.

Internal memory may include more context, but it still must avoid unnecessary sensitive detail and must follow confidentiality labels.

## Screening Range Vs Measured Value

A screening range is a planning placeholder. It supports sensitivity analysis and supplier questions.

A measured value comes from a defined method, sample, fixture, boundary condition, and review state. Do not use screening ranges as customer-facing measured values.

## Supplier Data Vs Validated Result

Supplier data is supplier-stated evidence. It may be useful, but it is not a validated case result unless the case review accepts its basis and relevance.

## Updating `material_properties.yml`

- Keep units explicit.
- Prefer qualitative or bounded screening language until evidence is reviewed.
- Record supplier or literature basis in case files, not as universal truth.
- Avoid one fixed universal value for process-dependent materials.

## Updating `tbr_ranges.yml`

- Treat TBR as process-dependent.
- Include interface category, units, and uncertainty notes.
- Mark whether a value is placeholder, supplier-stated, literature-supported, or measured.
- Do not commit to an architecture until TBR is measured or bounded.

## Preventing Confidential Leakage

- Do not include customer identifiers in public memory.
- Do not include proprietary process recipes.
- Do not include exact internal costs or undisclosed supplier pricing.
- Use case-specific restricted files outside public examples when sensitive detail is necessary.

## Marking Assumptions

Use these statuses:

- `unvalidated`: placeholder or assumption only.
- `supplier_stated`: supplier-provided and not independently accepted.
- `reviewed_principle`: accepted engineering principle but not case-specific validation.
- `measured`: supported by measurement under defined conditions.
- `validated_for_case`: reviewed evidence supports the claim for that case.

Every customer-facing claim must still pass the claim ledger review.
