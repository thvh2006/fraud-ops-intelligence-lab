# Non-linear challenger decision

## Selection

`gbm_transaction` is selected by a governed policy rule: maximize mean daily
precision at 100 entity-deduplicated alerts, but prefer the transaction-only model
unless added feature families improve absolute precision by at least 1 percentage
point. Selection reason: `parsimony_gate: best added-feature gain 0.0030 is below 0.0100`. All candidates use the same
development, calibration, policy, and locked OOT boundaries.

## Feature-family ablation on the policy window

- `gbm_plus_behaviour`: policy precision@100 **31.04%**, AP **0.401**, exposure capture **37.69%**.
- `gbm_transaction`: policy precision@100 **31.09%**, AP **0.398**, exposure capture **36.90%**.
- `gbm_plus_identity`: policy precision@100 **31.39%**, AP **0.404**, exposure capture **37.32%**.

The ablation isolates whether identity and behavioural history improve the operational queue; it does not attribute causality to anonymous source variables.

## Locked OOT evidence for the selected challenger

- Average precision: **0.461**
- ROC-AUC: **0.880**
- Brier score: **0.0241**
- Mean daily precision@100: **34.84%**
- Mean daily recall@100: **35.80%**
- Mean daily fraud-exposure capture@100: **32.44%**
- Calibrated linear reference precision@100: retained as a floor, not a headline uplift claim.
- Feature-family comparisons: interpreted with paired day-level uncertainty.

## Promotion gate

The challenger is promoted for policy design only if it improves the declared policy metric and does not create an incoherent friction/exposure trade-off. Promotion here means “preferred for the next offline policy stage,” not production deployment.
