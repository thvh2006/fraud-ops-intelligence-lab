# Research and decision charter

## Mandate

Design and evaluate a fraud alert system that makes defensible decisions under three operational constraints: limited investigator capacity, repeated transactions from related entities, and delayed/selected labels.

## Primary decision

Choose a scoring model and daily alert policy that maximise useful fraud capture at fixed review capacity without creating an unacceptable volume or value of legitimate interruptions.

## Decision owners represented

- **Fraud operations:** needs a workable, prioritised queue.
- **Risk strategy:** owns review and intervention thresholds.
- **Product/customer experience:** owns step-up and false-positive friction.
- **Model risk:** requires temporal evidence, calibration, stability, and limitations.
- **Data science:** owns reproducibility and monitoring logic.

## Falsifiable research questions

1. Does the model with the best ranking metric also win at 100 entity-deduplicated alerts per day?
2. How much incremental fraud exposure is captured when capacity rises from 50 to 500 alerts per day?
3. Does entity deduplication reduce queue volume without materially reducing captured exposure?
4. Do past-only velocity and novelty features outperform static transaction attributes out of time?
5. Which feature families lose stability fastest over the observation horizon?
6. Can ranking remain useful while probability calibration deteriorates?
7. How do 7-, 14-, and 30-day label delays alter retraining evidence and policy performance?
8. How sensitive are block/review thresholds to false-positive and review-cost assumptions?
9. Are reason codes stable enough for operations to use week over week?

## Minimum evidence for a strong conclusion

- A naive rules baseline and an interpretable statistical baseline.
- One justified non-linear challenger.
- Locked out-of-time evaluation untouched by feature/model selection.
- Per-day capacity metrics with uncertainty or day-level dispersion.
- Entity-deduplicated and transaction-level results side by side.
- Calibration diagnostics, not ranking metrics alone.
- Feature-family ablations.
- Label-delay and policy-cost sensitivity analysis.
- Explicit failure modes and claims boundary.

## Non-goals

- Winning or reproducing the original Kaggle leaderboard.
- Claiming realised savings without observed chargebacks and interventions.
- Fabricating analyst decisions, customer identity, or protected characteristics.
- Treating anonymous feature codes as known business semantics.
- Optimising solely for ROC-AUC.

## Stop/go gates

| Gate | Required evidence | Failure response |
|---|---|---|
| Data | Unique transaction IDs, valid target, monotonic time order after sort | Stop and repair ingestion |
| Split | All feature state respects event time; OOT boundary is recorded | Reject contaminated experiment |
| Model | Beats rules and logistic baselines on policy metric | Keep simpler baseline |
| Policy | Stable across adjacent capacity/cost scenarios | Do not recommend fixed thresholds |
| Monitoring | Drift and alert-volume triggers are computable | Do not claim production readiness |

