# Role D Information Receipt

**Protocol:** M15B Pre-Registration Protocol 1.0  
**Original preparation UTC:** 2026-08-11T08:38:13Z  
**Firewall revision:** 2.1 (non-semantic clarification)  
**Revised UTC:** 2026-08-11T09:42:05Z  
**Role D status:** Not yet started  
**Receipt status:** Exact prospective declaration; Role D must countersign in the fresh session.

## Exact files Role D may receive

1. `BLIND_INPUT_PACKET.yml`
2. `BLIND_INPUT_MANIFEST.md`
3. `ROLE_D_INFORMATION_RECEIPT.md`
4. `ROLE_D_HANDOFF.md`
5. `SEALED_REGISTRATION_MANIFEST.json`
6. `LEAKAGE_AUDIT_REPORT.json`
7. The merged `docs/benchmarks/M15B_PRE_REGISTRATION_PROTOCOL.md` from the frozen public repository
8. The public repository at exact baseline `2b45c63128dad6793dd753ca9300538769af8c53`

## Exact candidate-specific fact classes received

- two anonymous case inputs, identified only as `M15B-CASE-A` and `M15B-CASE-B`;
- material stacks;
- structural states before, during, and after integration;
- process order and integration methods;
- stated temperatures, pressures, gas composition, and cycle timing;
- stated layer, wafer, and lateral geometry;
- retained-interface facts;
- explicitly unresolved pre-outcome inputs;
- retrospective-risk labels attached to retained geometry/interface fields; and
- the evidence boundary and builder constraints in the blind packet.

## Authorized protocol-level information

The merged frozen protocol is received in full. Because it was frozen before final candidate
selection, Role D is allowed to see its candidate-independent benchmark design statements,
role-level category expectations, generic status and rule vocabulary, scoring definitions, and
control pass criteria. These public protocol statements are part of the evaluation contract. They
are not candidate evidence, do not reveal a sealed registration, and do not by themselves trigger
a contamination stop.

## Information explicitly not received

- source title, author, DOI, journal, publication identifier, or URL;
- full paper or supplementary material;
- candidate-screening aliases or alias-to-source mappings;
- measured outcomes or inferred mechanical quantities;
- success or failure labels;
- result-derived explanations;
- any candidate-specific sealed scope or expected screening conclusion beyond the public protocol;
- any candidate-specific expected activated M14 rule set;
- any candidate-specific relevance/N/A registration or scoring expectation;
- benchmark disposition or proposed rule fixes;
- any of the four sealed registration documents;
- the private leakage policy;
- Role B/C research reports, prior candidate conversations, or Library artifacts; and
- any source-search or browser history.

## Required Role D countersignature

Before building, Role D must state:

> I received only the files and facts listed above. I did not receive or retrieve source identity,
> full publications, outcomes, sealed registrations, candidate-specific expected activated rules,
> scores, or rule-fix ideas. I understand that candidate-independent expectations, vocabulary, and
> control criteria already published in the pre-candidate frozen protocol are authorized contract
> information, not contamination. I will use only the frozen repository, merged protocol, approved
> blind packet, and explicit Phase 3 instructions; I will build, run, freeze, commit, push, and stop.

If this statement is not true, Role D must stop and the benchmark must not proceed.
