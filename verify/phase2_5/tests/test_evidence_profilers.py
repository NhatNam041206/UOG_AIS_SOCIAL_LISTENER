from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from src.phase2_5_reliability.duplicate_amplification_profiler import DuplicateAmplificationProfiler
from src.phase2_5_reliability.model_suitability_profiler import ModelSuitabilityProfiler
from src.phase2_5_reliability.sarcasm_irony_risk_profiler import SarcasmIronyRiskProfiler
from src.phase2_5_reliability.spatial_validity_profiler import SpatialValidityProfiler
from src.phase2_5_reliability.temporal_coverage_profiler import TemporalCoverageProfiler
from src.phase2_5_reliability.textual_evidence_profiler import TextualEvidenceProfiler
from src.phase2_5_reliability.user_representativeness_profiler import UserRepresentativenessProfiler


class EvidenceProfilerTests(unittest.TestCase):
    def test_url_evidence_available_and_unavailable(self) -> None:
        dataframe = pd.DataFrame({"tweet": ["clean text", "other"]})
        unavailable = TextualEvidenceProfiler().profile(dataframe)
        self.assertFalse(unavailable["prior_url_evidence_available"].any())
        self.assertTrue(unavailable["had_url_before_cleaning"].isna().all())
        original = pd.Series(["clean text https://example.com", "other"])
        available = TextualEvidenceProfiler().profile(dataframe, original)
        self.assertTrue(available["prior_url_evidence_available"].all())
        self.assertEqual(available["had_url_before_cleaning"].tolist(), [True, False])
        self.assertTrue(available["prior_url_evidence_risk"].isna().all())

    def test_exact_normalized_and_near_duplicate_layers_are_distinct(self) -> None:
        dataframe = pd.DataFrame({
            "tweet": ["Vote NOW #A 10", "Vote NOW #A 10", "vote now #B 20", "unique"],
            "user_id": ["a", "b", "c", "d"],
        })
        result = DuplicateAmplificationProfiler().profile(dataframe, 193831)
        self.assertEqual(result.loc[0, "post_clean_exact_duplicate_count"], 2)
        self.assertEqual(result.loc[2, "post_clean_exact_duplicate_count"], 1)
        self.assertGreater(result.loc[0, "near_duplicate_cluster_size"], result.loc[3, "near_duplicate_cluster_size"])
        self.assertEqual(result.loc[0, "cross_user_repetition_count"], 2)
        self.assertIn("not confirmed coordination", result.loc[0, "near_duplicate_evidence_type"])
        self.assertEqual(result.loc[3, "duplicate_amplification_risk"], 0.0)

    def test_spatial_cases_are_separate_and_missing_risk_is_null(self) -> None:
        locations = [None, "USA", "Austin, TX", "CA / NY", "Middle of Nowhere", "Toronto, Canada"]
        result = SpatialValidityProfiler().profile(pd.DataFrame({"user_loc": locations}))
        self.assertTrue(result.loc[0, "missing_location"])
        self.assertTrue(pd.isna(result.loc[0, "spatial_validity_risk"]))
        self.assertTrue(result.loc[1, "national_only_location"])
        self.assertEqual(result.loc[2, "matched_state"], "TX")
        self.assertTrue(result.loc[3, "ambiguous_location"])
        self.assertTrue(result.loc[4, "fictional_location"])
        self.assertTrue(result.loc[5, "non_us_location"])
        self.assertTrue(result["national_temporal_analysis_available"].all())

    def test_temporal_event_window_and_missing_time_bin(self) -> None:
        dataframe = pd.DataFrame({"date": ["2020-11-03T00:00:00Z", "2020-11-03T02:00:00Z", None]})
        events = pd.DataFrame({"event_timestamp_utc": ["2020-11-03T00:30:00Z"]})
        result, diagnostics = TemporalCoverageProfiler().profile(dataframe, events)
        self.assertTrue(result.loc[0, "event_window_flag"])
        self.assertTrue(pd.isna(result.loc[2, "temporal_coverage_risk"]))
        self.assertTrue(diagnostics.loc[diagnostics["hour"].dt.hour.eq(1), "missing_time_bin"].iloc[0])

    def test_model_diagnostics_are_limited_to_matched_rows(self) -> None:
        dataframe = pd.DataFrame({
            "detected_language": ["en", pd.NA],
            "vader_compound": [0.5, -0.2],
            "roberta_score": [0.1, np.nan],
            "roberta_negative_probability": [0.2, np.nan],
            "roberta_neutral_probability": [0.5, np.nan],
            "roberta_positive_probability": [0.3, np.nan],
        })
        result = ModelSuitabilityProfiler().profile(dataframe)
        self.assertEqual(result["roberta_diagnostic_available"].tolist(), [True, False])
        self.assertEqual(result["language_diagnostic_available"].tolist(), [True, False])
        self.assertTrue(pd.isna(result.loc[1, "model_disagreement_risk"]))
        self.assertTrue(pd.isna(result.loc[1, "language_model_suitability_risk"]))
        self.assertFalse(result["baseline_roberta_diagnostic_available"].any())

    def test_sarcasm_remains_a_proxy(self) -> None:
        result = SarcasmIronyRiskProfiler().profile(pd.DataFrame({"tweet": ["Yeah right, great job 🙄", "plain news"]}))
        self.assertNotIn("is_sarcastic", result.columns)
        self.assertGreater(result.loc[0, "rule_based_sarcasm_indicator"], result.loc[1, "rule_based_sarcasm_indicator"])
        self.assertTrue(result["sarcasm_proxy_note"].str.contains("not confirmed").all())

    def test_prefilter_user_audit_join_and_threshold_provenance(self) -> None:
        tweets = pd.DataFrame({"user_id": ["u1", "u2"]})
        metrics = pd.DataFrame({
            "user_id": ["u1", "u2", "removed"], "total_tweets": [2, 4, 100],
            "active_days": [1, 1, 10], "tweets_per_active_day": [2.0, 4.0, 10.0],
        })
        audit = {"selected_threshold": 9.0, "tradeoffs": [{"method": "p99_5", "threshold": 9.0, "users_removed": 1, "tweets_removed": 100}]}
        result, tradeoffs = UserRepresentativenessProfiler().profile(tweets, metrics, audit)
        self.assertTrue(result["user_audit_available"].all())
        self.assertTrue(result["activity_threshold_provenance"].eq("Phase 2 pre-filter user audit").all())
        self.assertTrue(tradeoffs.loc[0, "approved"])


if __name__ == "__main__":
    unittest.main()
