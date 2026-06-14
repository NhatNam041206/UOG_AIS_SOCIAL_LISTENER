"""Tests for RoBERTa input normalization and configuration."""

from __future__ import annotations

import unittest

from src.phase3_sentiment.sentiment_models_model import RobertaSentimentModel


class RobertaSentimentModelTests(unittest.TestCase):
    """Verify model-specific preprocessing without loading model weights."""

    def test_normalize_replaces_usernames_and_urls(self) -> None:
        result = RobertaSentimentModel.normalize("@SomeUser see https://example.com now")

        self.assertEqual(result, "@user see http now")

    def test_normalize_does_not_change_regular_text(self) -> None:
        self.assertEqual(RobertaSentimentModel.normalize("Election update."), "Election update.")

    def test_invalid_maximum_length_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            RobertaSentimentModel(tokenizer=object(), model=object(), maximum_token_length=0)


if __name__ == "__main__":
    unittest.main()
