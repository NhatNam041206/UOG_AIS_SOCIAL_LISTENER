"""Language vs User Region Cross-Analyzer (Package D).

This module analyzes the cross-tabulation of user geocoded region (US State, Non-US,
Unmapped) against detected tweet language (English, Spanish, Other), ensuring that
non-English tweets geocoded to US states (e.g. Spanish-speaking residents in TX, FL,
CA, AZ) are retained rather than discarded.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

import pandas as pd


_SPANISH_INDICATOR_PATTERN = re.compile(
    r"\b(que|para|por|con|del|las|los|una|uno|como|mas|pero|este|esta|todos|bien|gracias|voto|elecciones|presidente|debatede|latinos)\b|[\u00c1\u00e1\u00c9\u00e9\u00cd\u00ed\u00d3\u00f3\u00da\u00fa\u00d1\u00f1\u00bf\u00a1]",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class LanguageRegionCrossAnalysisResult:
    """Results from language-region cross-tabulation."""

    cross_tabulation: pd.DataFrame
    total_tweets: int
    us_state_tweets: int
    us_spanish_tweets: int
    us_other_language_tweets: int
    non_us_tweets: int
    unmapped_tweets: int
    language_detection_method: str = "explicit_column"


class LanguageRegionCrossAnalyzer:
    """Analyze tweet language distribution across geographic user regions."""

    VALID_US_STATES = {
        "AK", "AL", "AR", "AZ", "CA", "CO", "CT", "DC", "DE", "FL",
        "GA", "HI", "IA", "ID", "IL", "IN", "KS", "KY", "LA", "MA",
        "MD", "ME", "MI", "MN", "MO", "MS", "MT", "NC", "ND", "NE",
        "NH", "NJ", "NM", "NV", "NY", "OH", "OK", "OR", "PA", "RI",
        "SC", "SD", "TN", "TX", "UT", "VA", "VT", "WA", "WI", "WV", "WY",
    }

    def __init__(
        self,
        location_col: str = "state_code",
        language_col: str = "detected_language",
        text_col: str = "tweet_cleaned",
    ) -> None:
        self.location_col = location_col
        self.language_col = language_col
        self.text_col = text_col

    def classify_region(self, state_val: Any) -> str:
        """Classify state_code into US State, Non-US, or Unmapped."""
        if pd.isna(state_val) or not str(state_val).strip():
            return "Unmapped"
        code = str(state_val).strip().upper()
        if code in self.VALID_US_STATES:
            return f"US_{code}"
        return "Non_US"

    def classify_language(self, lang_val: Any) -> str:
        """Normalize language tag into English, Spanish, Undetermined, or Other."""
        if pd.isna(lang_val) or not str(lang_val).strip():
            return "Unknown"
        lang = str(lang_val).strip().lower()
        if lang in {"en", "english"}:
            return "English"
        if lang in {"es", "spanish"}:
            return "Spanish"
        if lang in {"und", "undetermined"}:
            return "Undetermined"
        return "Other"

    def _heuristic_detect_language(self, text_val: Any) -> str:
        """Heuristic detection of Spanish vs English/Other when explicit language col is absent."""
        if pd.isna(text_val) or not str(text_val).strip():
            return "English"
        text = str(text_val)
        matches = len(_SPANISH_INDICATOR_PATTERN.findall(text))
        if matches >= 2 or (_SPANISH_INDICATOR_PATTERN.search(text) and len(text.split()) <= 6):
            return "Spanish"
        return "English"

    def analyze(self, df: pd.DataFrame) -> LanguageRegionCrossAnalysisResult:
        """Run cross-tabulation between geocoded region and tweet language."""
        working = df.copy()
        detection_method = "explicit_column"

        if self.location_col not in working.columns:
            working["_region_cat"] = "Unmapped"
        else:
            working["_region_cat"] = working[self.location_col].apply(self.classify_region)

        if self.language_col in working.columns:
            working["_lang_cat"] = working[self.language_col].apply(self.classify_language)
        elif self.text_col in working.columns:
            detection_method = "heuristic_two_class_regex"
            working["_lang_cat"] = working[self.text_col].apply(self._heuristic_detect_language)
        elif "tweet" in working.columns:
            detection_method = "heuristic_two_class_regex"
            working["_lang_cat"] = working["tweet"].apply(self._heuristic_detect_language)
        else:
            detection_method = "fallback_default_english"
            working["_lang_cat"] = "English"

        crosstab = pd.crosstab(
            working["_region_cat"],
            working["_lang_cat"],
            margins=True,
            margins_name="Total",
        )

        total_tweets = len(working)
        is_us = working["_region_cat"].str.startswith("US_")
        us_tweets = working[is_us]

        us_state_count = len(us_tweets)
        us_spanish_count = len(us_tweets[us_tweets["_lang_cat"] == "Spanish"])
        us_other_count = len(us_tweets[us_tweets["_lang_cat"] == "Other"])
        non_us_count = len(working[working["_region_cat"] == "Non_US"])
        unmapped_count = len(working[working["_region_cat"] == "Unmapped"])

        return LanguageRegionCrossAnalysisResult(
            cross_tabulation=crosstab,
            total_tweets=total_tweets,
            us_state_tweets=us_state_count,
            us_spanish_tweets=us_spanish_count,
            us_other_language_tweets=us_other_count,
            non_us_tweets=non_us_count,
            unmapped_tweets=unmapped_count,
            language_detection_method=detection_method,
        )
