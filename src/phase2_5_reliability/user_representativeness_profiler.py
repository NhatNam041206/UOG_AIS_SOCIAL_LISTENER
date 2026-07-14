"""User representativeness diagnostics sourced from the Phase 2 pre-filter audit."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .risk_score_normalizer import RiskScoreNormalizer


class UserRepresentativenessProfiler:
    """Join retained tweets to the approved 483,175-user audit."""

    def __init__(self, user_column: str = "user_id") -> None:
        self.user_column = user_column

    def profile(
        self,
        dataframe: pd.DataFrame,
        user_metrics: pd.DataFrame,
        threshold_audit: dict,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        required = {self.user_column, "total_tweets", "active_days", "tweets_per_active_day"}
        missing = sorted(required - set(user_metrics.columns))
        if missing:
            raise ValueError(f"Pre-filter user audit columns are missing: {missing}")
        metrics = user_metrics.copy()
        metrics["user_activity_percentile"] = RiskScoreNormalizer.percentile_rank(
            metrics["tweets_per_active_day"]
        )
        metrics["user_contribution_percentile"] = RiskScoreNormalizer.percentile_rank(
            metrics["total_tweets"]
        )
        metrics["user_representativeness_risk"] = RiskScoreNormalizer.available_mean(
            metrics, ["user_activity_percentile", "user_contribution_percentile"]
        )
        selected = float(threshold_audit["selected_threshold"])
        metrics["retained_by_approved_activity_threshold"] = metrics["tweets_per_active_day"].le(selected)
        joined = dataframe[[self.user_column]].merge(metrics, on=self.user_column, how="left", validate="many_to_one")
        joined.index = dataframe.index
        joined["user_audit_available"] = joined["tweets_per_active_day"].notna()
        joined["approved_activity_threshold"] = selected
        joined["activity_threshold_provenance"] = "Phase 2 pre-filter user audit"
        tradeoffs = pd.DataFrame(threshold_audit.get("tradeoffs", []))
        if not tradeoffs.empty:
            tradeoffs["approved"] = tradeoffs["threshold"].eq(selected)
            tradeoffs["provenance"] = "Phase 2 pre-filter user audit"
        return joined.drop(columns=[self.user_column]), tradeoffs

    @staticmethod
    def load_threshold_audit(path: str | Path) -> dict:
        return json.loads(Path(path).read_text(encoding="utf-8"))
