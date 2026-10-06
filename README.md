# Fraud Operations Intelligence Lab

An end-to-end fraud decision system built around a constrained operations team—not a leaderboard-only classifier.

## Decision question

> With limited daily investigation capacity and delayed labels, which transactions or entities should be allowed, stepped up, reviewed, or blocked to capture the most fraud exposure while controlling legitimate-customer friction?

## Why this project exists

Most fraud portfolio projects stop at ROC-AUC. This project starts where a model score becomes an operational decision. It will connect temporal model development to alert queues, entity deduplication, capacity constraints, delayed outcomes, policy economics, and monitoring.

## Evidence target

The project will use the IEEE-CIS Fraud Detection data: real, anonymised e-commerce transactions supplied by Vesta Corporation. The raw competition files are not redistributed. Anyone reproducing the analysis must accept the Kaggle competition rules and download the data into `data/raw/`.

## What the finished case study will demonstrate

1. **Temporal integrity** — development, calibration, policy, and locked out-of-time partitions.
2. **Leakage-safe behaviour** — velocity, novelty, amount deviation, and shared-entity features built from prior events only.
3. **Model ladder** — rules, an interpretable baseline, and a gradient-boosting challenger.
4. **Operations metrics** — daily precision@k, recall@k, exposure captured@k, queue stability, and legitimate value interrupted.
5. **Decision policy** — allow, step-up authentication, manual review, or block under explicit capacity and cost assumptions.
6. **Delayed labels** — separate fast investigator feedback from slower chargeback-style outcomes.
7. **Monitoring** — drift, calibration decay, alert-volume breaches, and reason-code stability.
8. **Executive communication** — a fraud operations control-room dashboard and a concise decision memo.

## Delivery status

| Phase | Outcome | Status |
|---|---|---|
| 0 | Research charter, source review, data contract, temporal design | Complete |
| 1 | Acquire data, validate schema, profile time/identity coverage | Complete |
| 2 | Leakage-safe baseline and locked out-of-time benchmark | Complete |
| 3 | Behavioural/entity features and non-linear challenger | In progress |
| 4 | Alert prioritisation and four-action policy | Planned |
| 5 | Delayed-label and drift backtests | Planned |
| 6 | Dashboard, model card, decision memo, publication | Planned |

## Repository map

```text
configs/                  analysis and policy assumptions
data/                     ignored raw/interim/processed data zones
docs/                     charter, evidence review, leakage and metric policy
scripts/                  acquisition and validation entry points
src/                      reusable data-contract, temporal and metric logic
tests/                    executable safeguards
dashboard/                final operations control room
reports/                  reproducible outputs and decision evidence
```

## Reproduce Phase 1

1. Accept the IEEE-CIS competition rules on Kaggle.
2. Configure Kaggle authentication locally; never commit credentials.
3. Install the project and run:

```bash
python scripts/acquire_data.py
python scripts/validate_raw_data.py
pytest
```

The acquisition script fails safely when credentials or rule acceptance are missing. See [`data/README.md`](data/README.md) for the exact contract.

## Phase 1 evidence

The labelled source contains 590,540 transactions over 182 elapsed days and 20,663 fraud cases (3.50%). Only 24.42% of transactions have an identity-table match. Fraud rate varies from 1.85% to 5.06% across elapsed weeks, making chronological validation a material design requirement. See [`docs/data_profile.md`](docs/data_profile.md) for the full aggregate-only readout.

## Baseline decision

A calibrated linear model was selected on the policy window at 100 entity-deduplicated alerts per elapsed day. On locked OOT data it reaches 14.16% mean daily precision@100, 14.28% mean daily recall@100, and 10.29% mean daily fraud-exposure capture@100. The rule baseline captures more exposure but interrupts almost five times as much legitimate value, showing why a single capture metric is not enough. See [`docs/baseline_decision_memo.md`](docs/baseline_decision_memo.md).

## Claims boundary

This is a portfolio-grade operational simulation on real anonymised transactions. It is not a deployed fraud system. `TransactionAmt` is treated as exposure, not confirmed recoverable loss; investigation decisions, chargeback dates, true intervention costs, and protected attributes are not available in the source data. Assumptions will therefore be surfaced and sensitivity-tested rather than presented as observed facts.
