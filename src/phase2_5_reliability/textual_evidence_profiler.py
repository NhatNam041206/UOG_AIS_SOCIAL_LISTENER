"""Observable textual-evidence diagnostics with explicit URL provenance."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from .risk_score_normalizer import RiskScoreNormalizer


EMOJI_PATTERN = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")
URL_PATTERN = r"https?://\S+|www\.\S+"


class TextualEvidenceProfiler:
    """Measure text structure without calling informal text invalid."""

    def __init__(self, text_column: str = "tweet") -> None:
        self.text_column = text_column

    def profile(
        self,
        dataframe: pd.DataFrame,
        original_text: pd.Series | None = None,
    ) -> pd.DataFrame:
        text = dataframe[self.text_column].fillna("").astype(str)
        result = pd.DataFrame(index=dataframe.index)
        result["word_count"] = text.str.count(r"\b\w+\b")
        result["character_count"] = text.str.len()
        result["hashtag_count"] = text.str.count(r"#\w+")
        result["mention_count"] = text.str.count(r"@\w+")
        result["emoji_count"] = text.map(lambda value: len(EMOJI_PATTERN.findall(value)))
        result["punctuation_count"] = text.str.count(r"[^\w\s#@]")
        denominator = result["word_count"].replace(0, np.nan)
        result["hashtag_ratio"] = result["hashtag_count"] / denominator
        result["mention_ratio"] = result["mention_count"] / denominator
        result["emoji_ratio"] = result["emoji_count"] / denominator
        result["is_extremely_short"] = result["word_count"].le(3)
        result["is_hashtag_only"] = text.str.strip().str.replace(r"#\w+", "", regex=True).str.strip().eq("") & result["hashtag_count"].gt(0)
        result["is_mention_only"] = text.str.strip().str.replace(r"@\w+", "", regex=True).str.strip().eq("") & result["mention_count"].gt(0)
        if original_text is None:
            result["prior_url_evidence_available"] = False
            result["had_url_before_cleaning"] = pd.Series(pd.NA, index=dataframe.index, dtype="boolean")
            result["prior_url_evidence_risk"] = np.nan
        else:
            aligned = original_text.reindex(dataframe.index)
            available = aligned.notna()
            result["prior_url_evidence_available"] = available
            result["had_url_before_cleaning"] = aligned.astype("string").str.contains(URL_PATTERN, regex=True, na=pd.NA)
            result["prior_url_evidence_risk"] = np.nan
        result["text_sparsity_risk"] = (1.0 - result["word_count"] / 12.0).clip(0, 1)
        result["hashtag_dominance_risk"] = RiskScoreNormalizer.percentile_rank(result["hashtag_ratio"])
        result["mention_dominance_risk"] = RiskScoreNormalizer.percentile_rank(result["mention_ratio"])
        result["emoji_dominance_risk"] = RiskScoreNormalizer.percentile_rank(result["emoji_ratio"])
        result["textual_evidence_risk"] = RiskScoreNormalizer.available_mean(
            result,
            ["text_sparsity_risk", "hashtag_dominance_risk", "mention_dominance_risk", "emoji_dominance_risk"],
        )
        return result
