"""Null-preserving normalization helpers for diagnostic risk scores."""

from __future__ import annotations

import numpy as np
import pandas as pd


class RiskScoreNormalizer:
    """Normalize observed values without manufacturing evidence for missing rows."""

    @staticmethod
    def clip01(series: pd.Series) -> pd.Series:
        return pd.to_numeric(series, errors="coerce").clip(0.0, 1.0)

    @staticmethod
    def percentile_rank(series: pd.Series) -> pd.Series:
        values = pd.to_numeric(series, errors="coerce")
        result = pd.Series(np.nan, index=series.index, dtype="float64")
        observed = values.dropna()
        if observed.empty:
            return result
        if observed.nunique() == 1:
            result.loc[observed.index] = 0.0
            return result
        result.loc[observed.index] = observed.rank(method="average", pct=True)
        return result.clip(0.0, 1.0)

    @staticmethod
    def robust_z_sigmoid(series: pd.Series) -> pd.Series:
        values = pd.to_numeric(series, errors="coerce")
        result = pd.Series(np.nan, index=series.index, dtype="float64")
        observed = values.dropna()
        if observed.empty:
            return result
        median = observed.median()
        iqr = observed.quantile(0.75) - observed.quantile(0.25)
        if iqr == 0 or pd.isna(iqr):
            result.loc[observed.index] = 0.0
            return result
        z = (observed - median) / iqr
        result.loc[observed.index] = 1.0 / (1.0 + np.exp(-z.clip(-40, 40)))
        return result.clip(0.0, 1.0)

    @staticmethod
    def available_mean(dataframe: pd.DataFrame, columns: list[str]) -> pd.Series:
        existing = [column for column in columns if column in dataframe]
        if not existing:
            return pd.Series(np.nan, index=dataframe.index, dtype="float64")
        return dataframe[existing].apply(pd.to_numeric, errors="coerce").mean(axis=1).clip(0, 1)
