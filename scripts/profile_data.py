"""Build aggregate-only Phase 1 profiling evidence from IEEE-CIS data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.temporal import assign_temporal_partitions  # noqa: E402


RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"
DOCS = ROOT / "docs"
SECONDS_PER_DAY = 86_400


def safe_rate(fraud_cases: pd.Series, transactions: pd.Series) -> pd.Series:
    return fraud_cases.div(transactions).replace([np.inf, -np.inf], np.nan).fillna(0.0)


def cohort_table(frame: pd.DataFrame, column: str, top_n: int = 25) -> pd.DataFrame:
    values = frame[column].astype("string").fillna("<MISSING>")
    work = frame[["isFraud", "TransactionAmt"]].assign(cohort=values)
    grouped = (
        work.groupby("cohort", dropna=False)
        .agg(
            transactions=("isFraud", "size"),
            fraud_cases=("isFraud", "sum"),
            total_exposure=("TransactionAmt", "sum"),
            fraud_exposure=(
                "TransactionAmt",
                lambda values: values[work.loc[values.index, "isFraud"].eq(1)].sum(),
            ),
        )
        .reset_index()
    )
    grouped["fraud_rate"] = safe_rate(grouped["fraud_cases"], grouped["transactions"])
    grouped["column"] = column
    return grouped.sort_values("transactions", ascending=False).head(top_n)


def feature_family(column: str) -> str:
    if column.startswith("card"):
        return "card"
    if column.startswith("addr") or column.startswith("dist"):
        return "address_distance"
    if column.startswith("C") and column[1:].isdigit():
        return "count"
    if column.startswith("D") and column[1:].isdigit():
        return "time_delta"
    if column.startswith("M") and column[1:].isdigit():
        return "match"
    if column.startswith("V") and column[1:].isdigit():
        return "vesta_engineered"
    if column.startswith("id_"):
        return "identity"
    if "emaildomain" in column:
        return "email"
    if column in {"DeviceType", "DeviceInfo"}:
        return "device"
    return "core"


def build_feature_inventory(transaction: pd.DataFrame, identity: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for table_name, frame in (("transaction", transaction), ("identity", identity)):
        for column in frame.columns:
            records.append(
                {
                    "table": table_name,
                    "feature": column,
                    "family": feature_family(column),
                    "dtype": str(frame[column].dtype),
                    "missing_rate": float(frame[column].isna().mean()),
                    "unique_values": int(frame[column].nunique(dropna=True)),
                }
            )
    return pd.DataFrame(records).sort_values(["table", "family", "feature"])


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    transaction = pd.read_csv(RAW / "train_transaction.csv", low_memory=False)
    identity = pd.read_csv(RAW / "train_identity.csv", low_memory=False)

    transaction = transaction.sort_values(["TransactionDT", "TransactionID"], kind="stable")
    transaction["elapsed_day"] = (transaction["TransactionDT"] // SECONDS_PER_DAY).astype(int)
    transaction["elapsed_week"] = (transaction["elapsed_day"] // 7).astype(int)
    transaction["partition"] = assign_temporal_partitions(transaction)

    identity_keys = ["TransactionID", "DeviceType", "DeviceInfo", "id_31"]
    joined = transaction.merge(
        identity[identity_keys].assign(has_identity=1),
        on="TransactionID",
        how="left",
        validate="one_to_one",
    )
    joined["has_identity"] = joined["has_identity"].fillna(0).astype("int8")

    weekly = (
        transaction.groupby("elapsed_week")
        .agg(
            transactions=("isFraud", "size"),
            fraud_cases=("isFraud", "sum"),
            total_exposure=("TransactionAmt", "sum"),
            fraud_exposure=(
                "TransactionAmt",
                lambda values: values[transaction.loc[values.index, "isFraud"].eq(1)].sum(),
            ),
            median_amount=("TransactionAmt", "median"),
        )
        .reset_index()
    )
    weekly["fraud_rate"] = safe_rate(weekly["fraud_cases"], weekly["transactions"])
    weekly["fraud_exposure_share"] = weekly["fraud_exposure"].div(weekly["total_exposure"])
    weekly.to_csv(REPORTS / "weekly_fraud_landscape.csv", index=False)

    inventory = build_feature_inventory(
        transaction.drop(columns=["elapsed_day", "elapsed_week", "partition"]), identity
    )
    inventory.to_csv(REPORTS / "feature_inventory.csv", index=False)

    cohort_columns = [
        "ProductCD",
        "card4",
        "card6",
        "P_emaildomain",
        "R_emaildomain",
        "DeviceType",
        "DeviceInfo",
        "id_31",
    ]
    cohorts = pd.concat([cohort_table(joined, column) for column in cohort_columns])
    cohorts.to_csv(REPORTS / "cohort_fraud_profile.csv", index=False)

    identity_profile = (
        joined.groupby("has_identity")
        .agg(
            transactions=("isFraud", "size"),
            fraud_cases=("isFraud", "sum"),
            average_amount=("TransactionAmt", "mean"),
            total_exposure=("TransactionAmt", "sum"),
        )
        .reset_index()
    )
    identity_profile["fraud_rate"] = safe_rate(
        identity_profile["fraud_cases"], identity_profile["transactions"]
    )
    identity_profile.to_csv(REPORTS / "identity_coverage_profile.csv", index=False)

    transaction["amount_decile"] = pd.qcut(
        transaction["TransactionAmt"], q=10, duplicates="drop"
    ).astype("string")
    amount_profile = (
        transaction.groupby("amount_decile", observed=True)
        .agg(
            transactions=("isFraud", "size"),
            fraud_cases=("isFraud", "sum"),
            min_amount=("TransactionAmt", "min"),
            median_amount=("TransactionAmt", "median"),
            max_amount=("TransactionAmt", "max"),
            total_exposure=("TransactionAmt", "sum"),
        )
        .reset_index()
    )
    amount_profile["fraud_rate"] = safe_rate(
        amount_profile["fraud_cases"], amount_profile["transactions"]
    )
    amount_profile.to_csv(REPORTS / "amount_decile_profile.csv", index=False)

    entity_columns = ["card1", "card2", "card3", "card5", "card6", "addr1", "P_emaildomain"]
    entity = transaction[entity_columns].astype("string").fillna("<MISSING>").agg("|".join, axis=1)
    entity_stats = (
        transaction.assign(entity_key=entity)
        .groupby("entity_key")
        .agg(
            transactions=("isFraud", "size"),
            fraud_cases=("isFraud", "sum"),
            fraud_exposure=(
                "TransactionAmt",
                lambda values: values[transaction.loc[values.index, "isFraud"].eq(1)].sum(),
            ),
        )
        .reset_index()
    )
    fraud_entities = entity_stats.loc[entity_stats["fraud_cases"] > 0].sort_values(
        "fraud_cases", ascending=False
    )
    top_one_percent = max(1, int(np.ceil(len(fraud_entities) * 0.01)))

    partitions = (
        transaction.groupby("partition", observed=True)
        .agg(
            rows=("isFraud", "size"),
            fraud_cases=("isFraud", "sum"),
            time_min=("TransactionDT", "min"),
            time_max=("TransactionDT", "max"),
        )
        .reset_index()
    )
    partitions["fraud_rate"] = safe_rate(partitions["fraud_cases"], partitions["rows"])
    partitions.to_csv(REPORTS / "temporal_partitions.csv", index=False)

    fraud_rows = transaction.loc[transaction["isFraud"].eq(1)]
    summary = {
        "transactions": int(len(transaction)),
        "columns_transaction": 394,
        "predictors_transaction": 390,
        "features_identity": int(len(identity.columns) - 1),
        "fraud_cases": int(transaction["isFraud"].sum()),
        "fraud_rate": float(transaction["isFraud"].mean()),
        "total_exposure": float(transaction["TransactionAmt"].sum()),
        "fraud_exposure": float(fraud_rows["TransactionAmt"].sum()),
        "fraud_exposure_share": float(
            fraud_rows["TransactionAmt"].sum() / transaction["TransactionAmt"].sum()
        ),
        "identity_coverage": float(joined["has_identity"].mean()),
        "elapsed_days": int(transaction["elapsed_day"].max() - transaction["elapsed_day"].min() + 1),
        "unique_proxy_entities": int(entity.nunique()),
        "repeat_entity_transaction_share": float(entity.duplicated(keep=False).mean()),
        "top_1pct_fraud_entity_case_share": float(
            fraud_entities.head(top_one_percent)["fraud_cases"].sum()
            / fraud_entities["fraud_cases"].sum()
        ),
        "fully_missing_features": int((inventory["missing_rate"] == 1.0).sum()),
        "features_over_90pct_missing": int((inventory["missing_rate"] >= 0.9).sum()),
    }
    (REPORTS / "data_profile_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )

    identity_with = identity_profile.loc[identity_profile["has_identity"].eq(1)].iloc[0]
    identity_without = identity_profile.loc[identity_profile["has_identity"].eq(0)].iloc[0]
    highest_week = weekly.loc[weekly["fraud_rate"].idxmax()]
    lowest_week = weekly.loc[weekly["fraud_rate"].idxmin()]
    markdown = f"""# Phase 1 data profile

## Executive readout

- **{summary['transactions']:,} transactions** span **{summary['elapsed_days']} elapsed days**; the hidden origin is not converted into calendar dates.
- **{summary['fraud_cases']:,} fraud cases** produce a **{summary['fraud_rate']:.2%} row-level fraud rate**.
- Fraud-labelled transactions represent **{summary['fraud_exposure_share']:.2%} of transaction exposure**. This is exposure, not realised loss.
- Only **{summary['identity_coverage']:.2%}** of transactions join to the identity table.
- Fraud rate is **{identity_with['fraud_rate']:.2%} with identity coverage** versus **{identity_without['fraud_rate']:.2%} without it**. Missing identity is therefore modelled as its own state, not interpreted as safety.
- The proxy entity key yields **{summary['unique_proxy_entities']:,} entities**; **{summary['repeat_entity_transaction_share']:.2%}** of rows belong to a repeated entity.
- The top 1% of proxy entities with observed fraud account for **{summary['top_1pct_fraud_entity_case_share']:.2%}** of fraud cases, supporting entity-aware prioritisation as a testable design.
- Weekly fraud rate ranges from **{lowest_week['fraud_rate']:.2%}** to **{highest_week['fraud_rate']:.2%}**, so random splitting would hide meaningful temporal variation.

## Data-quality implications

- The two source tables contain **{len(inventory):,} columns including keys/target**.
- **{summary['features_over_90pct_missing']} features** are at least 90% missing and **{summary['fully_missing_features']}** are fully missing in labelled data.
- High missingness is not automatically imputed away. Coverage flags, feature-family ablations, and temporal stability determine whether a feature survives.
- `TransactionDT` supplies ordering but not a real date. Reporting uses elapsed day/week only.
- Anonymous `V`, `C`, `D`, and `M` features will be described by statistical behaviour, never invented business meanings.

## Decision implications

1. Evaluate chronologically and keep the final 15% locked out of time.
2. Compare transaction-level queues with entity-deduplicated queues.
3. Report case capture and exposure capture because the two objectives need not select the same policy.
4. Treat identity availability and missingness patterns as monitored coverage signals.
5. Establish rule and logistic baselines before a gradient-boosting challenger.

## Generated evidence

- `reports/feature_inventory.csv`
- `reports/weekly_fraud_landscape.csv`
- `reports/cohort_fraud_profile.csv`
- `reports/identity_coverage_profile.csv`
- `reports/amount_decile_profile.csv`
- `reports/temporal_partitions.csv`
- `reports/data_profile_summary.json`
"""
    (DOCS / "data_profile.md").write_text(markdown)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
