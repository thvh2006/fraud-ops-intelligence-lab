import pandas as pd

from src.model_selection import select_governed_model


def test_parsimony_gate_prefers_transaction_model_for_immaterial_gain():
    summary = pd.DataFrame(
        {
            "model": ["gbm_transaction", "gbm_plus_identity"],
            "mean_precision_at_k": [0.3109, 0.3139],
        }
    )
    selected, reason = select_governed_model(summary)
    assert selected == "gbm_transaction"
    assert reason.startswith("parsimony_gate")


def test_material_gain_can_promote_added_feature_model():
    summary = pd.DataFrame(
        {
            "model": ["gbm_transaction", "gbm_plus_identity"],
            "mean_precision_at_k": [0.31, 0.33],
        }
    )
    selected, _ = select_governed_model(summary)
    assert selected == "gbm_plus_identity"
