"""Verification Test Script for Phase 4 and Phase 5 Modules.

This test validates:
1. Phase 4 Spatial-Temporal Matrix Aggregator (Hourly/Daily matrix, Event windows, State Margins Xi).
2. Phase 5 Inferential Statistical Evaluator (ITSA for H1, Stratified Spatial OLS for H2).
3. Package D Language-Region Cross-Analyzer.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.phase2_preprocessing.language_region_cross_analyzer import LanguageRegionCrossAnalyzer
from src.phase4_aggregation.temporal_spatial_aggregator import TemporalSpatialAggregator
from src.phase5_modeling.itsa_ols_evaluator import ITSAOLSEvaluator


def test_language_region_analyzer() -> None:
    print("Running Package D Language-Region Cross-Analyzer Test (explicit column)...")
    data = [
        {"id": "1", "state_code": "TX", "detected_language": "es"},
        {"id": "2", "state_code": "TX", "detected_language": "en"},
        {"id": "3", "state_code": "FL", "detected_language": "es"},
        {"id": "4", "state_code": "CA", "detected_language": "en"},
        {"id": "5", "state_code": None, "detected_language": "en"},
    ]
    df = pd.DataFrame(data)
    analyzer = LanguageRegionCrossAnalyzer()
    res = analyzer.analyze(df)
    assert res.total_tweets == 5
    assert res.us_state_tweets == 4
    assert res.us_spanish_tweets == 2
    assert res.unmapped_tweets == 1
    assert res.language_detection_method == "explicit_column", f"Expected explicit_column, got {res.language_detection_method}"
    print("  -> Package D Language-Region Test (explicit column) Passed!")


def test_language_region_analyzer_heuristic() -> None:
    print("Running Package D Language-Region Cross-Analyzer Test (heuristic fallback)...")
    data = [
        {"id": "1", "state_code": "TX", "tweet_cleaned": "Gracias por su apoyo, voto por Biden!"},
        {"id": "2", "state_code": "TX", "tweet_cleaned": "Trump is the best candidate for America"},
        {"id": "3", "state_code": "FL", "tweet_cleaned": "Todos debemos votar en estas elecciones"},
        {"id": "4", "state_code": "CA", "tweet_cleaned": "Biden wins California tonight"},
        {"id": "5", "state_code": None, "tweet_cleaned": "Election night is exciting"},
    ]
    df = pd.DataFrame(data)
    # No detected_language column — should fall through to heuristic_pattern_matcher
    analyzer = LanguageRegionCrossAnalyzer()
    res = analyzer.analyze(df)
    assert res.total_tweets == 5
    assert res.us_state_tweets == 4
    assert res.unmapped_tweets == 1
    assert res.language_detection_method == "heuristic_pattern_matcher", f"Expected heuristic_pattern_matcher, got {res.language_detection_method}"
    # Spanish heuristic should detect at least 2 Spanish tweets (TX and FL records)
    assert res.us_spanish_tweets >= 2, f"Expected >= 2 Spanish US tweets, got {res.us_spanish_tweets}"
    print(f"  -> Package D Heuristic Test Passed! Spanish detected: {res.us_spanish_tweets}")



def test_phase4_phase5_pipeline() -> None:
    print("Running Phase 4 & Phase 5 Integration Test...")
    # Synthetic tweet dataset
    dates = pd.date_range(start="2020-10-15", end="2020-10-25", freq="30min")
    states = ["PA", "FL", "TX", "CA", "WY", "AZ", "MI", "GA", "NC", "NV"]
    rows = []
    for idx, d in enumerate(dates):
        st = states[idx % len(states)]
        cand = "joe_biden" if idx % 2 == 0 else "donald_trump"
        score = 0.2 if cand == "joe_biden" else -0.1
        rows.append(
            {
                "id": str(idx),
                "created_at": d,
                "candidate": cand,
                "state_code": st,
                "sentiment_score": score + np.random.normal(0, 0.05),
                "detected_language": "es" if idx % 5 == 0 else "en",
            }
        )
    tweets_df = pd.DataFrame(rows)

    # Synthetic events dataset
    events_df = pd.DataFrame(
        [
            {
                "event_id": "e1",
                "event_timestamp_utc": "2020-10-22 21:00:00+00:00",
                "event_name": "Final Presidential Debate",
            }
        ]
    )

    # Load enriched returns dataset
    returns_source = PROJECT_ROOT / "data" / "01_raw" / "electoral_returns" / "electoral_returns.csv"
    returns_df = pd.read_csv(returns_source)

    # Test Phase 4 Aggregation
    aggregator = TemporalSpatialAggregator(sentiment_col="sentiment_score")
    temp_res = aggregator.aggregate_temporal(tweets_df, events_df, event_window_hours=48)
    assert not temp_res.hourly_matrix.empty
    assert not temp_res.daily_matrix.empty
    assert not temp_res.event_windows.empty
    print(f"  -> Phase 4 Temporal Matrix: {len(temp_res.hourly_matrix)} hourly rows, {len(temp_res.event_windows)} event window rows.")

    spat_res = aggregator.aggregate_spatial(tweets_df, returns_df)
    assert not spat_res.state_matrix.empty
    assert len(spat_res.battleground_states) > 0
    assert len(spat_res.safe_states) > 0
    print(f"  -> Phase 4 Spatial Matrix: {len(spat_res.state_matrix)} state rows. Battleground states: {len(spat_res.battleground_states)}.")

    # Test Phase 5 Statistical Evaluator
    evaluator = ITSAOLSEvaluator()
    itsa_res = evaluator.evaluate_h1_itsa(temp_res.event_windows, "Final Presidential Debate")
    assert itsa_res.r_squared >= 0.0
    print(f"  -> Phase 5 ITSA Shock (beta_2): {itsa_res.beta_2_immediate_shock:.4f}, p-value: {itsa_res.p_value_immediate_shock:.4f}, R2: {itsa_res.r_squared:.4f}")

    summary_eval = evaluator.evaluate_all(temp_res.event_windows, spat_res.state_matrix)
    assert summary_eval.h2_national_ols.sample_size == 51
    print(f"  -> Phase 5 National OLS (beta_1): {summary_eval.h2_national_ols.beta_1_sentiment_margin:.4f}, R2: {summary_eval.h2_national_ols.r_squared:.4f}")
    print(f"  -> Phase 5 Battleground OLS (beta_1): {summary_eval.h2_battleground_ols.beta_1_sentiment_margin:.4f}, R2: {summary_eval.h2_battleground_ols.r_squared:.4f}")

    print("  -> Phase 4 & Phase 5 Tests Completed Successfully!")


if __name__ == "__main__":
    test_language_region_analyzer()
    test_language_region_analyzer_heuristic()
    test_phase4_phase5_pipeline()
