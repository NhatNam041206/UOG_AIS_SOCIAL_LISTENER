"""Validate the full-dataset VADER output before later Phase 3 stages."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import pyarrow.parquet as pq


SOURCE_COLUMNS = (
    "id",
    "date",
    "tweet",
    "user_id",
    "user_loc",
    "retweets",
    "replies",
    "candidate",
    "source_file",
)
VADER_COLUMNS = (
    "vader_negative",
    "vader_neutral",
    "vader_positive",
    "vader_compound",
    "vader_label",
)
EXPECTED_LABELS = {"negative", "neutral", "positive"}


def validate_vader_output(project_root: str | Path = ".") -> Dict[str, Any]:
    """Validate schema preservation and all approved VADER output invariants."""
    root = Path(project_root).resolve()
    input_path = root / "data" / "02_interim" / "twitter_cleaned.parquet"
    output_path = root / "data" / "02_interim" / "twitter_sentiment.parquet"
    result_path = root / "output" / "results" / "phase3" / "vader_output_validation.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    checks: List[Dict[str, Any]] = []

    _record(checks, "phase2_cleaned_input_exists", input_path.exists(), str(input_path))
    _record(checks, "vader_output_exists", output_path.exists(), str(output_path))
    if not input_path.exists() or not output_path.exists():
        return _finish(checks, {}, result_path)

    source = pq.ParquetFile(input_path)
    output = pq.ParquetFile(output_path)
    source_schema = source.schema_arrow.names
    output_schema = output.schema_arrow.names
    _record(
        checks,
        "row_count_preserved",
        source.metadata.num_rows == output.metadata.num_rows,
        f"input={source.metadata.num_rows:,}; output={output.metadata.num_rows:,}",
    )
    _record(
        checks,
        "source_schema_preserved",
        output_schema[: len(source_schema)] == source_schema,
        f"source_columns={len(source_schema)}; output_prefix_columns={len(output_schema[:len(source_schema)])}",
    )
    _record(
        checks,
        "approved_vader_schema_appended",
        output_schema[len(source_schema) :] == list(VADER_COLUMNS),
        f"appended={output_schema[len(source_schema):]}",
    )

    dataframe = pd.read_parquet(output_path, columns=list(VADER_COLUMNS))
    null_counts = {column: int(dataframe[column].isna().sum()) for column in VADER_COLUMNS}
    _record(
        checks,
        "vader_fields_complete",
        not any(null_counts.values()),
        f"null_counts={null_counts}",
    )
    component_columns = ["vader_negative", "vader_neutral", "vader_positive"]
    component_min = float(dataframe[component_columns].min().min())
    component_max = float(dataframe[component_columns].max().max())
    _record(
        checks,
        "vader_components_in_unit_interval",
        component_min >= 0.0 and component_max <= 1.0,
        f"minimum={component_min}; maximum={component_max}",
    )
    compound_min = float(dataframe["vader_compound"].min())
    compound_max = float(dataframe["vader_compound"].max())
    _record(
        checks,
        "vader_compound_in_expected_range",
        compound_min >= -1.0 and compound_max <= 1.0,
        f"minimum={compound_min}; maximum={compound_max}",
    )
    component_sum_error = float((dataframe[component_columns].sum(axis=1) - 1.0).abs().max())
    _record(
        checks,
        "vader_component_sums_within_rounding_tolerance",
        component_sum_error <= 0.0011,
        f"maximum_absolute_error={component_sum_error}",
    )
    observed_labels = set(dataframe["vader_label"].astype(str).unique())
    _record(
        checks,
        "vader_labels_expected",
        bool(observed_labels) and observed_labels.issubset(EXPECTED_LABELS),
        f"observed={sorted(observed_labels)}",
    )
    expected = pd.Series("neutral", index=dataframe.index)
    expected.loc[dataframe["vader_compound"].le(-0.05)] = "negative"
    expected.loc[dataframe["vader_compound"].ge(0.05)] = "positive"
    label_mismatches = int(expected.ne(dataframe["vader_label"]).sum())
    _record(
        checks,
        "vader_labels_match_compound_thresholds",
        label_mismatches == 0,
        f"mismatches={label_mismatches:,}",
    )

    metrics = {
        "input_record_count": source.metadata.num_rows,
        "output_record_count": output.metadata.num_rows,
        "output_column_count": len(output_schema),
        "output_row_groups": output.metadata.num_row_groups,
        "null_counts": null_counts,
        "component_min": component_min,
        "component_max": component_max,
        "compound_min": compound_min,
        "compound_max": compound_max,
        "component_sum_maximum_absolute_error": component_sum_error,
        "label_mismatches": label_mismatches,
    }
    return _finish(checks, metrics, result_path)


def _record(checks: List[Dict[str, Any]], name: str, passed: bool, detail: str) -> None:
    checks.append({"name": name, "status": "passed" if passed else "failed", "detail": detail})


def _finish(
    checks: List[Dict[str, Any]],
    metrics: Dict[str, Any],
    result_path: Path,
) -> Dict[str, Any]:
    result = {
        "phase": "phase3_sentiment",
        "stage": "vader_output_validation",
        "status": "passed" if all(check["status"] == "passed" for check in checks) else "failed",
        "checks": checks,
        "metrics": metrics,
    }
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    validation = validate_vader_output(Path(__file__).resolve().parents[2])
    print(json.dumps(validation, indent=2))
    raise SystemExit(0 if validation["status"] == "passed" else 1)
