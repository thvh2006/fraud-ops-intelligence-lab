"""Capacity-constrained fraud operations metrics."""

from __future__ import annotations

import pandas as pd


def top_k_operations(
    frame: pd.DataFrame,
    *,
    k: int,
    day_column: str = "day",
    score_column: str = "score",
    target_column: str = "isFraud",
    amount_column: str = "TransactionAmt",
    entity_column: str | None = None,
) -> pd.DataFrame:
    """Calculate daily top-k outcomes, optionally deduplicating entities first."""
    if k <= 0:
        raise ValueError("k must be positive")
    required = {day_column, score_column, target_column, amount_column}
    if entity_column:
        required.add(entity_column)
    missing = required.difference(frame.columns)
    if missing:
        raise KeyError(f"Missing metric columns: {sorted(missing)}")

    rows: list[dict[str, float | int | str]] = []
    for day, day_frame in frame.groupby(day_column, sort=True):
        ranked = day_frame.sort_values(score_column, ascending=False, kind="stable")
        if entity_column:
            ranked = ranked.drop_duplicates(entity_column, keep="first")
        alerts = ranked.head(k)
        fraud_alerts = int(alerts[target_column].sum())
        total_fraud = int(day_frame[target_column].sum())
        fraud_exposure = float(
            day_frame.loc[day_frame[target_column] == 1, amount_column].sum()
        )
        captured_exposure = float(
            alerts.loc[alerts[target_column] == 1, amount_column].sum()
        )
        legitimate_exposure = float(
            alerts.loc[alerts[target_column] == 0, amount_column].sum()
        )
        rows.append(
            {
                "day": day,
                "capacity": k,
                "alerts": len(alerts),
                "fraud_alerts": fraud_alerts,
                "precision_at_k": fraud_alerts / len(alerts) if len(alerts) else 0.0,
                "recall_at_k": fraud_alerts / total_fraud if total_fraud else 0.0,
                "exposure_captured_at_k": (
                    captured_exposure / fraud_exposure if fraud_exposure else 0.0
                ),
                "legitimate_exposure_interrupted": legitimate_exposure,
            }
        )
    return pd.DataFrame(rows)

