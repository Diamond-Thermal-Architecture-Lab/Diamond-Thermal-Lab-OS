# Human Decision Record

`labos.decision_record` creates deterministic blank decision-record templates and validates completed records against a specific Decision Review Package.

The validator checks structure, manifest binding, route IDs, decision guardrails, customer-release guardrails, and human-entered attestations. It does not verify identity, create a cryptographic signature, approve a decision automatically, or write to canonical case artifacts.
