# Model card: fraud alert prioritisation challenger

## Model summary

| Field | Value |
|---|---|
| Model | `gbm_plus_identity` |
| Role | Rank transactions for fraud operations and supply calibrated risk to a simulated four-action policy |
| Algorithm | Histogram gradient boosting with post-hoc probability calibration |
| Prediction unit | Transaction |
| Queue unit | Highest-risk transaction per proxy entity per elapsed day |
| Target | `isFraud` from IEEE-CIS Fraud Detection |
| Selected on | Mean daily entity-deduplicated precision@100 in the policy window |
| Final evaluation | Locked last 15% of labelled events in chronological order |
| Status | Offline challenger; suitable for shadow-mode evaluation, not live automated blocking |

## Intended use

The model is designed to prioritise a capacity-constrained fraud investigation queue and to support scenario analysis across allow, step-up authentication, review, and block actions. It demonstrates how a score can become an auditable operating decision.

It is not intended to:

- identify a person as fraudulent;
- make autonomous live declines;
- estimate causal intervention effects;
- produce recoverable-loss or savings claims;
- transfer unchanged to another merchant, geography, product, or time period.

## Data and validation

The case study uses 590,540 anonymised e-commerce transactions over 182 elapsed days, with 20,663 positive labels (3.50%). The identity table matches 24.42% of transactions. Raw competition data is not redistributed.

After stable sorting by `TransactionDT` and `TransactionID`, the labelled population is split once:

| Partition | Share | Rows | Purpose |
|---|---:|---:|---|
| Development | 60% | 354,324 | Fit models and feature transformations |
| Calibration | 15% | 88,581 | Calibrate probabilities |
| Policy | 10% | 59,054 | Select model family and intervention policy |
| Locked OOT | 15% | 88,581 | One final evaluation |

Every behavioural feature at time `t` uses only events strictly earlier than `t`. Rows at the same timestamp do not observe one another. Thresholds and capacities are not tuned on locked OOT labels.

## Features

The selected challenger uses 49 features from two families:

- **Transaction core:** amount, product, payment-card, address, email-domain, device and anonymised transaction attributes.
- **Identity indicators:** availability and selected anonymised identity attributes, with missing joins treated as missing—not as low-risk evidence.

Past-only behavioural features were also tested. They did not produce a stable improvement over the selected feature set and were not required for the reference policy.

## Performance

### Locked OOT model diagnostics

| Metric | Linear baseline | Selected challenger | Change |
|---|---:|---:|---:|
| Average precision | 0.110 | 0.460 | +319.7% |
| ROC-AUC | 0.711 | 0.883 | +0.172 |
| Brier score | 0.0332 | 0.0242 | −0.0090 |
| Mean daily precision@100 | 14.16% | 34.71% | +20.55 pp |
| Mean daily recall@100 | 14.28% | 35.67% | +21.39 pp |
| Mean daily fraud-exposure capture@100 | 10.29% | 33.13% | +22.84 pp |

The day-level paired bootstrap supports the challenger over the linear baseline. It does not establish a reliable incremental gain from adding identity features to the transaction-only GBM: OOT precision@100 difference is −0.13 pp with a 95% interval from −0.94 to +0.68 pp.

## Operating policy example

Under the balanced reference assumptions and a nominal capacity of 100 reviews per elapsed day, the locked OOT policy:

- uses 83.8 reviews/day;
- intervenes on 11.99% of transactions;
- reaches 61.21% of fraud cases and 79.94% of fraud exposure;
- produces a 57.82% effectiveness-adjusted prevented-exposure proxy;
- interrupts 8,731 legitimate transactions.

These figures are scenario outputs. Intervention effectiveness, friction cost, review cost, and loss-given-fraud are assumptions—not outcomes observed in the source data.

## Risks and safeguards

| Risk | Why it matters | Safeguard in this project |
|---|---|---|
| Temporal leakage | Future behaviour can make offline metrics invalid | Chronological split; past-only transforms; tests for ordering and metric logic |
| Selection bias | Investigator feedback over-represents high-score cases | Fast reviewed outcomes separated from delayed population labels |
| Customer harm | False positives can create authentication, review, or decline friction | Legitimate transactions and exposure interrupted are first-class policy metrics |
| Partial identity coverage | Missing identity may correlate with channel and risk | Missingness is explicit; feature-family value is ablated and uncertainty-tested |
| Drift | Fraud patterns and traffic mix change | Weekly score PSI, amount PSI, calibration error, alert quality, identity coverage, and new-entity rate |
| Proxy economics | Transaction amount is not realised loss | Reported as exposure; cost outputs labelled simulations |

Protected attributes are not available, so subgroup fairness cannot be established. A real deployment would require lawful-basis review, customer-redress design, protected-group or defensible proxy testing, and adverse-action governance where applicable.

## Monitoring and retraining

Pre-declared weekly amber/red thresholds are 0.10/0.20 for score and amount PSI, and 0.02/0.04 for expected calibration error. Across six locked OOT weeks, maximum score PSI is 0.063 and no red alert fires.

Labels are simulated at 7-, 14-, and 30-day delays. Rolling calibration changes mean Brier score by only −0.00007 to −0.00008, so the evidence does not justify automatic frequent recalibration. A production candidate should enter shadow mode first, collect unbiased delayed outcomes, and require a documented promotion gate before live interventions.

## Reproducibility

The repository includes data contracts, temporal split logic, feature code, model and policy scripts, aggregate outputs, and executable tests. Raw IEEE-CIS files and local model binaries are intentionally excluded. See the main README for the run order and the source review for the evidence boundary.
