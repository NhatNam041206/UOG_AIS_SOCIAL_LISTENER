"""Tests for the flexible Phase 1 ingestion service controller."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.phase1_ingestion.ingestion_runner_controller import IngestionRunnerController
from src.phase1_ingestion.stream_readers_model import CsvStreamReader
from src.shared.data_interfaces_model import SchemaMapperInterface
from src.shared.pipeline_orchestrator_controller import PipelineControllerError
from verify.phase1.run_phase1 import _build_original_pdf_alignment


class RenameMapper(SchemaMapperInterface):
    """Minimal mapper used to verify projection occurs after mapping."""

    def map_record(self, raw_record):
        return {
            "id": raw_record["raw_id"],
            "created_at": raw_record["raw_date"],
            "text": raw_record["body"],
        }


class IngestionRunnerControllerTests(unittest.TestCase):
    """Verify controller-owned field and timestamp policy."""

    def test_controller_maps_then_selects_fields_and_converts_utc(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "records.csv"
            source.write_text(
                "raw_id,raw_date,body,ignored\n"
                "1,2020-10-08T08:00:00-04:00,hello,x\n",
                encoding="utf-8",
            )
            controller = IngestionRunnerController(CsvStreamReader(), RenameMapper())

            dataframe = controller.execute(
                str(source),
                {
                    "fields": ["id", "created_at", "text"],
                    "timestamp_columns": "created_at",
                },
            )

        self.assertEqual(dataframe.columns.tolist(), ["id", "created_at", "text"])
        self.assertEqual(str(dataframe["created_at"].dtype), "datetime64[ns, UTC]")
        self.assertEqual(dataframe.loc[0, "created_at"].hour, 12)

    def test_controller_can_project_raw_fields_without_mapper(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "records.csv"
            source.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
            controller = IngestionRunnerController(CsvStreamReader())

            dataframe = controller.execute(str(source), {"fields": ["c", "a"]})

        self.assertEqual(dataframe.columns.tolist(), ["c", "a"])

    def test_run_wraps_invalid_requested_field(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "records.csv"
            source.write_text("a\n1\n", encoding="utf-8")
            controller = IngestionRunnerController(CsvStreamReader())

            with self.assertRaises(PipelineControllerError) as context:
                controller.run(str(source), {"fields": ["missing"]})

        self.assertIn("Requested fields are missing", str(context.exception))

    def test_controller_forwards_reader_options(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "records.csv"
            source.write_text("a|b\n1|2\n", encoding="utf-8")
            controller = IngestionRunnerController(CsvStreamReader())

            dataframe = controller.execute(
                str(source),
                {"reader_options": {"sep": "|"}},
            )

        self.assertEqual(dataframe.columns.tolist(), ["a", "b"])

    def test_controller_renames_and_adds_constant_fields(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "records.csv"
            source.write_text("raw_id,text\n1,hello\n", encoding="utf-8")
            controller = IngestionRunnerController(CsvStreamReader())

            dataframe = controller.execute(
                str(source),
                {
                    "rename_fields": {"raw_id": "id"},
                    "constant_fields": {"stream": "twitter"},
                    "fields": ["id", "text", "stream"],
                },
            )

        self.assertEqual(
            dataframe.iloc[0].to_dict(),
            {"id": 1, "text": "hello", "stream": "twitter"},
        )

    def test_original_pdf_alignment_names_all_three_streams_and_gaps(self) -> None:
        manifest = {
            "streams": {
                "twitter_donald_trump": {"record_count": 10},
                "twitter_joe_biden": {"record_count": 8},
                "political_events": {"record_count": 4},
                "electoral_returns": {"record_count": 51},
            }
        }

        alignment = _build_original_pdf_alignment(manifest)

        self.assertEqual(
            set(alignment["streams"]),
            {
                "A_social_media",
                "B_exogenous_events",
                "C_electoral_benchmarks",
            },
        )
        self.assertEqual(alignment["streams"]["A_social_media"]["record_count"], 18)
        self.assertEqual(
            alignment["streams"]["B_exogenous_events"]["record_count"],
            4,
        )
        self.assertEqual(
            alignment["streams"]["C_electoral_benchmarks"]["record_count"],
            51,
        )
        self.assertTrue(
            all(stream["gaps"] for stream in alignment["streams"].values())
        )


if __name__ == "__main__":
    unittest.main()
