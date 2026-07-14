"""VADER ambiguity and optional RoBERTa uncertainty diagnostics."""

from __future__ import annotations

import math
import numpy as np
import pandas as pd


class SentimentAmbiguityProfiler:
    """Keep full-data VADER ambiguity separate from cross-model evidence."""

    PROBABILITY_COLUMNS = (
        "roberta_negative_probability",
        "roberta_neutral_probability",
        "roberta_positive_probability",
    )

    def profile(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        result = pd.DataFrame(index=dataframe.index)
        compound = pd.to_numeric(dataframe.get("vader_compound"), errors="coerce")
        result["vader_ambiguity_available"] = compound.notna()
        result["vader_ambiguity_risk"] = (1.0 - compound.abs()).clip(0, 1)
        result["sentiment_ambiguity_risk"] = result["vader_ambiguity_risk"]
        if all(column in dataframe for column in self.PROBABILITY_COLUMNS):
            probabilities = dataframe[list(self.PROBABILITY_COLUMNS)].apply(pd.to_numeric, errors="coerce")
            available = probabilities.notna().all(axis=1)
            entropy = -(probabilities * np.log(probabilities.clip(lower=1e-12))).sum(axis=1) / math.log(3)
            sorted_values = np.sort(probabilities.fillna(0).to_numpy(), axis=1)
            margin = pd.Series(sorted_values[:, -1] - sorted_values[:, -2], index=dataframe.index)
            result["roberta_entropy_risk"] = entropy.clip(0, 1).where(available)
            result["roberta_margin_ambiguity_risk"] = (1.0 - margin).clip(0, 1).where(available)
        else:
            result["roberta_entropy_risk"] = np.nan
            result["roberta_margin_ambiguity_risk"] = np.nan
        return result
