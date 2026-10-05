import pandas as pd
import pytest

from src.data_contract import DataContractError, join_identity, validate_transactions


def transactions() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "TransactionID": [1, 2, 3],
            "isFraud": [0, 1, 0],
            "TransactionDT": [10, 20, 30],
            "TransactionAmt": [20.0, 100.0, 5.0],
            "ProductCD": ["W", "C", "W"],
        }
    )


def test_valid_transaction_contract() -> None:
    summary = validate_transactions(transactions())
    assert summary.rows == 3
    assert summary.fraud_rate == pytest.approx(1 / 3)


def test_duplicate_transaction_id_fails() -> None:
    frame = transactions()
    frame.loc[2, "TransactionID"] = 2
    with pytest.raises(DataContractError, match="unique"):
        validate_transactions(frame)


def test_identity_join_preserves_unmatched_rows_and_reports_coverage() -> None:
    identity = pd.DataFrame({"TransactionID": [1, 3], "DeviceType": ["mobile", "desktop"]})
    joined, summary = join_identity(transactions(), identity)
    assert len(joined) == 3
    assert joined["has_identity"].tolist() == [1, 0, 1]
    assert summary.identity_coverage == pytest.approx(2 / 3)

