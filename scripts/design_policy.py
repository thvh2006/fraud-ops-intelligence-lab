"""Translate calibrated challenger scores into a four-action decision policy."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

import joblib
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.train_baseline import calibrated_probability, prepare_data  # noqa: E402
from src.policy import (  # noqa: E402
    PolicyAssumptions,
    assign_four_action_policy,
    realised_proxy_cost,
)


REPORTS = ROOT / "reports"
DOCS = ROOT / "docs"
MODELS = ROOT / "models"

SCENARIOS = [
    PolicyAssumptions(
        name="balanced_reference",
        loss_given_fraud=0.60,
        step_up_effectiveness=0.40,
        review_effectiveness=0.75,
        block_effectiveness=0.95,
        step_up_fixed_cost=0.50,
        step_up_legit_friction=1.50,
        review_fixed_cost=5.00,
        review_legit_friction=3.00,
        block_fixed_cost=10.00,
        block_legit_amount_fraction=0.08,
    ),
    PolicyAssumptions(
        name="customer_first",
        loss_given_fraud=0.50,
        step_up_effectiveness=0.35,
        review_effectiveness=0.70,
        block_effectiveness=0.95,
        step_up_fixed_cost=0.75,
        step_up_legit_friction=2.50,
        review_fixed_cost=8.00,
        review_legit_friction=5.00,
        block_fixed_cost=25.00,
        block_legit_amount_fraction=0.20,
    ),
    PolicyAssumptions(
        name="loss_first",
        loss_given_fraud=0.80,
        step_up_effectiveness=0.45,
        review_effectiveness=0.80,
        block_effectiveness=0.97,
        step_up_fixed_cost=0.40,
        step_up_legit_friction=0.75,
        review_fixed_cost=3.00,
        review_legit_friction=1.50,
        block_fixed_cost=5.00,
        block_legit_amount_fraction=0.03,
    ),
]


def score_partitions() -> dict[str, pd.DataFrame]:
    artifact = joblib.load(MODELS / "nonlinear_challenger.joblib")
    frame = prepare_data()
    outputs = {}
    for partition in ("policy", "oot"):
        part = frame.loc[frame["partition"].eq(partition)].copy()
        raw = artifact["pipeline"].decision_function(part[artifact["features"]])
        part["probability"] = calibrated_probability(artifact["calibrator"], raw)
        outputs[partition] = part
    return outputs


def evaluate_policy(
    assigned: pd.DataFrame,
    assumptions: PolicyAssumptions,
    partition: str,
    capacity: int,
) -> tuple[dict[str, object], pd.DataFrame]:
    evaluated = assigned.copy()
    evaluated["realised_proxy_cost"] = realised_proxy_cost(
        evaluated["action"], evaluated["isFraud"], evaluated["TransactionAmt"], assumptions
    )
    baseline_cost = (
        evaluated["isFraud"]
        * evaluated["TransactionAmt"]
        * assumptions.loss_given_fraud
    )
    intervened = evaluated["action"].ne("allow")
    fraud = evaluated["isFraud"].eq(1)
    legitimate = ~fraud
    effectiveness = evaluated["action"].map(
        {
            "allow": 0.0,
            "step_up": assumptions.step_up_effectiveness,
            "review": assumptions.review_effectiveness,
            "block": assumptions.block_effectiveness,
        }
    )
    prevented_exposure = (
        evaluated["TransactionAmt"] * fraud.astype(float) * effectiveness
    ).sum()
    review_transactions = int(evaluated["action"].eq("review").sum())
    operational_days = int(evaluated["day"].nunique())
    summary = {
        "scenario": assumptions.name,
        "partition": partition,
        "review_capacity": capacity,
        "operational_days": operational_days,
        "review_transactions": review_transactions,
        "mean_daily_reviews": review_transactions / operational_days,
        "review_capacity_utilisation": (
            review_transactions / (operational_days * capacity) if capacity else 0.0
        ),
        "transactions": len(evaluated),
        "fraud_cases": int(fraud.sum()),
        "intervention_rate": float(intervened.mean()),
        "fraud_case_intervention_rate": float(intervened.loc[fraud].mean()),
        "fraud_exposure_intervention_rate": float(
            evaluated.loc[fraud & intervened, "TransactionAmt"].sum()
            / evaluated.loc[fraud, "TransactionAmt"].sum()
        ),
        "prevented_exposure_proxy": float(prevented_exposure),
        "prevented_exposure_proxy_rate": float(
            prevented_exposure / evaluated.loc[fraud, "TransactionAmt"].sum()
        ),
        "legitimate_transactions_interrupted": int((legitimate & intervened).sum()),
        "legitimate_exposure_interrupted": float(
            evaluated.loc[legitimate & intervened, "TransactionAmt"].sum()
        ),
        "allow_all_proxy_cost": float(baseline_cost.sum()),
        "policy_proxy_cost": float(evaluated["realised_proxy_cost"].sum()),
        "proxy_cost_reduction": float(baseline_cost.sum() - evaluated["realised_proxy_cost"].sum()),
    }
    action_summary = (
        evaluated.groupby("action")
        .agg(
            transactions=("isFraud", "size"),
            fraud_cases=("isFraud", "sum"),
            exposure=("TransactionAmt", "sum"),
            average_probability=("probability", "mean"),
            realised_proxy_cost=("realised_proxy_cost", "sum"),
        )
        .reindex(["allow", "step_up", "review", "block"], fill_value=0)
        .reset_index()
    )
    action_summary["scenario"] = assumptions.name
    action_summary["partition"] = partition
    action_summary["review_capacity"] = capacity
    action_summary["fraud_rate"] = action_summary["fraud_cases"].div(
        action_summary["transactions"].replace(0, pd.NA)
    )
    return summary, action_summary


def main() -> None:
    partitions = score_partitions()
    summaries = []
    actions = []
    for assumptions in SCENARIOS:
        for capacity in (50, 100, 250, 500):
            for partition, frame in partitions.items():
                assigned = assign_four_action_policy(
                    frame,
                    assumptions=assumptions,
                    daily_review_capacity=capacity,
                )
                summary, action_summary = evaluate_policy(
                    assigned, assumptions, partition, capacity
                )
                summaries.append(summary)
                actions.append(action_summary)

    sensitivity = pd.DataFrame(summaries)
    sensitivity.to_csv(REPORTS / "policy_sensitivity.csv", index=False)
    action_frame = pd.concat(actions, ignore_index=True)
    action_frame.to_csv(REPORTS / "policy_action_summary.csv", index=False)
    assumptions_frame = pd.DataFrame([asdict(scenario) for scenario in SCENARIOS])
    assumptions_frame.to_csv(REPORTS / "policy_assumptions.csv", index=False)

    reference = sensitivity.query(
        "scenario == 'balanced_reference' and review_capacity == 100 and partition == 'oot'"
    ).iloc[0]
    reference_actions = action_frame.query(
        "scenario == 'balanced_reference' and review_capacity == 100 and partition == 'oot'"
    )
    action_lines = []
    for row in reference_actions.itertuples():
        action_lines.append(
            f"- **{row.action}**: {int(row.transactions):,} transactions, "
            f"observed fraud rate {row.fraud_rate:.2%}, mean calibrated risk {row.average_probability:.2%}."
        )
    result = {
        "reference_scenario": "balanced_reference",
        "reference_review_capacity": 100,
        "oot_intervention_rate": float(reference["intervention_rate"]),
        "oot_fraud_case_intervention_rate": float(reference["fraud_case_intervention_rate"]),
        "oot_fraud_exposure_intervention_rate": float(
            reference["fraud_exposure_intervention_rate"]
        ),
        "oot_prevented_exposure_proxy_rate": float(
            reference["prevented_exposure_proxy_rate"]
        ),
        "oot_mean_daily_reviews": float(reference["mean_daily_reviews"]),
        "oot_review_capacity_utilisation": float(reference["review_capacity_utilisation"]),
        "oot_legitimate_transactions_interrupted": int(
            reference["legitimate_transactions_interrupted"]
        ),
        "oot_proxy_cost_reduction": float(reference["proxy_cost_reduction"]),
    }
    (REPORTS / "policy_decision.json").write_text(json.dumps(result, indent=2) + "\n")

    memo = f"""# Four-action fraud policy memo

## Reference policy

The balanced reference scenario with capacity for 100 manual reviews per elapsed day is used as a readable operating example—not as a claim about Vesta's actual economics.

On locked OOT data it intervenes on **{result['oot_intervention_rate']:.2%}** of transactions, reaches **{result['oot_fraud_case_intervention_rate']:.2%}** of fraud cases, and covers **{result['oot_fraud_exposure_intervention_rate']:.2%}** of fraud exposure. After applying assumed action effectiveness, prevented-exposure proxy is **{result['oot_prevented_exposure_proxy_rate']:.2%}**. It uses **{result['oot_mean_daily_reviews']:.1f} reviews/day** (**{result['oot_review_capacity_utilisation']:.1%}** of nominal capacity), interrupts **{result['oot_legitimate_transactions_interrupted']:,} legitimate transactions**, and reduces simulated cost by **{result['oot_proxy_cost_reduction']:,.0f} units** under the stated assumptions only.

## Action mix on locked OOT

{chr(10).join(action_lines)}

## Policy logic

For every transaction, expected cost is estimated for allow, step-up, review, and block. Review is capacity-constrained per elapsed day: only cases with the largest positive expected benefit from review enter the queue; remaining cases fall back to their least-cost non-review action. This makes capacity an explicit optimisation constraint rather than a score threshold chosen after OOT inspection.

## Governance boundary

- Intervention effectiveness and friction costs are assumptions, not observed causal effects.
- `TransactionAmt` is exposure, not realised loss or recoverable chargeback value.
- The reference scenario is not universally optimal; `reports/policy_sensitivity.csv` preserves customer-first and loss-first alternatives across capacities 50/100/250/500.
- A real deployment would require controlled measurement of step-up completion, review outcomes, false-positive harm, and block effectiveness before monetary claims.
"""
    (DOCS / "policy_decision_memo.md").write_text(memo)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
