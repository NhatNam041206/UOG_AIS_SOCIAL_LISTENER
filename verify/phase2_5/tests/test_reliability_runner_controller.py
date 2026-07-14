from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.phase2_5_reliability.reliability_runner_controller import ReliabilityRunnerController


def fixture_config() -> dict:
    return {
        "inputs": {"required": {
            "sentiment_tweets": "data/twitter.parquet",
            "user_activity_metrics": "data/users.parquet",
            "user_activity_threshold_audit": "data/audit.json",
            "roberta_validation_sample": "data/validation.parquet",
            "political_events": "data/events.parquet",
        }, "optional": {"verified_full_three_model_output": None, "original_text_url_evidence": None}},
        "columns": {"tweet_id": "id", "text": "tweet", "timestamp": "date", "user_id": "user_id", "user_location": "user_loc", "candidate": "candidate"},
        "execution": {"mode": "sample", "smoke_size": 2, "sample_size": 4, "include_roberta_validation_rows_in_sample": True, "seed": 2020, "execute_mitigation": False},
        "provenance": {"phase2_prefilter_user_count": 5, "approved_activity_threshold": 9.0, "phase2_exact_duplicates_removed": 2},
        "duplicate_proxy": {"maximum_signature_length": 160},
        "temporal": {"event_window_hours": 24, "event_risk_horizon_hours": 48},
        "outputs": {"data_root": "out/data", "results_root": "out/results", "reports_root": "out/reports"},
    }


class ReliabilityRunnerControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "data").mkdir()
        self.source = pd.DataFrame({
            "id": [str(i) for i in range(8)],
            "tweet": ["plain", "same", "same", "#tag", "great job 🙄", "news", "hello", "final"],
            "date": pd.to_datetime([f"2020-11-03T0{i}:00:00Z" for i in range(8)], utc=True),
            "user_id": [f"u{i % 4}" for i in range(8)],
            "user_loc": ["TX", None, "USA", "CA / NY", "Earth", "Toronto Canada", "Florida", "WA"],
            "candidate": ["donald_trump", "joe_biden"] * 4,
            "vader_compound": [-0.8, -0.2, 0.0, 0.2, 0.8, 0.1, -0.1, 0.4],
            "vader_label": ["negative", "negative", "neutral", "positive", "positive", "positive", "negative", "positive"],
        })
        self.source.to_parquet(self.root / "data/twitter.parquet", index=False)
        users = pd.DataFrame({
            "user_id": ["u0", "u1", "u2", "u3", "removed"], "total_tweets": [2, 2, 2, 2, 20],
            "active_days": [1, 1, 1, 1, 2], "tweets_per_active_day": [2.0, 2.0, 2.0, 2.0, 10.0],
        })
        users.to_parquet(self.root / "data/users.parquet", index=False)
        (self.root / "data/audit.json").write_text(json.dumps({
            "selected_threshold": 9.0,
            "tradeoffs": [{"method": "p99_5", "threshold": 9.0, "users_removed": 1, "tweets_removed": 20}],
        }), encoding="utf-8")
        validation = self.source.loc[[0, 1]].copy()
        validation["detected_language"] = ["en", "es"]
        validation["roberta_negative_probability"] = [0.7, 0.2]
        validation["roberta_neutral_probability"] = [0.2, 0.6]
        validation["roberta_positive_probability"] = [0.1, 0.2]
        validation["roberta_score"] = [-0.6, 0.0]
        validation["roberta_label"] = ["negative", "neutral"]
        validation.to_parquet(self.root / "data/validation.parquet", index=False)
        pd.DataFrame({"event_timestamp_utc": pd.to_datetime(["2020-11-03T00:30:00Z"], utc=True)}).to_parquet(self.root / "data/events.parquet", index=False)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_deterministic_sample_replay_and_artifact_contract(self) -> None:
        first = ReliabilityRunnerController(self.root, fixture_config()).run()
        second = ReliabilityRunnerController(self.root, fixture_config()).run()
        self.assertEqual(first["sample_row_checksum"], second["sample_row_checksum"])
        self.assertEqual(first["output_row_count"], second["output_row_count"])
        self.assertIn("sample", Path(first["output_paths"]["scores"]).parts)
        for path in first["output_paths"].values():
            self.assertTrue(Path(path).exists())
        required = {"run_id", "run_mode", "input_path", "input_row_count", "output_row_count", "sample_size", "seed", "timestamp", "output_paths"}
        self.assertTrue(required.issubset(first))

    def test_canonical_rows_fields_nulls_and_score_bounds_are_preserved(self) -> None:
        manifest = ReliabilityRunnerController(self.root, fixture_config()).run()
        output = pd.read_parquet(manifest["output_paths"]["scores"])
        source_by_id = self.source.set_index("id")
        for _, row in output.iterrows():
            original = source_by_id.loc[row["id"]]
            self.assertEqual(row["tweet"], original["tweet"])
            self.assertEqual(row["user_id"], original["user_id"])
            self.assertEqual(row["vader_compound"], original["vader_compound"])
        risk_columns = [column for column in output if column.endswith("_risk")]
        for column in risk_columns:
            self.assertTrue(pd.to_numeric(output[column], errors="coerce").dropna().between(0, 1).all())
        unmatched = ~output["roberta_diagnostic_available"]
        self.assertTrue(output.loc[unmatched, "model_suitability_risk"].isna().all())
        self.assertTrue(output.loc[unmatched, "language_model_suitability_risk"].isna().all())
        self.assertFalse(output["prior_url_evidence_available"].any())

    def test_full_mode_is_defined_without_execution(self) -> None:
        config = fixture_config()
        config["execution"]["mode"] = "full"
        controller = ReliabilityRunnerController(self.root, config)
        validation = pd.read_parquet(self.root / "data/validation.parquet")
        selected = controller.select_records(self.source, validation)
        self.assertEqual(len(selected), len(self.source))

    def test_full_mode_joins_validation_diagnostics_without_changing_rows(self) -> None:
        config = fixture_config()
        config["execution"]["mode"] = "full"
        manifest = ReliabilityRunnerController(self.root, config).run()
        output = pd.read_parquet(manifest["output_paths"]["scores"])
        self.assertEqual(len(output), len(self.source))
        self.assertEqual(int(output["roberta_diagnostic_available"].sum()), 2)
        self.assertEqual(int(output["language_diagnostic_available"].sum()), 2)
        self.assertEqual(
            output.loc[output["roberta_diagnostic_available"], "id"].tolist(),
            ["0", "1"],
        )
        self.assertEqual(output["tweet"].tolist(), self.source["tweet"].tolist())
        report = Path(manifest["output_paths"]["report"]).read_text(encoding="utf-8")
        self.assertIn("Full results are diagnostic findings", report)
        self.assertNotIn("Sample results are verification evidence", report)

    def test_runtime_mitigation_guard(self) -> None:
        config = fixture_config()
        config["execution"]["execute_mitigation"] = True
        with self.assertRaises(ValueError):
            ReliabilityRunnerController(self.root, config)


if __name__ == "__main__":
    unittest.main()
