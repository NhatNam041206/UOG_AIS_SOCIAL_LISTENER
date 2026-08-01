"""Phase 4: Spatial-Temporal Matrix Aggregator.

This module reshapes cleaned and sentiment-scored tweet records into:
1. Temporal Aggregation Matrix (For H1): Hourly/Daily slices with volume (N_t), mean
   sentiment (mu_t), and polarization standard deviation (sigma_t) aligned with political event shocks.
2. Spatial Aggregation Matrix (For H2): State-level candidate sentiment margins
   (X_i = Mean_Biden - Mean_Trump) aligned with certified election returns (Y_i),
   historical classifications, and demographic controls (Z_ki).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TemporalAggregationResult:
    """Hourly and daily temporal aggregates for H1 ITSA modeling."""

    hourly_matrix: pd.DataFrame
    daily_matrix: pd.DataFrame
    event_windows: pd.DataFrame


@dataclass(frozen=True)
class SpatialAggregationResult:
    """State-level spatial aggregate matrix for H2 OLS spatial modeling."""

    state_matrix: pd.DataFrame
    battleground_states: List[str]
    safe_states: List[str]


class TemporalSpatialAggregator:
    """Build structured temporal and spatial matrices for Phase 5 statistical evaluation."""

    US_STATE_CODES = {
        "AK", "AL", "AR", "AZ", "CA", "CO", "CT", "DC", "DE", "FL",
        "GA", "HI", "IA", "ID", "IL", "IN", "KS", "KY", "LA", "MA",
        "MD", "ME", "MI", "MN", "MO", "MS", "MT", "NC", "ND", "NE",
        "NH", "NJ", "NM", "NV", "NY", "OH", "OK", "OR", "PA", "RI",
        "SC", "SD", "TN", "TX", "UT", "VA", "VT", "WA", "WI", "WV", "WY",
    }

    def __init__(
        self,
        sentiment_col: str = "sentiment_score",
        candidate_col: str = "candidate",
        timestamp_col: str = "created_at",
        location_col: str = "state_code",
    ) -> None:
        self.sentiment_col = sentiment_col
        self.candidate_col = candidate_col
        self.timestamp_col = timestamp_col
        self.location_col = location_col

    def aggregate_temporal(
        self,
        tweets_df: pd.DataFrame,
        events_df: Optional[pd.DataFrame] = None,
        event_window_hours: int = 48,
    ) -> TemporalAggregationResult:
        """Construct hourly and daily temporal matrices for H1 analysis."""
        df = tweets_df.copy()
        if self.timestamp_col not in df.columns:
            raise ValueError(f"Missing timestamp column: {self.timestamp_col}")
        if self.sentiment_col not in df.columns:
            # Fallback to vader_compound or roberta_score if present
            if "roberta_score" in df.columns:
                df[self.sentiment_col] = df["roberta_score"]
            elif "vader_compound" in df.columns:
                df[self.sentiment_col] = df["vader_compound"]
            else:
                raise ValueError("No sentiment score column found in DataFrame")

        df["_datetime"] = pd.to_datetime(df[self.timestamp_col], utc=True, errors="coerce")
        df = df.dropna(subset=["_datetime"])

        df["_hour"] = df["_datetime"].dt.floor("h")
        df["_day"] = df["_datetime"].dt.floor("D")

        # Hourly matrix
        hourly = df.groupby("_hour").agg(
            volume=("id" if "id" in df.columns else self.sentiment_col, "count"),
            mean_sentiment=(self.sentiment_col, "mean"),
            std_sentiment=(self.sentiment_col, "std"),
        ).reset_index().rename(columns={"_hour": "timestamp_hourly"})
        hourly["std_sentiment"] = hourly["std_sentiment"].fillna(0.0)

        # Daily matrix
        daily = df.groupby("_day").agg(
            volume=("id" if "id" in df.columns else self.sentiment_col, "count"),
            mean_sentiment=(self.sentiment_col, "mean"),
            std_sentiment=(self.sentiment_col, "std"),
        ).reset_index().rename(columns={"_day": "timestamp_daily"})
        daily["std_sentiment"] = daily["std_sentiment"].fillna(0.0)

        # Align with events if provided
        event_windows_df = pd.DataFrame()
        if events_df is not None and not events_df.empty:
            event_rows = []
            events_df["_event_utc"] = pd.to_datetime(events_df["event_timestamp_utc"], utc=True, errors="coerce")
            for _, event in events_df.iterrows():
                event_time = event["_event_utc"]
                if pd.isna(event_time):
                    continue
                start_window = event_time - pd.Timedelta(hours=event_window_hours)
                end_window = event_time + pd.Timedelta(hours=event_window_hours)

                window_hourly = hourly[
                    (hourly["timestamp_hourly"] >= start_window) &
                    (hourly["timestamp_hourly"] <= end_window)
                ].copy()

                window_hourly["event_name"] = event.get("event_name", "Unknown Event")
                window_hourly["event_time_utc"] = event_time
                window_hourly["time_elapsed_hours"] = (
                    (window_hourly["timestamp_hourly"] - event_time).dt.total_seconds() / 3600.0
                )
                window_hourly["post_event_dummy"] = (window_hourly["time_elapsed_hours"] >= 0).astype(int)
                event_rows.append(window_hourly)

            if event_rows:
                event_windows_df = pd.concat(event_rows, ignore_index=True)

        return TemporalAggregationResult(
            hourly_matrix=hourly,
            daily_matrix=daily,
            event_windows=event_windows_df,
        )

    def aggregate_spatial(
        self,
        tweets_df: pd.DataFrame,
        returns_df: pd.DataFrame,
    ) -> SpatialAggregationResult:
        """Construct state-level spatial aggregate matrix for H2 analysis."""
        df = tweets_df.copy()

        if self.sentiment_col not in df.columns:
            if "roberta_score" in df.columns:
                df[self.sentiment_col] = df["roberta_score"]
            elif "vader_compound" in df.columns:
                df[self.sentiment_col] = df["vader_compound"]
            else:
                raise ValueError("No sentiment score column found in DataFrame")

        # Map state code
        if self.location_col not in df.columns:
            raise ValueError(f"Missing location column: {self.location_col}")

        df["_state_clean"] = df[self.location_col].astype(str).str.strip().str.upper()
        us_df = df[df["_state_clean"].isin(self.US_STATE_CODES)].copy()

        # Compute candidate mean sentiment per state
        # Standardize candidate column values
        us_df["_candidate_clean"] = us_df[self.candidate_col].astype(str).str.lower()
        
        biden_mask = us_df["_candidate_clean"].str.contains("biden|joe")
        trump_mask = us_df["_candidate_clean"].str.contains("trump|donald")

        biden_state = us_df[biden_mask].groupby("_state_clean")[self.sentiment_col].agg(
            biden_mean_sentiment="mean",
            biden_tweet_count="count",
        )
        trump_state = us_df[trump_mask].groupby("_state_clean")[self.sentiment_col].agg(
            trump_mean_sentiment="mean",
            trump_tweet_count="count",
        )

        state_spatial = pd.concat([biden_state, trump_state], axis=1).reset_index()
        state_spatial = state_spatial.rename(columns={"_state_clean": "state_code"})

        state_spatial["biden_mean_sentiment"] = state_spatial["biden_mean_sentiment"].fillna(0.0)
        state_spatial["trump_mean_sentiment"] = state_spatial["trump_mean_sentiment"].fillna(0.0)
        state_spatial["biden_tweet_count"] = state_spatial["biden_tweet_count"].fillna(0).astype(int)
        state_spatial["trump_tweet_count"] = state_spatial["trump_tweet_count"].fillna(0).astype(int)

        # Spatial Candidate Sentiment Margin Xi = Mean(Biden) - Mean(Trump)
        state_spatial["state_sentiment_margin_Xi"] = (
            state_spatial["biden_mean_sentiment"] - state_spatial["trump_mean_sentiment"]
        )

        # Merge with Certified Electoral Returns & Demographic Controls
        merged = returns_df.merge(state_spatial, on="state_code", how="left")
        merged["state_sentiment_margin_Xi"] = merged["state_sentiment_margin_Xi"].fillna(0.0)

        # Separate battleground vs safe states
        battleground_list = merged[
            merged["historical_classification"] == "battleground"
        ]["state_code"].tolist()
        safe_list = merged[
            merged["historical_classification"].isin(["safe_red", "safe_blue"])
        ]["state_code"].tolist()

        return SpatialAggregationResult(
            state_matrix=merged,
            battleground_states=battleground_list,
            safe_states=safe_list,
        )
