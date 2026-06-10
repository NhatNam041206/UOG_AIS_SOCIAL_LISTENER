"""Deterministic Phase 2 bot, duplicate, and text-cleaning rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import html
import re
from typing import Any, Dict, List, Optional

import pandas as pd


_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_URL_PATTERN = re.compile(r"https?://\S*|www\.\S+", flags=re.IGNORECASE)
_INVALID_UNICODE_PATTERN = re.compile(r"[\ud800-\udfff\ufffd]")


@dataclass(frozen=True)
class CleaningPolicy:
    """Configuration for Phase 2 rules without embedding dataset-specific choices."""

    text_key: str = "tweet"
    user_key: str = "user_id"
    timestamp_key: str = "date"
    account_created_key: str = "user_created_at"
    election_date: datetime = datetime(2020, 11, 3, tzinfo=timezone.utc)
    minimum_account_age_days: int = 30
    maximum_tweets_per_active_day: Optional[float] = None
    bot_score_threshold: Optional[float] = None

    def __post_init__(self) -> None:
        if self.minimum_account_age_days < 0:
            raise ValueError("minimum_account_age_days must be non-negative")
        if (
            self.maximum_tweets_per_active_day is not None
            and self.maximum_tweets_per_active_day <= 0
        ):
            raise ValueError("maximum_tweets_per_active_day must be positive")


class TextCleaner:
    """Remove HTML and URLs while preserving sentiment-relevant text signals."""

    def clean(self, value: Any) -> Optional[str]:
        """Return cleaned text, preserving capitalization, punctuation, and emoji."""
        if value is None or pd.isna(value):
            return None
        text = html.unescape(str(value))
        text = _HTML_TAG_PATTERN.sub(" ", text)
        text = _URL_PATTERN.sub("", text)
        return " ".join(text.split())

    def is_valid(self, value: Any) -> bool:
        """Return whether text is non-empty and contains valid Unicode."""
        cleaned = self.clean(value)
        return bool(cleaned and not _INVALID_UNICODE_PATTERN.search(cleaned))


class BotFilter:
    """Identify records matching the documented account-level bot heuristics."""

    def __init__(self, policy: CleaningPolicy) -> None:
        self.policy = policy

    def retained_mask(self, dataframe: pd.DataFrame) -> pd.Series:
        """Return a Boolean mask retaining records that pass available bot rules."""
        self._require_columns(
            dataframe,
            [self.policy.user_key, self.policy.timestamp_key],
        )
        retained = pd.Series(True, index=dataframe.index, dtype=bool)

        if self.policy.maximum_tweets_per_active_day is not None:
            from .user_activity_audit_model import UserActivityAuditor

            auditor = UserActivityAuditor(
                user_key=self.policy.user_key,
                timestamp_key=self.policy.timestamp_key,
            )
            metrics = auditor.compute_user_metrics(dataframe)
            high_volume_users = set(
                metrics.loc[
                    metrics["tweets_per_active_day"].gt(
                        self.policy.maximum_tweets_per_active_day
                    ),
                    self.policy.user_key,
                ]
            )
            identities = auditor.user_identity(dataframe[self.policy.user_key])
            retained &= ~identities.isin(high_volume_users)

        if self.policy.account_created_key in dataframe.columns:
            created = pd.to_datetime(
                dataframe[self.policy.account_created_key],
                utc=True,
                errors="coerce",
            )
            cutoff = pd.Timestamp(self.policy.election_date) - pd.Timedelta(
                days=self.policy.minimum_account_age_days
            )
            retained &= created.isna() | created.le(cutoff)

        if (
            self.policy.bot_score_threshold is not None
            and "bot_score" in dataframe.columns
        ):
            scores = pd.to_numeric(dataframe["bot_score"], errors="coerce")
            retained &= scores.isna() | scores.lt(self.policy.bot_score_threshold)
        return retained

    @staticmethod
    def _require_columns(dataframe: pd.DataFrame, columns: List[str]) -> None:
        missing = [column for column in columns if column not in dataframe.columns]
        if missing:
            raise ValueError(f"Required preprocessing columns are missing: {missing}")


class DuplicateFilter:
    """Identify exact duplicate text while retaining the first observed record."""

    def retained_mask(self, dataframe: pd.DataFrame, text_key: str) -> pd.Series:
        """Return a Boolean mask that rejects exact non-null text duplicates."""
        if text_key not in dataframe.columns:
            raise ValueError(f"Required preprocessing column is missing: {text_key}")
        return ~dataframe[text_key].duplicated(keep="first")


def filter_bots(
    records: List[Dict[str, Any]],
    bot_score_threshold: float,
) -> List[Dict[str, Any]]:
    """Exclude records at or above ``bot_score_threshold``."""
    if bot_score_threshold < 0:
        raise ValueError("bot_score_threshold must be non-negative")
    return [
        record.copy()
        for record in records
        if record.get("bot_score") is None
        or float(record["bot_score"]) < bot_score_threshold
    ]


def deduplicate_text(
    records: List[Dict[str, Any]],
    text_key: str = "text",
) -> List[Dict[str, Any]]:
    """Drop exact text duplicates while retaining order and the first occurrence."""
    seen = set()
    retained = []
    for record in records:
        value = record.get(text_key)
        marker = ("null", None) if value is None else ("text", str(value))
        if marker in seen:
            continue
        seen.add(marker)
        retained.append(record.copy())
    return retained


def verify_syntax(record: Dict[str, Any], text_key: str = "text") -> bool:
    """Return whether a record has non-empty text after HTML and URL removal."""
    return TextCleaner().is_valid(record.get(text_key))


def verify_emoji_integrity(record: Dict[str, Any], text_key: str = "text") -> bool:
    """Return whether text can be represented as valid UTF-8 without replacement."""
    value = record.get(text_key)
    if value is None:
        return False
    text = str(value)
    if _INVALID_UNICODE_PATTERN.search(text):
        return False
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True
