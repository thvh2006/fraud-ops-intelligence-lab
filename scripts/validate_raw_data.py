"""Validate source files and write an aggregate-only data receipt."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data_contract import join_identity  # noqa: E402
from src.temporal import assign_temporal_partitions, assert_temporal_separation  # noqa: E402


RAW = ROOT / "data" / "raw"
REPORT = ROOT / "reports" / "data_receipt.json"


def main() -> None:
    transaction_path = RAW / "train_transaction.csv"
    identity_path = RAW / "train_identity.csv"
    missing = [str(path) for path in (transaction_path, identity_path) if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required raw files: {missing}")

    transactions = pd.read_csv(transaction_path)
    identity = pd.read_csv(identity_path)
    joined, summary = join_identity(transactions, identity)
    labels = assign_temporal_partitions(joined)
    assert_temporal_separation(joined, labels)

    receipt = {
        "rows": summary.rows,
        "fraud_rate": summary.fraud_rate,
        "identity_coverage": summary.identity_coverage,
        "time_min": summary.time_min,
        "time_max": summary.time_max,
        "partition_rows": labels.value_counts().to_dict(),
        "raw_rows_published": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
