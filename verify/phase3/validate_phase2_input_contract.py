"""Validate the Phase 2 cleaned Twitter dataset before Phase 3 sentiment scoring."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import pyarrow.parquet as pq


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


REQUIRED_COLUMNS = {
    "id": "string",
    "date": "timestamp",
    "tweet": "string",
    "user_id": "string",
    "user_loc": "string",
    "retweets": "double",
    "replies": "null",
    "candidate": "string",
    "source_file": "string",
}
NON_NULL_COLUMNS = ("tweet", "date", "candidate")
EXPECTED_CANDIDATES = {"donald_trump", "joe_biden"}
INVALID_UNICODE_PATTERN = re.compile(r"[\ud800-\udfff\ufffd]")


def validate_phase2_input_contract(project_root: str | Path = ".") -> Dict[str, Any]:
    """Validate and report the Phase 2 output contract required by Phase 3."""
    root = Path(project_root).resolve()
    dataset_path = root / "data" / "02_interim" / "twitter_cleaned.parquet"
    phase2_manifest_path = root / "output" / "results" / "phase2" / "preprocessing_manifest.json"
    result_path = root / "output" / "results" / "phase3" / "phase2_input_contract_validation.json"
    report_path = root / "output" / "reports" / "phase3" / "phase2_input_contract_validation.md"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    checks: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    _record(checks, "cleaned_dataset_exists", dataset_path.exists(), str(dataset_path))
    _record(checks, "phase2_manifest_exists", phase2_manifest_path.exists(), str(phase2_manifest_path))
    if not dataset_path.exists() or not phase2_manifest_path.exists():
        return _finish(
            dataset_path,
            phase2_manifest_path,
            checks,
            warnings,
            {},
            result_path,
            report_path,
        )

    manifest = json.loads(phase2_manifest_path.read_text(encoding="utf-8"))
    parquet_file = pq.ParquetFile(dataset_path)
    schema = parquet_file.schema_arrow
    schema_types = {field.name: str(field.type) for field in schema}
    row_count = parquet_file.metadata.num_rows

    _record(
        checks,
        "phase2_manifest_completed",
        manifest.get("status") == "completed",
        f"status={manifest.get('status')!r}",
    )
    _record(
        checks,
        "row_count_matches_manifest",
        row_count == manifest.get("final_record_count"),
        f"parquet={row_count:,}; manifest={manifest.get('final_record_count'):,}",
    )
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(schema_types))
    _record(
        checks,
        "required_columns_present",
        not missing_columns,
        "none missing" if not missing_columns else f"missing={missing_columns}",
    )
    incompatible_types = {
        name: {"expected": expected, "actual": schema_types.get(name)}
        for name, expected in REQUIRED_COLUMNS.items()
        if name in schema_types and not schema_types[name].startswith(expected)
    }
    _record(
        checks,
        "required_column_types_compatible",
        not incompatible_types,
        "all compatible" if not incompatible_types else f"incompatible={incompatible_types}",
    )

    dataframe = pd.read_parquet(dataset_path)
    null_counts = {column: int(dataframe[column].isna().sum()) for column in dataframe.columns}
    required_nulls = {column: null_counts[column] for column in NON_NULL_COLUMNS if null_counts[column]}
    _record(
        checks,
        "phase3_required_values_non_null",
        not required_nulls,
        "no required nulls" if not required_nulls else f"nulls={required_nulls}",
    )

    tweet_text = dataframe["tweet"].astype("string")
    blank_count = int(tweet_text.str.strip().eq("").sum())
    invalid_unicode_count = int(
        tweet_text.map(lambda value: bool(INVALID_UNICODE_PATTERN.search(value)) if pd.notna(value) else False).sum()
    )
    _record(checks, "tweet_text_non_empty", blank_count == 0, f"blank_count={blank_count:,}")
    _record(
        checks,
        "tweet_text_has_valid_unicode",
        invalid_unicode_count == 0,
        f"invalid_unicode_count={invalid_unicode_count:,}",
    )

    dates = pd.to_datetime(dataframe["date"], utc=True, errors="coerce")
    invalid_date_count = int(dates.isna().sum())
    _record(checks, "timestamps_valid_and_utc", invalid_date_count == 0, f"invalid_count={invalid_date_count:,}")

    candidates = set(dataframe["candidate"].dropna().astype(str).unique())
    unexpected_candidates = sorted(candidates - EXPECTED_CANDIDATES)
    missing_candidates = sorted(EXPECTED_CANDIDATES - candidates)
    _record(
        checks,
        "candidate_values_expected",
        not unexpected_candidates and not missing_candidates,
        f"observed={sorted(candidates)}; unexpected={unexpected_candidates}; missing={missing_candidates}",
    )

    strata = dataframe.assign(_utc_day=dates.dt.floor("D")).groupby(["candidate", "_utc_day"]).size()
    _record(
        checks,
        "candidate_day_strata_available",
        len(strata) > 0 and int(strata.min()) > 0,
        f"strata={len(strata)}; minimum_records={int(strata.min()):,}",
    )

    exact_duplicate_count = int(dataframe["tweet"].duplicated(keep="first").sum())
    long_text_count = int(tweet_text.str.len().gt(512).sum())
    blank_user_location_count = int(dataframe["user_loc"].astype("string").str.strip().eq("").sum())
    nullable_summary = {column: null_counts[column] for column in ("user_loc", "replies")}
    _warn(
        warnings,
        "post_cleaning_exact_duplicate_text",
        exact_duplicate_count > 0,
        f"count={exact_duplicate_count:,}; permitted because Phase 2 deduplicates before text normalization",
    )
    _warn(
        warnings,
        "long_text_truncation_risk",
        long_text_count > 0,
        f"records_over_512_characters={long_text_count:,}; token-level truncation must be measured during RoBERTa inference",
    )
    _warn(
        warnings,
        "known_nullable_source_fields",
        any(nullable_summary.values()),
        f"null_counts={nullable_summary}",
    )
    _warn(
        warnings,
        "blank_user_locations",
        blank_user_location_count > 0,
        f"count={blank_user_location_count:,}; treat blank strings as missing during Phase 4 spatial mapping",
    )

    metrics = {
        "dataset_path": str(dataset_path),
        "phase2_manifest_path": str(phase2_manifest_path),
        "row_count": row_count,
        "column_count": len(schema_types),
        "schema": schema_types,
        "null_counts": null_counts,
        "date_min_utc": dates.min().isoformat(),
        "date_max_utc": dates.max().isoformat(),
        "candidate_counts": {
            str(key): int(value)
            for key, value in dataframe["candidate"].value_counts(dropna=False).items()
        },
        "candidate_day_strata": len(strata),
        "minimum_stratum_records": int(strata.min()),
        "maximum_stratum_records": int(strata.max()),
        "exact_duplicate_text_count_after_cleaning": exact_duplicate_count,
        "records_over_512_characters": long_text_count,
        "blank_user_location_count": blank_user_location_count,
    }
    return _finish(
        dataset_path,
        phase2_manifest_path,
        checks,
        warnings,
        metrics,
        result_path,
        report_path,
    )


def _record(checks: List[Dict[str, Any]], name: str, passed: bool, detail: str) -> None:
    checks.append({"name": name, "status": "passed" if passed else "failed", "detail": detail})


def _warn(warnings: List[Dict[str, Any]], name: str, active: bool, detail: str) -> None:
    warnings.append({"name": name, "status": "warning" if active else "clear", "detail": detail})


def _finish(
    dataset_path: Path,
    manifest_path: Path,
    checks: List[Dict[str, Any]],
    warnings: List[Dict[str, Any]],
    metrics: Dict[str, Any],
    result_path: Path,
    report_path: Path,
) -> Dict[str, Any]:
    failed = [check for check in checks if check["status"] == "failed"]
    result = {
        "phase": "phase3_input_contract",
        "status": "passed" if not failed else "failed",
        "dataset_path": str(dataset_path),
        "phase2_manifest_path": str(manifest_path),
        "checks": checks,
        "warnings": warnings,
        "metrics": metrics,
    }
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    report_path.write_text(_render_report(result), encoding="utf-8")
    return result


def _render_report(result: Dict[str, Any]) -> str:
    metrics = result["metrics"]
    lines = [
        "# Phase 3 Entry Gate: Phase 2 Input Contract Validation",
        "",
        f"Overall status: **{result['status'].upper()}**",
        "",
        "## Contract Checks",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for check in result["checks"]:
        lines.append(f"| `{check['name']}` | {check['status']} | {check['detail']} |")
    lines.extend(["", "## Reported Warnings", "", "| Item | Status | Detail |", "| --- | --- | --- |"])
    for warning in result["warnings"]:
        lines.append(f"| `{warning['name']}` | {warning['status']} | {warning['detail']} |")
    if metrics:
        lines.extend(
            [
                "",
                "## Dataset Summary",
                "",
                f"- Records: {metrics['row_count']:,}",
                f"- Columns: {metrics['column_count']}",
                f"- UTC coverage: {metrics['date_min_utc']} through {metrics['date_max_utc']}",
                f"- Candidate counts: `{metrics['candidate_counts']}`",
                f"- Candidate-by-day strata: {metrics['candidate_day_strata']}",
                f"- Stratum size range: {metrics['minimum_stratum_records']:,} to {metrics['maximum_stratum_records']:,}",
                "",
                "## Entry Decision",
                "",
                (
                    "The Phase 2 cleaned dataset satisfies the Phase 3 input contract and may proceed to sentiment scoring."
                    if result["status"] == "passed"
                    else "The Phase 2 cleaned dataset does not satisfy the Phase 3 input contract. Resolve failed checks before sentiment scoring."
                ),
            ]
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    validation = validate_phase2_input_contract(PROJECT_ROOT)
    print(json.dumps(validation, indent=2))
    raise SystemExit(0 if validation["status"] == "passed" else 1)
