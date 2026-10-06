# Day-level model comparison uncertainty

## Why this check exists

The model is used to form a daily queue, so transaction-level confidence intervals would overstate precision by treating correlated transactions from the same day as independent. This comparison resamples whole elapsed days and measures paired differences in entity-deduplicated precision@100.

## Results

- Against the calibrated linear baseline on the **policy window**, `gbm_plus_identity` improves mean daily precision@100 by **19.48%** (95% bootstrap interval **16.48% to 22.35%**; probability of positive uplift **100.0%**).
- Against transaction-only GBM on the **policy window**, the identity increment is **0.30%** (95% interval **-0.30% to 0.96%**).
- On locked OOT, the identity increment versus transaction-only GBM is **-0.13%** (95% interval **-0.94% to 0.68%**).

## Decision

The non-linear family clearly improves the queue over the linear baseline. The incremental value of identity and engineered behavioural history is not yet established if its paired interval includes zero. `gbm_plus_identity` remains the policy-selected candidate because the selection rule was declared before OOT inspection, but the simpler transaction model stays an active challenger. This prevents a tiny policy-window difference from being marketed as a robust feature uplift.
