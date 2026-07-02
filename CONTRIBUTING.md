# Contributing

## Contribution Scope

Contributions should improve the GaN-on-Diamond engineering validation Lab OS while preserving confidentiality and review discipline. Keep changes focused, public-safe, and aligned with the task layer.

## Contribution Flow

Use this workflow for substantive changes:

Issue -> Task Brief -> Design Doc -> Simulation / Measurement Plan -> Spec -> PR Review -> Merge

For MVP decision cases, use the case workflow:

problem intake -> thermal design passport -> decision board -> architecture comparison -> red flags -> next best action -> validation plan -> supplier specification -> customer memo -> claim ledger -> engineering memory update

Small L0 documentation fixes may use a shorter path, but the PR should still explain scope, layer, and confidentiality impact.

## Branch and PR Expectations

- Use a descriptive branch name.
- Keep PRs small enough for technical and confidentiality review.
- Link the related issue or task brief.
- Complete the PR template.
- Do not mix unrelated layers or unrelated engineering cases in one PR.
- State whether API was used. The expected MVP answer is no.

## Required Artifacts by Layer

| Layer | Minimum Artifact |
| --- | --- |
| L0 Lab OS | PR summary and review checklist. |
| L1 Architecture | Task brief plus design doc when decisions are introduced. |
| L2 Engineering Case | Task brief plus simulation case or analysis note. |
| L3 Validation | Measurement plan plus data handling notes. |
| L4 Specification | Reviewed specification with version history and acceptance checks. |

## Confidentiality Review

Before submitting, confirm that the change does not include:

- Proprietary MPCVD recipes or process know-how.
- Restricted process parameters or chamber design details.
- Customer data, supplier pricing, contract details, or confidential project details.
- Unreleased measurements or performance metrics that have not been cleared for publication.
- Claims that imply validated performance without evidence and review.
- API-generated long reports, customer memos, full case packs, or automatic paid API calls.

## Documentation Style

- Use concise engineering language.
- Prefer checklists, short tables, and explicit assumptions.
- Identify evidence sources for technical claims.
- Mark unresolved questions instead of hiding uncertainty.
- Avoid marketing tone and broad unsupported claims.

## Review Checklist

- [ ] The change is mapped to a Lab OS layer.
- [ ] The related issue or task brief is linked.
- [ ] Confidentiality-sensitive information has been removed or sanitized.
- [ ] Technical claims are verified, cited, or clearly marked as assumptions.
- [ ] The PR is narrow and reviewable.
- [ ] The next step is clear.
