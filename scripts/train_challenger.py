"""Train non-linear challengers and run feature-family ablations."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.train_baseline import (
    CATEGORICAL,
    NUMERIC,
    calibrated_probability,
    fit_platt,
    metric_row,
    operations_for,
    prepare_data,
)
from src.model_selection import select_governed_model

REPORTS = ROOT / "reports"
MODELS = ROOT / "models"
DOCS = ROOT / "docs"

BEHAVIOUR_FEATURES = [
    "entity_prior_tx_count",
    "entity_prior_amount_mean",
    "entity_seconds_since_previous",
    "amount_to_entity_prior_mean",
    "entity_is_new",
]
IDENTITY_NUMERIC = ["has_identity"]
IDENTITY_CATEGORICAL = ["DeviceType", "id_31"]
CORE_NUMERIC = [feature for feature in NUMERIC if feature not in BEHAVIOUR_FEATURES + IDENTITY_NUMERIC]
CORE_CATEGORICAL = [feature for feature in CATEGORICAL if feature not in IDENTITY_CATEGORICAL]

FEATURE_SETS = {
    "gbm_transaction": (CORE_NUMERIC, CORE_CATEGORICAL),
    "gbm_plus_identity": (
        CORE_NUMERIC + IDENTITY_NUMERIC,
        CORE_CATEGORICAL + IDENTITY_CATEGORICAL,
    ),
    "gbm_plus_behaviour": (NUMERIC, CATEGORICAL),
}


def build_challenger(numeric: list[str], categorical: list[str]) -> Pipeline:
    preprocess = ColumnTransformer(
        transformers=[
            ("numeric", SimpleImputer(strategy="median"), numeric),
            (
                "categorical",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        (
                            "encode",
                            OrdinalEncoder(
                                handle_unknown="use_encoded_value",
                                unknown_value=-1,
                                encoded_missing_value=-1,
                            ),
                        ),
                    ]
                ),
                categorical,
            ),
        ]
    )
    categorical_positions = list(range(len(numeric), len(numeric) + len(categorical)))
    model = HistGradientBoostingClassifier(
        learning_rate=0.08,
        max_iter=140,
        max_leaf_nodes=31,
        min_samples_leaf=40,
        l2_regularization=1.0,
        class_weight="balanced",
        categorical_features=categorical_positions,
        early_stopping=True,
        validation_fraction=0.10,
        n_iter_no_change=15,
        random_state=42,
    )
    return Pipeline([("preprocess", preprocess), ("model", model)])


def main() -> None:
    MODELS.mkdir(exist_ok=True)
    frame = prepare_data()
    masks = {name: frame["partition"].eq(name) for name in ("development", "calibration", "policy", "oot")}
    metrics: list[dict[str, object]] = []
    operation_tables = []
    fitted: dict[str, dict[str, object]] = {}

    for model_name, (numeric, categorical) in FEATURE_SETS.items():
        features = numeric + categorical
        pipeline = build_challenger(numeric, categorical)
        pipeline.fit(
            frame.loc[masks["development"], features],
            frame.loc[masks["development"], "isFraud"],
        )
        calibration_raw = pipeline.decision_function(frame.loc[masks["calibration"], features])
        calibrator = fit_platt(calibration_raw, frame.loc[masks["calibration"], "isFraud"])
        fitted[model_name] = {
            "pipeline": pipeline,
            "calibrator": calibrator,
            "features": features,
            "feature_families": {
                "core": CORE_NUMERIC + CORE_CATEGORICAL,
                "identity": [feature for feature in features if feature in IDENTITY_NUMERIC + IDENTITY_CATEGORICAL],
                "behaviour": [feature for feature in features if feature in BEHAVIOUR_FEATURES],
            },
        }

        for partition in ("policy", "oot"):
            part = frame.loc[masks[partition]]
            raw_score = pipeline.decision_function(part[features])
            probability = calibrated_probability(calibrator, raw_score)
            row = metric_row(model_name, partition, part["isFraud"], probability)
            row["feature_count"] = len(features)
            row["boosting_iterations"] = pipeline.named_steps["model"].n_iter_
            metrics.append(row)
            operation_tables.append(operations_for(part, probability, model_name, partition))

    metrics_frame = pd.DataFrame(metrics)
    metrics_frame.to_csv(REPORTS / "challenger_model_metrics.csv", index=False)
    daily = pd.concat(operation_tables, ignore_index=True)
    daily.to_csv(REPORTS / "challenger_daily_operations.csv", index=False)
    summary = (
        daily.groupby(["model", "partition", "queue_type", "capacity"])
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
    summary.to_csv(REPORTS / "challenger_operations_summary.csv", index=False)

    selection = summary.query(
        "partition == 'policy' and queue_type == 'entity_deduplicated' and capacity == 100"
    ).sort_values(["mean_precision_at_k", "mean_exposure_captured_at_k"], ascending=False)
    selected_model, selection_reason = select_governed_model(selection)
    selected = fitted[selected_model]
    joblib.dump(selected, MODELS / "nonlinear_challenger.joblib")

    baseline_metrics = pd.read_csv(REPORTS / "baseline_model_metrics.csv")
    baseline_ops = pd.read_csv(REPORTS / "baseline_operations_summary.csv")
    linear_oot_metric = baseline_metrics.query("model == 'linear' and partition == 'oot'").iloc[0]
    linear_oot_ops = baseline_ops.query(
        "model == 'linear' and partition == 'oot' and queue_type == 'entity_deduplicated' and capacity == 100"
    ).iloc[0]
    selected_oot_metric = metrics_frame.query(
        "model == @selected_model and partition == 'oot'"
    ).iloc[0]
    selected_oot_ops = summary.query(
        "model == @selected_model and partition == 'oot' and queue_type == 'entity_deduplicated' and capacity == 100"
    ).iloc[0]

    ablation = summary.query(
        "partition == 'policy' and queue_type == 'entity_deduplicated' and capacity == 100"
    )[
        [
            "model",
            "mean_precision_at_k",
            "mean_recall_at_k",
            "mean_exposure_captured_at_k",
            "total_legitimate_exposure_interrupted",
        ]
    ].merge(
        metrics_frame.query("partition == 'policy'")[
            ["model", "average_precision", "roc_auc", "brier_score"]
        ],
        on="model",
        validate="one_to_one",
    )
    ablation.to_csv(REPORTS / "feature_family_ablation.csv", index=False)

    result = {
        "selected_on_policy_window": selected_model,
        "selection_reason": selection_reason,
        "parsimony_gate_absolute_precision_gain": 0.01,
        "selection_metric": "mean daily precision at 100 entity-deduplicated alerts",
        "oot_average_precision": float(selected_oot_metric["average_precision"]),
        "oot_roc_auc": float(selected_oot_metric["roc_auc"]),
        "oot_brier_score": float(selected_oot_metric["brier_score"]),
        "oot_mean_daily_precision_at_100": float(selected_oot_ops["mean_precision_at_k"]),
        "oot_mean_daily_recall_at_100": float(selected_oot_ops["mean_recall_at_k"]),
        "oot_mean_daily_exposure_capture_at_100": float(
            selected_oot_ops["mean_exposure_captured_at_k"]
        ),
        "oot_legitimate_exposure_interrupted_at_100": float(
            selected_oot_ops["total_legitimate_exposure_interrupted"]
        ),
        "precision_uplift_vs_linear": float(
            selected_oot_ops["mean_precision_at_k"] / linear_oot_ops["mean_precision_at_k"] - 1
        ),
        "average_precision_uplift_vs_linear": float(
            selected_oot_metric["average_precision"] / linear_oot_metric["average_precision"] - 1
        ),
    }
    (REPORTS / "challenger_decision.json").write_text(json.dumps(result, indent=2) + "\n")

    ablation_lines = []
    for row in ablation.sort_values("mean_precision_at_k").itertuples():
        ablation_lines.append(
            f"- `{row.model}`: policy precision@100 **{row.mean_precision_at_k:.2%}**, "
            f"AP **{row.average_precision:.3f}**, exposure capture **{row.mean_exposure_captured_at_k:.2%}**."
        )
    memo = f"""# Non-linear challenger decision

## Selection

`{selected_model}` is selected by a governed policy rule: maximize mean daily
precision at 100 entity-deduplicated alerts, but prefer the transaction-only model
unless added feature families improve absolute precision by at least 1 percentage
point. Selection reason: `{selection_reason}`. All candidates use the same
development, calibration, policy, and locked OOT boundaries.

## Feature-family ablation on the policy window

{chr(10).join(ablation_lines)}

The ablation isolates whether identity and behavioural history improve the operational queue; it does not attribute causality to anonymous source variables.

## Locked OOT evidence for the selected challenger

- Average precision: **{result['oot_average_precision']:.3f}**
- ROC-AUC: **{result['oot_roc_auc']:.3f}**
- Brier score: **{result['oot_brier_score']:.4f}**
- Mean daily precision@100: **{result['oot_mean_daily_precision_at_100']:.2%}**
- Mean daily recall@100: **{result['oot_mean_daily_recall_at_100']:.2%}**
- Mean daily fraud-exposure capture@100: **{result['oot_mean_daily_exposure_capture_at_100']:.2%}**
- Calibrated linear reference precision@100: retained as a floor, not a headline uplift claim.
- Feature-family comparisons: interpreted with paired day-level uncertainty.

## Promotion gate

The challenger is promoted for policy design only if it improves the declared policy metric and does not create an incoherent friction/exposure trade-off. Promotion here means “preferred for the next offline policy stage,” not production deployment.
"""
    (DOCS / "challenger_decision_memo.md").write_text(memo)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
