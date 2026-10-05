# Source and evidence review

## Dataset selection

IEEE-CIS was selected over popular synthetic or PCA-transformed alternatives because it combines scale, a meaningful event-time ordering, transaction and identity tables, and multiple behavioural/entity keys. Those properties allow the project to test operational questions that a static row-level classifier cannot.

The source is still imperfect. Features are anonymised, the elapsed-time origin is hidden, identity coverage is incomplete, and there are no observed investigation actions or chargeback timestamps. These limits shape every public claim.

## Prior evidence incorporated into the design

- The original competition uses real-world e-commerce transactions from Vesta and evaluates fraud ranking.
- The Amazon Fraud Dataset Benchmark documents 590,540 source transactions, a low fraud base rate, and a time-ordered benchmark design.
- Fraud operations literature motivates precision at a fixed daily investigation capacity rather than threshold-free ranking alone.
- Delayed-label research distinguishes immediate feedback on a selected investigated subset from outcomes that arrive later for the broader population.
- Strong competition solutions emphasise temporal validation and entity/user aggregation, but competition performance is not accepted as operational validation by itself.

## Design implications

1. Use `TransactionDT` only as elapsed event order; do not invent dates.
2. Lock a labelled, chronological OOT period from the training table.
3. Build entity aggregates using past observations only.
4. Report average precision and calibration alongside daily top-k metrics.
5. Treat investigator feedback as selected data in delay simulations.
6. Call `TransactionAmt` exposure and publish cost scenarios rather than savings claims.
7. Keep raw competition data out of version control.

## Primary references

- Kaggle, IEEE-CIS Fraud Detection overview and data documentation: https://www.kaggle.com/competitions/ieee-fraud-detection/
- Kaggle competition rules: https://www.kaggle.com/competitions/ieee-fraud-detection/rules
- Amazon Science Fraud Dataset Benchmark: https://github.com/amazon-science/fraud-dataset-benchmark
- Fraud Detection Handbook, top-k metrics: https://fraud-detection-handbook.github.io/fraud-detection-handbook/Chapter_4_PerformanceMetrics/TopKBased.html
- Dal Pozzolo et al., credit-card fraud detection with delayed supervised information: https://ieeexplore.ieee.org/document/7280527

