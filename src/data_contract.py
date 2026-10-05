"""Raw IEEE-CIS schema and integrity checks."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


class DataContractError(ValueError):
    """Raised when source data violates a required invariant."""


@dataclass(frozen=True)
class ContractSummary:
    rows: int
    fraud_rate: float
    identity_coverage: float | None
    time_min: float
    time_max: float


REQUIRED_TRANSACTION_COLUMNS = {
    "TransactionID",
    "isFraud",
    "TransactionDT",
    "TransactionAmt",
    "ProductCD",
}
REQUIRED_IDENTITY_COLUMNS = {"TransactionID"}


def validate_transactions(frame: pd.DataFrame) -> ContractSummary:
    missing = REQUIRED_TRANSACTION_COLUMNS.difference(frame.columns)
    if missing:
        raise DataContractError(f"Missing transaction columns: {sorted(missing)}")
    if frame.empty:
        raise DataContractError("Transaction table is empty")
    if frame["TransactionID"].isna().any() or frame["TransactionID"].duplicated().any():
        raise DataContractError("TransactionID must be present and unique")
    if frame["TransactionDT"].isna().any() or (frame["TransactionDT"] < 0).any():
        raise DataContractError("TransactionDT must be present and non-negative")
    target_values = set(frame["isFraud"].dropna().unique())
    if target_values != {0, 1}:
        raise DataContractError(f"isFraud must contain both binary classes; got {target_values}")
    if frame["TransactionAmt"].isna().any() or (frame["TransactionAmt"] < 0).any():
        raise DataContractError("TransactionAmt must be present and non-negative")

    return ContractSummary(
        rows=len(frame),
        fraud_rate=float(frame["isFraud"].mean()),
        identity_coverage=None,
        time_min=float(frame["TransactionDT"].min()),
        time_max=float(frame["TransactionDT"].max()),
    )


def join_identity(
    transactions: pd.DataFrame, identity: pd.DataFrame
) -> tuple[pd.DataFrame, ContractSummary]:
    missing = REQUIRED_IDENTITY_COLUMNS.difference(identity.columns)
    if missing:
        raise DataContractError(f"Missing identity columns: {sorted(missing)}")
    if identity["TransactionID"].duplicated().any():
        raise DataContractError("Identity TransactionID must be unique")
    orphan_ids = set(identity["TransactionID"]) - set(transactions["TransactionID"])
    if orphan_ids:
        raise DataContractError(f"Identity table contains {len(orphan_ids)} orphan IDs")

    base_summary = validate_transactions(transactions)
    identity_columns = [column for column in identity.columns if column != "TransactionID"]
    joined = transactions.merge(
        identity.assign(_has_identity=1), on="TransactionID", how="left", validate="one_to_one"
    )
    joined["has_identity"] = joined.pop("_has_identity").fillna(0).astype("int8")
    coverage = float(joined["has_identity"].mean())
    summary = ContractSummary(
        rows=base_summary.rows,
        fraud_rate=base_summary.fraud_rate,
        identity_coverage=coverage,
        time_min=base_summary.time_min,
        time_max=base_summary.time_max,
    )
    expected_columns = len(transactions.columns) + len(identity_columns) + 1
    if len(joined.columns) != expected_columns:
        raise DataContractError("Unexpected column count after identity join")
    return joined, summary

