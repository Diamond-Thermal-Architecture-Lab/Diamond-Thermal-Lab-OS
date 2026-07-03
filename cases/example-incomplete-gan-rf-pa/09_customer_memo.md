# Customer Memo: Example Incomplete GaN RF PA

Memo ID: MEMO-001

## Audience

Technical customer stakeholder.

## Decision Summary

The current information is not sufficient to select a final thermal architecture. Diamond-based options may be relevant, but direct GaN-on-Diamond should not be the default first recommendation.

## What Is Known

- The device is a GaN RF PA.
- The application is high-power RF.
- The current package is overheating.
- The customer is considering both diamond and non-diamond routes.

## What Is Unknown

- Heat source geometry and power density.
- Interface thermal resistance.
- Package-to-heat-sink boundary condition.
- RF, mechanical, cost, and schedule constraints.

## Recommended Next Step

Define bounded assumptions for the heat source, stack, interfaces, and cooling boundary. Then compare conventional package improvement, diamond spreader/submount routes, Cu-diamond composite, die-near diamond routes, double-side cooling, and cooling-boundary improvements under the same assumptions.

## Claims Allowed

- The conclusion is preliminary and assumption-based.
- Additional input is needed before selecting a final architecture.
- Interface resistance and cooling boundary are top uncertainties.

## Claims Not Allowed

- Diamond is required.
- Direct GaN-on-Diamond is the best first step.
- Any route will meet the temperature target.
- Any numeric junction temperature reduction has been validated.

## Validation Needed

- Interface sensitivity.
- Cooling-boundary review.
- Heat source and stack definition.
- Route screening under bounded assumptions.

## Confidentiality Level

public
