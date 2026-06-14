"""Generate final Phase 3 figures and verify the complete phase for closure."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

import matplotlib

matplotlib.use("Agg")

import pandas as pd
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.phase3_sentiment.sentiment_reporter_view import SentimentReporterView


def close_phase3(project_root: str | Path = ".") -> Dict[str, Any]:
    """Render final figures, reconcile artifacts, and write Phase 3 closure evidence."""
    root = Path(project_root).resolve()
    result_dir = root / "output" / "results" / "phase3"
    report_dir = root / "output" / "reports" / "phase3"
    graph_dir = root / "output" / "graphs" / "phase3"
    sample_path = result_dir / "sentiment_validation_sample.parquet"
    metrics_path = result_dir / "sentiment_validation_metrics.json"
    sentiment_manifest_path = result_dir / "sentiment_manifest.json"
    completion_manifest_path = result_dir / "phase3_completion_manifest.json"
    completion_report_path = report_dir / "phase3_completion_report.md"

    sample = pd.read_parquet(sample_path)
    validation = json.loads(metrics_path.read_text(encoding="utf-8"))
    sentiment_manifest = json.loads(sentiment_manifest_path.read_text(encoding="utf-8"))
    SentimentReporterView().render_validation_graphs(sample, validation["metrics"], graph_dir)

    required_paths = [
        root / "data/02_interim/twitter_sentiment.parquet",
        result_dir / "phase2_input_contract_validation.json",
        result_dir / "sentiment_manifest.json",
        result_dir / "vader_output_validation.json",
        result_dir / "sentiment_validation_sample.parquet",
        result_dir / "validation_sample_manifest.json",
        result_dir / "roberta_setup_validation.json",
        result_dir / "roberta_inference_manifest.json",
        result_dir / "sentiment_validation_metrics.json",
        result_dir / "sentiment_disagreements.json",
        graph_dir / "vader_sentiment_distribution.png",
        graph_dir / "sentiment_distribution_by_candidate.png",
        graph_dir / "vader_roberta_score_comparison.png",
        graph_dir / "vader_roberta_confusion_matrix.png",
    ]
    vader_output = pq.ParquetFile(root / "data/02_interim/twitter_sentiment.parquet")
    required_roberta = [
        "roberta_negative_probability",
        "roberta_neutral_probability",
        "roberta_positive_probability",
        "roberta_score",
        "roberta_label",
        "models_agree",
        "absolute_score_difference",
    ]
    checks = {
        "all_required_artifacts_exist": all(path.exists() for path in required_paths),
        "full_sentiment_dataset_matches_vader_manifest": (
            vader_output.metadata.num_rows == sentiment_manifest["output_record_count"] == 1_331_317
        ),
        "validation_sample_has_5000_records": len(sample) == 5_000,
        "validation_fields_complete": not bool(sample[required_roberta].isna().any().any()),
        "pearson_metric_available": validation["metrics"]["overall"]["pearson_r"] is not None,
        "all_four_approved_figures_exist": all(path.exists() for path in required_paths[-4:]),
        "phase4_input_schema_available": all(
            column in vader_output.schema_arrow.names
            for column in ["date", "candidate", "user_loc", "vader_compound", "vader_label"]
        ),
    }
    sentiment_manifest["validation_status"] = "roberta_validation_completed"
    sentiment_manifest["phase_status"] = "completed" if all(checks.values()) else "closure_failed"
    sentiment_manifest["validation_summary"] = {
        "sample_record_count": len(sample),
        "pearson_r": validation["metrics"]["overall"]["pearson_r"],
        "pearson_95_ci": validation["metrics"]["overall"]["pearson_95_ci"],
        "label_agreement_rate": validation["metrics"]["overall"]["label_agreement_rate"],
        "likely_english_pct": validation["language_audit"]["likely_english_pct"],
    }
    sentiment_manifest_path.write_text(json.dumps(sentiment_manifest, indent=2), encoding="utf-8")

    completion: Dict[str, Any] = {
        "phase": "phase3_sentiment",
        "status": "completed" if all(checks.values()) else "failed",
        "checks": checks,
        "full_sentiment_record_count": vader_output.metadata.num_rows,
        "validation_sample_record_count": len(sample),
        "headline_metrics": sentiment_manifest["validation_summary"],
        "phase4_input_path": str(root / "data/02_interim/twitter_sentiment.parquet"),
        "known_limitations": [
            "RoBERTa is a comparison model, not human ground truth.",
            "The deterministic language audit estimates 68.72% likely English and can misclassify short tweets.",
            "The models show moderate agreement and are not interchangeable.",
            "Spatial mapping must treat blank user locations as missing.",
        ],
    }
    completion_manifest_path.write_text(json.dumps(completion, indent=2), encoding="utf-8")
    completion_report_path.write_text(_render_report(completion), encoding="utf-8")
    if completion["status"] != "completed":
        raise ValueError("Phase 3 closure checks failed")
    return completion


def _render_report(completion: Dict[str, Any]) -> str:
    metrics = completion["headline_metrics"]
    lines = [
        "# Phase 3 Completion Report: Hybrid Sentiment Extraction and Validation",
        "",
        f"Phase status: **{completion['status'].upper()}**",
        "",
        "## Completed Work",
        "",
        "- Validated the Phase 2 cleaned-data input contract.",
        "- Scored all 1,331,317 cleaned tweets with VADER.",
        "- Created a reproducible proportional 5,000-record candidate-by-UTC-day sample.",
        "- Scored all sampled tweets with the configured Twitter-RoBERTa model.",
        "- Calculated continuous-score, label-agreement, subgroup, language, and disagreement metrics.",
        "- Generated the four approved Phase 3 research figures.",
        "",
        "## Headline Results",
        "",
        "| Measure | Result |",
        "| --- | ---: |",
        f"| Full sentiment records | {completion['full_sentiment_record_count']:,} |",
        f"| Validation sample records | {completion['validation_sample_record_count']:,} |",
        f"| Pearson r | {metrics['pearson_r']:.4f} |",
        f"| Pearson 95% CI | [{metrics['pearson_95_ci'][0]:.4f}, {metrics['pearson_95_ci'][1]:.4f}] |",
        f"| Label agreement | {100.0 * metrics['label_agreement_rate']:.2f}% |",
        f"| Likely-English sample share | {metrics['likely_english_pct']:.2f}% |",
        "",
        "## Closure Checks",
        "",
        "| Check | Result |",
        "| --- | --- |",
    ]
    for name, passed in completion["checks"].items():
        lines.append(f"| `{name}` | {'passed' if passed else 'failed'} |")
    lines.extend(["", "## Interpretation and Limitations", ""])
    for limitation in completion["known_limitations"]:
        lines.append(f"- {limitation}")
    lines.extend(
        [
            "",
            "## Phase 4 Readiness",
            "",
            f"The sentiment-enriched dataset at `{completion['phase4_input_path']}` is verified as the primary Twitter input for Phase 4 spatial-temporal aggregation.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    result = close_phase3(PROJECT_ROOT)
    print(json.dumps(result, indent=2))
