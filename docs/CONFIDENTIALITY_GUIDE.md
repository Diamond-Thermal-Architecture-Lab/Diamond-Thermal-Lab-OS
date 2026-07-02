# Confidentiality Guide

## Purpose

This guide defines what can be included in repository artifacts. When uncertain, classify higher and use a sanitized summary.

## Level 1: Public

Can include:

- Public literature references.
- General engineering questions.
- Sanitized architecture options.
- Non-confidential assumptions.
- Public-safe examples.

Cannot include customer names unless approved, non-public measurements, proprietary process parameters, supplier pricing, or contract details.

## Level 2: Internal

Can include internal summaries, sanitized lessons learned, internal review notes, and references to restricted sources by neutral identifier.

Cannot include detailed restricted process recipes, customer-confidential designs, or raw internal measurement data unless explicitly cleared.

## Level 3: Customer-Confidential

Can include only in approved private storage: customer problem statements, stack descriptions, operating constraints, and project-specific validation results.

Cannot include in public-safe repository artifacts: customer names, pricing, contract details, unreleased products, exact geometry, or proprietary constraints.

Repository artifacts should use anonymized summaries and sanitized identifiers.

## Level 4: Restricted

Includes proprietary MPCVD recipes or process know-how, restricted process parameters, chamber design details, partner-confidential methods, export-controlled information, or regulated information.

Do not include restricted details in this repository. Use only sanitized summaries and non-sensitive source identifiers.

## Review Rule

Every case artifact must state a confidentiality level. Customer-facing language must be checked separately from internal engineering notes.
