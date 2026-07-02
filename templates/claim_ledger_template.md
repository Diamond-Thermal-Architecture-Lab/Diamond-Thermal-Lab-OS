# Claim Ledger: <case title>

## Purpose

Track every technical claim that may influence a decision, supplier specification, or customer memo.

## When To Use

Use throughout the case. Update it before PR review and before any customer-facing memo.

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
| CLM-001 | <claim> | <basis> | <assumptions> | Low / Medium / High | <need> | Proposed / Validated / Rejected | Yes / No / Needs Review | public / internal / customer-confidential / restricted |

## Review Checklist

- [ ] Each claim is narrow and testable.
- [ ] Each claim has basis and assumptions.
- [ ] Customer-facing claims are marked for release.

## Confidentiality Note

Do not include restricted source content in the claim text.

## Claim Safety Note

Claims with low confidence or missing validation must not be used as final conclusions.
