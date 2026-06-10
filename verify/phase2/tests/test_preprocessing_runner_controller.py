"""Tests for the Phase 2 preprocessing controller."""

from __future__ import annotations

import unittest

from src.phase2_preprocessing.cleaning_heuristics_model import CleaningPolicy
from src.phase2_preprocessing.preprocessing_runner_controller import PreprocessingRunnerController
from src.phase2_preprocessing.telemetry_reporter_view import TelemetryReporterView
from src.shared.pipeline_orchestrator_controller import PipelineControllerError


class PreprocessingRunnerControllerTests(unittest.TestCase):
    """Verify ordering, output preservation, and error handling."""

    def test_controller_applies_rules_without_mutating_input(self) -> None:
        records = [
            {"user_id": "a", "date": "2020-11-01", "tweet": "<b>GOOD!!!</b> 😊 http://x.test"},
            {"user_id": "b", "date": "2020-11-01", "tweet": "<b>GOOD!!!</b> 😊 http://x.test"},
            {"user_id": "c", "date": "2020-11-01", "tweet": "BAD??? 😠"},
        ]
        reporter = TelemetryReporterView()
        controller = PreprocessingRunnerController(reporter)

        result = controller.execute(records)

        self.assertEqual([record["tweet"] for record in result], ["GOOD!!! 😊", "BAD??? 😠"])
        self.assertEqual(records[0]["tweet"], "<b>GOOD!!!</b> 😊 http://x.test")
        self.assertEqual(reporter.stage_metrics["exact_duplicate_filter"]["dropped_count"], 1)

    def test_controller_rejects_more_than_configured_daily_volume(self) -> None:
        records = [
            {"user_id": "busy", "date": "2020-11-01", "tweet": f"tweet {index}"}
            for index in range(3)
        ]
        controller = PreprocessingRunnerController(
            TelemetryReporterView(),
            CleaningPolicy(maximum_tweets_per_day=2),
        )

        self.assertEqual(controller.execute(records), [])

    def test_controller_accepts_empty_record_list(self) -> None:
        reporter = TelemetryReporterView()
        controller = PreprocessingRunnerController(reporter)

        self.assertEqual(controller.execute([]), [])
        self.assertEqual(reporter.stage_metrics["text_cleaning"]["initial_count"], 0)

    def test_run_wraps_missing_required_columns(self) -> None:
        controller = PreprocessingRunnerController(TelemetryReporterView())

        with self.assertRaises(PipelineControllerError) as context:
            controller.run([{"tweet": "hello"}])

        self.assertIn("Required preprocessing columns are missing", str(context.exception))


if __name__ == "__main__":
    unittest.main()
