# Non-linear challenger decision

## Selection

`gbm_plus_identity` wins on the pre-declared policy metric: mean daily precision at 100 entity-deduplicated alerts. All candidates use the same development, calibration, policy, and locked OOT boundaries.

## Feature-family ablation on the policy window

- `gbm_plus_behaviour`: policy precision@100 **31.04%**, AP **0.401**, exposure capture **37.69%**.
- `gbm_transaction`: policy precision@100 **31.09%**, AP **0.398**, exposure capture **36.90%**.
- `gbm_plus_identity`: policy precision@100 **31.39%**, AP **0.404**, exposure capture **37.32%**.

The ablation isolates whether identity and behavioural history improve the operational queue; it does not attribute causality to anonymous source variables.

## Locked OOT evidence for the selected challenger

- Average precision: **0.460**
- ROC-AUC: **0.883**
- Brier score: **0.0242**
- Mean daily precision@100: **34.71%**
- Mean daily recall@100: **35.67%**
- Mean daily fraud-exposure capture@100: **33.13%**
- Precision uplift versus calibrated linear baseline: **145.1%**
- AP uplift versus calibrated linear baseline: **319.7%**

## Promotion gate

The challenger is promoted for policy design only if it improves the declared policy metric and does not create an incoherent friction/exposure trade-off. Promotion here means “preferred for the next offline policy stage,” not production deployment.

Day-level paired bootstrap confirms that the non-linear family materially improves on the linear baseline, while the small differences among GBM feature sets are not robust. See `docs/model_comparison_uncertainty.md`.
