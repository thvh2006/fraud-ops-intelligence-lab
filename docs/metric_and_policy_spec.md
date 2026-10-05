# Metric and policy specification

## Model diagnostics

- Average precision is the primary global ranking diagnostic.
- ROC-AUC is reported for comparability, not used alone for selection.
- Brier score and calibration error test whether risk estimates support policy choices.

## Operations metrics

For each operational day and review capacity `k`:

- `precision@k`: fraud alerts / investigated alerts;
- `recall@k`: fraud alerts / all fraud transactions;
- `exposure_captured@k`: fraud transaction amount in alerts / total fraud transaction amount;
- `legitimate_exposure_interrupted`: legitimate amount routed to an intervention;
- `alerts_per_captured_fraud`: reviewed alerts / detected fraud alerts.

Daily metrics are aggregated with both the mean and distribution across days. Empty and low-volume days are surfaced rather than silently discarded.

## Entity-level queue

Where a defensible entity key can be constructed, alerts are deduplicated within an operational day. The highest-risk transaction represents the entity; linked transactions remain visible to the reviewer. Transaction-level results are retained as a sensitivity comparison.

## Four-action policy

1. **Allow:** no intervention.
2. **Step up:** request additional authentication; incurs friction.
3. **Review:** enter the capacity-constrained analyst queue.
4. **Block:** reserved for a high-confidence/high-cost threshold justified on the policy window.

No cost scenario is labelled optimal without stability across plausible false-positive, review, and fraud-loss assumptions.

