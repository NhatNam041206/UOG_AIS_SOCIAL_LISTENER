"""Temporal volume, missing-bin, and curated event-window diagnostics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .risk_score_normalizer import RiskScoreNormalizer


class TemporalCoverageProfiler:
    def __init__(self, timestamp_column: str = "date", event_window_hours: int = 24, risk_horizon_hours: int = 48) -> None:
        self.timestamp_column = timestamp_column
        self.event_window_hours = event_window_hours
        self.risk_horizon_hours = risk_horizon_hours

    def profile(self, dataframe: pd.DataFrame, events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        timestamp = pd.to_datetime(dataframe[self.timestamp_column], utc=True, errors="coerce")
        hour = timestamp.dt.floor("h")
        observed = hour.dropna().value_counts().sort_index()
        if observed.empty:
            diagnostics = pd.DataFrame(columns=["hour", "tweet_volume", "missing_time_bin", "volume_spike_risk"])
        else:
            full = pd.date_range(observed.index.min(), observed.index.max(), freq="h")
            diagnostics = observed.reindex(full, fill_value=0).rename("tweet_volume").rename_axis("hour").reset_index()
            diagnostics["missing_time_bin"] = diagnostics["tweet_volume"].eq(0)
            diagnostics["volume_spike_risk"] = RiskScoreNormalizer.percentile_rank(diagnostics["tweet_volume"])
        event_times = pd.to_datetime(events.get("event_timestamp_utc", pd.Series(dtype="datetime64[ns]")), utc=True, errors="coerce").dropna().tolist()
        def nearest(value: pd.Timestamp) -> float:
            if pd.isna(value) or not event_times:
                return np.nan
            return min(abs((value - event).total_seconds()) for event in event_times) / 3600.0
        result = pd.DataFrame(index=dataframe.index)
        result["temporal_diagnostic_available"] = timestamp.notna()
        result["tweet_hour"] = hour
        result["time_to_nearest_event_hours"] = timestamp.map(nearest)
        result["event_window_flag"] = result["time_to_nearest_event_hours"].le(self.event_window_hours).where(timestamp.notna())
        volume_map = diagnostics.set_index("hour")["volume_spike_risk"] if not diagnostics.empty else pd.Series(dtype=float)
        result["volume_spike_risk"] = hour.map(volume_map).where(timestamp.notna())
        event_risk = (1.0 - result["time_to_nearest_event_hours"] / self.risk_horizon_hours).clip(0, 1)
        result["event_concentration_risk"] = event_risk.where(result["time_to_nearest_event_hours"].notna())
        result["temporal_coverage_risk"] = RiskScoreNormalizer.available_mean(
            result, ["volume_spike_risk", "event_concentration_risk"]
        ).where(timestamp.notna())
        return result, diagnostics
