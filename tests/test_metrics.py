import pandas as pd
import pytest

from src.metrics import top_k_operations


def test_daily_top_k_metrics() -> None:
    frame = pd.DataFrame(
        {
            "day": [1, 1, 1, 2, 2],
            "score": [0.9, 0.8, 0.1, 0.7, 0.2],
            "isFraud": [1, 0, 1, 0, 1],
            "TransactionAmt": [100.0, 50.0, 20.0, 40.0, 10.0],
            "entity": ["a", "b", "c", "d", "e"],
        }
    )
    result = top_k_operations(frame, k=2, entity_column="entity")
    day_one = result.loc[result["day"] == 1].iloc[0]
    assert day_one["precision_at_k"] == pytest.approx(0.5)
    assert day_one["recall_at_k"] == pytest.approx(0.5)
    assert day_one["exposure_captured_at_k"] == pytest.approx(100 / 120)
    assert day_one["legitimate_exposure_interrupted"] == pytest.approx(50.0)


def test_entity_deduplication_keeps_highest_score() -> None:
    frame = pd.DataFrame(
        {
            "day": [1, 1, 1],
            "score": [0.9, 0.8, 0.7],
            "isFraud": [1, 1, 0],
            "TransactionAmt": [100.0, 50.0, 20.0],
            "entity": ["same", "same", "other"],
        }
    )
    result = top_k_operations(frame, k=2, entity_column="entity")
    assert result.loc[0, "alerts"] == 2
    assert result.loc[0, "fraud_alerts"] == 1

