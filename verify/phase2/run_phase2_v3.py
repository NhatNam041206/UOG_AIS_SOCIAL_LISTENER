"""Execute Phase 2 v3 preprocessing, filtering, and language-region cross-analysis.

Phase 2 v3 takes Phase 1 v2 interim Twitter data, executes multivariable user activity
auditing, applies exact duplicate removal and text cleaning, resolves language with fasttext,
and applies a gazetteer to recover geographic data.
"""

from __future__ import annotations

import json
import sys
import re
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import numpy as np
import fasttext

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.phase1_ingestion.storage_serializers_view import StorageSerializersView
from src.phase2_preprocessing.cleaning_heuristics_model import TextCleaner
from src.phase2_preprocessing.language_region_cross_analyzer import LanguageRegionCrossAnalyzer
from src.phase2_preprocessing.user_activity_audit_model import UserActivityAuditor

PHASE2_V3_RUN_ID = "phase2_v3_multivariable_20260801"

US_STATES_ABBR = {
    "AK", "AL", "AR", "AZ", "CA", "CO", "CT", "DC", "DE", "FL",
    "GA", "HI", "IA", "ID", "IL", "IN", "KS", "KY", "LA", "MA",
    "MD", "ME", "MI", "MN", "MO", "MS", "MT", "NC", "ND", "NE",
    "NH", "NJ", "NM", "NV", "NY", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VA", "VT", "WA", "WI", "WV", "WY",
}

US_STATES_NAMES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT",
    "delaware": "DE", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN",
    "iowa": "IA", "kansas": "KS", "kentucky": "KY", "louisiana": "LA",
    "maine": "ME", "maryland": "MD", "massachusetts": "MA",
    "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND",
    "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC"
}

NON_US_REGIONS = {"ENG", "IDF", "ON"}

def resolve_geo(row):
    state_code = str(row.get("state_code", "")).strip().upper()
    state = str(row.get("state", "")).strip().lower()
    user_loc = str(row.get("user_location", "")).strip()
    country = str(row.get("country", "")).strip().upper()

    if state_code in US_STATES_ABBR:
        return state_code, "original_state_code"
    
    if state in US_STATES_NAMES:
        return US_STATES_NAMES[state], "state_name_match"
    
    # Treat 'NAN', 'NONE', 'NULL' string as blank
    if country in {"NAN", "NONE", "NULL"}:
        country = ""
        
    is_us_country = (country in {"US", "USA", "UNITED STATES", "UNITED STATES OF AMERICA", ""})

    if state_code in NON_US_REGIONS or not is_us_country:
        return None, "non_us"
    
    if user_loc and is_us_country:
        user_loc_lower = user_loc.lower()
        for name, code in US_STATES_NAMES.items():
            if re.search(rf'\b{name}\b', user_loc_lower):
                return code, "user_location_gazetteer"
                
        for code in US_STATES_ABBR:
            # Need a US signal. US signal = word USA/US/United States OR a comma before it e.g. ", TX"
            # It must be token bounded.
            has_us_word = bool(re.search(r'\b(usa|us|united states)\b', user_loc, flags=re.IGNORECASE))
            # Require exact case for abbr to avoid matching random lowercase letters
            has_comma_abbr = bool(re.search(rf',\s*{code}\b', user_loc))
            has_bare_abbr = bool(re.search(rf'\b{code}\b', user_loc))
            
            if has_comma_abbr or (has_bare_abbr and has_us_word):
                return code, "user_location_gazetteer"

    return None, "unmapped"


def run_phase2_v3(project_root: str | Path = ".") -> Dict[str, Any]:
    root = Path(project_root).resolve()
    p1_dir = root / "data" / "02_interim" / "phase1_v2"
    p2_dir = root / "data" / "02_interim" / "phase2_v3"
    graph_dir = root / "output" / "graphs" / "phase2" / "v3"
    report_dir = root / "output" / "reports" / "phase2" / "v3"
    result_dir = root / "output" / "results" / "phase2" / "v3"
    evidence_dir = result_dir / "evidence"

    for d in (p2_dir, graph_dir, report_dir, result_dir, evidence_dir):
        d.mkdir(parents=True, exist_ok=True)

    serializer = StorageSerializersView()

    trump_path = p1_dir / "twitter_donald_trump_v2.parquet"
    biden_path = p1_dir / "twitter_joe_biden_v2.parquet"

    trump_df = pd.read_parquet(trump_path)
    biden_df = pd.read_parquet(biden_path)

    # T1.1 Stream membership resolution
    trump_ids = set(trump_df["tweet_id"])
    biden_ids = set(biden_df["tweet_id"])
    both_ids = trump_ids & biden_ids

    combined_raw = pd.concat([trump_df, biden_df], ignore_index=True)
    combined_raw = combined_raw.drop_duplicates(subset=["tweet_id"], keep="first")
    
    def resolve_membership(tid):
        if tid in both_ids: return "both"
        if tid in trump_ids: return "trump_only"
        return "biden_only"
        
    combined_raw["stream_membership"] = combined_raw["tweet_id"].apply(resolve_membership)
    
    def resolve_candidate(mem):
        if mem == "trump_only": return "donald_trump"
        if mem == "biden_only": return "joe_biden"
        return "both"
        
    combined_raw["candidate_resolved"] = combined_raw["stream_membership"].apply(resolve_candidate)
    
    unique_tweet_ids = len(combined_raw)
    mem_counts = combined_raw["stream_membership"].value_counts().to_dict()

    # T1.2 Activity filter
    auditor = UserActivityAuditor(user_key="user_id", timestamp_key="created_at")
    
    # For evidence comparison
    combined_double_counted = pd.concat([trump_df, biden_df], ignore_index=True)
    audit_res_raw = auditor.audit(combined_double_counted)
    p99_raw = audit_res_raw.user_metrics["tweets_per_active_day"].quantile(0.99)
    p995_raw = audit_res_raw.user_metrics["tweets_per_active_day"].quantile(0.995)
    p999_raw = audit_res_raw.user_metrics["tweets_per_active_day"].quantile(0.999)
    
    audit_res = auditor.audit(combined_raw)
    user_metrics = audit_res.user_metrics
    selected_threshold = audit_res.selected_threshold  # P99.5 on deduplicated
    
    p99_dedup = user_metrics["tweets_per_active_day"].quantile(0.99)
    p995_dedup = user_metrics["tweets_per_active_day"].quantile(0.995)
    p999_dedup = user_metrics["tweets_per_active_day"].quantile(0.999)

    high_volume_users = set(
        user_metrics[user_metrics["tweets_per_active_day"] > selected_threshold]["user_id"]
    )
    after_activity_df = combined_raw[~combined_raw["user_id"].isin(high_volume_users)].copy()
    
    activity_filtered_tweets = unique_tweet_ids - len(after_activity_df)

    # T1.3 Text cleaning and dedup
    cleaner = TextCleaner()
    after_activity_df["tweet_cleaned"] = after_activity_df["tweet"].apply(cleaner.clean)
    after_cleaned_df = after_activity_df[after_activity_df["tweet_cleaned"].fillna("").astype(str).str.len() > 0].copy()
    cleaning_filtered_tweets = len(after_activity_df) - len(after_cleaned_df)

    after_dedup_df = after_cleaned_df.drop_duplicates(subset=["user_id", "tweet_cleaned"], keep="first").copy()
    dedup_filtered_tweets = len(after_cleaned_df) - len(after_dedup_df)
    
    # Collect dedup metrics
    text_counts = after_dedup_df["tweet_cleaned"].value_counts()
    repeated_texts = text_counts[text_counts >= 2]
    
    # T1.4 Real language ID
    model = fasttext.load_model(str(root / "models" / "lid.176.ftz"))
    
    def detect_lang(text):
        text_str = str(text).replace('\n', ' ')
        if len(text_str.split()) < 3:
            return "und", None
        preds = model.predict(text_str, k=1)
        lang = preds[0][0].replace("__label__", "")
        conf = float(preds[1][0])
        return lang, conf
        
    lang_res = after_dedup_df["tweet_cleaned"].apply(detect_lang)
    after_dedup_df["detected_language"] = [x[0] for x in lang_res]
    after_dedup_df["language_confidence"] = [x[1] for x in lang_res]
    
    # T1.5 Geographic recovery
    geo_res = after_dedup_df.apply(resolve_geo, axis=1)
    after_dedup_df["state_code_resolved"] = [x[0] for x in geo_res]
    after_dedup_df["state_code_source"] = [x[1] for x in geo_res]

    # Package D Analyzer
    lr_analyzer = LanguageRegionCrossAnalyzer(location_col="state_code_resolved")
    lr_res = lr_analyzer.analyze(after_dedup_df)

    # Save cleaned interim Parquet
    cleaned_path = p2_dir / "twitter_cleaned_v3.parquet"
    serializer.serialize_to_parquet(after_dedup_df, cleaned_path)
    
    # Output language survey
    lang_counts = after_dedup_df["detected_language"].value_counts()
    us_state_df = after_dedup_df[after_dedup_df["state_code_source"].isin(["original_state_code", "state_name_match", "user_location_gazetteer"])]
    us_lang_counts = us_state_df["detected_language"].value_counts()
    
    lang_survey = {
        "corpus_wide": [{"lang": k, "n": int(v), "pct": float(v/len(after_dedup_df)*100)} for k, v in lang_counts.items()],
        "us_state_mapped": [{"lang": k, "n": int(v), "pct": float(v/len(us_state_df)*100)} for k, v in us_lang_counts.items()],
        "top_non_english_us": [{"lang": k, "n": int(v), "pct": float(v/len(us_state_df)*100)} for k, v in us_lang_counts.items() if k != "en"],
        "threshold_pct_for_dedicated_handling": 1.0,
        "languages_above_threshold_us": [k for k, v in us_lang_counts.items() if k != "en" and float(v/len(us_state_df)*100) > 1.0]
    }
    
    with open(evidence_dir / "language_survey.json", "w") as f:
        json.dump(lang_survey, f, indent=2)
        
    # Output gazetteer sample
    gaz_sample = us_state_df[us_state_df["state_code_source"] == "user_location_gazetteer"]
    if len(gaz_sample) > 50:
        gaz_sample = gaz_sample.sample(n=50, random_state=42)
    
    with open(evidence_dir / "gazetteer_sample.json", "w") as f:
        json.dump(gaz_sample[["user_location", "state_code_resolved"]].to_dict(orient="records"), f, indent=2)

    us_ceiling_mask = (after_dedup_df["country"].str.strip().str.upper().isin({"US", "USA", "UNITED STATES", "UNITED STATES OF AMERICA"})) | (after_dedup_df["country"].fillna("").str.strip() == "")
    # Actually wait, US ceiling is just those with country in US or USA
    us_ceiling_rows = len(after_dedup_df[after_dedup_df["country"].str.strip().str.upper().isin({"US", "USA", "UNITED STATES", "UNITED STATES OF AMERICA"})])
    
    # Save Manifest
    manifest = {
        "phase": "phase2_preprocessing_v3",
        "run_id": PHASE2_V3_RUN_ID,
        "initial_record_count": len(combined_raw), # deduplicated
        "stream_membership": mem_counts,
        "activity_filter": {
            "selected_threshold": selected_threshold,
            "users_examined": len(user_metrics),
            "high_volume_users_removed": len(high_volume_users),
            "tweets_removed": activity_filtered_tweets,
            "p99_double_counted": float(p99_raw),
            "p995_double_counted": float(p995_raw),
            "p999_double_counted": float(p999_raw),
            "p99_dedup": float(p99_dedup),
            "p995_dedup": float(p995_dedup),
            "p999_dedup": float(p999_dedup),
        },
        "text_cleaning": {
            "tweets_removed_invalid_text": cleaning_filtered_tweets,
            "tweets_removed_user_text_duplicate": dedup_filtered_tweets,
            "cross_user_repeated_texts_count": len(repeated_texts),
            "top_repeated_texts": repeated_texts.head(20).to_dict()
        },
        "package_d_language_region_summary": {
            "total_tweets": lr_res.total_tweets,
            "us_state_tweets": lr_res.us_state_tweets,
            "us_spanish_tweets": lr_res.us_spanish_tweets,
            "us_other_language_tweets": lr_res.us_other_language_tweets,
            "unmapped_tweets": lr_res.unmapped_tweets,
            "language_detection_method": lr_res.language_detection_method,
        },
        "geographic_recovery": {
            "us_mappable_ceiling_rows": us_ceiling_rows,
            "us_mappable_ceiling_pct": float(us_ceiling_rows / len(after_dedup_df) * 100) if len(after_dedup_df) else 0.0,
            "resolved_us_rows_v3": lr_res.us_state_tweets,
            "resolved_us_pct_v3": float(lr_res.us_state_tweets / len(after_dedup_df) * 100) if len(after_dedup_df) else 0.0,
            "gain_over_v2_pct_points": float(lr_res.us_state_tweets / len(after_dedup_df) * 100) - 20.5, # V2 claimed ~20.5%
            "by_source": after_dedup_df["state_code_source"].value_counts().to_dict()
        },
        "final_cleaned_record_count": len(after_dedup_df),
        "v2_comparison": {
            "final_count_v2": 1280784,
            "final_count_v3": len(after_dedup_df)
        },
        "deltas_explained": [
            "D1 fixed: Deduplicated on tweet_id BEFORE assigning stream membership. 'both' candidate added.",
            "D2 fixed: Dedup key now includes user_id.",
            "D3 fixed: Language ID uses fasttext lid.176, emitting 'Other' when not en/es.",
            "D4 fixed: Gazetteer added to recover US state from user_location."
        ],
        "output_paths": {
            "cleaned_parquet": str(cleaned_path),
            "manifest": str(result_dir / "preprocessing_manifest_v3.json"),
            "report": str(report_dir / "preprocessing_report_v3.md"),
        },
    }

    (result_dir / "preprocessing_manifest_v3.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Generate language target justification report
    with open(report_dir / "language_target_justification.md", "w", encoding="utf-8") as f:
        f.write("# Language Target Justification\n\n")
        f.write("Based on the language survey data in `evidence/language_survey.json`:\n")
        for x in lang_survey["top_non_english_us"][:5]:
            f.write(f"- {x['lang']}: {x['pct']:.2f}% ({x['n']} tweets)\n")
        
        above_thresh = lang_survey["languages_above_threshold_us"]
        if "es" in above_thresh:
            f.write("\nSpanish ('es') exceeds the 1.0% threshold of US-state-mapped tweets, justifying dedicated handling.\n")
        else:
            f.write("\nSpanish ('es') does NOT exceed the 1.0% threshold. It does not warrant dedicated handling.\n")
            
        other_above = [l for l in above_thresh if l != "es"]
        if other_above:
            f.write(f"\nOther languages exceeding threshold: {', '.join(other_above)}\n")
        else:
            f.write("\nNo other languages exceed the threshold for dedicated handling.\n")


    # Generate Report
    report_lines = [
        "# Phase 2 v3 Preprocessing Report",
        "",
        f"Run ID: `{PHASE2_V3_RUN_ID}`",
        "",
        "## Summary Metrics",
        f"- Initial Distinct Tweets: {unique_tweet_ids:,}",
        f"- Stream Membership: {mem_counts}",
        f"- Selected Empirical Activity Threshold: `{selected_threshold}` tweets/active day",
        f"- High-Volume User Filtered Tweets: {activity_filtered_tweets:,}",
        f"- Cross-User Dedup Filtered Tweets: {dedup_filtered_tweets:,}",
        f"- Invalid Text Filtered Tweets: {cleaning_filtered_tweets:,}",
        f"- Final Cleaned Retention: {len(after_dedup_df):,}",
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
        f"- {lr_res.us_state_tweets/lr_res.total_tweets*100:.1f}% of tweets carry a valid US state code (ceiling: {float(us_ceiling_rows / len(after_dedup_df) * 100):.1f}% based on country fields).",
        "- Missing state codes do not invalidate national temporal (H1) analysis.",
        "- State-level (H2) spatial regression uses geocoded subset only; selection bias should be acknowledged.",
    ]
    (report_dir / "preprocessing_report_v3.md").write_text("\n".join(report_lines), encoding="utf-8")

    return manifest

if __name__ == "__main__":
    res = run_phase2_v3(PROJECT_ROOT)
    print("Phase 2 v3 completed successfully.")
