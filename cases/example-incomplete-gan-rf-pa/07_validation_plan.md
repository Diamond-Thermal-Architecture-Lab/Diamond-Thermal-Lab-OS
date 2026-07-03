# Validation Plan: Example Incomplete GaN RF PA

| Validation ID | Question | Method | Parameter To Measure | Sample Or Fixture | Success Criteria | Falsification Criteria | Required Equipment | Risk If Not Done |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| VAL-001 | Does interface resistance dominate route ranking? | Sensitivity analysis over plausible interface ranges | Effective interface thermal resistance | Bounded model, no physical sample required initially | Ranking sensitivity is understood | Route ranking changes unpredictably across plausible interface values | Thermal modeling tool or spreadsheet | A high-conductivity route may be selected for the wrong reason. |
| VAL-002 | Is the cooling boundary limiting? | Thermal resistance partition and boundary review | Package-to-heat-sink thermal resistance | Current package and heat sink description | Boundary contribution is bounded | Boundary dominates and material route alone cannot meet target | Package stack data, heat sink data | Material changes may fail to improve junction temperature. |
| VAL-003 | Is direct GaN-on-Diamond justified? | Compare simpler routes before die-near route | Route-level thermal leverage and integration burden | Architecture comparison | Simpler routes are shown insufficient before escalation | Package or submount routes look adequate | Bounded model and integration review | Expensive process route may be chosen prematurely. |

## Claim Safety

No validation has been completed in this example. The plan defines what must be checked before stronger conclusions are allowed.
