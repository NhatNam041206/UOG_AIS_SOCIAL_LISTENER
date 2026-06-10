"""Execute and verify Phase 2 preprocessing over Phase 1 Twitter outputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

import matplotlib

matplotlib.use("Agg")

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.phase2_preprocessing.cleaning_heuristics_model import CleaningPolicy
from src.phase2_preprocessing.preprocessing_runner_controller import PreprocessingRunnerController
from src.phase2_preprocessing.telemetry_reporter_view import TelemetryReporterView
from src.phase2_preprocessing.user_activity_audit_model import UserActivityAuditor
from src.phase2_preprocessing.user_activity_audit_view import UserActivityAuditView


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
    auditor = UserActivityAuditor()
    audit = auditor.audit(dataframe)
    audit_view = UserActivityAuditView()
    audit_view.render_graphs(dataframe, audit, graph_dir)
    audit_view.write_report(
        audit,
        report_dir / "user_activity_threshold_report.md",
    )
    audit.user_metrics.to_parquet(
        result_dir / "user_activity_metrics.parquet",
        index=False,
    )
    audit_manifest = {
        "metric": auditor.METRIC,
        "selected_threshold": audit.selected_threshold,
        "selection_reason": audit.selection_reason,
        "candidate_thresholds": audit.candidate_thresholds,
        "tradeoffs": json.loads(audit.tradeoffs.to_json(orient="records")),
    }
    (result_dir / "user_activity_threshold_audit.json").write_text(
        json.dumps(audit_manifest, indent=2),
        encoding="utf-8",
    )

    reporter = TelemetryReporterView()
    policy = CleaningPolicy(maximum_tweets_per_active_day=audit.selected_threshold)
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
            "activity_metric": auditor.METRIC,
            "maximum_tweets_per_active_day": policy.maximum_tweets_per_active_day,
            "duplicate_rule": "exact tweet text; first observed record retained",
            "text_rule": "remove HTML and URLs; preserve capitalization, punctuation, and emoji",
        },
        "user_activity_audit": audit_manifest,
        "account_age_rule_applied": policy.account_created_key in dataframe.columns,
        "notes": [
            "High-volume users are evaluated using the empirically selected tweets-per-active-day threshold.",
            "The account-age rule is skipped when Phase 1 input lacks user_created_at.",
            "Exact duplicates are removed before text normalization.",
        ],
    }
    (result_dir / "preprocessing_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    _write_report(manifest, report_dir / "preprocessing_report.md")
    return manifest


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
            "## User-Activity Audit",
            "",
            f"- Selected threshold: `{manifest['policy']['maximum_tweets_per_active_day']:.3f}` tweets per active day.",
            "- Full decision evidence: `output/reports/phase2/user_activity_threshold_report.md`.",
            "- Reproducible metrics: `output/results/phase2/user_activity_metrics.parquet` and `output/results/phase2/user_activity_threshold_audit.json`.",
            "",
            "## Method and Limitations",
            "",
            "- All records from users exceeding the selected empirical tweets-per-active-day threshold are rejected.",
            "- Exact duplicate tweet text is removed before normalization; the first observation is retained.",
            "- HTML and URLs are removed while capitalization, punctuation, and emoji are retained for VADER.",
            "- No Phase 5 ITSA, OLS, model-performance, or robustness output is produced by this Phase 2 workflow.",
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
