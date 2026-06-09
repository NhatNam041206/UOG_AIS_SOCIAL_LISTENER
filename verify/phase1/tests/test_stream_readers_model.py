"""Tests for flexible CSV and JSON stream readers."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from src.phase1_ingestion.stream_readers_model import CsvStreamReader, JsonStreamReader


class StreamReaderTests(unittest.TestCase):
    """Verify readers remain format adapters without fixed field policy."""

    def test_csv_reader_forwards_parser_options(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "records.csv"
            source.write_text("tweet_id|text|unused\n1|hello|x\n", encoding="utf-8")

            dataframe = CsvStreamReader().read(
                str(source),
                {"sep": "|", "usecols": ["tweet_id", "text"]},
            )

        self.assertEqual(dataframe.columns.tolist(), ["tweet_id", "text"])
        self.assertEqual(dataframe.iloc[0].to_dict(), {"tweet_id": 1, "text": "hello"})

    def test_json_reader_supports_newline_delimited_json(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "records.jsonl"
            source.write_text(
                "\n".join(json.dumps(record) for record in [{"id": 1}, {"id": 2}]),
                encoding="utf-8",
            )

            dataframe = JsonStreamReader().read(str(source), {"lines": True})

        self.assertEqual(dataframe["id"].tolist(), [1, 2])

    def test_json_reader_supports_standard_json_array(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "records.json"
            source.write_text(json.dumps([{"id": 1, "text": "hello"}]), encoding="utf-8")

            dataframe = JsonStreamReader().read(str(source))

        self.assertEqual(dataframe.iloc[0].to_dict(), {"id": 1, "text": "hello"})

    def test_reader_rejects_missing_source(self) -> None:
        with self.assertRaises(FileNotFoundError):
            CsvStreamReader().read("missing.csv")

    def test_csv_reader_streams_and_counts_invalid_rows(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "records.csv"
            source.write_text("id,text\n1,valid\n2,too,many\n3,valid\n", encoding="utf-8")
            reader = CsvStreamReader()

            dataframe = pd.concat(
                reader.iter_batches(
                    str(source),
                    {"columns": ["id", "text"], "invalid_row_behavior": "skip"},
                ),
                ignore_index=True,
            )

        self.assertEqual(dataframe["id"].tolist(), [1, 3])
        self.assertEqual(reader.invalid_row_count, 1)


if __name__ == "__main__":
    unittest.main()
