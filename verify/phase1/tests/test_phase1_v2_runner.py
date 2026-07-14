"""Tests for Phase 1 v2 schema contracts."""

from __future__ import annotations

import unittest

from verify.phase1.run_phase1_v2 import (
    RAW_TWITTER_COLUMNS,
    V2_TWITTER_FIELDS,
    _build_phase1_v2_alignment,
    _build_schema_contract,
)


class Phase1V2RunnerTests(unittest.TestCase):
    """Verify v2 preserves source evidence without inventing unavailable data."""

    def test_stream_a_contract_retains_raw_fields_and_aliases(self) -> None:
        contract = _build_schema_contract()["stream_a"]

        self.assertEqual(contract["raw_fields_retained"], RAW_TWITTER_COLUMNS)
        self.assertIn("user_join_date", contract["v2_fields"])
        self.assertIn("user_followers_count", contract["v2_fields"])
        self.assertIn("state_code", contract["v2_fields"])
        self.assertEqual(contract["compatibility_aliases"]["id"], "tweet_id")
        self.assertEqual(contract["compatibility_aliases"]["date"], "created_at")
        self.assertEqual(contract["unavailable_fields"]["replies"], "not present in raw Kaggle files")

    def test_v2_alignment_preserves_verified_window_and_pending_controls(self) -> None:
        manifest = {
            "streams": {
                "twitter_donald_trump_v2": {"record_count": 10},
                "twitter_joe_biden_v2": {"record_count": 8},
                "political_events_v2": {"record_count": 4},
                "electoral_returns_v2": {"record_count": 51},
            }
        }

        alignment = _build_phase1_v2_alignment(manifest)

        self.assertEqual(alignment["verified_twitter_window_utc"]["start"], "2020-10-15")
        self.assertEqual(alignment["verified_twitter_window_utc"]["end"], "2020-11-08")
        self.assertEqual(
            alignment["streams"]["A_social_media"]["status"],
            "available_complete_fields_for_verified_window",
        )
        self.assertIn(
            "2012/2016 historical classification is unavailable.",
            alignment["streams"]["C_electoral_benchmarks"]["limitations"],
        )

    def test_v2_field_order_contains_compatibility_aliases(self) -> None:
        self.assertLess(V2_TWITTER_FIELDS.index("tweet_id"), V2_TWITTER_FIELDS.index("id"))
        self.assertIn("candidate_stream", V2_TWITTER_FIELDS)
        self.assertIn("candidate", V2_TWITTER_FIELDS)
        self.assertIn("user_loc", V2_TWITTER_FIELDS)


if __name__ == "__main__":
    unittest.main()
