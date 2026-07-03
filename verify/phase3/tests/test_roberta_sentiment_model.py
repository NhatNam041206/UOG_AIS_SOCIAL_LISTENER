"""Tests for RoBERTa input normalization and configuration."""

from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from src.phase3_sentiment.sentiment_models_model import (
    RobertaModelConfig,
    RobertaSentimentModel,
    load_roberta_model_config,
)


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

    def test_default_model_is_latest_twitter_roberta(self) -> None:
        self.assertEqual(
            RobertaSentimentModel.MODEL_ID,
            "cardiffnlp/twitter-roberta-base-sentiment-latest",
        )

    def test_config_rejects_unknown_keys(self) -> None:
        with self.assertRaises(ValueError):
            RobertaModelConfig.from_dict({"unknown": "value"})

    def test_config_loads_model_settings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "roberta.json"
            path.write_text(
                '{"model_id": "cardiffnlp/twitter-roberta-base-sentiment-latest", '
                '"maximum_token_length": 256, "batch_size": 8, "device": "cpu"}',
                encoding="utf-8",
            )

            config = load_roberta_model_config(path)

        self.assertEqual(config.model_id, "cardiffnlp/twitter-roberta-base-sentiment-latest")
        self.assertEqual(config.maximum_token_length, 256)
        self.assertEqual(config.batch_size, 8)


if __name__ == "__main__":
    unittest.main()
