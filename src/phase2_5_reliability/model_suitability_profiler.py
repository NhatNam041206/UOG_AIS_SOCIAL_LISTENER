"""Availability-limited language and sentiment-model suitability diagnostics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .risk_score_normalizer import RiskScoreNormalizer


class ModelSuitabilityProfiler:
    PROBABILITIES = (
        "roberta_negative_probability", "roberta_neutral_probability", "roberta_positive_probability"
    )

    def profile(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        result = pd.DataFrame(index=dataframe.index)
        language = dataframe.get("detected_language", pd.Series(pd.NA, index=dataframe.index, dtype="string")).astype("string")
        language_available = language.notna()
        result["language_diagnostic_available"] = language_available
        result["language_model_suitability_risk"] = pd.Series(np.nan, index=dataframe.index)
        result.loc[language_available, "language_model_suitability_risk"] = (~language.loc[language_available].str.lower().eq("en")).astype(float)
        if all(column in dataframe for column in self.PROBABILITIES):
            probabilities = dataframe[list(self.PROBABILITIES)].apply(pd.to_numeric, errors="coerce")
            roberta_available = probabilities.notna().all(axis=1)
        else:
            probabilities = pd.DataFrame(index=dataframe.index)
            roberta_available = pd.Series(False, index=dataframe.index)
        result["roberta_diagnostic_available"] = roberta_available
        result["baseline_roberta_diagnostic_available"] = False
        result["model_disagreement_risk"] = np.nan
        if "vader_compound" in dataframe and "roberta_score" in dataframe:
            difference = (pd.to_numeric(dataframe["vader_compound"], errors="coerce") - pd.to_numeric(dataframe["roberta_score"], errors="coerce")).abs() / 2.0
            result["model_disagreement_risk"] = difference.clip(0, 1).where(roberta_available)
        result["roberta_model_uncertainty_risk"] = np.nan
        if not probabilities.empty:
            result["roberta_model_uncertainty_risk"] = (1.0 - probabilities.max(axis=1)).clip(0, 1).where(roberta_available)
        result["model_suitability_risk"] = RiskScoreNormalizer.available_mean(
            result, ["model_disagreement_risk", "roberta_model_uncertainty_risk"]
        ).where(roberta_available)
        return result
