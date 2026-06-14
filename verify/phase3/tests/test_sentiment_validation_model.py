"""Tests for Phase 3 model-agreement validation."""

from __future__ import annotations

import unittest

import pandas as pd

from src.phase3_sentiment.sentiment_validation_model import SentimentValidator


class SentimentValidatorTests(unittest.TestCase):
    """Verify agreement metrics and confidence intervals."""

    def test_identical_models_have_perfect_agreement(self) -> None:
        dataframe = pd.DataFrame(
            {
                "vader_compound": [-0.8, -0.4, 0.2, 0.9],
                "roberta_score": [-0.8, -0.4, 0.2, 0.9],
                "vader_label": ["negative", "negative", "positive", "positive"],
                "roberta_label": ["negative", "negative", "positive", "positive"],
                "candidate": ["a", "a", "b", "b"],
                "date": pd.to_datetime(["2020-11-01"] * 4, utc=True),
                "detected_language": ["en"] * 4,
            }
        )

        result = SentimentValidator().validate(dataframe)

        self.assertAlmostEqual(result["overall"]["pearson_r"], 1.0)
        self.assertEqual(result["overall"]["label_agreement_rate"], 1.0)
        self.assertEqual(result["overall"]["mean_absolute_score_difference"], 0.0)

    def test_missing_columns_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            SentimentValidator().validate(pd.DataFrame({"vader_compound": [0.1] * 4}))


if __name__ == "__main__":
    unittest.main()
