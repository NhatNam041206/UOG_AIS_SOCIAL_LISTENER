"""Create and verify the Phase 3 stratified model-validation sample."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.phase3_sentiment.validation_sampler_model import ValidationSampler
from verify.phase3.validate_vader_output import validate_vader_output


def run_phase3_validation_sample(
    project_root: str | Path = ".",
    sample_size: int = 5_000,
    random_seed: int = 2020,
) -> Dict[str, Any]:
    """Write the reproducible candidate-by-UTC-day validation sample."""
    root = Path(project_root).resolve()
    input_path = root / "data" / "02_interim" / "twitter_sentiment.parquet"
    sample_path = root / "output" / "results" / "phase3" / "sentiment_validation_sample.parquet"
    manifest_path = root / "output" / "results" / "phase3" / "validation_sample_manifest.json"
    report_path = root / "output" / "reports" / "phase3" / "validation_sample_report.md"
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    vader_validation = validate_vader_output(root)
    if vader_validation["status"] != "passed":
        raise ValueError("VADER output validation must pass before sampling")

    dataframe = pd.read_parquet(input_path)
    sampler = ValidationSampler(sample_size=sample_size, random_seed=random_seed)
    result = sampler.sample(dataframe)
    result.sample.to_parquet(sample_path, index=False)

    allocation_records = json.loads(
        result.allocation.assign(
            validation_utc_day=result.allocation["validation_utc_day"].astype(str)
        ).to_json(orient="records")
    )
    candidate_source = dataframe["candidate"].value_counts().sort_index()
    candidate_sample = result.sample["candidate"].value_counts().sort_index()
    candidate_summary = {
        candidate: {
            "source_records": int(candidate_source[candidate]),
            "source_share_pct": 100.0 * int(candidate_source[candidate]) / len(dataframe),
            "sample_records": int(candidate_sample[candidate]),
            "sample_share_pct": 100.0 * int(candidate_sample[candidate]) / len(result.sample),
        }
        for candidate in candidate_source.index
    }
    stored = pq.ParquetFile(sample_path)
    checks = {
        "sample_size_exact": len(result.sample) == sample_size,
        "source_rows_unique": result.sample[ValidationSampler.SOURCE_ROW_COLUMN].is_unique,
        "all_source_rows_in_range": bool(
            result.sample[ValidationSampler.SOURCE_ROW_COLUMN].between(0, len(dataframe) - 1).all()
        ),
        "all_source_strata_represented": len(result.allocation)
        == result.sample.groupby(["candidate", ValidationSampler.UTC_DAY_COLUMN]).ngroups,
        "allocation_matches_sample": bool(
            result.sample.groupby(["candidate", ValidationSampler.UTC_DAY_COLUMN]).size().sort_index().equals(
                result.allocation.set_index(["candidate", ValidationSampler.UTC_DAY_COLUMN])[
                    "allocated_records"
                ].sort_index()
            )
        ),
        "stored_row_count_matches": stored.metadata.num_rows == sample_size,
        "stored_checksum_matches": ValidationSampler.checksum(
            pd.read_parquet(sample_path, columns=[ValidationSampler.SOURCE_ROW_COLUMN])[
                ValidationSampler.SOURCE_ROW_COLUMN
            ]
        )
        == result.checksum_sha256,
    }
    manifest: Dict[str, Any] = {
        "phase": "phase3_sentiment",
        "stage": "stratified_validation_sampling",
        "status": "completed" if all(checks.values()) else "failed",
        "input_path": str(input_path),
        "output_path": str(sample_path),
        "source_record_count": len(dataframe),
        "sample_record_count": len(result.sample),
        "sample_size_requested": sample_size,
        "random_seed": random_seed,
        "strata": ["candidate", "UTC date"],
        "allocation_method": "proportional Hamilton largest-remainder allocation",
        "source_strata_count": len(result.allocation),
        "sample_strata_count": result.sample.groupby(
            ["candidate", ValidationSampler.UTC_DAY_COLUMN]
        ).ngroups,
        "sample_checksum_sha256": result.checksum_sha256,
        "candidate_summary": candidate_summary,
        "checks": checks,
        "allocation": allocation_records,
        "notes": [
            "Sampling is proportional to candidate-by-UTC-day source volume.",
            "The fixed seed and source-row checksum make the sample reproducible.",
            "Sampling is not stratified by VADER labels because VADER is the model being validated.",
            "RoBERTa inference has not yet been applied.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    report_path.write_text(_render_report(manifest), encoding="utf-8")
    if manifest["status"] != "completed":
        raise ValueError("Validation sample checks failed")
    return manifest


def _render_report(manifest: Dict[str, Any]) -> str:
    lines = [
        "# Phase 3 Stratified Validation Sample Report",
        "",
        "## Stage Status",
        "",
        f"- Status: **{manifest['status']}**.",
        f"- Source records: {manifest['source_record_count']:,}.",
        f"- Sample records: {manifest['sample_record_count']:,}.",
        f"- Random seed: `{manifest['random_seed']}`.",
        f"- Sample checksum: `{manifest['sample_checksum_sha256']}`.",
        "",
        "## Method",
        "",
        "- Strata: candidate stream by UTC date.",
        "- Allocation: proportional Hamilton largest-remainder allocation.",
        "- Selection: random without replacement using a fixed seed.",
        "- VADER labels are not used for stratification because VADER is the model being validated.",
        "",
        "## Candidate Representation",
        "",
        "| Candidate stream | Source records | Source share | Sample records | Sample share |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for candidate, values in manifest["candidate_summary"].items():
        lines.append(
            f"| `{candidate}` | {values['source_records']:,} | {values['source_share_pct']:.2f}% | "
            f"{values['sample_records']:,} | {values['sample_share_pct']:.2f}% |"
        )
    lines.extend(
        [
            "",
            "## Verification Checks",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
    )
    for name, passed in manifest["checks"].items():
        lines.append(f"| `{name}` | {'passed' if passed else 'failed'} |")
    lines.extend(
        [
            "",
            "## Decision",
            "",
            "The validation sample is reproducible and preserves candidate-by-day source representation. It is ready for RoBERTa inference.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    output = run_phase3_validation_sample(PROJECT_ROOT)
    print(json.dumps(output, indent=2))

