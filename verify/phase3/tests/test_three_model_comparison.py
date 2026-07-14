"""Tests for the three-model comparison CLI helpers."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from verify.phase3.run_three_model_comparison import (
    build_execution_manifest,
    pairwise_metrics,
    Phase3ArtifactPaths,
    resolve_phase3_artifact_paths,
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

    def test_sample_and_full_paths_are_non_overlapping(self) -> None:
        with TemporaryDirectory() as directory:
            sample = resolve_phase3_artifact_paths(directory, "three_model_sample", "sample_run")
            full = resolve_phase3_artifact_paths(directory, "three_model_full", "full_run")

        self.assertNotEqual(sample.data_path, full.data_path)
        self.assertEqual(sample.data_path.parent.name, "sample_run")
        self.assertEqual(sample.data_path.parent.parent.name, "three_model_sample")
        self.assertEqual(full.data_path.parent.name, "full_run")
        self.assertEqual(full.data_path.parent.parent.name, "three_model_full")

    def test_primary_validation_remains_distinct(self) -> None:
        with TemporaryDirectory() as directory:
            primary = resolve_phase3_artifact_paths(directory, "primary_5000_validation")

        self.assertEqual(primary.data_path.name, "sentiment_validation_sample.parquet")
        self.assertIsNone(primary.run_id)

    def test_manifest_contains_required_contract_fields(self) -> None:
        paths = Phase3ArtifactPaths(
            namespace="three_model_sample",
            run_id="test_run",
            data_path=Path("data.parquet"),
            metrics_path=Path("metrics.json"),
            manifest_path=Path("manifest.json"),
            report_path=Path("report.md"),
        )
        result = {
            "run_id": "test_run", "run_mode": "sample", "input_path": "input.parquet",
            "input_row_count": 10, "output_row_count": 2, "sample_size_requested": 2,
            "seed": 2020, "models": {"vader": "vader", "baseline_roberta": "a", "cardiff_roberta": "b"},
            "model_revisions": {"baseline_roberta": "r1", "cardiff_roberta": "r2"},
            "device_used": "cpu", "batch_size": 4, "maximum_token_length": 128,
        }

        manifest = build_execution_manifest(result, paths)

        required = {"run_id", "run_mode", "input_path", "input_row_count", "output_row_count",
                    "sample_size", "seed", "model_ids", "model_revisions", "device",
                    "batch_size", "maximum_token_length", "timestamp", "output_paths"}
        self.assertEqual(required, set(manifest))


if __name__ == "__main__":
    unittest.main()
