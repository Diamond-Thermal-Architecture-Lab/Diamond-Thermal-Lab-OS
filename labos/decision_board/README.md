# Decision Board Preview

This package builds a deterministic, read-only Decision Board preview from an existing canonical case, the structured triage result, and approved pattern references. It does not edit `02_decision_board.md`, select a winning architecture, or establish a validated thermal conclusion.

Use `python scripts/labos_case.py decision-board <case-path>` for a concise preview or add `--json` for stable structured output. Pattern references remain screening candidates; any approved decision requires case-specific evidence, human review, and a validation path.
