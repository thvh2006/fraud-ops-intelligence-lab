# Phase 1 data profile

## Executive readout

- **590,540 transactions** span **182 elapsed days**; the hidden origin is not converted into calendar dates.
- **20,663 fraud cases** produce a **3.50% row-level fraud rate**.
- Fraud-labelled transactions represent **3.87% of transaction exposure**. This is exposure, not realised loss.
- Only **24.42%** of transactions join to the identity table.
- Fraud rate is **7.85% with identity coverage** versus **2.09% without it**. Missing identity is therefore modelled as its own state, not interpreted as safety.
- The proxy entity key yields **94,873 entities**; **92.11%** of rows belong to a repeated entity.
- The top 1% of proxy entities with observed fraud account for **24.71%** of fraud cases, supporting entity-aware prioritisation as a testable design.
- Weekly fraud rate ranges from **1.85%** to **5.06%**, so random splitting would hide meaningful temporal variation.

## Data-quality implications

- The two source tables contain **435 columns including keys/target**.
- **11 features** are at least 90% missing and **0** are fully missing in labelled data.
- High missingness is not automatically imputed away. Coverage flags, feature-family ablations, and temporal stability determine whether a feature survives.
- `TransactionDT` supplies ordering but not a real date. Reporting uses elapsed day/week only.
- Anonymous `V`, `C`, `D`, and `M` features will be described by statistical behaviour, never invented business meanings.

## Decision implications

1. Evaluate chronologically and keep the final 15% locked out of time.
2. Compare transaction-level queues with entity-deduplicated queues.
3. Report case capture and exposure capture because the two objectives need not select the same policy.
4. Treat identity availability and missingness patterns as monitored coverage signals.
5. Establish rule and logistic baselines before a gradient-boosting challenger.

## Generated evidence

- `reports/feature_inventory.csv`
- `reports/weekly_fraud_landscape.csv`
- `reports/cohort_fraud_profile.csv`
- `reports/identity_coverage_profile.csv`
- `reports/amount_decile_profile.csv`
- `reports/temporal_partitions.csv`
- `reports/data_profile_summary.json`
