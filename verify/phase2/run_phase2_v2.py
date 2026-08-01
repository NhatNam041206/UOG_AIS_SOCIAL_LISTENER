"""Execute Phase 2 v2 preprocessing, filtering, and language-region cross-analysis.

Phase 2 v2 takes Phase 1 v2 interim Twitter data, executes multivariable user activity
auditing, applies exact duplicate removal and text cleaning, and runs Package D
Language-Region cross-analysis.
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
from src.phase2_preprocessing.cleaning_heuristics_model import TextCleaner
from src.phase2_preprocessing.language_region_cross_analyzer import LanguageRegionCrossAnalyzer
from src.phase2_preprocessing.user_activity_audit_model import UserActivityAuditor


PHASE2_V2_RUN_ID = "phase2_v2_multivariable_20260731"


def run_phase2_v2(project_root: str | Path = ".") -> Dict[str, Any]:
    """Execute Phase 2 v2 preprocessing pipeline."""
    root = Path(project_root).resolve()
    p1_dir = root / "data" / "02_interim" / "phase1_v2"
    p2_dir = root / "data" / "02_interim" / "phase2_v2"
    graph_dir = root / "output" / "graphs" / "phase2" / "v2"
    report_dir = root / "output" / "reports" / "phase2" / "v2"
    result_dir = root / "output" / "results" / "phase2" / "v2"

    for d in (p2_dir, graph_dir, report_dir, result_dir):
        d.mkdir(parents=True, exist_ok=True)

    serializer = StorageSerializersView()

    # Load Phase 1 v2 Parquet streams
    trump_path = p1_dir / "twitter_donald_trump_v2.parquet"
    biden_path = p1_dir / "twitter_joe_biden_v2.parquet"

    if not trump_path.exists() or not biden_path.exists():
        raise FileNotFoundError("Phase 1 v2 interim files missing. Run Phase 1 v2 first.")

    trump_df = pd.read_parquet(trump_path)
    biden_df = pd.read_parquet(biden_path)

    combined_raw = pd.concat([trump_df, biden_df], ignore_index=True)
    initial_count = len(combined_raw)

    # 1. Multivariable User Activity Audit
    auditor = UserActivityAuditor(user_key="user_id", timestamp_key="created_at")
    audit_res = auditor.audit(combined_raw)
    selected_threshold = audit_res.selected_threshold  # P99.5 = 9.0 tweets/active day

    # Filter out high-volume users (> 9.0 tweets/active day)
    user_metrics = audit_res.user_metrics
    high_volume_users = set(
        user_metrics[user_metrics["tweets_per_active_day"] > selected_threshold]["user_id"]
    )
    after_activity_df = combined_raw[~combined_raw["user_id"].isin(high_volume_users)].copy()
    after_activity_count = len(after_activity_df)
    activity_filtered_count = initial_count - after_activity_count

    # 2. VADER-Preserving Text Normalization & Cleaning (runs BEFORE dedup so dedup acts on clean text)
    cleaner = TextCleaner()
    after_activity_df["tweet_cleaned"] = after_activity_df["tweet"].apply(cleaner.clean)
    after_cleaned_df = after_activity_df[after_activity_df["tweet_cleaned"].fillna("").astype(str).str.len() > 0].copy()
    cleaning_filtered_count = after_activity_count - len(after_cleaned_df)

    # 3. Exact Duplicate Removal on cleaned text (retaining first occurrence)
    # Deduplication runs AFTER cleaning so tweets differing only by URL are correctly collapsed.
    after_cleaned_df["_clean_text_temp"] = after_cleaned_df["tweet_cleaned"].fillna("").astype(str).str.strip()
    after_dedup_df = after_cleaned_df.drop_duplicates(subset=["_clean_text_temp"], keep="first").copy()
    after_dedup_count = len(after_dedup_df)
    dedup_filtered_count = len(after_cleaned_df) - after_dedup_count

    final_df = after_dedup_df.drop(columns=["_clean_text_temp"])
    final_count = len(final_df)

    # 4. Package D: Language-Region Cross-Analysis
    lr_analyzer = LanguageRegionCrossAnalyzer()
    lr_res = lr_analyzer.analyze(final_df)

    # Save cleaned interim Parquet
    cleaned_path = p2_dir / "twitter_cleaned_v2.parquet"
    serializer.serialize_to_parquet(final_df, cleaned_path)

    manifest = {
        "phase": "phase2_preprocessing_v2",
        "run_id": PHASE2_V2_RUN_ID,
        "initial_record_count": initial_count,
        "selected_activity_threshold": selected_threshold,
        "users_examined": len(user_metrics),
        "high_volume_users_removed": len(high_volume_users),
        "tweets_removed_activity_filter": activity_filtered_count,
        "tweets_removed_exact_duplicate_filter": dedup_filtered_count,
        "tweets_removed_text_cleaning": cleaning_filtered_count,
        "final_cleaned_record_count": final_count,
        "retention_pct": (final_count / initial_count) * 100.0,
        "package_d_language_region_summary": {
            "total_tweets": lr_res.total_tweets,
            "us_state_tweets": lr_res.us_state_tweets,
            "us_spanish_tweets": lr_res.us_spanish_tweets,
            "us_other_language_tweets": lr_res.us_other_language_tweets,
            "unmapped_tweets": lr_res.unmapped_tweets,
            "language_detection_method": lr_res.language_detection_method,
        },
        "output_paths": {
            "cleaned_parquet": str(cleaned_path),
            "manifest": str(result_dir / "preprocessing_manifest_v2.json"),
            "report": str(report_dir / "preprocessing_report_v2.md"),
        },
    }

    (result_dir / "preprocessing_manifest_v2.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Generate Report
    report_lines = [
        "# Phase 2 v2 Preprocessing Report",
        "",
        f"Run ID: `{PHASE2_V2_RUN_ID}`",
        "",
        "## Summary Metrics",
        f"- Initial Records: {initial_count:,}",
        f"- Selected Empirical Activity Threshold: `{selected_threshold}` tweets/active day",
        f"- High-Volume User Filtered Tweets: {activity_filtered_count:,} ({activity_filtered_count/initial_count*100:.2f}%)",
        f"- Exact Duplicate Filtered Tweets: {dedup_filtered_count:,} ({dedup_filtered_count/initial_count*100:.2f}%)",
        f"- Invalid Text Filtered Tweets: {cleaning_filtered_count:,}",
        f"- Final Cleaned Retention: {final_count:,} ({final_count/initial_count*100:.2f}%)",
        "",
        "## Package D Language-Region Cross-Analysis",
        f"- Total Clean Tweets Analyzed: {lr_res.total_tweets:,}",
        f"- Language Detection Method: `{lr_res.language_detection_method}`",
        f"- US State-Mapped Tweets: {lr_res.us_state_tweets:,} ({lr_res.us_state_tweets/lr_res.total_tweets*100:.1f}%)",
        f"- US State Spanish Tweets Retained: {lr_res.us_spanish_tweets:,}",
        f"- US State Other Language Tweets: {lr_res.us_other_language_tweets:,}",
        f"- Unmapped Region Tweets: {lr_res.unmapped_tweets:,} ({lr_res.unmapped_tweets/lr_res.total_tweets*100:.1f}%)",
        "",
        "## Coverage Note",
        "- Approximately 20.5% of tweets carry a valid US state code.",
        "- Missing state codes do not invalidate national temporal (H1) analysis.",
        "- State-level (H2) spatial regression uses geocoded subset only; selection bias should be acknowledged.",
    ]
    (report_dir / "preprocessing_report_v2.md").write_text("\n".join(report_lines), encoding="utf-8")

    return manifest


if __name__ == "__main__":
    res = run_phase2_v2(PROJECT_ROOT)
    print(json.dumps(res, indent=2))
