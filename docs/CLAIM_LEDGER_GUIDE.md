# Claim Ledger Guide

## Purpose

The claim ledger prevents unsupported conclusions from entering architecture decisions, supplier specifications, and customer memos.

## Required Fields

`claim_id`: Stable identifier, such as `CLM-001`.

`claim`: The exact statement being made. Keep it narrow and testable.

`claim_type`: The evidence role of the statement. Use `pattern_based`, `screening`, or `architecture_screening` when a reusable pattern supports reasoning but does not provide case validation.

`basis`: Source of the claim, such as public literature, assumption, calculation, simulation, measurement, or expert review.

`assumptions`: Conditions that must be true for the claim to hold.

`confidence`: Low, medium, or high. Use low when data is incomplete.

`validation_required`: What must be done before the claim can support a decision or customer-facing statement.

`status`: Proposed, under review, validated, rejected, or retired.

`public_release`: Yes, no, or needs review.

`confidentiality_level`: Public, internal, customer-confidential, or restricted.

## Review Rule

Do not use a claim in a customer memo unless its status, basis, confidence, validation need, and public release status are clear.

Pattern-based claims are not validated claims unless they are tied to measured or reviewed evidence for the specific case. A pattern ID may support screening structure, but it does not prove performance, manufacturability, reliability, or customer suitability by itself.

Pattern-based claims must keep confidence at low or medium until validation supports a stronger level. Do not mark one validated while validation remains open unless validation evidence is referenced. Public release of pattern-only reasoning requires completed review, and the pattern ID must exist in `patterns/pattern_index.yml`.
