"""Tests for empirical Phase 2 user-activity auditing."""

from __future__ import annotations

import unittest

import pandas as pd

from src.phase2_preprocessing.user_activity_audit_model import UserActivityAuditor


class UserActivityAuditorTests(unittest.TestCase):
    """Verify required metrics, candidate methods, and transparent selection."""

    def setUp(self) -> None:
        self.auditor = UserActivityAuditor()
        self.dataframe = pd.DataFrame(
            [
                {"user_id": "a", "date": "2020-11-01"},
                {"user_id": "a", "date": "2020-11-01"},
                {"user_id": "a", "date": "2020-11-03"},
                {"user_id": "b", "date": "2020-11-02"},
            ]
        )

    def test_compute_user_metrics_includes_all_required_measures(self) -> None:
        metrics = self.auditor.compute_user_metrics(self.dataframe).set_index("user_id")

        self.assertEqual(metrics.loc["a", "total_tweets"], 3)
        self.assertEqual(metrics.loc["a", "active_days"], 2)
        self.assertEqual(metrics.loc["a", "observed_span_days"], 3)
        self.assertEqual(metrics.loc["a", "tweets_per_active_day"], 1.5)
        self.assertEqual(metrics.loc["a", "tweets_per_observed_day"], 1.0)
        self.assertEqual(metrics.loc["a", "max_tweets_single_day"], 2)

    def test_audit_produces_all_required_candidate_methods(self) -> None:
        audit = self.auditor.audit(self.dataframe)

        self.assertEqual(
            set(audit.candidate_thresholds),
            {
                "p95",
                "p97_5",
                "p99",
                "p99_5",
                "iqr_upper_fence",
                "extreme_iqr_upper_fence",
                "log_z_threshold",
                "mad_threshold",
            },
        )
        self.assertEqual(len(audit.tradeoffs), 8)

    def test_selection_uses_smallest_safeguard_exceedance_when_all_fail(self) -> None:
        candidates = {"p99": 6.0, "p99_5": 9.0}
        tradeoffs = pd.DataFrame(
            [
                {
                    "method": "p99",
                    "threshold": 6.0,
                    "users_removed_pct": 0.5,
                    "tweets_removed_pct": 20.0,
                },
                {
                    "method": "p99_5",
                    "threshold": 9.0,
                    "users_removed_pct": 0.4,
                    "tweets_removed_pct": 13.0,
                },
            ]
        )

        threshold, reason = self.auditor.select_threshold(candidates, tradeoffs)

        self.assertEqual(threshold, 9.0)
        self.assertIn("smallest combined safeguard exceedance", reason)


if __name__ == "__main__":
    unittest.main()
