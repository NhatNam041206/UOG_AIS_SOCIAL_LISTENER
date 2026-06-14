"""Execute full-dataset VADER scoring for the second Phase 3 stage."""

from __future__ import annotations

import importlib.metadata
import json
import sys
from pathlib import Path
from typing import Any, Dict

import matplotlib

matplotlib.use("Agg")

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.phase3_sentiment.sentiment_reporter_view import SentimentReporterView
from src.phase3_sentiment.sentiment_runner_controller import SentimentRunnerController
from verify.phase3.validate_phase2_input_contract import validate_phase2_input_contract
from verify.phase3.validate_vader_output import validate_vader_output


def run_phase3_vader(
    project_root: str | Path = ".",
    batch_size: int = 50_000,
) -> Dict[str, Any]:
    """Score every cleaned tweet with VADER and write auditable stage artifacts."""
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    root = Path(project_root).resolve()
    input_path = root / "data" / "02_interim" / "twitter_cleaned.parquet"
    output_path = root / "data" / "02_interim" / "twitter_sentiment.parquet"
    graph_dir = root / "output" / "graphs" / "phase3"
    report_path = root / "output" / "reports" / "phase3" / "sentiment_report.md"
    manifest_path = root / "output" / "results" / "phase3" / "sentiment_manifest.json"
    graph_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    contract = validate_phase2_input_contract(root)
    if contract["status"] != "passed":
        raise ValueError("Phase 2 input contract must pass before VADER scoring")

    controller = SentimentRunnerController()
    source = pq.ParquetFile(input_path)
    writer: pq.ParquetWriter | None = None
    output_count = 0
    label_counts: Dict[str, int] = {"negative": 0, "neutral": 0, "positive": 0}
    compound_count = 0
    compound_sum = 0.0
    compound_sum_squares = 0.0
    compound_min = 1.0
    compound_max = -1.0
    try:
        for record_batch in source.iter_batches(batch_size=batch_size):
            scored = controller.execute_dataframe(record_batch.to_pandas())
            compound = scored["vader_compound"]
            output_count += len(scored)
            compound_count += int(compound.count())
            compound_sum += float(compound.sum())
            compound_sum_squares += float((compound * compound).sum())
            compound_min = min(compound_min, float(compound.min()))
            compound_max = max(compound_max, float(compound.max()))
            for label, count in scored["vader_label"].value_counts().items():
                label_counts[str(label)] = label_counts.get(str(label), 0) + int(count)
            table = pa.Table.from_pandas(scored, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(output_path, table.schema)
            writer.write_table(table)
    finally:
        if writer is not None:
            writer.close()
    if writer is None:
        raise ValueError("Phase 2 cleaned dataset contained no scoreable batches")

    mean = compound_sum / compound_count
    variance = max(0.0, (compound_sum_squares - compound_count * mean * mean) / (compound_count - 1))
    output_validation = validate_vader_output(root)
    if output_validation["status"] != "passed":
        raise ValueError("VADER output validation failed")
    manifest: Dict[str, Any] = {
        "phase": "phase3_sentiment",
        "stage": "vader_full_dataset_scoring",
        "status": "vader_scoring_completed",
        "input_path": str(input_path),
        "output_path": str(output_path),
        "input_record_count": source.metadata.num_rows,
        "output_record_count": output_count,
        "batch_size": batch_size,
        "model": {
            "name": "vaderSentiment",
            "version": importlib.metadata.version("vaderSentiment"),
            "text_field": "tweet",
            "negative_threshold": -0.05,
            "positive_threshold": 0.05,
        },
        "output_fields": list(SentimentRunnerController.VADER_COLUMNS),
        "vader_summary": {
            "compound_mean": mean,
            "compound_std": variance**0.5,
            "compound_min": compound_min,
            "compound_max": compound_max,
            "label_counts": label_counts,
            "label_percentages": {
                label: 100.0 * count / output_count for label, count in label_counts.items()
            },
        },
        "validation_status": "roberta_validation_pending",
        "output_validation": {
            "status": output_validation["status"],
            "result_path": str(root / "output" / "results" / "phase3" / "vader_output_validation.json"),
            "checks_passed": len(output_validation["checks"]),
        },
        "notes": [
            "VADER scored the Phase 2 cleaned tweet text without additional normalization.",
            "The output preserves all Phase 2 fields and appends the approved five-field VADER schema.",
            "RoBERTa validation is required before Phase 3 closure.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    reporting_data = pd.read_parquet(output_path, columns=["candidate", "vader_compound", "vader_label"])
    reporter = SentimentReporterView()
    reporter.render_vader_graphs(reporting_data, graph_dir)
    reporter.write_vader_report(manifest, report_path)
    return manifest


if __name__ == "__main__":
    result = run_phase3_vader(PROJECT_ROOT)
    print(json.dumps(result, indent=2))
