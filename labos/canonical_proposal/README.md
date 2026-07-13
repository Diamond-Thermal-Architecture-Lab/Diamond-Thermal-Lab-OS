# Canonical Decision Proposal

This package produces a deterministic, proposal-only replacement for a canonical `02_decision_board.md`. It requires a valid Decision Review Package and a final Human Decision Record whose validator result is `PASS`.

It writes four separate review artifacts to an explicit output directory. It never applies the proposal, edits a canonical case, verifies human identity, or treats a JSON record as a cryptographic signature. Canonical application remains a separate, explicit pull-request workflow.
