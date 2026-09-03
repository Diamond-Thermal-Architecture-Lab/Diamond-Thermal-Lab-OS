# AGENTS.md

## Repository Role

This repository is the focused GaN-on-Diamond engineering validation lab for Diamond Thermal Architecture Lab. It is used to organize public-safe engineering tasks, design reasoning, simulation cases, measurement plans, specifications, and review records.

For the MVP, this repository is also a GitHub-native thermal architecture decision system. It converts incomplete semiconductor thermal problems into structured intake, thermal design passports, decision boards, architecture comparisons, red flags, next best actions, validation plans, supplier specifications, customer memos, claim ledgers, and reusable engineering memory.

## Operating Principles

- Keep work professional, international, engineering-oriented, and non-marketing.
- Use the Lab OS workflow for substantive changes: Issue -> Task Brief -> Design Doc -> Simulation / Measurement Plan -> Spec -> PR Review -> Merge.
- Keep documents concise. Prefer scoped briefs, checklists, and traceable assumptions over broad narrative reports.
- Separate verified facts, assumptions, hypotheses, and open questions.
- Do not claim performance metrics unless they are verified, source-backed, and appropriate for the repository.

## Execution and Delivery Conventions

- Base conclusions on the actual repository, applicable agreements, and executed verification. Treat user assumptions and prior conversation conclusions as unverified until evidenced; distinguish facts, inferences, and recommendations.
- For authorized work, independently inspect, implement, troubleshoot, verify, and deliver. Do not require command-by-command direction for routine in-scope work or repeat an unchanged failure without new evidence.
- These conventions grant no new authority. Obtain explicit authorization before expanding scope, changing freeze rules or protected semantics, merging, deploying, or taking destructive action; never bypass authentication, permissions, or approvals.
- Preserve user work and frozen history. Do not make checks pass by changing historical expectations, weakening acceptance criteria, or rewriting historical results. Respect the current role's evidence-access and independence boundaries; author self-checks are not independent review.
- Prefer the smallest necessary change and run verification proportionate to risk. Do not omit required checks, and do not add scientific-freeze or governance process to an ordinary documentation task. Report conclusions from actual runs and list checks not run.
- When work fails, preserve safe, valuable work and necessary non-sensitive diagnostics. Do not delete user files, revert commits, or clear the worktree without authorization.
- After each delivery, recommend one evidence-based next step with user value, minimum scope, acceptance criteria, risk, and required authorization. It is valid to recommend no development; do not create work merely to continue working.
- Recommend a suitable model and reasoning level for the next step, without claiming that instructions switched models. State whether to continue the current conversation or open a project task or independent-review conversation.
- Separate user operating instructions from task handoff. Provide a handoff prompt only when handoff is needed, and do not make users repeatedly copy long instructions within one task.

## Codex Should Do

- Preserve confidentiality before completeness. If a request would expose restricted information, stop and ask for a sanitized direction.
- Use the templates in `templates/` for new task briefs, design docs, simulation cases, measurement plans, substrate specs, and literature notes.
- Use the MVP case templates for `cases/<case_id>/` artifacts and keep the case workflow manual unless API use is explicitly reviewed later.
- Keep changes narrowly scoped to the requested Lab OS layer.
- Add or update review checklists when a workflow step changes.
- Mark assumptions clearly and identify evidence sources for technical claims.
- Recommend labels that match the task layer, work type, status, and domain.

## Codex Should Not Do

- Do not edit existing issues unless explicitly asked.
- Do not create or disclose proprietary MPCVD recipes or process know-how.
- Do not include restricted process parameters, chamber design details, customer data, supplier pricing, or confidential project details.
- Do not invent validation results, yield data, reliability data, thermal metrics, or material performance claims.
- Do not convert exploratory ideas into specifications without a documented review path.
- Do not broaden a task into large technical documentation unless explicitly requested.
- Do not add API automation or paid GitHub Actions for the MVP.
- Do not blindly recommend diamond when conventional package, interface, cooling-boundary, or non-diamond routes remain plausible.

## Confidentiality Guardrails

Treat the following as restricted unless the repository owner explicitly provides a public-safe version:

- Proprietary growth, bonding, or substrate preparation process details.
- Equipment configuration details that reveal unique process capability.
- Customer, supplier, pricing, schedule, or contract information.
- Unreleased measurements, internal failure analysis, and non-public design trade studies.
- Any export-controlled or partner-confidential information.

## Expected Output Shape

For most repository tasks, Codex output should include:

- A short summary of the change.
- The Lab OS layer touched.
- The artifact path or issue reference.
- Confidentiality notes or assumptions.
- Recommended next step.
