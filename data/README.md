# Data access and handling

## Source

The intended source is the Kaggle competition **IEEE-CIS Fraud Detection**. The source contains separate transaction and identity tables joined on `TransactionID`; not every transaction has an identity row.

## Access

1. Sign in to Kaggle.
2. Open the competition rules and accept them.
3. Create a Kaggle API token or configure the official Kaggle CLI.
4. Run `python scripts/acquire_data.py` from the repository root.

The script uses the official competition download endpoint through the Kaggle CLI. Credentials stay in the user's Kaggle configuration or environment and must never be copied into this repository.

## Expected raw files

```text
data/raw/train_transaction.csv
data/raw/train_identity.csv
data/raw/test_transaction.csv
data/raw/test_identity.csv
data/raw/sample_submission.csv
```

Only the labelled training transaction and identity tables are required for the core portfolio analysis. The competition test set may be profiled for shift but is not used as the final evaluation set because its labels are unavailable. A chronological slice of the labelled training set is locked as the out-of-time evaluation period.

## Handling policy

- Raw, interim, and processed records are git-ignored.
- No raw rows are displayed in the public dashboard.
- Published outputs contain aggregate statistics only.
- `TransactionDT` is an elapsed-time value, not a real calendar timestamp.
- `TransactionAmt` is exposure, not confirmed loss.
- An identity-table miss is represented as missing coverage, never silently converted into a known low-risk identity.

