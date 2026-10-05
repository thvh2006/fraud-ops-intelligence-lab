# Leakage and validation policy

## Observation rule

For a transaction at time `t`, every model feature must be derivable from the current transaction and information whose event time is strictly earlier than `t`. Target-derived history must also respect the chosen label-availability delay.

## Temporal partitions

After stable sorting by `TransactionDT` and `TransactionID`, the labelled population is divided into:

- **Development (first 60%)** for feature and model development.
- **Calibration (next 15%)** for probability calibration.
- **Policy (next 10%)** for choosing capacities and action thresholds.
- **Locked OOT (last 15%)** for one final evaluation.

Exact boundaries and row counts will be recorded after acquisition. Fractions may be changed once during profiling if the event horizon or day coverage makes them operationally incoherent; no boundary is changed after examining OOT outcomes.

## Prohibited patterns

- Random train/test split for the final result.
- Full-dataset frequency encoding or scaling fitted before the split.
- Aggregates that include the current/future transaction.
- Target encoding without cross-fitting and event-time controls.
- Tuning thresholds on the locked OOT period.
- Using competition test predictions as labelled validation.
- Treating missing identity joins as zero-risk identity evidence.

## Same-time events

Rows sharing the same `TransactionDT` cannot observe one another in sequential features unless a deterministic batch rule is defined. The default implementation shifts cumulative state by the full timestamp group.

## Label availability

Two streams are modelled separately:

1. selected, fast investigator feedback from reviewed top-k alerts;
2. delayed outcomes for the rest of the population under 7/14/30-day scenarios.

Training snapshots can use only labels available as of the snapshot time.

