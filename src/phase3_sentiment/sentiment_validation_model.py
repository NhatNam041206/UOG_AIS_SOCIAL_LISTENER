"""Agreement metrics and language audit for Phase 3 sentiment validation."""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd
from scipy.stats import norm, pearsonr, spearmanr
from sklearn.metrics import confusion_matrix, f1_score


class SentimentValidator:
    """Compare VADER and RoBERTa without treating either as human ground truth."""

    LABELS = ["negative", "neutral", "positive"]

    def validate(self, dataframe: pd.DataFrame) -> Dict[str, Any]:
        """Return complete agreement metrics for the supplied scored sample."""
        required = {
            "vader_compound",
            "vader_label",
            "roberta_score",
            "roberta_label",
            "candidate",
            "date",
        }
        missing = sorted(required - set(dataframe.columns))
        if missing:
            raise ValueError(f"Required validation columns are missing: {missing}")
        if len(dataframe) < 4:
            raise ValueError("at least four records are required for correlation validation")

        overall = self._metrics(dataframe)
        candidate_metrics = {
            str(candidate): self._metrics(group)
            for candidate, group in dataframe.groupby("candidate", sort=True)
            if len(group) >= 4
        }
        daily_metrics = {
            str(day.date()): self._metrics(group)
            for day, group in dataframe.assign(
                _utc_day=pd.to_datetime(dataframe["date"], utc=True).dt.floor("D")
            ).groupby("_utc_day", sort=True)
            if len(group) >= 4
        }
        english = dataframe.loc[dataframe["detected_language"].eq("en")]
        english_metrics = self._metrics(english) if len(english) >= 4 else None
        return {
            "overall": overall,
            "likely_english": english_metrics,
            "candidate_metrics": candidate_metrics,
            "daily_metrics": daily_metrics,
        }

    def _metrics(self, dataframe: pd.DataFrame) -> Dict[str, Any]:
        vader = dataframe["vader_compound"].astype(float)
        roberta = dataframe["roberta_score"].astype(float)
        pearson = pearsonr(vader, roberta)
        spearman = spearmanr(vader, roberta)
        lower, upper = self._fisher_confidence_interval(float(pearson.statistic), len(dataframe))
        matrix = confusion_matrix(
            dataframe["vader_label"],
            dataframe["roberta_label"],
            labels=self.LABELS,
        )
        return {
            "record_count": len(dataframe),
            "pearson_r": float(pearson.statistic),
            "pearson_p_value": float(pearson.pvalue),
            "pearson_95_ci": [lower, upper],
            "spearman_rho": float(spearman.statistic),
            "spearman_p_value": float(spearman.pvalue),
            "label_agreement_rate": float(
                dataframe["vader_label"].eq(dataframe["roberta_label"]).mean()
            ),
            "macro_f1_agreement": float(
                f1_score(
                    dataframe["roberta_label"],
                    dataframe["vader_label"],
                    labels=self.LABELS,
                    average="macro",
                    zero_division=0,
                )
            ),
            "mean_absolute_score_difference": float((vader - roberta).abs().mean()),
            "confusion_matrix": matrix.tolist(),
        }

    @staticmethod
    def _fisher_confidence_interval(
        correlation: float,
        sample_size: int,
        confidence: float = 0.95,
    ) -> tuple[float, float]:
        clipped = float(np.clip(correlation, -0.999999, 0.999999))
        transformed = np.arctanh(clipped)
        standard_error = 1.0 / np.sqrt(sample_size - 3)
        critical = norm.ppf(0.5 + confidence / 2.0)
        return (
            float(np.tanh(transformed - critical * standard_error)),
            float(np.tanh(transformed + critical * standard_error)),
        )
