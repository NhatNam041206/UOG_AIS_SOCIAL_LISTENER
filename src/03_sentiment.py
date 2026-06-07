"""Phase 3 sentiment module for lexicon scoring and validation steps."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SentimentScore:
    """Container for sentiment score outputs."""

    compound: float


class SentimentAnalyzer:
    """Compute and validate sentiment signals from cleaned text."""

    def analyze(self, text: str) -> SentimentScore:
        raise NotImplementedError
