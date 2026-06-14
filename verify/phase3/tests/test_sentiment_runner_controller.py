"""Tests for the Phase 3 VADER scoring controller."""

from __future__ import annotations

import unittest

import pandas as pd

from src.phase3_sentiment.sentiment_runner_controller import SentimentRunnerController
from src.shared.pipeline_orchestrator_controller import PipelineControllerError


class SentimentRunnerControllerTests(unittest.TestCase):
    """Verify schema preservation, scoring, and guarded failures."""

    def test_controller_preserves_input_and_appends_vader_fields(self) -> None:
        source = pd.DataFrame([{"id": "1", "tweet": "GOOD!!!"}, {"id": "2", "tweet": "bad"}])

        result = SentimentRunnerController().execute_dataframe(source)

        self.assertEqual(source.columns.tolist(), ["id", "tweet"])
        self.assertEqual(result.columns.tolist(), ["id", "tweet", *SentimentRunnerController.VADER_COLUMNS])
        self.assertEqual(result["vader_label"].tolist(), ["positive", "negative"])

    def test_controller_rejects_existing_output_columns(self) -> None:
        dataframe = pd.DataFrame([{"tweet": "good", "vader_compound": 0.1}])

        with self.assertRaises(ValueError):
            SentimentRunnerController().execute_dataframe(dataframe)

    def test_run_wraps_missing_text_column(self) -> None:
        with self.assertRaises(PipelineControllerError):
            SentimentRunnerController().run([{"id": "1"}])


if __name__ == "__main__":
    unittest.main()

