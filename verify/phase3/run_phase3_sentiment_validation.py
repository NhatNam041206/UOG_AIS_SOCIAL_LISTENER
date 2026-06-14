"""Calculate Phase 3 VADER/RoBERTa agreement and language-suitability metrics."""

from __future__ import annotations

import importlib.metadata
import json
import sys
from pathlib import Path
from typing import Any, Dict

import pandas as pd
from langdetect import DetectorFactory, LangDetectException, detect

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.phase3_sentiment.sentiment_validation_model import SentimentValidator


def run_phase3_sentiment_validation(project_root: str | Path = ".") -> Dict[str, Any]:
    """Audit language and calculate complete model-agreement metrics."""
    root = Path(project_root).resolve()
    sample_path = root / "output" / "results" / "phase3" / "sentiment_validation_sample.parquet"
    metrics_path = root / "output" / "results" / "phase3" / "sentiment_validation_metrics.json"
    disagreements_path = root / "output" / "results" / "phase3" / "sentiment_disagreements.json"
    report_path = root / "output" / "reports" / "phase3" / "sentiment_validation_report.md"

    dataframe = pd.read_parquet(sample_path)
    required_roberta = {
        "roberta_negative_probability",
        "roberta_neutral_probability",
        "roberta_positive_probability",
        "roberta_score",
        "roberta_label",
    }
    missing = sorted(required_roberta - set(dataframe.columns))
    if missing:
        raise ValueError(f"RoBERTa inference fields are missing: {missing}")

    DetectorFactory.seed = 0
    dataframe["detected_language"] = dataframe["tweet"].map(_detect_language)
    dataframe["models_agree"] = dataframe["vader_label"].eq(dataframe["roberta_label"])
    dataframe["absolute_score_difference"] = (
        dataframe["vader_compound"] - dataframe["roberta_score"]
    ).abs()
    dataframe.to_parquet(sample_path, index=False)

    validator = SentimentValidator()
    metrics = validator.validate(dataframe)
    language_counts = {
        str(key): int(value)
        for key, value in dataframe["detected_language"].value_counts(dropna=False).items()
    }
    top_disagreements = (
        dataframe.nlargest(50, "absolute_score_difference")[
            [
                "validation_source_row",
                "candidate",
                "date",
                "tweet",
                "detected_language",
                "vader_compound",
                "vader_label",
                "roberta_score",
                "roberta_label",
                "absolute_score_difference",
            ]
        ]
        .assign(date=lambda value: value["date"].astype(str))
        .to_dict(orient="records")
    )
    disagreements_path.write_text(json.dumps(top_disagreements, indent=2), encoding="utf-8")
    result: Dict[str, Any] = {
        "phase": "phase3_sentiment",
        "stage": "model_agreement_validation",
        "status": "completed",
        "sample_path": str(sample_path),
        "record_count": len(dataframe),
        "score_mapping": {
            "vader": "vader_compound",
            "roberta": "positive_probability - negative_probability",
        },
        "interpretation": "agreement between two models; RoBERTa is not human ground truth",
        "language_audit": {
            "method": "langdetect with deterministic seed 0",
            "version": importlib.metadata.version("langdetect"),
            "counts": language_counts,
            "likely_english_count": int(dataframe["detected_language"].eq("en").sum()),
            "likely_english_pct": float(100.0 * dataframe["detected_language"].eq("en").mean()),
        },
        "metrics": metrics,
        "top_disagreements_path": str(disagreements_path),
    }
    metrics_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    report_path.write_text(_render_report(result), encoding="utf-8")
    return result


def _detect_language(text: str) -> str:
    try:
        return detect(text)
    except LangDetectException:
        return "unknown"


def _render_report(result: Dict[str, Any]) -> str:
    overall = result["metrics"]["overall"]
    english = result["metrics"]["likely_english"]
    lines = [
        "# Phase 3 VADER and RoBERTa Agreement Validation Report",
        "",
        "## Interpretation Boundary",
        "",
        "These metrics measure agreement between VADER and RoBERTa. RoBERTa is not human ground truth, so the metrics must not be described as VADER accuracy.",
        "",
        "## Overall Agreement",
        "",
        "| Metric | Result |",
        "| --- | ---: |",
        f"| Records | {overall['record_count']:,} |",
        f"| Pearson r | {overall['pearson_r']:.4f} |",
        f"| Pearson 95% CI | [{overall['pearson_95_ci'][0]:.4f}, {overall['pearson_95_ci'][1]:.4f}] |",
        f"| Pearson p-value | {overall['pearson_p_value']:.4g} |",
        f"| Spearman rho | {overall['spearman_rho']:.4f} |",
        f"| Label agreement | {100.0 * overall['label_agreement_rate']:.2f}% |",
        f"| Macro-F1 agreement | {overall['macro_f1_agreement']:.4f} |",
        f"| Mean absolute score difference | {overall['mean_absolute_score_difference']:.4f} |",
        "",
        "## Language Suitability Audit",
        "",
        f"- Likely-English records: {result['language_audit']['likely_english_count']:,} "
        f"({result['language_audit']['likely_english_pct']:.2f}%).",
        "- Language identification uses deterministic `langdetect`; short social-media text may be misclassified.",
    ]
    if english:
        lines.extend(
            [
                f"- Likely-English Pearson r: {english['pearson_r']:.4f}.",
                f"- Likely-English label agreement: {100.0 * english['label_agreement_rate']:.2f}%.",
            ]
        )
    lines.extend(
        [
            "",
            "## Candidate-Level Agreement",
            "",
            "| Candidate stream | Records | Pearson r | Label agreement |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for candidate, metrics in result["metrics"]["candidate_metrics"].items():
        lines.append(
            f"| `{candidate}` | {metrics['record_count']:,} | {metrics['pearson_r']:.4f} | "
            f"{100.0 * metrics['label_agreement_rate']:.2f}% |"
        )
    lines.extend(
        [
            "",
            "## Disagreement Audit",
            "",
            f"The 50 records with the largest continuous-score differences are stored in `{result['top_disagreements_path']}` for qualitative review.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    output = run_phase3_sentiment_validation(PROJECT_ROOT)
    print(json.dumps(output, indent=2))

