import numpy as np
import pandas as pd
import pytest

from src.monitoring import (
    available_label_mask,
    expected_calibration_error,
    population_stability_index,
)


def test_perfect_calibration_has_zero_error() -> None:
    target = np.array([0, 0, 1, 1])
    probability = np.array([0.0, 0.0, 1.0, 1.0])
    assert expected_calibration_error(target, probability) == pytest.approx(0.0)


def test_identical_populations_have_zero_psi() -> None:
    values = np.arange(100)
    assert population_stability_index(values, values) == pytest.approx(0.0)


def test_fast_labels_arrive_before_delayed_labels_but_not_before_event() -> None:
    days = pd.Series([5, 8, 10])
    reviewed = pd.Series([False, True, True])
    mask = available_label_mask(days, reviewed, snapshot_day=10, delayed_days=7)
    assert mask.tolist() == [False, True, False]

