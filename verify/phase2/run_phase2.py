"""Execute and verify Phase 2 preprocessing over Phase 1 Twitter outputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.phase2_preprocessing.cleaning_heuristics_model import CleaningPolicy
from src.phase2_preprocessing.preprocessing_runner_controller import PreprocessingRunnerController
from src.phase2_preprocessing.telemetry_reporter_view import TelemetryReporterView


def run_phase2(project_root: str | Path = ".") -> Dict[str, Any]:
    """Clean the Phase 1 Twitter streams and write auditable Phase 2 artifacts."""
    root = Path(project_root).resolve()
    interim = root / "data" / "02_interim"
    graph_dir = root / "output" / "graphs" / "phase2"
    report_dir = root / "output" / "reports" / "phase2"
    result_dir = root / "output" / "results" / "phase2"
    for directory in (interim, graph_dir, report_dir, result_dir):
        directory.mkdir(parents=True, exist_ok=True)

    sources = [
        interim / "twitter_donald_trump.parquet",
        interim / "twitter_joe_biden.parquet",
    ]
    missing_sources = [str(source) for source in sources if not source.exists()]
    if missing_sources:
        raise FileNotFoundError(f"Phase 1 Twitter outputs are missing: {missing_sources}")

    dataframe = pd.concat(
        [pd.read_parquet(source) for source in sources],
        ignore_index=True,
    )
    reporter = TelemetryReporterView()
    policy = CleaningPolicy()
    cleaned = PreprocessingRunnerController(reporter, policy).execute_dataframe(dataframe)
    destination = interim / "twitter_cleaned.parquet"
    cleaned.to_parquet(destination, index=False)

    metrics = reporter.stage_metrics
    manifest: Dict[str, Any] = {
        "phase": "phase2_preprocessing",
        "status": "completed",
        "input_paths": [str(source) for source in sources],
        "output_path": str(destination),
        "initial_record_count": len(dataframe),
        "final_record_count": len(cleaned),
        "retention_rate_pct": 0.0 if dataframe.empty else 100.0 * len(cleaned) / len(dataframe),
        "stage_metrics": metrics,
        "policy": {
            "minimum_account_age_days": policy.minimum_account_age_days,
            "maximum_tweets_per_day": policy.maximum_tweets_per_day,
            "duplicate_rule": "exact tweet text; first observed record retained",
            "text_rule": "remove HTML and URLs; preserve capitalization, punctuation, and emoji",
        },
        "account_age_rule_applied": policy.account_created_key in dataframe.columns,
        "notes": [
            "Bot volume is evaluated per user and UTC day across both candidate streams.",
            "The account-age rule is skipped when Phase 1 input lacks user_created_at.",
            "Exact duplicates are removed before text normalization.",
        ],
    }
    (result_dir / "preprocessing_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    _write_attrition_graph(metrics, graph_dir / "preprocessing_attrition.png")
    _write_report(manifest, report_dir / "preprocessing_report.md")
    return manifest


def _write_attrition_graph(metrics: Dict[str, Dict[str, Any]], destination: Path) -> None:
    """Write the single major Phase 2 data-quality figure."""
    rows = [
        {"Stage": "Input", "Records": next(iter(metrics.values()))["initial_count"]},
        *[
            {"Stage": stage.replace("_", " ").title(), "Records": values["final_count"]}
            for stage, values in metrics.items()
        ],
    ]
    dataframe = pd.DataFrame(rows)
    sns.set_theme(style="whitegrid", context="paper")
    figure, axis = plt.subplots(figsize=(8.0, 4.8))
    sns.barplot(data=dataframe, x="Stage", y="Records", color="#3977C3", errorbar=None, ax=axis)
    axis.set_title("Phase 2 Record Attrition by Cleaning Stage", weight="bold", pad=12)
    axis.set_xlabel("")
    axis.set_ylabel("Tweet records")
    axis.set_ylim(bottom=0)
    axis.ticklabel_format(axis="y", style="plain")
    axis.tick_params(axis="x", rotation=15)
    for container in axis.containers:
        axis.bar_label(container, labels=[f"{value:,.0f}" for value in container.datavalues], padding=3, fontsize=8)
    figure.text(
        0.01,
        0.01,
        "Source: Phase 1 aligned Twitter streams. Bars show retained records after each ordered Phase 2 rule.",
        fontsize=7.5,
        color="#555555",
    )
    figure.tight_layout(rect=(0, 0.06, 1, 1))
    figure.savefig(destination, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def _write_report(manifest: Dict[str, Any], destination: Path) -> None:
    metrics = manifest["stage_metrics"]
    lines = [
        "# Phase 2 Preprocessing Report",
        "",
        "## Summary",
        "",
        f"- Initial records: {manifest['initial_record_count']:,}.",
        f"- Final records: {manifest['final_record_count']:,}.",
        f"- Overall retention: {manifest['retention_rate_pct']:.2f}%.",
        "",
        "## Stage Results",
        "",
        "| Stage | Initial | Retained | Dropped | Drop rate |",
        "|---|---:|---:|---:|---:|",
    ]
    for stage, values in metrics.items():
        lines.append(
            f"| {stage} | {values['initial_count']:,} | {values['final_count']:,} | "
            f"{values['dropped_count']:,} | {values['drop_rate_pct']:.2f}% |"
        )
    lines.extend(
        [
            "",
            "## Major Figure",
            "",
            "- `output/graphs/phase2/preprocessing_attrition.png` shows retained records after each ordered rule and makes the effect of bot filtering, exact deduplication, and invalid-text rejection auditable.",
            "",
            "## Method and Limitations",
            "",
            "- Users exceeding 50 records on a UTC day are rejected for that day.",
            "- Exact duplicate tweet text is removed before normalization; the first observation is retained.",
            "- HTML and URLs are removed while capitalization, punctuation, and emoji are retained for VADER.",
            (
                "- The account-age rule was applied."
                if manifest["account_age_rule_applied"]
                else "- The account-age rule could not be applied because Phase 1 interim files do not contain `user_created_at`; Phase 1 was intentionally left unchanged."
            ),
        ]
    )
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    result = run_phase2(PROJECT_ROOT)
    print(json.dumps(result, indent=2))
