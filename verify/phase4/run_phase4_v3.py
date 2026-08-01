"""WP4 Phase 4 v3: Aggregation with corrected inputs."""
import json
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

def run_phase4_v3(project_root: str | Path = ".") -> None:
    root = Path(project_root).resolve()
    
    # Inputs
    sentiment_path = root / "data" / "02_interim" / "phase3_v3" / "twitter_sentiment_v3.parquet"
    returns_path = root / "data" / "02_interim" / "phase1_v2" / "electoral_returns_v2.parquet"
    events_path = root / "data" / "02_interim" / "phase1_v2" / "political_events_v2.parquet"
    
    # Outputs
    out_dir = root / "data" / "03_processed" / "v3"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "phase4_manifest_v3.json"
    
    # 1. Load data
    df = pd.read_parquet(sentiment_path)
    returns_df = pd.read_parquet(returns_path)
    events_df = pd.read_parquet(events_path)
    
    # T4.1 Rewiring
    candidate_col = "candidate_resolved"
    location_col = "state_code_resolved"
    
    both_count = int((df[candidate_col] == "both").sum())
    
    # 2. Temporal Aggregation (H1) - Include 'both'
    # For H1, we want mean sentiment for both roberta and vader
    df["_datetime"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    df_temp = df.dropna(subset=["_datetime"]).copy()
    df_temp["_hour"] = df_temp["_datetime"].dt.floor("h")
    
    hourly = df_temp.groupby("_hour").agg(
        volume=("tweet_id", "count"),
        mean_sentiment_roberta=("roberta_score", "mean"),
        std_sentiment_roberta=("roberta_score", "std"),
        mean_sentiment_vader=("vader_compound", "mean"),
        std_sentiment_vader=("vader_compound", "std"),
    ).reset_index().rename(columns={"_hour": "timestamp_hourly"})
    
    hourly["std_sentiment_roberta"] = hourly["std_sentiment_roberta"].fillna(0.0)
    hourly["std_sentiment_vader"] = hourly["std_sentiment_vader"].fillna(0.0)
    
    hourly.to_parquet(out_dir / "temporal_hourly_matrix_v3.parquet")
    
    daily = df_temp.assign(_day=df_temp["_datetime"].dt.floor("D")).groupby("_day").agg(
        volume=("tweet_id", "count"),
        mean_sentiment_roberta=("roberta_score", "mean"),
        std_sentiment_roberta=("roberta_score", "std"),
        mean_sentiment_vader=("vader_compound", "mean"),
        std_sentiment_vader=("vader_compound", "std"),
    ).reset_index().rename(columns={"_day": "timestamp_daily"})
    daily["std_sentiment_roberta"] = daily["std_sentiment_roberta"].fillna(0.0)
    daily["std_sentiment_vader"] = daily["std_sentiment_vader"].fillna(0.0)
    daily.to_parquet(out_dir / "temporal_daily_matrix_v3.parquet")
    
    event_windows = []
    events_df["_event_utc"] = pd.to_datetime(events_df["event_timestamp_utc"], utc=True, errors="coerce")
    for _, event in events_df.iterrows():
        event_time = event["_event_utc"]
        if pd.isna(event_time): continue
        start_w = event_time - pd.Timedelta(hours=48)
        end_w = event_time + pd.Timedelta(hours=48)
        
        window = hourly[(hourly["timestamp_hourly"] >= start_w) & (hourly["timestamp_hourly"] <= end_w)].copy()
        window["event_name"] = event["event_name"]
        window["event_time_utc"] = event_time
        window["time_elapsed_hours"] = (window["timestamp_hourly"] - event_time).dt.total_seconds() / 3600.0
        window["post_event_dummy"] = (window["time_elapsed_hours"] >= 0).astype(int)
        event_windows.append(window)
        
    temporal_df = pd.concat(event_windows, ignore_index=True) if event_windows else pd.DataFrame()
    temporal_df.to_parquet(out_dir / "temporal_event_windows_v3.parquet")
    
    # 3. Spatial Aggregation (H2)
    US_STATE_CODES = {
        "AK", "AL", "AR", "AZ", "CA", "CO", "CT", "DC", "DE", "FL",
        "GA", "HI", "IA", "ID", "IL", "IN", "KS", "KY", "LA", "MA",
        "MD", "ME", "MI", "MN", "MO", "MS", "MT", "NC", "ND", "NE",
        "NH", "NJ", "NM", "NV", "NY", "OH", "OK", "OR", "PA", "RI",
        "SC", "SD", "TN", "TX", "UT", "VA", "VT", "WA", "WI", "WV", "WY"
    }
    
    df["_state_clean"] = df[location_col].astype(str).str.strip().str.upper()
    us_df = df[df["_state_clean"].isin(US_STATE_CODES)].copy()
    
    # Function to build spatial matrix
    def build_spatial(subset_df, suffix):
        biden_mask = subset_df[candidate_col].str.contains("biden|joe", case=False, na=False)
        trump_mask = subset_df[candidate_col].str.contains("trump|donald", case=False, na=False)
        
        b_df = subset_df[biden_mask]
        t_df = subset_df[trump_mask]
        
        biden_state = b_df.groupby("_state_clean").agg(
            biden_mean_sentiment_roberta=("roberta_score", "mean"),
            biden_mean_sentiment_vader=("vader_compound", "mean"),
            biden_tweet_count=("tweet_id", "count")
        )
        trump_state = t_df.groupby("_state_clean").agg(
            trump_mean_sentiment_roberta=("roberta_score", "mean"),
            trump_mean_sentiment_vader=("vader_compound", "mean"),
            trump_tweet_count=("tweet_id", "count")
        )
        
        spatial = pd.concat([biden_state, trump_state], axis=1).reset_index().rename(columns={"_state_clean": "state_code"})
        spatial = spatial.fillna(0.0)
        
        spatial["state_sentiment_margin_Xi_roberta"] = spatial["biden_mean_sentiment_roberta"] - spatial["trump_mean_sentiment_roberta"]
        spatial["state_sentiment_margin_Xi_vader"] = spatial["biden_mean_sentiment_vader"] - spatial["trump_mean_sentiment_vader"]
        
        merged = returns_df.merge(spatial, on="state_code", how="left").fillna(0.0)
        return merged
        
    # Primary: exclude 'both'
    us_df_primary = us_df[us_df[candidate_col] != "both"].copy()
    spatial_primary = build_spatial(us_df_primary, "")
    spatial_primary.to_parquet(out_dir / "spatial_state_matrix_v3.parquet")
    
    # Both-split: 'both' tweets contribute to both
    # A tweet with candidate='both' will match both biden_mask and trump_mask in build_spatial!
    # Because they contain both? Wait, candidate_resolved is exactly "both" for these, not "biden and trump".
    # We must explicitly map them.
    us_df_split = us_df.copy()
    # If candidate_resolved is "both", it doesn't contain "biden" or "trump" string literally.
    # We need to change the logic in build_spatial to handle this, or just replace "both" with "biden trump".
    us_df_split.loc[us_df_split[candidate_col] == "both", candidate_col] = "biden trump"
    spatial_split = build_spatial(us_df_split, "_both_split")
    spatial_split.to_parquet(out_dir / "spatial_state_matrix_v3_both_split.parquet")
    
    # 4. Save manifest
    manifest = {
        "temporal_both_row_count": both_count,
        "spatial_both_row_count": both_count,
        "hourly_row_count": len(hourly),
        "daily_row_count": len(daily),
        "roberta_inference_status": "completed"
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
        
    print("Phase 4 v3 Aggregation complete.")

if __name__ == "__main__":
    run_phase4_v3(PROJECT_ROOT)
