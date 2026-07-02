# Lab OS

## Purpose

The Lab OS defines how this repository organizes GaN-on-Diamond engineering validation work. It is intentionally lightweight: it provides workflow structure, confidentiality boundaries, review expectations, and templates without becoming a large technical handbook.

## Workflow

All substantive work should move through this path:

Issue -> Task Brief -> Design Doc -> Simulation / Measurement Plan -> Spec -> PR Review -> Merge

Decision-system case work should move through this MVP loop:

Thermal Intake -> Thermal Design Passport -> Decision Board -> Architecture Comparison -> Red Flags -> Next Best Action -> Validation Plan -> Supplier Specification -> Customer Memo -> Claim Ledger -> Engineering Memory Update

1. Issue: define the problem, owner, priority, Lab OS layer, and expected artifact.
2. Task Brief: clarify objective, scope, assumptions, inputs, deliverables, and acceptance criteria.
3. Design Doc: document the engineering approach, alternatives, risks, interfaces, and open questions.
4. Simulation / Measurement Plan: define how the case will be explored or validated using public-safe parameters.
5. Spec: capture reviewed requirements, interfaces, acceptance checks, and version history.
6. PR Review: verify confidentiality, traceability, scope control, and documentation quality.
7. Merge: integrate only reviewed, public-safe, and properly scoped artifacts.

## Task Layers

| Layer | Name | Purpose | Typical Artifacts |
| --- | --- | --- | --- |
| L0 | Lab OS | Repository operating system, workflow, templates, labels, review policy. | `AGENTS.md`, templates, PR template, contribution rules. |
| L1 | Architecture | Non-confidential system structure and decision framing. | Architecture notes, design docs, interface summaries. |
| L2 | Engineering Case | Focused analysis or simulation of one engineering question. | Task briefs, simulation cases, comparison notes. |
| L3 | Validation | Measurement planning, evidence capture, validation logic. | Measurement plans, data handling notes, validation checklists. |
| L4 | Specification | Reviewed requirements and controlled public-safe specs. | Substrate specs, acceptance criteria, revision history. |

## Confidentiality Rules

- Public-safe by default does not mean public-complete. Omit restricted implementation details.
- Do not include proprietary MPCVD recipes or process know-how.
- Do not include restricted process parameters, chamber design details, customer data, supplier pricing, or confidential project details.
- Do not publish internal measurements, reliability data, yield data, or performance metrics unless they are reviewed and explicitly cleared.
- Use anonymized identifiers for samples, devices, partners, and projects unless the name is already public and approved for use.
- If a document needs restricted information to be useful, store only a sanitized summary here and reference the internal source by non-sensitive identifier.

## Documentation Style

- Write for an international engineering audience.
- Prefer concise sections, tables, and checklists.
- State assumptions explicitly.
- Separate facts, hypotheses, decisions, and open questions.
- Use SI units where appropriate, but do not expose restricted process settings.
- Cite public literature or standards when making technical claims.
- Avoid marketing language, exaggerated claims, and unverified benchmarks.
- Compare diamond and non-diamond routes neutrally unless reviewed evidence supports narrowing the option set.

## Review Checklist

Before merge, reviewers should confirm:

- [ ] The artifact follows the Lab OS workflow and references its issue or task brief.
- [ ] The correct Lab OS layer is identified.
- [ ] Confidentiality-sensitive content has been removed or sanitized.
- [ ] No proprietary process details, customer data, supplier pricing, or confidential project details are included.
- [ ] Technical claims are either source-backed, clearly marked as assumptions, or removed.
- [ ] The scope is narrow and matches the task brief.
- [ ] Open questions and next steps are clear.
- [ ] The PR template is completed.
- [ ] API use, if any, is disclosed and justified. The MVP default is no API.

## Recommended Labels

- `layer:L0-lab-os`
- `layer:L1-architecture`
- `layer:L2-engineering-case`
- `layer:L3-validation`
- `layer:L4-specification`
- `type:task-brief`
- `type:design-doc`
- `type:simulation`
- `type:measurement-plan`
- `type:spec`
- `type:literature-note`
- `type:problem-intake`
- `type:decision-board`
- `type:architecture-comparison`
- `type:validation-plan`
- `type:supplier-spec`
- `type:customer-memo`
- `type:claim-ledger`
- `status:triage`
- `status:ready-for-review`
- `status:blocked`
- `status:needs-confidentiality-review`
- `domain:thermal`
- `domain:materials`
- `domain:device-integration`
- `domain:simulation`
- `domain:measurement`
- `priority:P0`
- `priority:P1`
- `priority:P2`
