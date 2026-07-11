# Red Flags: Example Incomplete GaN RF PA

| Flag ID | Type | Severity | Description | Why It Matters | Affected Decision | Required Data Or Action | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RF-001 | missing-interface-data | high | Interface thermal resistance is unknown. | A poor interface can dominate the thermal path and reduce value from high-conductivity materials. | Route ranking | Bound die attach, submount, TIM, and package interfaces. | open |
| RF-002 | missing-boundary-data | high | Package-to-heat-sink boundary is uncertain. | Cooling boundary can dominate junction temperature. | Whether package/material changes will help | Define heat sink, mounting, flow, and reference temperature. | open |
| RF-003 | missing-heat-source-geometry | high | Heat source size and location are incomplete. | Spreading benefit depends strongly on heat source geometry. | Heat spreader and submount selection | Request sanitized heat map or bounded dimensions. | open |
| RF-004 | premature-diamond-selection | medium | Direct GaN-on-Diamond may be over-scoped. | It may add cost and process risk before simpler routes are ruled out. | Route selection | Hold die-near diamond as later candidate. | open |
| RF-005 | customer-language-risk | medium | Customer-facing language may overstate diamond need. | Premature claims can create expectation and cost risk. | Customer memo | Use claim ledger and conservative memo language. | open |

## Pattern References

- `PAT-DIA-SPREADER-001`, `PAT-DIA-SUBMOUNT-001`, and `PAT-GAN-DIA-001` reinforce that interface thermal resistance and bonding quality are critical uncertainties for diamond routes.
- `PAT-CONV-PKG-001` reinforces that conventional package improvement remains a serious near-term candidate while package and cooling boundary data are incomplete.
- `PAT-CUDIA-001`, `PAT-DOUBLE-COOL-001`, and `PAT-MICRO-DIA-001` remain screening alternatives only until boundary, interface, and integration assumptions are bounded.

## Review Note

No red flag is a confirmed failure mechanism. Each one identifies missing evidence that could change the decision.
