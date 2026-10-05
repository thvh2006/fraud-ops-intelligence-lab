import pandas as pd

from src.temporal import assign_temporal_partitions, assert_temporal_separation


def test_partitions_are_separated_and_keep_ties_together() -> None:
    frame = pd.DataFrame(
        {
            "TransactionID": range(12),
            "TransactionDT": [1, 2, 3, 4, 5, 6, 6, 7, 8, 9, 10, 11],
        }
    )
    labels = assign_temporal_partitions(frame, boundaries=(0.4, 0.65, 0.8))
    assert labels.loc[frame["TransactionDT"] == 6].nunique() == 1
    assert_temporal_separation(frame, labels)


def test_partition_result_is_aligned_to_original_index() -> None:
    frame = pd.DataFrame(
        {"TransactionID": [3, 1, 4, 2], "TransactionDT": [30, 10, 40, 20]},
        index=[30, 10, 40, 20],
    )
    labels = assign_temporal_partitions(frame, boundaries=(0.25, 0.5, 0.75))
    assert labels.index.tolist() == frame.index.tolist()
    assert labels.loc[10] == "development"
    assert labels.loc[40] == "oot"

