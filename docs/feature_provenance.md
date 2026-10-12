# Feature provenance and decision-time policy

This register explains where portfolio-facing features come from and what was known at the decision point. The machine-readable source is [`reports/feature_provenance.csv`](../reports/feature_provenance.csv).

| Feature | Family | Raw source | Transformation | Cutoff | Fit scope | Role | Main risk |
|---|---|---|---|---|---|---|---|
| TransactionAmt | transaction core | train_transaction.TransactionAmt | Raw amount | current transaction | none | model | low |
| ProductCD/card/address/email/device core | transaction core | train_transaction | Selected numeric/categorical source fields | current transaction | development | model | medium: anonymous semantics |
| has_identity | identity | train_identity join | 1 when identity row exists | current transaction | none | research challenger | medium: availability process |
| DeviceType/id_31 | identity | train_identity | Categorical identity values | current transaction | development | research challenger | medium |
| entity_prior_tx_count | past behaviour | proxy entity transaction history | Count transactions in strictly earlier timestamp groups | strictly before TransactionDT | none | research challenger | low after batch-safe grouping |
| entity_prior_amount_mean | past behaviour | proxy entity transaction history | Mean amount over strictly earlier timestamp groups | strictly before TransactionDT | none | research challenger | low |
| entity_seconds_since_previous | past behaviour | proxy entity transaction history | Elapsed seconds since previous timestamp group | strictly before TransactionDT | none | research challenger | low |
| amount_to_entity_prior_mean | past behaviour | current amount and past-only mean | TransactionAmt / entity_prior_amount_mean | past history plus current amount | none | research challenger | low |
| entity_is_new | past behaviour | entity_prior_tx_count | 1 when no strictly prior transaction exists | strictly before TransactionDT | none | research challenger | low |
| entity_key | entity proxy | card/address/email components | Normalized string concatenation | current transaction | none | queue deduplication | medium: merges/splits are unverified |

## Governance rules

1. Outcomes and post-decision events are targets or evaluation evidence, never predictors.
2. Learned bins, imputers, encoders, cutoffs, and feature eligibility are fitted before locked evaluation.
3. Anonymous fields are described by source and statistical behavior; business meanings are not invented.
4. Proxy and fairness risks remain explicit even when protected attributes are unavailable.
5. The notebook is explanatory; reusable code and tests remain the implementation source of truth.
