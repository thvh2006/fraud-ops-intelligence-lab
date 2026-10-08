# Day-level model comparison uncertainty

## Why this check exists

The model is used to form a daily queue, so transaction-level confidence intervals would overstate precision by treating correlated transactions from the same day as independent. This comparison resamples whole elapsed days and measures paired differences in entity-deduplicated precision@100.

## Results

- Against the calibrated linear reference on the **policy window**, `gbm_transaction` improves mean daily precision@100 by **19.17%** (95% bootstrap interval **16.04% to 22.09%**). This confirms nonlinear ranking value but is not marketed as percentage uplift.
- Against identity GBM on the **policy window**, the selected transaction-only model differs by **-0.30%** (95% interval **-0.96% to 0.30%**).
- On locked OOT, the transaction-only difference versus identity GBM is **0.13%** (95% interval **-0.68% to 0.94%**).

## Decision

The non-linear family clearly improves the queue over the linear reference. Identity
and engineered behavioural history do not clear the 1-point parsimony gate and their
paired intervals include zero. Governance therefore selects `gbm_transaction`; the
added-feature models remain research challengers. Proxy identity must also pass an
independent entity-resolution validation before production use.
