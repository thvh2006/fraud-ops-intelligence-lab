# Baseline decision memo

## Decision

The **linear baseline** is selected on the policy window using mean daily precision at 100 entity-deduplicated alerts. The locked OOT period was not used for this choice.

## Locked OOT evidence

- Average precision: **0.110**
- ROC-AUC: **0.711**
- Brier score after development/calibration separation: **0.0332**
- Mean daily precision@100: **14.16%**
- Mean daily recall@100: **14.28%**
- Mean daily fraud-exposure capture@100: **10.29%**

## Interpretation boundary

This result demonstrates a reproducible baseline and queue evaluation—not a deployable block policy. The proxy entity is not a verified customer ID; transaction amount is exposure rather than realised loss; and analyst outcomes are not observed. A non-linear challenger must beat this baseline on the policy metric and remain stable OOT before it is preferred.
