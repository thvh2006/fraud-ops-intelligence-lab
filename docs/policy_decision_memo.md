# Four-action fraud policy memo

## Reference policy

The balanced reference scenario with capacity for 100 manual reviews per elapsed day is used as a readable operating example—not as a claim about Vesta's actual economics.

On locked OOT data it intervenes on **11.99%** of transactions, reaches **61.21%** of fraud cases, and covers **79.94%** of fraud exposure. After applying assumed action effectiveness, prevented-exposure proxy is **57.82%**. It uses **83.8 reviews/day** (**83.8%** of nominal capacity), interrupts **8,731 legitimate transactions**, and reduces simulated cost by **118,783 units** under the stated assumptions only.

## Action mix on locked OOT

- **allow**: 77,963 transactions, observed fraud rate 1.53%, mean calibrated risk 1.53%.
- **step_up**: 6,451 transactions, observed fraud rate 8.42%, mean calibrated risk 10.18%.
- **review**: 2,599 transactions, observed fraud rate 12.16%, mean calibrated risk 15.68%.
- **block**: 1,568 transactions, observed fraud rate 65.56%, mean calibrated risk 73.32%.

## Policy logic

For every transaction, expected cost is estimated for allow, step-up, review, and block. Review is capacity-constrained per elapsed day: only cases with the largest positive expected benefit from review enter the queue; remaining cases fall back to their least-cost non-review action. This makes capacity an explicit optimisation constraint rather than a score threshold chosen after OOT inspection.

## Governance boundary

- Intervention effectiveness and friction costs are assumptions, not observed causal effects.
- `TransactionAmt` is exposure, not realised loss or recoverable chargeback value.
- The reference scenario is not universally optimal; `reports/policy_sensitivity.csv` preserves customer-first and loss-first alternatives across capacities 50/100/250/500.
- A real deployment would require controlled measurement of step-up completion, review outcomes, false-positive harm, and block effectiveness before monetary claims.
