# M15B Blind Input Manifest

**Packet version:** 1.0  
**Protocol version:** 1.0  
**Original preparation UTC:** 2026-08-11T08:38:13Z  
**Firewall revision:** 2.1 (non-semantic clarification)  
**Revised UTC:** 2026-08-11T09:42:05Z  
**Status:** Role C approved after leakage, source-fidelity, and protocol-firewall review  
**Confidentiality:** Public-safe blind material. Source identity and outcomes are withheld.

## Files provided to Role D

- `BLIND_INPUT_PACKET.yml`
- `BLIND_INPUT_MANIFEST.md`
- `ROLE_D_INFORMATION_RECEIPT.md`
- `ROLE_D_HANDOFF.md`
- `SEALED_REGISTRATION_MANIFEST.json`
- `LEAKAGE_AUDIT_REPORT.json`

The merged protocol and public repository are supplied separately from the packet.

## Authorized public-protocol context

The frozen protocol predates candidate selection and is an authorized input in full. Its public,
candidate-independent benchmark roles, category expectations, generic vocabulary, scoring
definitions, and control pass criteria are evaluation-contract information. They are not treated
as candidate-specific leakage and must not be used as source evidence.

## Included fact classes

- anonymous case identifiers;
- material categories and retained layer relationships;
- structural state before, during, and after integration;
- natural structural and process terminology;
- process order;
- stated deposition and conversion temperatures;
- stated exposure-cycle details, reactor context, pressure, and gas composition;
- layer, wafer, and lateral geometry;
- explicitly unresolved pre-outcome inputs;
- assumptions that are not derived from results; and
- retrospective-risk labels for post-fabrication geometry retained as input.

## Excluded until evidence reveal

- paper titles, authors, DOI, journal, publication identifier, and source URLs;
- candidate-screening aliases and alias-to-source mappings;
- measured or inferred stress, deflection, bow, curvature, warpage, or pretension;
- elastic modulus, resonance frequency, quality factor, dissipation, hardness, or adhesion outcomes;
- device success, failure, cracking, rupture, buckling, or delamination labels;
- causal conclusions derived from results;
- candidate-specific sealed scope or screening conclusions beyond the public protocol;
- candidate-specific expected activated rule sets;
- candidate-specific relevance mapping, scoring expectations, benchmark disposition, and rule-fix
  ideas; and
- the four sealed registration documents and the private leakage policy.

## Source-fidelity controls

- Circular radius is not rewritten as diameter.
- A supported wafer is not described as a membrane or released structure.
- The membrane exists before the deposited-layer sequence.
- Plasma-enhanced atomic layer deposition and later sulfurization remain distinct process steps.
- Known cycle timing and chamber conditions are retained rather than deleted.
- Missing sulfurization duration and cooling route remain explicit unknowns.
- No outcome-derived mechanical conclusion is converted into an input fact.

## Retrospective-risk declaration

Approximate layer thicknesses and the top-layer relationship for `M15B-CASE-A` are retained as
geometry/interface facts. They were characterized after fabrication, so the packet labels their
retrospective origin and does not import any associated mechanical response or outcome.

## Knowledge-isolation statement

This packet is the complete candidate-specific information set authorized for Role D. The Role D
session must be fresh and must not receive this Role C workspace, prior conversations, candidate
research, full papers, sealed files, private policy, Library files, browser history, or source links.
Public protocol statements frozen before candidate selection remain authorized and are not a
contamination event merely because they express generic benchmark expectations or control criteria.

## Leakage-audit status

The candidate-specific Role D inputs and the candidate-neutral sealed hash manifest were scanned
against the private 41-token leakage policy. The completed audit returned `pass` with 0 findings.
The generated public-safe audit report is included as `LEAKAGE_AUDIT_REPORT.json`; the report is an
output of the scan and is not counted as one of its scanned input files.
