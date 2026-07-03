# Red Flags: Example Incomplete GaN RF PA

| Flag ID | Type | Severity | Description | Why It Matters | Affected Decision | Required Data Or Action | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RF-001 | missing-interface-data | high | Interface thermal resistance is unknown. | A poor interface can dominate the thermal path and reduce value from high-conductivity materials. | Route ranking | Bound die attach, submount, TIM, and package interfaces. | open |
| RF-002 | missing-boundary-data | high | Package-to-heat-sink boundary is uncertain. | Cooling boundary can dominate junction temperature. | Whether package/material changes will help | Define heat sink, mounting, flow, and reference temperature. | open |
| RF-003 | missing-heat-source-geometry | high | Heat source size and location are incomplete. | Spreading benefit depends strongly on heat source geometry. | Heat spreader and submount selection | Request sanitized heat map or bounded dimensions. | open |
| RF-004 | premature-diamond-selection | medium | Direct GaN-on-Diamond may be over-scoped. | It may add cost and process risk before simpler routes are ruled out. | Route selection | Hold die-near diamond as later candidate. | open |
| RF-005 | customer-language-risk | medium | Customer-facing language may overstate diamond need. | Premature claims can create expectation and cost risk. | Customer memo | Use claim ledger and conservative memo language. | open |

## Review Note

No red flag is a confirmed failure mechanism. Each one identifies missing evidence that could change the decision.
