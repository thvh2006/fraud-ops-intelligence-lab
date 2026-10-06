"""Backtest drift, delayed labels, and point-in-time recalibration."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.train_baseline import calibrated_probability, fit_platt, prepare_data  # noqa: E402
from src.monitoring import (  # noqa: E402
    available_label_mask,
    expected_calibration_error,
    population_stability_index,
)


REPORTS = ROOT / "reports"
DOCS = ROOT / "docs"
MODELS = ROOT / "models"


def mark_fast_reviews(frame: pd.DataFrame, capacity: int = 100) -> pd.Series:
    reviewed = pd.Series(False, index=frame.index)
    for _, group in frame.groupby("day", sort=True):
        queue = group.sort_values("probability", ascending=False, kind="stable")
        queue = queue.drop_duplicates("entity_key", keep="first").head(capacity)
        reviewed.loc[queue.index] = True
    return reviewed


def score_frame() -> tuple[pd.DataFrame, object]:
    artifact = joblib.load(MODELS / "nonlinear_challenger.joblib")
    frame = prepare_data()
    raw = artifact["pipeline"].decision_function(frame[artifact["features"]])
    frame["raw_score"] = raw
    frame["probability"] = calibrated_probability(artifact["calibrator"], raw)
    frame["reviewed_fast"] = mark_fast_reviews(frame)
    frame["elapsed_week"] = (frame["day"] // 7).astype(int)
    return frame, artifact


def weekly_monitoring(frame: pd.DataFrame) -> pd.DataFrame:
    development = frame.loc[frame["partition"].eq("development")]
    reference_probability = development["probability"].to_numpy()
    reference_amount = np.log1p(development["TransactionAmt"].to_numpy())
    rows = []
    for week, group in frame.loc[frame["partition"].eq("oot")].groupby("elapsed_week"):
        rows.append(
            {
                "elapsed_week": int(week),
                "rows": len(group),
                "fraud_rate": float(group["isFraud"].mean()),
                "average_probability": float(group["probability"].mean()),
                "average_precision": float(
                    average_precision_score(group["isFraud"], group["probability"])
                ),
                "brier_score": float(
                    brier_score_loss(group["isFraud"], group["probability"])
                ),
                "ece": expected_calibration_error(group["isFraud"], group["probability"]),
                "score_psi": population_stability_index(
                    reference_probability, group["probability"]
                ),
                "amount_psi": population_stability_index(
                    reference_amount, np.log1p(group["TransactionAmt"])
                ),
                "identity_coverage": float(group["has_identity"].mean()),
                "new_entity_rate": float(group["entity_is_new"].mean()),
                "mean_daily_alert_precision_at_100": float(
                    group.loc[group["reviewed_fast"], "isFraud"].mean()
                ),
            }
        )
    return pd.DataFrame(rows)


def delayed_label_backtest(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    oot = frame.loc[frame["partition"].eq("oot")]
    week_starts = sorted(oot.groupby("elapsed_week")["day"].min().astype(int).tolist())
    backtest_rows = []
    availability_rows = []
    for delay in (7, 14, 30):
        for snapshot_day in week_starts:
            current = oot.loc[(oot["day"] >= snapshot_day) & (oot["day"] < snapshot_day + 7)]
            available = available_label_mask(
                frame["day"],
                frame["reviewed_fast"],
                snapshot_day=snapshot_day,
                delayed_days=delay,
            )
            history = frame.loc[available & frame["day"].ge(snapshot_day - 60)]
            population_before = frame.loc[frame["day"].lt(snapshot_day)]
            availability_rows.append(
                {
                    "delay_days": delay,
                    "snapshot_day": snapshot_day,
                    "available_rows": len(history),
                    "label_coverage_all_history": float(
                        available.loc[population_before.index].mean()
                    ),
                    "available_fraud_cases": int(history["isFraud"].sum()),
                    "available_fraud_rate": float(history["isFraud"].mean()),
                    "fast_feedback_share_of_available_fraud": float(
                        history.loc[history["isFraud"].eq(1), "reviewed_fast"].mean()
                    ),
                }
            )
            if history["isFraud"].nunique() < 2 or current.empty:
                continue
            rolling_calibrator = fit_platt(
                history["raw_score"].to_numpy(), history["isFraud"]
            )
            rolling_probability = calibrated_probability(
                rolling_calibrator, current["raw_score"].to_numpy()
            )
            backtest_rows.append(
                {
                    "delay_days": delay,
                    "snapshot_day": snapshot_day,
                    "week_rows": len(current),
                    "week_fraud_rate": float(current["isFraud"].mean()),
                    "fixed_brier": float(
                        brier_score_loss(current["isFraud"], current["probability"])
                    ),
                    "rolling_brier": float(
                        brier_score_loss(current["isFraud"], rolling_probability)
                    ),
                    "fixed_ece": expected_calibration_error(
                        current["isFraud"], current["probability"]
                    ),
                    "rolling_ece": expected_calibration_error(
                        current["isFraud"], rolling_probability
                    ),
                    "average_precision": float(
                        average_precision_score(current["isFraud"], rolling_probability)
                    ),
                }
            )
    return pd.DataFrame(backtest_rows), pd.DataFrame(availability_rows)


def monitoring_alerts(weekly: pd.DataFrame) -> pd.DataFrame:
    records = []
    for row in weekly.itertuples():
        checks = {
            "score_psi": (row.score_psi, 0.10, 0.20),
            "amount_psi": (row.amount_psi, 0.10, 0.20),
            "ece": (row.ece, 0.02, 0.04),
        }
        for metric, (value, amber, red) in checks.items():
            status = "red" if value >= red else "amber" if value >= amber else "green"
            records.append(
                {
                    "elapsed_week": row.elapsed_week,
                    "metric": metric,
                    "value": value,
                    "amber_threshold": amber,
                    "red_threshold": red,
                    "status": status,
                }
            )
    return pd.DataFrame(records)


def main() -> None:
    frame, _ = score_frame()
    weekly = weekly_monitoring(frame)
    weekly.to_csv(REPORTS / "weekly_monitoring.csv", index=False)
    backtest, availability = delayed_label_backtest(frame)
    backtest.to_csv(REPORTS / "delayed_label_recalibration.csv", index=False)
    availability.to_csv(REPORTS / "label_availability.csv", index=False)
    alerts = monitoring_alerts(weekly)
    alerts.to_csv(REPORTS / "monitoring_alerts.csv", index=False)

    reviewed = frame.loc[frame["partition"].isin(["policy", "oot"])]
    reviewed_fraud_rate = float(reviewed.loc[reviewed["reviewed_fast"], "isFraud"].mean())
    non_reviewed_fraud_rate = float(reviewed.loc[~reviewed["reviewed_fast"], "isFraud"].mean())
    summary_by_delay = (
        backtest.groupby("delay_days")
        .agg(
            weeks=("snapshot_day", "size"),
            mean_fixed_brier=("fixed_brier", "mean"),
            mean_rolling_brier=("rolling_brier", "mean"),
            mean_fixed_ece=("fixed_ece", "mean"),
            mean_rolling_ece=("rolling_ece", "mean"),
        )
        .reset_index()
    )
    summary_by_delay["brier_change"] = (
        summary_by_delay["mean_rolling_brier"] - summary_by_delay["mean_fixed_brier"]
    )
    availability_summary = (
        availability.groupby("delay_days")
        .agg(
            mean_label_coverage=("label_coverage_all_history", "mean"),
            mean_available_rows=("available_rows", "mean"),
            mean_fast_feedback_share_of_available_fraud=(
                "fast_feedback_share_of_available_fraud",
                "mean",
            ),
        )
        .reset_index()
    )
    summary_by_delay = summary_by_delay.merge(
        availability_summary, on="delay_days", validate="one_to_one"
    )
    summary_by_delay.to_csv(REPORTS / "delayed_label_summary.csv", index=False)

    red_alerts = int(alerts["status"].eq("red").sum())
    max_score_psi = float(weekly["score_psi"].max())
    brier_improvements = -summary_by_delay["brier_change"]
    result = {
        "reviewed_feedback_fraud_rate": reviewed_fraud_rate,
        "non_reviewed_population_fraud_rate": non_reviewed_fraud_rate,
        "selection_bias_rate_ratio": reviewed_fraud_rate / non_reviewed_fraud_rate,
        "oot_weeks": int(len(weekly)),
        "max_weekly_score_psi": max_score_psi,
        "red_monitoring_alerts": red_alerts,
        "minimum_mean_brier_improvement": float(brier_improvements.min()),
        "maximum_mean_brier_improvement": float(brier_improvements.max()),
        "delay_window_recommended": False,
    }
    (REPORTS / "monitoring_decision.json").write_text(json.dumps(result, indent=2) + "\n")

    delay_lines = []
    for row in summary_by_delay.itertuples():
        direction = "improves" if row.brier_change < 0 else "worsens"
        delay_lines.append(
            f"- **{row.delay_days}-day delay:** rolling calibration {direction} mean Brier by "
            f"**{abs(row.brier_change):.5f}** versus the fixed calibrator; mean rolling ECE **{row.mean_rolling_ece:.3f}**; "
            f"mean historical label coverage **{row.mean_label_coverage:.1%}**."
        )
    memo = f"""# Delayed-label and monitoring backtest

## Feedback is selected, not representative

The simulated top-100 investigator stream has an observed fraud rate of **{reviewed_fraud_rate:.2%}**, versus **{non_reviewed_fraud_rate:.2%}** outside the reviewed queue—a **{result['selection_bias_rate_ratio']:.1f}×** rate ratio. Fast feedback therefore cannot be treated as a random training sample.

## Point-in-time recalibration

At the start of each OOT elapsed week, a Platt calibrator is refit using only labels available by that snapshot: immediate labels for previously reviewed alerts plus delayed labels for the remaining population. No current/future-week label enters the fit.

{chr(10).join(delay_lines)}

Rolling recalibration is not automatically promoted. Its value depends on delay and selected-feedback bias; the fixed development/calibration model remains the fallback whenever rolling Brier deteriorates.

The Brier differences across delay scenarios are only **{brier_improvements.min():.5f}–{brier_improvements.max():.5f}**. No delay setting is declared a winner from this short six-week OOT horizon.

## Drift monitoring

- Locked OOT covers **{len(weekly)} elapsed weeks**.
- Maximum weekly score PSI versus development is **{max_score_psi:.3f}**.
- The rules emit **{red_alerts} red alerts** across score PSI, amount PSI, and ECE checks.
- Thresholds are portfolio operating assumptions: PSI amber/red at 0.10/0.20 and ECE amber/red at 0.02/0.04. They require production calibration before operational use.

## Governance decision

Monitor score distribution, amount distribution, calibration, identity coverage, and alert precision weekly. Keep fast investigator feedback and delayed population outcomes as separate labelled streams; record label provenance and availability time. Trigger diagnosis before retraining because drift may reflect calibration, population, coverage, or policy selection rather than model ranking failure.
"""
    (DOCS / "monitoring_and_delayed_labels.md").write_text(memo)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
