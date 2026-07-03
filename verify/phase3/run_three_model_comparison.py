"""Compare VADER, baseline RoBERTa, and Cardiff latest RoBERTa on a sample."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import sys
from pathlib import Path
from typing import Any, Dict

import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import f1_score

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.phase3_sentiment.sentiment_models_model import (
    DEFAULT_TWITTER_ROBERTA_MODEL_ID,
    RobertaSentimentModel,
)


BASELINE_ROBERTA_MODEL_ID = "cardiffnlp/twitter-roberta-base-sentiment"
CARDIFF_LATEST_MODEL_ID = DEFAULT_TWITTER_ROBERTA_MODEL_ID
LABELS = list(RobertaSentimentModel.LABELS)


def run_three_model_comparison(
    project_root: str | Path = ".",
    input_path: str | Path | None = None,
    sample_size: int = 100,
    full_dataset: bool = False,
    seed: int = 2020,
    batch_size: int = 16,
    maximum_token_length: int = 512,
    device: str = "auto",
    baseline_model_id: str = BASELINE_ROBERTA_MODEL_ID,
    cardiff_model_id: str = CARDIFF_LATEST_MODEL_ID,
) -> Dict[str, Any]:
    """Sample the sentiment dataset and compare all three sentiment models."""
    if not full_dataset and sample_size <= 0:
        raise ValueError("sample_size must be positive")
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    root = Path(project_root).resolve()
    source_path = Path(input_path or root / "data" / "02_interim" / "twitter_sentiment.parquet")
    if not source_path.exists():
        raise FileNotFoundError(f"Input dataset is missing: {source_path}")

    result_dir = root / "output" / "results" / "phase3"
    report_dir = root / "output" / "reports" / "phase3"
    result_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    sample_output_path = result_dir / "three_model_comparison_sample.parquet"
    metrics_path = result_dir / "three_model_comparison_metrics.json"
    report_path = report_dir / "three_model_comparison_report.md"

    dataframe = pd.read_parquet(source_path)
    required = {"tweet", "vader_compound", "vader_label"}
    missing = sorted(required - set(dataframe.columns))
    if missing:
        raise ValueError(f"Required comparison columns are missing: {missing}")

    sample = select_comparison_records(dataframe, sample_size, seed, full_dataset)
    resolved_device = resolve_device(device)

    baseline_model = RobertaSentimentModel.load(
        model_id=baseline_model_id,
        maximum_token_length=maximum_token_length,
        device=resolved_device,
    )
    baseline_scores = _prefix_scores(
        pd.DataFrame(baseline_model.score_many(sample["tweet"].tolist(), batch_size=batch_size)),
        "baseline_roberta",
    )

    cardiff_model = RobertaSentimentModel.load(
        model_id=cardiff_model_id,
        maximum_token_length=maximum_token_length,
        device=resolved_device,
    )
    cardiff_scores = _prefix_scores(
        pd.DataFrame(cardiff_model.score_many(sample["tweet"].tolist(), batch_size=batch_size)),
        "cardiff_roberta",
    )

    scored = pd.concat([sample, baseline_scores, cardiff_scores], axis=1)
    scored["vader_baseline_roberta_label_agree"] = scored["vader_label"].eq(
        scored["baseline_roberta_label"]
    )
    scored["vader_cardiff_roberta_label_agree"] = scored["vader_label"].eq(
        scored["cardiff_roberta_label"]
    )
    scored["baseline_cardiff_roberta_label_agree"] = scored["baseline_roberta_label"].eq(
        scored["cardiff_roberta_label"]
    )
    scored["all_three_labels_agree"] = (
        scored["vader_label"].eq(scored["baseline_roberta_label"])
        & scored["vader_label"].eq(scored["cardiff_roberta_label"])
    )
    scored.to_parquet(sample_output_path, index=False)

    result: Dict[str, Any] = {
        "phase": "phase3_sentiment",
        "stage": "three_model_comparison",
        "status": "completed",
        "input_path": str(source_path),
        "sample_output_path": str(sample_output_path),
        "run_mode": "full" if full_dataset else "sample",
        "sample_size_requested": None if full_dataset else sample_size,
        "sample_size_used": len(scored),
        "seed": seed,
        "device_requested": device,
        "device_used": resolved_device,
        "batch_size": batch_size,
        "maximum_token_length": maximum_token_length,
        "models": {
            "vader": "vaderSentiment rule/lexicon model",
            "baseline_roberta": baseline_model_id,
            "cardiff_roberta": cardiff_model_id,
        },
        "model_revisions": {
            "baseline_roberta": getattr(baseline_model.model.config, "_commit_hash", None),
            "cardiff_roberta": getattr(cardiff_model.model.config, "_commit_hash", None),
        },
        "versions": {
            "torch": importlib.metadata.version("torch"),
            "transformers": importlib.metadata.version("transformers"),
            "scipy": importlib.metadata.version("scipy"),
            "sklearn": importlib.metadata.version("scikit-learn"),
        },
        "label_counts": {
            "vader": _label_counts(scored, "vader_label"),
            "baseline_roberta": _label_counts(scored, "baseline_roberta_label"),
            "cardiff_roberta": _label_counts(scored, "cardiff_roberta_label"),
        },
        "pairwise_metrics": {
            "vader_vs_baseline_roberta": pairwise_metrics(
                scored,
                left_score="vader_compound",
                left_label="vader_label",
                right_score="baseline_roberta_score",
                right_label="baseline_roberta_label",
            ),
            "vader_vs_cardiff_roberta": pairwise_metrics(
                scored,
                left_score="vader_compound",
                left_label="vader_label",
                right_score="cardiff_roberta_score",
                right_label="cardiff_roberta_label",
            ),
            "baseline_roberta_vs_cardiff_roberta": pairwise_metrics(
                scored,
                left_score="baseline_roberta_score",
                left_label="baseline_roberta_label",
                right_score="cardiff_roberta_score",
                right_label="cardiff_roberta_label",
            ),
        },
        "three_way_label_agreement_rate": float(scored["all_three_labels_agree"].mean()),
    }
    metrics_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    report_path.write_text(_render_report(result), encoding="utf-8")
    return result


def resolve_device(device: str) -> str:
    """Resolve auto/cuda/cpu into a torch device string."""
    normalized = device.lower().strip()
    if normalized not in {"auto", "cpu", "cuda"}:
        raise ValueError("device must be one of: auto, cpu, cuda")
    if normalized == "cpu":
        return "cpu"

    import torch

    cuda_available = torch.cuda.is_available()
    if normalized == "cuda" and not cuda_available:
        raise RuntimeError("CUDA was requested but torch.cuda.is_available() is false")
    if normalized == "cuda":
        return "cuda"
    return "cuda" if cuda_available else "cpu"


def select_comparison_records(
    dataframe: pd.DataFrame,
    sample_size: int,
    seed: int,
    full_dataset: bool,
) -> pd.DataFrame:
    """Return either the full dataset or a reproducible random sample."""
    if full_dataset:
        return dataframe.reset_index(names="source_row").copy()
    resolved_sample_size = min(sample_size, len(dataframe))
    return (
        dataframe.sample(n=resolved_sample_size, random_state=seed)
        .reset_index(names="source_row")
        .copy()
    )


def pairwise_metrics(
    dataframe: pd.DataFrame,
    left_score: str,
    left_label: str,
    right_score: str,
    right_label: str,
) -> Dict[str, Any]:
    """Return compact score and label agreement metrics for two model outputs."""
    left = dataframe[left_score].astype(float)
    right = dataframe[right_score].astype(float)
    pearson = pearsonr(left, right)
    spearman = spearmanr(left, right)
    return {
        "record_count": len(dataframe),
        "pearson_r": float(pearson.statistic),
        "pearson_p_value": float(pearson.pvalue),
        "spearman_rho": float(spearman.statistic),
        "spearman_p_value": float(spearman.pvalue),
        "label_agreement_rate": float(dataframe[left_label].eq(dataframe[right_label]).mean()),
        "macro_f1_agreement": float(
            f1_score(
                dataframe[right_label],
                dataframe[left_label],
                labels=LABELS,
                average="macro",
                zero_division=0,
            )
        ),
        "mean_absolute_score_difference": float((left - right).abs().mean()),
    }


def _prefix_scores(dataframe: pd.DataFrame, prefix: str) -> pd.DataFrame:
    rename_map = {
        "roberta_negative_probability": f"{prefix}_negative_probability",
        "roberta_neutral_probability": f"{prefix}_neutral_probability",
        "roberta_positive_probability": f"{prefix}_positive_probability",
        "roberta_score": f"{prefix}_score",
        "roberta_label": f"{prefix}_label",
        "roberta_token_count": f"{prefix}_token_count",
        "roberta_truncated": f"{prefix}_truncated",
    }
    return dataframe.rename(columns=rename_map)


def _label_counts(dataframe: pd.DataFrame, column: str) -> Dict[str, int]:
    return {label: int((dataframe[column] == label).sum()) for label in LABELS}


def _render_report(result: Dict[str, Any]) -> str:
    lines = [
        "# Phase 3 Three-Model Sentiment Comparison",
        "",
        "## Run Configuration",
        "",
        f"- Input: `{result['input_path']}`.",
        f"- Run mode: `{result['run_mode']}`.",
        f"- Records compared: {result['sample_size_used']:,}.",
        f"- Seed: {result['seed']}.",
        f"- Device: `{result['device_used']}`.",
        f"- Batch size: {result['batch_size']}.",
        "",
        "## Models",
        "",
        "| Alias | Model | Revision |",
        "| --- | --- | --- |",
        f"| `vader` | {result['models']['vader']} | n/a |",
        f"| `baseline_roberta` | `{result['models']['baseline_roberta']}` | "
        f"`{result['model_revisions']['baseline_roberta']}` |",
        f"| `cardiff_roberta` | `{result['models']['cardiff_roberta']}` | "
        f"`{result['model_revisions']['cardiff_roberta']}` |",
        "",
        "## Label Counts",
        "",
        "| Model | Negative | Neutral | Positive |",
        "| --- | ---: | ---: | ---: |",
    ]
    for alias, counts in result["label_counts"].items():
        lines.append(
            f"| `{alias}` | {counts['negative']:,} | {counts['neutral']:,} | {counts['positive']:,} |"
        )
    lines.extend(
        [
            "",
            "## Pairwise Agreement",
            "",
            "| Pair | Pearson r | Spearman rho | Label agreement | Macro-F1 | Mean abs score diff |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for pair, metrics in result["pairwise_metrics"].items():
        lines.append(
            f"| `{pair}` | {metrics['pearson_r']:.4f} | {metrics['spearman_rho']:.4f} | "
            f"{100.0 * metrics['label_agreement_rate']:.2f}% | "
            f"{metrics['macro_f1_agreement']:.4f} | "
            f"{metrics['mean_absolute_score_difference']:.4f} |"
        )
    lines.extend(
        [
            "",
            f"Three-way label agreement: {100.0 * result['three_way_label_agreement_rate']:.2f}%.",
            "",
            f"Sample with all model outputs: `{result['sample_output_path']}`.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default=None,
        help="Input sentiment Parquet file. Defaults to data/02_interim/twitter_sentiment.parquet.",
    )
    parser.add_argument("--sample-size", type=int, default=100, help="Random sample size.")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Compare the full input dataset instead of a random sample.",
    )
    parser.add_argument("--seed", type=int, default=2020, help="Random sample seed.")
    parser.add_argument("--batch-size", type=int, default=16, help="RoBERTa inference batch size.")
    parser.add_argument(
        "--maximum-token-length",
        type=int,
        default=512,
        help="RoBERTa maximum token length.",
    )
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "cuda"],
        default="auto",
        help="Inference device. auto uses CUDA when available, otherwise CPU.",
    )
    parser.add_argument(
        "--baseline-model-id",
        default=BASELINE_ROBERTA_MODEL_ID,
        help="Older baseline CardiffNLP RoBERTa model id.",
    )
    parser.add_argument(
        "--cardiff-model-id",
        default=CARDIFF_LATEST_MODEL_ID,
        help="Latest CardiffNLP RoBERTa model id.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    output = run_three_model_comparison(
        PROJECT_ROOT,
        input_path=arguments.input,
        sample_size=arguments.sample_size,
        full_dataset=arguments.full,
        seed=arguments.seed,
        batch_size=arguments.batch_size,
        maximum_token_length=arguments.maximum_token_length,
        device=arguments.device,
        baseline_model_id=arguments.baseline_model_id,
        cardiff_model_id=arguments.cardiff_model_id,
    )
    print(json.dumps(output, indent=2))
