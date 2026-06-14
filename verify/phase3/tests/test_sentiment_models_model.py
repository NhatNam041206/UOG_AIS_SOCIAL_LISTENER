"""Tests for Phase 3 VADER model behavior."""

from __future__ import annotations

import unittest

from src.phase3_sentiment.sentiment_models_model import VaderSentimentModel


class VaderSentimentModelTests(unittest.TestCase):
    """Verify VADER schema and approved label thresholds."""

    def test_score_returns_approved_schema(self) -> None:
        result = VaderSentimentModel().score("I absolutely LOVE this!!!")

        self.assertEqual(
            set(result),
            {
                "vader_negative",
                "vader_neutral",
                "vader_positive",
                "vader_compound",
                "vader_label",
            },
        )
        self.assertEqual(result["vader_label"], "positive")
        self.assertGreater(result["vader_compound"], 0.05)

    def test_label_boundaries_are_inclusive(self) -> None:
        self.assertEqual(VaderSentimentModel.label(-0.05), "negative")
        self.assertEqual(VaderSentimentModel.label(0.0), "neutral")
        self.assertEqual(VaderSentimentModel.label(0.05), "positive")

    def test_blank_text_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            VaderSentimentModel().score(" ")


if __name__ == "__main__":
    unittest.main()

