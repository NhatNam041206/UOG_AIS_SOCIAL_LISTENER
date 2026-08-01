"""Execute Phase 4 Spatial-Temporal Aggregation.

Phase 4 generates:
1. Hourly/Daily Temporal Aggregation Matrix (N_t, mu_t, sigma_t) aligned with political event timeline.
2. State Spatial Aggregation Matrix (Candidate Sentiment Margin X_i) merged with certified 2020 returns and demographic controls (Z_ki).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.phase1_ingestion.storage_serializers_view import StorageSerializersView
from src.phase4_aggregation.temporal_spatial_aggregator import TemporalSpatialAggregator


PHASE4_RUN_ID = "phase4_matrix_aggregation_20260731"


def run_phase4(project_root: str | Path = ".") -> Dict[str, Any]:
    """Execute Phase 4 matrix aggregation."""
    root = Path(project_root).resolve()
    p3_dir = root / "data" / "02_interim" / "phase3_v2"
    p1_dir = root / "data" / "02_interim" / "phase1_v2"
    p4_processed_dir = root / "data" / "03_processed"
    report_dir = root / "output" / "reports" / "phase4"
    result_dir = root / "output" / "results" / "phase4"

    for d in (p4_processed_dir, report_dir, result_dir):
        d.mkdir(parents=True, exist_ok=True)

    serializer = StorageSerializersView()

    # Load inputs
    sentiment_path = p3_dir / "twitter_sentiment_v2.parquet"
    if not sentiment_path.exists():
        sentiment_path = root / "data" / "02_interim" / "twitter_sentiment.parquet"

    events_path = p1_dir / "political_events_v2.parquet"
    tweets_df = pd.read_parquet(sentiment_path)
    events_df = pd.read_parquet(events_path) if events_path.exists() else None

    # Use Phase 1 v2 enriched electoral returns parquet (already has democratic_margin_pct_2020
    # and all demographic control covariates Z_ki). Fall back to raw CSV if v2 parquet absent.
    returns_v2_path = p1_dir / "electoral_returns_v2.parquet"
    if returns_v2_path.exists():
        returns_df = pd.read_parquet(returns_v2_path)
    else:
        returns_df = pd.read_csv(root / "data" / "01_raw" / "electoral_returns" / "electoral_returns.csv")
        print("[WARN] Phase 1 v2 electoral_returns_v2.parquet not found; falling back to raw CSV.")

    # Use vader_compound as the authoritative sentiment column.
    # roberta_score is deferred (GPU environment required) and stored as NaN.
    aggregator = TemporalSpatialAggregator(sentiment_col="vader_compound")

    temp_res = aggregator.aggregate_temporal(tweets_df, events_df, event_window_hours=48)
    spat_res = aggregator.aggregate_spatial(tweets_df, returns_df)

    # Save Processed Matrices
    hourly_path = p4_processed_dir / "temporal_hourly_matrix.parquet"
    daily_path = p4_processed_dir / "temporal_daily_matrix.parquet"
    event_window_path = p4_processed_dir / "temporal_event_windows.parquet"
    spatial_path = p4_processed_dir / "spatial_state_matrix.parquet"

    serializer.serialize_to_parquet(temp_res.hourly_matrix, hourly_path)
    serializer.serialize_to_parquet(temp_res.daily_matrix, daily_path)
    if not temp_res.event_windows.empty:
        serializer.serialize_to_parquet(temp_res.event_windows, event_window_path)
    serializer.serialize_to_parquet(spat_res.state_matrix, spatial_path)

    manifest = {
        "phase": "phase4_spatial_temporal_aggregation",
        "run_id": PHASE4_RUN_ID,
        "temporal_hourly_rows": len(temp_res.hourly_matrix),
        "temporal_daily_rows": len(temp_res.daily_matrix),
        "event_window_rows": len(temp_res.event_windows),
        "spatial_state_rows": len(spat_res.state_matrix),
        "battleground_states_count": len(spat_res.battleground_states),
        "safe_states_count": len(spat_res.safe_states),
        "output_paths": {
            "temporal_hourly": str(hourly_path),
            "temporal_daily": str(daily_path),
            "temporal_event_windows": str(event_window_path),
            "spatial_state_matrix": str(spatial_path),
            "manifest": str(result_dir / "aggregation_manifest.json"),
            "report": str(report_dir / "aggregation_report.md"),
        },
    }

    (result_dir / "aggregation_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Write Report
    us_tweet_count = tweets_df[tweets_df["state_code"].astype(str).str.strip().isin(
        {"AK","AL","AR","AZ","CA","CO","CT","DC","DE","FL","GA","HI","IA","ID","IL","IN","KS","KY","LA","MA",
         "MD","ME","MI","MN","MO","MS","MT","NC","ND","NE","NH","NJ","NM","NV","NY","OH","OK","OR","PA","RI",
         "SC","SD","TN","TX","UT","VA","VT","WA","WI","WV","WY"}
    )].shape[0]
    state_coverage_pct = 100.0 * us_tweet_count / len(tweets_df)
    report_lines = [
        "# Phase 4 Aggregation Report",
        "",
        f"Run ID: `{PHASE4_RUN_ID}`",
        "",
        "## Aggregation Summary",
        f"- Temporal Hourly Slices: {len(temp_res.hourly_matrix):,}",
        f"- Temporal Daily Slices: {len(temp_res.daily_matrix):,}",
        f"- Event Window Hourly Slices: {len(temp_res.event_windows):,}",
        f"- State Spatial Aggregate Rows: {len(spat_res.state_matrix):,} (50 States + DC)",
        f"- Classified Battleground States ({len(spat_res.battleground_states)}): {', '.join(sorted(spat_res.battleground_states))}",
        f"- Classified Safe States ({len(spat_res.safe_states)}): {', '.join(sorted(spat_res.safe_states))}",
        "",
        "## State Coverage Limitation",
        f"- Tweets with valid US state code: {us_tweet_count:,} / {len(tweets_df):,} ({state_coverage_pct:.1f}%)",
        "- The spatial sentiment matrix (Xi) is computed from this subset only.",
        "- **Limitation**: ~79.5% of tweets have missing or non-US state codes. State-level H2 results",
        "  reflect users who chose to provide geocoded location, which may not represent all states equally.",
        "  This selection bias should be acknowledged when interpreting H2 OLS coefficients.",
    ]
    (report_dir / "aggregation_report.md").write_text("\n".join(report_lines), encoding="utf-8")

    return manifest


if __name__ == "__main__":
    res = run_phase4(PROJECT_ROOT)
    print(json.dumps(res, indent=2))
