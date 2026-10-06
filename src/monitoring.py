"""Monitoring statistics and point-in-time label availability."""

from __future__ import annotations

import numpy as np
import pandas as pd


def expected_calibration_error(
    target: np.ndarray | pd.Series,
    probability: np.ndarray | pd.Series,
    *,
    bins: int = 10,
) -> float:
    y = np.asarray(target, dtype=float)
    p = np.asarray(probability, dtype=float)
    if len(y) != len(p) or len(y) == 0:
        raise ValueError("target and probability must be non-empty and equally sized")
    if np.any((p < 0) | (p > 1)):
        raise ValueError("probabilities must be inside [0, 1]")
    edges = np.linspace(0, 1, bins + 1)
    assignment = np.clip(np.digitize(p, edges[1:-1], right=True), 0, bins - 1)
    ece = 0.0
    for index in range(bins):
        mask = assignment == index
        if mask.any():
            ece += mask.mean() * abs(y[mask].mean() - p[mask].mean())
    return float(ece)


def population_stability_index(
    reference: np.ndarray | pd.Series,
    current: np.ndarray | pd.Series,
    *,
    bins: int = 10,
    epsilon: float = 1e-6,
) -> float:
    reference_values = np.asarray(reference, dtype=float)
    current_values = np.asarray(current, dtype=float)
    if len(reference_values) == 0 or len(current_values) == 0:
        raise ValueError("reference and current samples must be non-empty")
    quantiles = np.linspace(0, 1, bins + 1)
    edges = np.unique(np.quantile(reference_values, quantiles))
    if len(edges) < 2:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf
    expected, _ = np.histogram(reference_values, bins=edges)
    actual, _ = np.histogram(current_values, bins=edges)
    expected_share = np.clip(expected / expected.sum(), epsilon, None)
    actual_share = np.clip(actual / actual.sum(), epsilon, None)
    return float(np.sum((actual_share - expected_share) * np.log(actual_share / expected_share)))


def available_label_mask(
    event_day: pd.Series,
    reviewed_fast: pd.Series,
    *,
    snapshot_day: int,
    delayed_days: int,
) -> pd.Series:
    """Labels are usable only after event time and their simulated arrival time."""
    if delayed_days < 0:
        raise ValueError("delayed_days must be non-negative")
    happened_before_snapshot = event_day < snapshot_day
    fast_available = reviewed_fast.astype(bool) & happened_before_snapshot
    delayed_available = event_day.add(delayed_days).le(snapshot_day) & happened_before_snapshot
    return fast_available | delayed_available

