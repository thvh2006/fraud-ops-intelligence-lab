# Executive decision memo

**Decision:** advance the gradient-boosting challenger to a controlled shadow-mode pilot; do not enable automatic blocking.

## Why advance it

On the locked final 15% of events, the governed transaction GBM improves mean daily precision@100 from 14.16% to 34.84% and fraud-exposure capture@100 from 10.29% to 32.44%. This is a meaningful operations improvement: at the same top-100 queue size, investigators would see roughly 21 additional fraud-labelled alerts per 100 reviewed alerts.

The result survives the design choices that matter most for this use case: chronological evaluation, entity-deduplicated queues, probability calibration, capacity-aware metrics, and a locked final holdout.

## Recommended operating posture

Use the **balanced policy** as the reference for shadow-mode measurement, with 100 reviews/day as the nominal capacity. On the locked holdout, this routes 78,065 transactions to allow, 6,372 to step-up, 2,601 to review, and 1,543 to block. Observed fraud rate increases monotonically from 1.54% in allow to 65.98% in block, which is directionally coherent.

Do not treat those actions as deployment instructions. In shadow mode, record the recommended action while the existing process remains authoritative. Measure completion, investigator yield, false-positive complaints, review time, and eventual chargebacks.

## What the evidence does—and does not—say

The evidence supports the **nonlinear model family**. It does not show that identity or behavioural features add a stable incremental benefit: the day-level confidence interval for identity versus the transaction-only GBM crosses zero. The transaction-only GBM should therefore remain the fallback if identity availability, latency, or governance cost becomes problematic.

The balanced policy's simulated 117,104-unit cost reduction is not a savings forecast. It depends on hypothetical action effectiveness and cost inputs, while `TransactionAmt` is only an exposure proxy.

## Promotion gates

Move from shadow mode to a limited live test only when all gates pass:

1. Alert precision and exposure capture remain above the linear baseline for at least four consecutive production weeks.
2. Review throughput, step-up completion, false-positive complaints, and customer abandonment are measured—not assumed.
3. Score PSI remains below 0.10 and expected calibration error below 0.02, or a documented review approves the exception.
4. Delayed population outcomes confirm the fast investigator stream is not creating a misleading feedback loop.
5. Compliance, privacy, security, fairness, and customer-redress owners approve the feature and action design.

## Stop conditions

Pause or roll back if there is a red monitoring breach, a sustained decline in queue precision, disproportionate legitimate-customer friction, material identity-feed degradation, or a gap between reviewed and population outcomes that invalidates calibration.

## Bottom line

This project has enough offline evidence to justify learning in shadow mode, not enough causal or production evidence to justify autonomous intervention. That boundary is the decision.
