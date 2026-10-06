"""Capacity-constrained four-action fraud policy simulation."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd


ACTIONS = ("allow", "step_up", "review", "block")


@dataclass(frozen=True)
class PolicyAssumptions:
    name: str
    loss_given_fraud: float
    step_up_effectiveness: float
    review_effectiveness: float
    block_effectiveness: float
    step_up_fixed_cost: float
    step_up_legit_friction: float
    review_fixed_cost: float
    review_legit_friction: float
    block_fixed_cost: float
    block_legit_amount_fraction: float

    def validate(self) -> None:
        probabilities = (
            self.loss_given_fraud,
            self.step_up_effectiveness,
            self.review_effectiveness,
            self.block_effectiveness,
            self.block_legit_amount_fraction,
        )
        if any(value < 0 or value > 1 for value in probabilities):
            raise ValueError("Probability/fraction assumptions must be inside [0, 1]")
        if any(value < 0 for value in asdict(self).values() if isinstance(value, (int, float))):
            raise ValueError("Cost assumptions must be non-negative")


def expected_action_costs(
    probability: np.ndarray, amount: np.ndarray, assumptions: PolicyAssumptions
) -> pd.DataFrame:
    assumptions.validate()
    p = np.asarray(probability, dtype=float)
    exposure = np.asarray(amount, dtype=float)
    if p.shape != exposure.shape:
        raise ValueError("probability and amount must have the same shape")
    if np.any((p < 0) | (p > 1)) or np.any(exposure < 0):
        raise ValueError("probabilities must be in [0,1] and amounts non-negative")

    fraud_loss = p * exposure * assumptions.loss_given_fraud
    legitimate = 1 - p
    return pd.DataFrame(
        {
            "allow": fraud_loss,
            "step_up": (
                assumptions.step_up_fixed_cost
                + legitimate * assumptions.step_up_legit_friction
                + fraud_loss * (1 - assumptions.step_up_effectiveness)
            ),
            "review": (
                assumptions.review_fixed_cost
                + legitimate * assumptions.review_legit_friction
                + fraud_loss * (1 - assumptions.review_effectiveness)
            ),
            "block": (
                legitimate
                * (
                    assumptions.block_fixed_cost
                    + assumptions.block_legit_amount_fraction * exposure
                )
                + fraud_loss * (1 - assumptions.block_effectiveness)
            ),
        }
    )


def assign_four_action_policy(
    frame: pd.DataFrame,
    *,
    assumptions: PolicyAssumptions,
    daily_review_capacity: int,
    probability_column: str = "probability",
    amount_column: str = "TransactionAmt",
    day_column: str = "day",
) -> pd.DataFrame:
    """Minimise expected cost while enforcing a hard daily review capacity."""
    if daily_review_capacity < 0:
        raise ValueError("daily_review_capacity must be non-negative")
    required = {probability_column, amount_column, day_column}
    missing = required.difference(frame.columns)
    if missing:
        raise KeyError(f"Missing policy columns: {sorted(missing)}")

    result = frame.copy()
    costs = expected_action_costs(
        result[probability_column].to_numpy(), result[amount_column].to_numpy(), assumptions
    )
    costs.index = result.index
    non_review = costs[["allow", "step_up", "block"]]
    best_non_review_action = non_review.idxmin(axis=1)
    best_non_review_cost = non_review.min(axis=1)
    review_benefit = best_non_review_cost - costs["review"]
    result["action"] = best_non_review_action
    result["expected_cost"] = best_non_review_cost
    result["review_benefit"] = review_benefit

    for _, index in result.groupby(day_column, sort=False).groups.items():
        eligible = review_benefit.loc[index]
        eligible = eligible.loc[eligible > 0].sort_values(ascending=False, kind="stable")
        selected = eligible.head(daily_review_capacity).index
        result.loc[selected, "action"] = "review"
        result.loc[selected, "expected_cost"] = costs.loc[selected, "review"]
    return result


def realised_proxy_cost(
    action: pd.Series,
    target: pd.Series,
    amount: pd.Series,
    assumptions: PolicyAssumptions,
) -> pd.Series:
    """Evaluate simulated policy cost using observed labels and assumed effects."""
    y = target.astype(float)
    exposure = amount.astype(float)
    output = pd.Series(index=action.index, dtype=float)
    output.loc[action.eq("allow")] = (
        y * exposure * assumptions.loss_given_fraud
    ).loc[action.eq("allow")]
    output.loc[action.eq("step_up")] = (
        assumptions.step_up_fixed_cost
        + (1 - y) * assumptions.step_up_legit_friction
        + y * exposure * assumptions.loss_given_fraud * (1 - assumptions.step_up_effectiveness)
    ).loc[action.eq("step_up")]
    output.loc[action.eq("review")] = (
        assumptions.review_fixed_cost
        + (1 - y) * assumptions.review_legit_friction
        + y * exposure * assumptions.loss_given_fraud * (1 - assumptions.review_effectiveness)
    ).loc[action.eq("review")]
    output.loc[action.eq("block")] = (
        (1 - y)
        * (assumptions.block_fixed_cost + assumptions.block_legit_amount_fraction * exposure)
        + y * exposure * assumptions.loss_given_fraud * (1 - assumptions.block_effectiveness)
    ).loc[action.eq("block")]
    return output

