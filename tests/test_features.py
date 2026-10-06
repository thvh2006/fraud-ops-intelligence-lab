import numpy as np
import pandas as pd

from src.features import add_past_only_entity_history, make_proxy_entity


def test_proxy_entity_is_stable_with_missing_values() -> None:
    frame = pd.DataFrame({"card1": [10, 10], "addr1": [20, None]})
    entity = make_proxy_entity(frame, ["card1", "addr1"])
    assert entity.tolist() == ["10|20.0", "10|<MISSING>"]


def test_same_timestamp_rows_cannot_observe_each_other() -> None:
    frame = pd.DataFrame(
        {
            "entity_key": ["a", "a", "a"],
            "TransactionDT": [10, 10, 20],
            "TransactionAmt": [5.0, 15.0, 30.0],
        }
    )
    result = add_past_only_entity_history(frame)
    assert result.loc[:1, "entity_prior_tx_count"].tolist() == [0, 0]
    assert result.loc[2, "entity_prior_tx_count"] == 2
    assert result.loc[2, "entity_prior_amount_mean"] == 10.0
    assert result.loc[2, "entity_seconds_since_previous"] == 10


def test_new_entity_has_unknown_history_not_zero_mean() -> None:
    frame = pd.DataFrame(
        {"entity_key": ["a"], "TransactionDT": [10], "TransactionAmt": [5.0]}
    )
    result = add_past_only_entity_history(frame)
    assert result.loc[0, "entity_is_new"] == 1
    assert np.isnan(result.loc[0, "entity_prior_amount_mean"])
    assert np.isnan(result.loc[0, "amount_to_entity_prior_mean"])
