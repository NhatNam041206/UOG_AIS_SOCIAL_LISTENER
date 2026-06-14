"""Tests for the Phase 3 entry-gate validator."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from verify.phase3.validate_phase2_input_contract import validate_phase2_input_contract


class Phase2InputContractValidationTests(unittest.TestCase):
    """Verify pass and fail behavior for the Phase 3 input contract."""

    def test_valid_dataset_passes(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_fixture(root, tweet_values=["GOOD!", "bad"])

            result = validate_phase2_input_contract(root)

            self.assertEqual(result["status"], "passed")
            self.assertTrue((root / "output/results/phase3/phase2_input_contract_validation.json").exists())
            self.assertTrue((root / "output/reports/phase3/phase2_input_contract_validation.md").exists())

    def test_blank_tweet_fails(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_fixture(root, tweet_values=["GOOD!", " "])

            result = validate_phase2_input_contract(root)

            self.assertEqual(result["status"], "failed")
            failed = {check["name"] for check in result["checks"] if check["status"] == "failed"}
            self.assertIn("tweet_text_non_empty", failed)

    @staticmethod
    def _write_fixture(root: Path, tweet_values: list[str]) -> None:
        interim = root / "data/02_interim"
        results = root / "output/results/phase2"
        interim.mkdir(parents=True)
        results.mkdir(parents=True)
        dataframe = pd.DataFrame(
            {
                "id": pd.Series(["1", "2"], dtype="string"),
                "date": pd.to_datetime(["2020-11-01", "2020-11-01"], utc=True),
                "tweet": pd.Series(tweet_values, dtype="string"),
                "user_id": pd.Series(["a", "b"], dtype="string"),
                "user_loc": pd.Series([None, "NY"], dtype="string"),
                "retweets": pd.Series([0.0, 1.0], dtype="float64"),
                "replies": pd.Series([None, None], dtype="object"),
                "candidate": pd.Series(["donald_trump", "joe_biden"], dtype="string"),
                "source_file": pd.Series(["a.csv", "b.csv"], dtype="string"),
            }
        )
        dataframe.to_parquet(interim / "twitter_cleaned.parquet", index=False)
        (results / "preprocessing_manifest.json").write_text(
            json.dumps({"status": "completed", "final_record_count": len(dataframe)}),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
