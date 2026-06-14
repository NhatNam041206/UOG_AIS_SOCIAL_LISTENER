"""Sentiment model adapters for Phase 3."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


class VaderSentimentModel:
    """Score text with VADER and apply the documented compound-score labels."""

    NEGATIVE_THRESHOLD = -0.05
    POSITIVE_THRESHOLD = 0.05

    def __init__(self, analyzer: SentimentIntensityAnalyzer | None = None) -> None:
        self._analyzer = analyzer or SentimentIntensityAnalyzer()

    def score(self, text: Any) -> Dict[str, float | str]:
        """Return the approved VADER schema for one non-empty text value."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError("VADER text must be a non-empty string")
        scores = self._analyzer.polarity_scores(text)
        compound = float(scores["compound"])
        return {
            "vader_negative": float(scores["neg"]),
            "vader_neutral": float(scores["neu"]),
            "vader_positive": float(scores["pos"]),
            "vader_compound": compound,
            "vader_label": self.label(compound),
        }

    def score_many(self, texts: Iterable[Any]) -> List[Dict[str, float | str]]:
        """Score text values in order."""
        return [self.score(text) for text in texts]

    @classmethod
    def label(cls, compound: float) -> str:
        """Convert a VADER compound score to the approved three-class label."""
        if compound <= cls.NEGATIVE_THRESHOLD:
            return "negative"
        if compound >= cls.POSITIVE_THRESHOLD:
            return "positive"
        return "neutral"

