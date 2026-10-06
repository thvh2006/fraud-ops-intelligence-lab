"""Leakage-safe behavioural features built from strictly prior timestamp groups."""

from __future__ import annotations

import numpy as np
import pandas as pd


def make_proxy_entity(frame: pd.DataFrame, columns: list[str]) -> pd.Series:
    """Construct a documented proxy entity without claiming a true customer ID."""
    missing = set(columns).difference(frame.columns)
    if missing:
        raise KeyError(f"Missing proxy entity columns: {sorted(missing)}")
    normalized = frame[columns].astype("string").fillna("<MISSING>")
    return normalized.agg("|".join, axis=1).rename("entity_key")


def add_past_only_entity_history(
    frame: pd.DataFrame,
    *,
    entity_column: str = "entity_key",
    time_column: str = "TransactionDT",
    amount_column: str = "TransactionAmt",
) -> pd.DataFrame:
    """Add history visible strictly before each entity/timestamp batch.

    Transactions sharing a timestamp receive identical pre-batch state and cannot
    observe one another. The input row order and index are preserved.
    """
    required = {entity_column, time_column, amount_column}
    missing = required.difference(frame.columns)
    if missing:
        raise KeyError(f"Missing history columns: {sorted(missing)}")
    if frame.empty:
        return frame.assign(
            entity_prior_tx_count=pd.Series(dtype="int64"),
            entity_prior_amount_mean=pd.Series(dtype="float64"),
            entity_seconds_since_previous=pd.Series(dtype="float64"),
            amount_to_entity_prior_mean=pd.Series(dtype="float64"),
            entity_is_new=pd.Series(dtype="int8"),
        )

    batch = (
        frame.groupby([entity_column, time_column], dropna=False, sort=True)[amount_column]
        .agg(batch_count="size", batch_amount_sum="sum")
        .reset_index()
        .sort_values([entity_column, time_column], kind="stable")
    )
    batch["entity_prior_tx_count"] = (
        batch.groupby(entity_column, dropna=False)["batch_count"].cumsum()
        - batch["batch_count"]
    )
    batch["entity_prior_amount_sum"] = (
        batch.groupby(entity_column, dropna=False)["batch_amount_sum"].cumsum()
        - batch["batch_amount_sum"]
    )
    batch["entity_prior_amount_mean"] = batch["entity_prior_amount_sum"].div(
        batch["entity_prior_tx_count"].replace(0, np.nan)
    )
    batch["previous_entity_time"] = batch.groupby(entity_column, dropna=False)[
        time_column
    ].shift(1)
    batch["entity_seconds_since_previous"] = (
        batch[time_column] - batch["previous_entity_time"]
    )

    history_columns = [
        entity_column,
        time_column,
        "entity_prior_tx_count",
        "entity_prior_amount_mean",
        "entity_seconds_since_previous",
    ]
    result = frame.merge(
        batch[history_columns],
        on=[entity_column, time_column],
        how="left",
        validate="many_to_one",
        sort=False,
    )
    result["amount_to_entity_prior_mean"] = result[amount_column].div(
        result["entity_prior_amount_mean"].replace(0, np.nan)
    )
    result["entity_is_new"] = result["entity_prior_tx_count"].eq(0).astype("int8")
    return result
