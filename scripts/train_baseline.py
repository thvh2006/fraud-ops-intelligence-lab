"""Train leakage-safe rule and linear baselines, then score locked OOT data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.features import add_past_only_entity_history, make_proxy_entity  # noqa: E402
from src.metrics import top_k_operations  # noqa: E402
from src.temporal import assign_temporal_partitions  # noqa: E402


RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"
MODELS = ROOT / "models"
DOCS = ROOT / "docs"

CORE_COLUMNS = [
    "TransactionID",
    "isFraud",
    "TransactionDT",
    "TransactionAmt",
    "ProductCD",
    "card1",
    "card2",
    "card3",
    "card4",
    "card5",
    "card6",
    "addr1",
    "addr2",
    "dist1",
    "dist2",
    "P_emaildomain",
    "R_emaildomain",
] + [f"C{i}" for i in range(1, 15)] + [f"D{i}" for i in range(1, 16)]

CATEGORICAL = [
    "ProductCD",
    "card4",
    "card6",
    "P_emaildomain",
    "R_emaildomain",
    "DeviceType",
    "id_31",
]

NUMERIC = [
    "TransactionAmt",
    "card1",
    "card2",
    "card3",
    "card5",
    "addr1",
    "addr2",
    "dist1",
    "dist2",
    *[f"C{i}" for i in range(1, 15)],
    *[f"D{i}" for i in range(1, 16)],
    "has_identity",
    "elapsed_day",
    "hour_sin",
    "hour_cos",
    "entity_prior_tx_count",
    "entity_prior_amount_mean",
    "entity_seconds_since_previous",
    "amount_to_entity_prior_mean",
    "entity_is_new",
]


def prepare_data() -> pd.DataFrame:
    transaction = pd.read_csv(RAW / "train_transaction.csv", usecols=CORE_COLUMNS, low_memory=False)
    identity = pd.read_csv(
        RAW / "train_identity.csv",
        usecols=["TransactionID", "DeviceType", "id_31"],
        low_memory=False,
    )
    frame = transaction.merge(
        identity.assign(has_identity=1), on="TransactionID", how="left", validate="one_to_one"
    )
    frame["has_identity"] = frame["has_identity"].fillna(0).astype("int8")
    frame = frame.sort_values(["TransactionDT", "TransactionID"], kind="stable").reset_index(drop=True)
    frame["entity_key"] = make_proxy_entity(
        frame, ["card1", "addr1", "P_emaildomain"]
    )
    frame = add_past_only_entity_history(frame)
    frame["elapsed_day"] = (frame["TransactionDT"] // 86_400).astype("int16")
    hour = (frame["TransactionDT"] % 86_400) / 3_600
    frame["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    frame["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    frame["day"] = frame["elapsed_day"]
    frame["partition"] = assign_temporal_partitions(frame)
    return frame


def fit_rule_score(development: pd.DataFrame, frame: pd.DataFrame) -> np.ndarray:
    """Operational rules use development-only quantiles and signal direction."""
    amount_cut = development["TransactionAmt"].quantile(0.95)
    velocity_cut = development["entity_prior_tx_count"].quantile(0.95)
    ratio_cut = development["amount_to_entity_prior_mean"].replace([np.inf, -np.inf], np.nan).quantile(0.95)
    identity_rates = development.groupby("has_identity")["isFraud"].mean()
    risky_identity_state = int(identity_rates.idxmax())
    return (
        (frame["TransactionAmt"] >= amount_cut).astype(float)
        + (frame["entity_prior_tx_count"] >= velocity_cut).astype(float)
        + (frame["amount_to_entity_prior_mean"] >= ratio_cut).fillna(False).astype(float)
        + (frame["has_identity"] == risky_identity_state).astype(float)
        + frame["entity_is_new"].astype(float) * 0.5
    ).to_numpy()


def fit_platt(raw_score: np.ndarray, target: pd.Series) -> LogisticRegression:
    calibrator = LogisticRegression(C=1.0, solver="lbfgs", max_iter=200)
    calibrator.fit(raw_score.reshape(-1, 1), target)
    return calibrator


def calibrated_probability(calibrator: LogisticRegression, raw_score: np.ndarray) -> np.ndarray:
    return calibrator.predict_proba(raw_score.reshape(-1, 1))[:, 1]


def metric_row(model: str, partition: str, target: pd.Series, probability: np.ndarray) -> dict[str, object]:
    return {
        "model": model,
        "partition": partition,
        "rows": len(target),
        "fraud_rate": float(target.mean()),
        "average_precision": float(average_precision_score(target, probability)),
        "roc_auc": float(roc_auc_score(target, probability)),
        "brier_score": float(brier_score_loss(target, probability)),
    }


def operations_for(
    frame: pd.DataFrame, probability: np.ndarray, model: str, partition: str
) -> pd.DataFrame:
    scored = frame[["day", "isFraud", "TransactionAmt", "entity_key"]].copy()
    scored["score"] = probability
    outputs = []
    for queue_type, entity_column in (("transaction", None), ("entity_deduplicated", "entity_key")):
        for capacity in (50, 100, 250, 500):
            daily = top_k_operations(
                scored,
                k=capacity,
                entity_column=entity_column,
            )
            daily["model"] = model
            daily["partition"] = partition
            daily["queue_type"] = queue_type
            outputs.append(daily)
    return pd.concat(outputs, ignore_index=True)


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    MODELS.mkdir(parents=True, exist_ok=True)
    frame = prepare_data()
    masks = {name: frame["partition"].eq(name) for name in ("development", "calibration", "policy", "oot")}

    rule_raw = fit_rule_score(frame.loc[masks["development"]], frame)
    rule_calibrator = fit_platt(rule_raw[masks["calibration"].to_numpy()], frame.loc[masks["calibration"], "isFraud"])

    preprocess = ColumnTransformer(
        transformers=[
            (
                "numeric",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="median", add_indicator=True)),
                        ("scale", StandardScaler()),
                    ]
                ),
                NUMERIC,
            ),
            (
                "categorical",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        (
                            "encode",
                            OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=100),
                        ),
                    ]
                ),
                CATEGORICAL,
            ),
        ]
    )
    linear = Pipeline(
        [
            ("preprocess", preprocess),
            (
                "model",
                SGDClassifier(
                    loss="log_loss",
                    penalty="elasticnet",
                    l1_ratio=0.05,
                    alpha=1e-5,
                    class_weight="balanced",
                    max_iter=80,
                    tol=1e-4,
                    random_state=42,
                    average=True,
                ),
            ),
        ]
    )
    linear.fit(frame.loc[masks["development"], NUMERIC + CATEGORICAL], frame.loc[masks["development"], "isFraud"])
    calibration_raw = linear.decision_function(frame.loc[masks["calibration"], NUMERIC + CATEGORICAL])
    linear_calibrator = fit_platt(calibration_raw, frame.loc[masks["calibration"], "isFraud"])

    metrics: list[dict[str, object]] = []
    operation_tables = []
    probability_cache: dict[tuple[str, str], np.ndarray] = {}
    for partition in ("policy", "oot"):
        part = frame.loc[masks[partition]]
        rule_probability = calibrated_probability(
            rule_calibrator, rule_raw[masks[partition].to_numpy()]
        )
        linear_raw = linear.decision_function(part[NUMERIC + CATEGORICAL])
        linear_probability = calibrated_probability(linear_calibrator, linear_raw)
        for model, probability in (("rules", rule_probability), ("linear", linear_probability)):
            probability_cache[(model, partition)] = probability
            metrics.append(metric_row(model, partition, part["isFraud"], probability))
            operation_tables.append(operations_for(part, probability, model, partition))

    metrics_frame = pd.DataFrame(metrics)
    metrics_frame.to_csv(REPORTS / "baseline_model_metrics.csv", index=False)
    daily_operations = pd.concat(operation_tables, ignore_index=True)
    daily_operations.to_csv(REPORTS / "baseline_daily_operations.csv", index=False)

    operations_summary = (
        daily_operations.groupby(["model", "partition", "queue_type", "capacity"])
        .agg(
            days=("day", "nunique"),
            mean_alerts=("alerts", "mean"),
            mean_precision_at_k=("precision_at_k", "mean"),
            median_precision_at_k=("precision_at_k", "median"),
            mean_recall_at_k=("recall_at_k", "mean"),
            mean_exposure_captured_at_k=("exposure_captured_at_k", "mean"),
            total_legitimate_exposure_interrupted=("legitimate_exposure_interrupted", "sum"),
        )
        .reset_index()
    )
    operations_summary.to_csv(REPORTS / "baseline_operations_summary.csv", index=False)

    policy_choice = operations_summary.query(
        "partition == 'policy' and queue_type == 'entity_deduplicated' and capacity == 100"
    ).sort_values(["mean_precision_at_k", "mean_exposure_captured_at_k"], ascending=False)
    selected_model = str(policy_choice.iloc[0]["model"])

    feature_names = linear.named_steps["preprocess"].get_feature_names_out()
    coefficients = linear.named_steps["model"].coef_.ravel()
    coefficient_frame = pd.DataFrame(
        {"feature": feature_names, "coefficient": coefficients, "absolute_coefficient": np.abs(coefficients)}
    ).sort_values("absolute_coefficient", ascending=False)
    coefficient_frame.to_csv(REPORTS / "linear_coefficients.csv", index=False)

    joblib.dump(
        {
            "pipeline": linear,
            "calibrator": linear_calibrator,
            "features": NUMERIC + CATEGORICAL,
            "entity_definition": ["card1", "addr1", "P_emaildomain"],
        },
        MODELS / "linear_baseline.joblib",
    )

    oot_metrics = metrics_frame.loc[metrics_frame["partition"].eq("oot")].set_index("model")
    oot_ops = operations_summary.query(
        "partition == 'oot' and queue_type == 'entity_deduplicated' and capacity == 100"
    ).set_index("model")
    result = {
        "selected_on_policy_window": selected_model,
        "selection_metric": "mean daily precision at 100 entity-deduplicated alerts",
        "oot_average_precision": float(oot_metrics.loc[selected_model, "average_precision"]),
        "oot_roc_auc": float(oot_metrics.loc[selected_model, "roc_auc"]),
        "oot_brier_score": float(oot_metrics.loc[selected_model, "brier_score"]),
        "oot_mean_daily_precision_at_100": float(oot_ops.loc[selected_model, "mean_precision_at_k"]),
        "oot_mean_daily_recall_at_100": float(oot_ops.loc[selected_model, "mean_recall_at_k"]),
        "oot_mean_daily_exposure_capture_at_100": float(
            oot_ops.loc[selected_model, "mean_exposure_captured_at_k"]
        ),
    }
    (REPORTS / "baseline_decision.json").write_text(json.dumps(result, indent=2) + "\n")

    memo = f"""# Baseline decision memo

## Decision

The **{selected_model} baseline** is selected on the policy window using mean daily precision at 100 entity-deduplicated alerts. The locked OOT period was not used for this choice.

## Locked OOT evidence

- Average precision: **{result['oot_average_precision']:.3f}**
- ROC-AUC: **{result['oot_roc_auc']:.3f}**
- Brier score after development/calibration separation: **{result['oot_brier_score']:.4f}**
- Mean daily precision@100: **{result['oot_mean_daily_precision_at_100']:.2%}**
- Mean daily recall@100: **{result['oot_mean_daily_recall_at_100']:.2%}**
- Mean daily fraud-exposure capture@100: **{result['oot_mean_daily_exposure_capture_at_100']:.2%}**

## Interpretation boundary

This result demonstrates a reproducible baseline and queue evaluation—not a deployable block policy. The proxy entity is not a verified customer ID; transaction amount is exposure rather than realised loss; and analyst outcomes are not observed. A non-linear challenger must beat this baseline on the policy metric and remain stable OOT before it is preferred.
"""
    (DOCS / "baseline_decision_memo.md").write_text(memo)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
