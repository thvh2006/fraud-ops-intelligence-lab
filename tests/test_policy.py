import pandas as pd

from src.policy import PolicyAssumptions, assign_four_action_policy, expected_action_costs


ASSUMPTIONS = PolicyAssumptions(
    name="test",
    loss_given_fraud=1.0,
    step_up_effectiveness=0.4,
    review_effectiveness=0.8,
    block_effectiveness=0.95,
    step_up_fixed_cost=1.0,
    step_up_legit_friction=1.0,
    review_fixed_cost=2.0,
    review_legit_friction=1.0,
    block_fixed_cost=5.0,
    block_legit_amount_fraction=0.1,
)


def test_expected_costs_make_allow_cheapest_at_zero_risk() -> None:
    costs = expected_action_costs([0.0], [100.0], ASSUMPTIONS)
    assert costs.idxmin(axis=1).iloc[0] == "allow"


def test_review_capacity_is_enforced_per_day() -> None:
    frame = pd.DataFrame(
        {
            "day": [1, 1, 1, 2, 2],
            "probability": [0.4, 0.5, 0.6, 0.5, 0.7],
            "TransactionAmt": [100.0] * 5,
        }
    )
    result = assign_four_action_policy(
        frame, assumptions=ASSUMPTIONS, daily_review_capacity=1
    )
    assert result.groupby("day")["action"].apply(lambda values: (values == "review").sum()).max() <= 1


def test_zero_review_capacity_assigns_no_review() -> None:
    frame = pd.DataFrame(
        {"day": [1], "probability": [0.5], "TransactionAmt": [100.0]}
    )
    result = assign_four_action_policy(
        frame, assumptions=ASSUMPTIONS, daily_review_capacity=0
    )
    assert result.loc[0, "action"] != "review"

