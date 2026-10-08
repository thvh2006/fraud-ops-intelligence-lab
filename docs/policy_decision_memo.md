# Four-action fraud policy memo

## Reference policy

The balanced reference scenario with capacity for 100 manual reviews per elapsed day is used as a readable operating example—not as a claim about Vesta's actual economics.

On locked OOT data it intervenes on **11.87%** of transactions, reaches **61.08%** of fraud cases, and covers **79.18%** of fraud exposure. It uses **83.9 reviews/day** (**83.9%** of nominal capacity) and interrupts **8,633 legitimate transactions**. Under assumed—not observed—action effectiveness, the scenario produces a **56.92% exposure-effect proxy** and a **117,104-unit simulated cost difference**. Neither is a prevention or savings claim.

## Action mix on locked OOT

- **allow**: 78,065 transactions, observed fraud rate 1.54%, mean calibrated risk 1.58%.
- **step_up**: 6,372 transactions, observed fraud rate 8.46%, mean calibrated risk 10.21%.
- **review**: 2,601 transactions, observed fraud rate 12.53%, mean calibrated risk 15.61%.
- **block**: 1,543 transactions, observed fraud rate 65.98%, mean calibrated risk 71.76%.

## Policy logic

For every transaction, expected cost is estimated for allow, step-up, review, and block. Review is capacity-constrained per elapsed day: only cases with the largest positive expected benefit from review enter the queue; remaining cases fall back to their least-cost non-review action. This makes capacity an explicit optimisation constraint rather than a score threshold chosen after OOT inspection.

## Governance boundary

- Intervention effectiveness and friction costs are assumptions, not observed causal effects.
- `TransactionAmt` is exposure, not realised loss or recoverable chargeback value.
- The reference scenario is not universally optimal; `reports/policy_sensitivity.csv` preserves customer-first and loss-first alternatives across capacities 50/100/250/500.
- A real deployment would require controlled measurement of step-up completion, review outcomes, false-positive harm, and block effectiveness before monetary claims.
