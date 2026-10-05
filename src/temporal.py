"""Deterministic chronological partitions for model and policy development."""

from __future__ import annotations

import pandas as pd


PARTITION_ORDER = ("development", "calibration", "policy", "oot")


def assign_temporal_partitions(
    frame: pd.DataFrame,
    *,
    time_column: str = "TransactionDT",
    id_column: str = "TransactionID",
    boundaries: tuple[float, float, float] = (0.60, 0.75, 0.85),
) -> pd.Series:
    """Return row-aligned chronological partition labels.

    Same-time events are kept in the same partition. Boundary rows therefore move
    forward to the end of their timestamp group instead of splitting a batch.
    """
    if frame.empty:
        raise ValueError("Cannot partition an empty frame")
    if not 0 < boundaries[0] < boundaries[1] < boundaries[2] < 1:
        raise ValueError("Boundaries must be strictly increasing inside (0, 1)")
    for column in (time_column, id_column):
        if column not in frame:
            raise KeyError(f"Missing partition column: {column}")

    ordered = frame[[time_column, id_column]].sort_values(
        [time_column, id_column], kind="stable"
    )
    n_rows = len(ordered)
    raw_positions = [max(1, min(n_rows - 1, int(n_rows * value))) for value in boundaries]
    cut_times = [ordered.iloc[position - 1][time_column] for position in raw_positions]

    labels = pd.Series("oot", index=frame.index, dtype="object")
    labels.loc[frame[time_column] <= cut_times[0]] = "development"
    labels.loc[
        (frame[time_column] > cut_times[0]) & (frame[time_column] <= cut_times[1])
    ] = "calibration"
    labels.loc[
        (frame[time_column] > cut_times[1]) & (frame[time_column] <= cut_times[2])
    ] = "policy"
    return labels


def assert_temporal_separation(
    frame: pd.DataFrame, labels: pd.Series, time_column: str = "TransactionDT"
) -> None:
    previous_max = None
    for partition in PARTITION_ORDER:
        values = frame.loc[labels == partition, time_column]
        if values.empty:
            raise ValueError(f"Temporal partition is empty: {partition}")
        if previous_max is not None and values.min() <= previous_max:
            raise ValueError(f"Temporal overlap detected at partition: {partition}")
        previous_max = values.max()

