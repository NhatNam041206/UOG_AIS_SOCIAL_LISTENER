"""Tests for Phase 2 telemetry presentation."""

from __future__ import annotations

import unittest

from src.phase2_preprocessing.telemetry_reporter_view import TelemetryReporterView


class TelemetryReporterViewTests(unittest.TestCase):
    """Verify telemetry calculations and validation."""

    def test_drop_rate_and_report(self) -> None:
        reporter = TelemetryReporterView()

        report = reporter.format_drop_rate_report("deduplication", 100, 75)

        self.assertEqual(reporter.compute_drop_rate(100, 75), 25.0)
        self.assertIn("dropped 25 (25.00%)", report)

    def test_invalid_counts_raise(self) -> None:
        reporter = TelemetryReporterView()

        with self.assertRaises(ValueError):
            reporter.compute_drop_rate(2, 3)


if __name__ == "__main__":
    unittest.main()
