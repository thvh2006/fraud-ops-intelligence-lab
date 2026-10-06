"""Quantify day-level uncertainty around operational model comparisons."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
DOCS = ROOT / "docs"
RNG = np.random.default_rng(42)


def paired_bootstrap(
    frame: pd.DataFrame,
    candidate: str,
    reference: str,
    partition: str,
    metric: str = "precision_at_k",
    draws: int = 10_000,
) -> dict[str, object]:
    subset = frame.query(
        "partition == @partition and queue_type == 'entity_deduplicated' and capacity == 100"
    )
    pivot = subset.pivot(index="day", columns="model", values=metric).dropna(
        subset=[candidate, reference]
    )
    differences = (pivot[candidate] - pivot[reference]).to_numpy()
    sampled = differences[RNG.integers(0, len(differences), size=(draws, len(differences)))].mean(axis=1)
    return {
        "partition": partition,
        "candidate": candidate,
        "reference": reference,
        "metric": metric,
        "days": len(differences),
        "mean_difference": float(differences.mean()),
        "ci_low_95": float(np.quantile(sampled, 0.025)),
        "ci_high_95": float(np.quantile(sampled, 0.975)),
        "probability_candidate_better": float((sampled > 0).mean()),
    }


def main() -> None:
    baseline = pd.read_csv(REPORTS / "baseline_daily_operations.csv")
    challenger = pd.read_csv(REPORTS / "challenger_daily_operations.csv")
    combined = pd.concat([baseline, challenger], ignore_index=True)
    selected = "gbm_plus_identity"
    comparisons = []
    for partition in ("policy", "oot"):
        for reference in ("linear", "gbm_transaction", "gbm_plus_behaviour"):
            comparisons.append(paired_bootstrap(combined, selected, reference, partition))
    result = pd.DataFrame(comparisons)
    result.to_csv(REPORTS / "model_comparison_uncertainty.csv", index=False)

    policy_linear = result.query("partition == 'policy' and reference == 'linear'").iloc[0]
    policy_core = result.query("partition == 'policy' and reference == 'gbm_transaction'").iloc[0]
    oot_core = result.query("partition == 'oot' and reference == 'gbm_transaction'").iloc[0]
    markdown = f"""# Day-level model comparison uncertainty

## Why this check exists

The model is used to form a daily queue, so transaction-level confidence intervals would overstate precision by treating correlated transactions from the same day as independent. This comparison resamples whole elapsed days and measures paired differences in entity-deduplicated precision@100.

## Results

- Against the calibrated linear baseline on the **policy window**, `gbm_plus_identity` improves mean daily precision@100 by **{policy_linear['mean_difference']:.2%}** (95% bootstrap interval **{policy_linear['ci_low_95']:.2%} to {policy_linear['ci_high_95']:.2%}**; probability of positive uplift **{policy_linear['probability_candidate_better']:.1%}**).
- Against transaction-only GBM on the **policy window**, the identity increment is **{policy_core['mean_difference']:.2%}** (95% interval **{policy_core['ci_low_95']:.2%} to {policy_core['ci_high_95']:.2%}**).
- On locked OOT, the identity increment versus transaction-only GBM is **{oot_core['mean_difference']:.2%}** (95% interval **{oot_core['ci_low_95']:.2%} to {oot_core['ci_high_95']:.2%}**).

## Decision

The non-linear family clearly improves the queue over the linear baseline. The incremental value of identity and engineered behavioural history is not yet established if its paired interval includes zero. `gbm_plus_identity` remains the policy-selected candidate because the selection rule was declared before OOT inspection, but the simpler transaction model stays an active challenger. This prevents a tiny policy-window difference from being marketed as a robust feature uplift.
"""
    (DOCS / "model_comparison_uncertainty.md").write_text(markdown)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
