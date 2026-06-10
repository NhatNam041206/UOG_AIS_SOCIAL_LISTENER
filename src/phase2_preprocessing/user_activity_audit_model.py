"""Empirical user-activity metrics and threshold selection for Phase 2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ThresholdSelectionPolicy:
    """Transparent retention constraints for selecting an empirical threshold."""

    minimum_percentile: str = "p99"
    maximum_users_removed_pct: float = 1.0
    maximum_tweets_removed_pct: float = 10.0


@dataclass(frozen=True)
class UserActivityAuditResult:
    """Complete reproducible output from one user-activity audit."""

    user_metrics: pd.DataFrame
    candidate_thresholds: Dict[str, float]
    tradeoffs: pd.DataFrame
    selected_threshold: float
    selection_reason: str


class UserActivityAuditor:
    """Measure user activity and derive a defensible high-volume threshold."""

    METRIC = "tweets_per_active_day"

    def __init__(
        self,
        user_key: str = "user_id",
        timestamp_key: str = "date",
        selection_policy: ThresholdSelectionPolicy | None = None,
    ) -> None:
        self.user_key = user_key
        self.timestamp_key = timestamp_key
        self.selection_policy = selection_policy or ThresholdSelectionPolicy()

    def audit(self, dataframe: pd.DataFrame) -> UserActivityAuditResult:
        """Compute metrics, candidate thresholds, tradeoffs, and recommendation."""
        user_metrics = self.compute_user_metrics(dataframe)
        candidates = self.derive_candidate_thresholds(user_metrics[self.METRIC])
        tradeoffs = self.compute_tradeoffs(user_metrics, candidates)
        threshold, reason = self.select_threshold(candidates, tradeoffs)
        return UserActivityAuditResult(
            user_metrics=user_metrics,
            candidate_thresholds=candidates,
            tradeoffs=tradeoffs,
            selected_threshold=threshold,
            selection_reason=reason,
        )

    def compute_user_metrics(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Calculate required activity measures for each observed user."""
        self._require_columns(dataframe)
        working = pd.DataFrame(
            {
                self.user_key: self.user_identity(dataframe[self.user_key]),
                "_timestamp": pd.to_datetime(
                    dataframe[self.timestamp_key],
                    utc=True,
                    errors="coerce",
                ),
            }
        )
        totals = working.groupby(self.user_key, dropna=False).size().rename("total_tweets")
        valid = working.dropna(subset=["_timestamp"]).assign(
            _day=lambda value: value["_timestamp"].dt.floor("D")
        )
        daily = (
            valid.groupby([self.user_key, "_day"], dropna=False)
            .size()
            .rename("_daily_tweets")
            .reset_index()
        )
        activity = daily.groupby(self.user_key, dropna=False).agg(
            active_days=("_day", "nunique"),
            first_observed_day=("_day", "min"),
            last_observed_day=("_day", "max"),
            max_tweets_single_day=("_daily_tweets", "max"),
        )
        metrics = totals.to_frame().join(activity, how="left").reset_index()
        metrics["active_days"] = metrics["active_days"].fillna(0).astype(int)
        metrics["observed_span_days"] = (
            metrics["last_observed_day"] - metrics["first_observed_day"]
        ).dt.days.add(1)
        metrics["tweets_per_active_day"] = (
            metrics["total_tweets"] / metrics["active_days"].replace(0, np.nan)
        )
        metrics["tweets_per_observed_day"] = (
            metrics["total_tweets"] / metrics["observed_span_days"].replace(0, np.nan)
        )
        metrics["max_tweets_single_day"] = metrics["max_tweets_single_day"].fillna(0).astype(int)
        return metrics

    def derive_candidate_thresholds(self, activity: pd.Series) -> Dict[str, float]:
        """Derive robust and percentile candidates from valid positive activity."""
        values = pd.to_numeric(activity, errors="coerce").dropna()
        values = values.loc[values.ge(0)]
        if values.empty:
            raise ValueError("at least one valid user-activity value is required")

        q1, q3 = values.quantile([0.25, 0.75])
        iqr = q3 - q1
        logged = np.log1p(values)
        median = float(values.median())
        mad = float(np.median(np.abs(values - median)))
        return {
            "p95": float(values.quantile(0.95)),
            "p97_5": float(values.quantile(0.975)),
            "p99": float(values.quantile(0.99)),
            "p99_5": float(values.quantile(0.995)),
            "iqr_upper_fence": float(q3 + 1.5 * iqr),
            "extreme_iqr_upper_fence": float(q3 + 3.0 * iqr),
            "log_z_threshold": float(np.expm1(logged.mean() + 3.0 * logged.std(ddof=1))),
            "mad_threshold": float(median + 3.0 * 1.4826 * mad),
        }

    def compute_tradeoffs(
        self,
        user_metrics: pd.DataFrame,
        candidates: Dict[str, float],
    ) -> pd.DataFrame:
        """Measure user and tweet removal for every candidate threshold."""
        total_users = len(user_metrics)
        total_tweets = int(user_metrics["total_tweets"].sum())
        rows = []
        for method, threshold in candidates.items():
            removed = user_metrics[self.METRIC].gt(threshold)
            users_removed = int(removed.sum())
            tweets_removed = int(user_metrics.loc[removed, "total_tweets"].sum())
            rows.append(
                {
                    "method": method,
                    "threshold": threshold,
                    "users_removed": users_removed,
                    "users_removed_pct": 100.0 * users_removed / total_users,
                    "tweets_removed": tweets_removed,
                    "tweets_removed_pct": 100.0 * tweets_removed / total_tweets,
                }
            )
        return pd.DataFrame(rows)

    def select_threshold(
        self,
        candidates: Dict[str, float],
        tradeoffs: pd.DataFrame,
    ) -> tuple[float, str]:
        """Select the least permissive candidate satisfying stated safeguards."""
        minimum = candidates[self.selection_policy.minimum_percentile]
        eligible = tradeoffs.loc[
            tradeoffs["threshold"].ge(minimum)
            & tradeoffs["users_removed_pct"].le(
                self.selection_policy.maximum_users_removed_pct
            )
            & tradeoffs["tweets_removed_pct"].le(
                self.selection_policy.maximum_tweets_removed_pct
            )
        ].sort_values(["threshold", "method"])
        if not eligible.empty:
            row = eligible.iloc[0]
            return float(row["threshold"]), (
                f"Selected {self._method_label(str(row['method']))} as the smallest candidate at or above "
                f"{self.selection_policy.minimum_percentile.upper()} that removes no more "
                f"than {self.selection_policy.maximum_users_removed_pct:.1f}% of users and "
                f"{self.selection_policy.maximum_tweets_removed_pct:.1f}% of tweets."
            )
        fallback = tradeoffs.loc[tradeoffs["threshold"].ge(minimum)].copy()
        fallback["_safeguard_exceedance"] = (
            (
                fallback["users_removed_pct"]
                - self.selection_policy.maximum_users_removed_pct
            ).clip(lower=0)
            + (
                fallback["tweets_removed_pct"]
                - self.selection_policy.maximum_tweets_removed_pct
            ).clip(lower=0)
        )
        row = fallback.sort_values(
            ["_safeguard_exceedance", "threshold", "method"]
        ).iloc[0]
        return float(row["threshold"]), (
            f"No candidate at or above {self.selection_policy.minimum_percentile.upper()} "
            f"met both retention safeguards; selected {self._method_label(str(row['method']))} because it has the "
            "smallest combined safeguard exceedance among eligible tail thresholds."
        )

    @staticmethod
    def user_identity(series: pd.Series) -> pd.Series:
        """Normalize user identifiers and retain missing-user records consistently."""
        return series.astype("string").fillna("__MISSING_USER_ID__")

    def _require_columns(self, dataframe: pd.DataFrame) -> None:
        missing = [
            column
            for column in (self.user_key, self.timestamp_key)
            if column not in dataframe.columns
        ]
        if missing:
            raise ValueError(f"Required activity-audit columns are missing: {missing}")

    @staticmethod
    def _method_label(method: str) -> str:
        labels = {
            "p95": "P95",
            "p97_5": "P97.5",
            "p99": "P99",
            "p99_5": "P99.5",
            "iqr_upper_fence": "IQR upper fence",
            "extreme_iqr_upper_fence": "extreme IQR upper fence",
            "log_z_threshold": "log-z threshold",
            "mad_threshold": "MAD threshold",
        }
        return labels.get(method, method)
