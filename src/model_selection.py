"""Governed model selection with an explicit parsimony gate."""

from __future__ import annotations

import pandas as pd


def select_governed_model(
    policy_summary: pd.DataFrame,
    reference: str = "gbm_transaction",
    minimum_absolute_precision_gain: float = 0.01,
) -> tuple[str, str]:
    """Prefer the simpler reference unless added features clear a materiality gate."""

    required = {"model", "mean_precision_at_k"}
    missing = required.difference(policy_summary.columns)
    if missing:
        raise ValueError(f"Missing selection fields: {sorted(missing)}")
    indexed = policy_summary.set_index("model")
    if reference not in indexed.index:
        raise ValueError(f"Reference model {reference!r} is unavailable")
    best = str(indexed["mean_precision_at_k"].idxmax())
    gain = float(
        indexed.loc[best, "mean_precision_at_k"]
        - indexed.loc[reference, "mean_precision_at_k"]
    )
    if best != reference and gain < minimum_absolute_precision_gain:
        return (
            reference,
            (
                f"parsimony_gate: best added-feature gain {gain:.4f} is below "
                f"{minimum_absolute_precision_gain:.4f}"
            ),
        )
    return best, "material policy-window precision gain"
