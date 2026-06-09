"""Tests for Phase 1 output persistence and metrics."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from src.phase1_ingestion.storage_serializers_view import StorageSerializersView


class StorageSerializersViewTests(unittest.TestCase):
    """Verify Parquet persistence and ingestion metrics."""

    def test_serialize_to_parquet_round_trips_dataframe(self) -> None:
        with TemporaryDirectory() as directory:
            destination = Path(directory) / "nested" / "records.parquet"
            dataframe = pd.DataFrame([{"id": 1, "text": "hello"}])

            StorageSerializersView().serialize_to_parquet(dataframe, destination)
            loaded = pd.read_parquet(destination)

        pd.testing.assert_frame_equal(loaded, dataframe)

    def test_log_ingestion_baseline_metrics(self) -> None:
        metrics = StorageSerializersView().log_ingestion_baseline_metrics(
            10,
            8,
            {"stream": "events"},
        )

        self.assertEqual(metrics["dropped_records"], 2)
        self.assertEqual(metrics["retention_rate_pct"], 80.0)
        self.assertEqual(metrics["metadata"], {"stream": "events"})

    def test_serialize_batches_to_parquet(self) -> None:
        with TemporaryDirectory() as directory:
            destination = Path(directory) / "records.parquet"
            batches = [
                pd.DataFrame([{"id": 1}]),
                pd.DataFrame([{"id": 2}]),
            ]

            count = StorageSerializersView().serialize_batches_to_parquet(
                batches,
                destination,
            )
            loaded = pd.read_parquet(destination)

        self.assertEqual(count, 2)
        self.assertEqual(loaded["id"].tolist(), [1, 2])


if __name__ == "__main__":
    unittest.main()
