"""Tests for Phase 2 deterministic cleaning rules."""

from __future__ import annotations

from datetime import datetime, timezone
import unittest

import pandas as pd

from src.phase2_preprocessing.cleaning_heuristics_model import (
    BotFilter,
    CleaningPolicy,
    TextCleaner,
    deduplicate_text,
    filter_bots,
    verify_emoji_integrity,
)


class CleaningHeuristicsTests(unittest.TestCase):
    """Verify each model component independently."""

    def test_cleaner_removes_html_and_urls_but_preserves_vader_signals(self) -> None:
        value = "<b>AMAZING!!!</b> Vote 😊 https://example.com"

        cleaned = TextCleaner().clean(value)

        self.assertEqual(cleaned, "AMAZING!!! Vote 😊")
        self.assertEqual(TextCleaner().clean("Test https:// broken source"), "Test broken source")

    def test_bot_filter_rejects_new_accounts_and_high_activity_users(self) -> None:
        policy = CleaningPolicy(maximum_tweets_per_active_day=2)
        dataframe = pd.DataFrame(
            [
                {"user_id": "steady", "date": "2020-11-01", "user_created_at": "2019-01-01"},
                {"user_id": "busy", "date": "2020-11-01", "user_created_at": "2019-01-01"},
                {"user_id": "busy", "date": "2020-11-01", "user_created_at": "2019-01-01"},
                {"user_id": "busy", "date": "2020-11-01", "user_created_at": "2019-01-01"},
                {"user_id": "new", "date": "2020-11-01", "user_created_at": "2020-10-20"},
            ]
        )

        retained = dataframe.loc[BotFilter(policy).retained_mask(dataframe)]

        self.assertEqual(retained["user_id"].tolist(), ["steady"])

    def test_compatibility_helpers_are_deterministic(self) -> None:
        records = [
            {"text": "same", "bot_score": 0.1},
            {"text": "same", "bot_score": 0.2},
            {"text": "other", "bot_score": 0.9},
        ]

        retained = deduplicate_text(filter_bots(records, 0.5))

        self.assertEqual(retained, [{"text": "same", "bot_score": 0.1}])
        self.assertTrue(verify_emoji_integrity({"text": "Valid 😊"}))
        self.assertFalse(verify_emoji_integrity({"text": "Invalid \ufffd"}))


if __name__ == "__main__":
    unittest.main()
