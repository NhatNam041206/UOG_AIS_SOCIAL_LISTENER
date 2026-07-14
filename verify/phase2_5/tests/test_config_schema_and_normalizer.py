from __future__ import annotations

import copy
import unittest

import numpy as np
import pandas as pd

from src.phase2_5_reliability.dataset_schema_profiler import (
    DatasetSchemaProfiler,
    validate_reliability_config,
)
from src.phase2_5_reliability.risk_score_normalizer import RiskScoreNormalizer


def valid_config() -> dict:
    return {
        "inputs": {"required": {
            "sentiment_tweets": "a", "user_activity_metrics": "b",
            "user_activity_threshold_audit": "c", "roberta_validation_sample": "d",
            "political_events": "e",
        }, "optional": {}},
        "columns": {},
        "execution": {"mode": "sample", "seed": 2020, "execute_mitigation": False},
        "outputs": {},
        "provenance": {},
    }


class ConfigSchemaAndNormalizerTests(unittest.TestCase):
    def test_valid_config_and_rejected_mitigation(self) -> None:
        config = valid_config()
        validate_reliability_config(config)
        invalid = copy.deepcopy(config)
        invalid["execution"]["execute_mitigation"] = True
        with self.assertRaisesRegex(ValueError, "rejects mitigation"):
            validate_reliability_config(invalid)

    def test_invalid_mode_and_missing_input_are_rejected(self) -> None:
        invalid = valid_config()
        invalid["execution"]["mode"] = "production"
        with self.assertRaises(ValueError):
            validate_reliability_config(invalid)
        invalid = valid_config()
        del invalid["inputs"]["required"]["political_events"]
        with self.assertRaises(ValueError):
            validate_reliability_config(invalid)

    def test_schema_required_and_optional_columns(self) -> None:
        profiler = DatasetSchemaProfiler({
            "tweet_id": "id", "text": "tweet", "timestamp": "date",
            "user_id": "user_id", "candidate": "candidate", "user_location": "user_loc",
        })
        dataframe = pd.DataFrame({"id": ["1"], "tweet": ["x"], "date": ["2020-11-03"], "user_id": ["u"], "candidate": ["c"]})
        manifest = profiler.profile(dataframe)
        self.assertEqual(manifest["missing_optional_columns"], ["user_loc"])
        with self.assertRaises(ValueError):
            profiler.profile(dataframe.drop(columns="tweet"))

    def test_normalizers_handle_empty_constant_skewed_and_missing(self) -> None:
        empty = RiskScoreNormalizer.percentile_rank(pd.Series([np.nan, np.nan]))
        self.assertTrue(empty.isna().all())
        constant = RiskScoreNormalizer.percentile_rank(pd.Series([4.0, 4.0, np.nan]))
        self.assertEqual(constant.iloc[:2].tolist(), [0.0, 0.0])
        self.assertTrue(pd.isna(constant.iloc[2]))
        skewed = RiskScoreNormalizer.robust_z_sigmoid(pd.Series([1.0, 2.0, 3.0, 1000.0, np.nan]))
        self.assertTrue(skewed.dropna().between(0, 1).all())
        self.assertTrue(pd.isna(skewed.iloc[-1]))


if __name__ == "__main__":
    unittest.main()
