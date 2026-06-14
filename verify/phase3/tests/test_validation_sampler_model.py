"""Tests for deterministic Phase 3 validation sampling."""

from __future__ import annotations

import unittest

import pandas as pd

from src.phase3_sentiment.validation_sampler_model import ValidationSampler


class ValidationSamplerTests(unittest.TestCase):
    """Verify proportional allocation, reproducibility, and validation."""

    def setUp(self) -> None:
        self.dataframe = pd.DataFrame(
            [
                {"candidate": candidate, "date": day, "tweet": f"{candidate}-{day}-{index}"}
                for candidate, day, count in (
                    ("a", "2020-11-01", 40),
                    ("a", "2020-11-02", 30),
                    ("b", "2020-11-01", 20),
                    ("b", "2020-11-02", 10),
                )
                for index in range(count)
            ]
        )

    def test_sample_is_exact_and_proportional(self) -> None:
        result = ValidationSampler(sample_size=20, random_seed=7).sample(self.dataframe)

        self.assertEqual(len(result.sample), 20)
        self.assertEqual(result.allocation["allocated_records"].tolist(), [8, 6, 4, 2])
        self.assertEqual(result.sample["candidate"].value_counts().to_dict(), {"a": 14, "b": 6})
        self.assertTrue(result.sample["validation_source_row"].is_unique)

    def test_same_seed_reproduces_source_rows_and_checksum(self) -> None:
        sampler = ValidationSampler(sample_size=20, random_seed=7)

        first = sampler.sample(self.dataframe)
        second = sampler.sample(self.dataframe)

        self.assertEqual(
            first.sample["validation_source_row"].tolist(),
            second.sample["validation_source_row"].tolist(),
        )
        self.assertEqual(first.checksum_sha256, second.checksum_sha256)

    def test_sample_size_cannot_exceed_source(self) -> None:
        with self.assertRaises(ValueError):
            ValidationSampler(sample_size=101).sample(self.dataframe)


if __name__ == "__main__":
    unittest.main()

