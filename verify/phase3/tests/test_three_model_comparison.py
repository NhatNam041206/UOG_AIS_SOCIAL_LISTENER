"""Tests for the three-model comparison CLI helpers."""

from __future__ import annotations

import unittest

import pandas as pd

from verify.phase3.run_three_model_comparison import (
    pairwise_metrics,
    resolve_device,
    select_comparison_records,
)


class ThreeModelComparisonTests(unittest.TestCase):
    """Verify comparison helper behavior without loading transformer weights."""

    def test_cpu_device_resolves_without_cuda(self) -> None:
        self.assertEqual(resolve_device("cpu"), "cpu")

    def test_invalid_device_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            resolve_device("tpu")

    def test_pairwise_metrics_reports_label_agreement(self) -> None:
        dataframe = pd.DataFrame(
            {
                "left_score": [-0.9, -0.2, 0.3, 0.8],
                "right_score": [-0.8, -0.1, 0.4, 0.7],
                "left_label": ["negative", "negative", "positive", "positive"],
                "right_label": ["negative", "neutral", "positive", "positive"],
            }
        )

        result = pairwise_metrics(
            dataframe,
            left_score="left_score",
            left_label="left_label",
            right_score="right_score",
            right_label="right_label",
        )

        self.assertEqual(result["record_count"], 4)
        self.assertEqual(result["label_agreement_rate"], 0.75)
        self.assertGreater(result["pearson_r"], 0.9)

    def test_select_comparison_records_samples_reproducibly(self) -> None:
        dataframe = pd.DataFrame({"value": range(10)})

        first = select_comparison_records(dataframe, sample_size=4, seed=2020, full_dataset=False)
        second = select_comparison_records(dataframe, sample_size=4, seed=2020, full_dataset=False)

        self.assertEqual(first["source_row"].tolist(), second["source_row"].tolist())
        self.assertEqual(len(first), 4)

    def test_select_comparison_records_can_use_full_dataset(self) -> None:
        dataframe = pd.DataFrame({"value": range(10)})

        result = select_comparison_records(dataframe, sample_size=4, seed=2020, full_dataset=True)

        self.assertEqual(len(result), 10)
        self.assertEqual(result["source_row"].tolist(), list(range(10)))


if __name__ == "__main__":
    unittest.main()
