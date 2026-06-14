"""Tests for full-dataset VADER output validation."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from verify.phase3.validate_vader_output import validate_vader_output


class VaderOutputValidationTests(unittest.TestCase):
    """Verify passing and failing VADER output contracts."""

    def test_valid_output_passes(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_fixture(root, label="positive")

            result = validate_vader_output(root)

            self.assertEqual(result["status"], "passed")

    def test_inconsistent_label_fails(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_fixture(root, label="negative")

            result = validate_vader_output(root)

            failed = {check["name"] for check in result["checks"] if check["status"] == "failed"}
            self.assertIn("vader_labels_match_compound_thresholds", failed)

    @staticmethod
    def _write_fixture(root: Path, label: str) -> None:
        interim = root / "data/02_interim"
        interim.mkdir(parents=True)
        source = pd.DataFrame(
            {
                "id": pd.Series(["1"], dtype="string"),
                "date": pd.to_datetime(["2020-11-01"], utc=True),
                "tweet": pd.Series(["good"], dtype="string"),
                "user_id": pd.Series(["a"], dtype="string"),
                "user_loc": pd.Series(["NY"], dtype="string"),
                "retweets": pd.Series([0.0]),
                "replies": pd.Series([None], dtype="object"),
                "candidate": pd.Series(["joe_biden"], dtype="string"),
                "source_file": pd.Series(["source.csv"], dtype="string"),
            }
        )
        scored = source.assign(
            vader_negative=0.0,
            vader_neutral=0.2,
            vader_positive=0.8,
            vader_compound=0.7,
            vader_label=label,
        )
        source.to_parquet(interim / "twitter_cleaned.parquet", index=False)
        scored.to_parquet(interim / "twitter_sentiment.parquet", index=False)


if __name__ == "__main__":
    unittest.main()

