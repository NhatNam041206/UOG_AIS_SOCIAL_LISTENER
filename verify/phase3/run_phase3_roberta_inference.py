"""Score the Phase 3 validation sample with Twitter-RoBERTa."""

from __future__ import annotations

import importlib.metadata
import json
import sys
from pathlib import Path
from typing import Any, Dict

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.phase3_sentiment.sentiment_models_model import RobertaSentimentModel


def run_phase3_roberta_inference(
    project_root: str | Path = ".",
    batch_size: int = 16,
    maximum_token_length: int = 512,
) -> Dict[str, Any]:
    """Score every validation-sample record and write inference evidence."""
    root = Path(project_root).resolve()
    sample_path = root / "output" / "results" / "phase3" / "sentiment_validation_sample.parquet"
    manifest_path = root / "output" / "results" / "phase3" / "roberta_inference_manifest.json"
    report_path = root / "output" / "reports" / "phase3" / "roberta_inference_report.md"
    if not sample_path.exists():
        raise FileNotFoundError(f"Validation sample is missing: {sample_path}")

    dataframe = pd.read_parquet(sample_path)
    conflicts = [column for column in dataframe.columns if column.startswith("roberta_")]
    if conflicts:
        dataframe = dataframe.drop(columns=conflicts)
    model = RobertaSentimentModel.load(maximum_token_length=maximum_token_length)
    scores = pd.DataFrame(model.score_many(dataframe["tweet"].tolist(), batch_size=batch_size))
    scored = pd.concat([dataframe.reset_index(drop=True), scores], axis=1)
    scored.to_parquet(sample_path, index=False)

    probability_columns = [
        "roberta_negative_probability",
        "roberta_neutral_probability",
        "roberta_positive_probability",
    ]
    probability_error = float((scored[probability_columns].sum(axis=1) - 1.0).abs().max())
    required = [*probability_columns, "roberta_score", "roberta_label", "roberta_token_count", "roberta_truncated"]
    checks = {
        "all_sample_records_scored": len(scored) == 5_000,
        "roberta_fields_complete": not bool(scored[required].isna().any().any()),
        "probabilities_in_unit_interval": bool(
            scored[probability_columns].ge(0.0).all().all()
            and scored[probability_columns].le(1.0).all().all()
        ),
        "probabilities_sum_to_one": probability_error < 1e-5,
        "roberta_score_in_expected_range": bool(scored["roberta_score"].between(-1.0, 1.0).all()),
        "labels_expected": set(scored["roberta_label"].unique()) == set(RobertaSentimentModel.LABELS),
    }
    label_counts = {str(key): int(value) for key, value in scored["roberta_label"].value_counts().items()}
    revision = getattr(model.model.config, "_commit_hash", None)
    manifest: Dict[str, Any] = {
        "phase": "phase3_sentiment",
        "stage": "roberta_sample_inference",
        "status": "completed" if all(checks.values()) else "failed",
        "sample_path": str(sample_path),
        "record_count": len(scored),
        "model_id": RobertaSentimentModel.MODEL_ID,
        "model_revision": revision,
        "label_mapping": {str(index): label for index, label in enumerate(RobertaSentimentModel.LABELS)},
        "backend": "torch",
        "device": model.device,
        "batch_size": batch_size,
        "maximum_token_length": maximum_token_length,
        "versions": {
            "torch": importlib.metadata.version("torch"),
            "transformers": importlib.metadata.version("transformers"),
        },
        "preprocessing": {
            "usernames": "replace @-prefixed tokens with @user",
            "urls": "replace URLs with http",
            "canonical_tweet_text_modified": False,
        },
        "truncated_record_count": int(scored["roberta_truncated"].sum()),
        "maximum_observed_token_count": int(scored["roberta_token_count"].max()),
        "probability_sum_maximum_absolute_error": probability_error,
        "label_counts": label_counts,
        "checks": checks,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    report_path.write_text(_render_report(manifest), encoding="utf-8")
    if manifest["status"] != "completed":
        raise ValueError("RoBERTa inference validation failed")
    return manifest


def _render_report(manifest: Dict[str, Any]) -> str:
    lines = [
        "# Phase 3 RoBERTa Sample Inference Report",
        "",
        f"- Status: **{manifest['status']}**.",
        f"- Records scored: {manifest['record_count']:,}.",
        f"- Model: `{manifest['model_id']}`.",
        f"- Resolved revision: `{manifest['model_revision']}`.",
        f"- Backend/device: `{manifest['backend']}` / `{manifest['device']}`.",
        f"- Batch size: {manifest['batch_size']}.",
        f"- Maximum token length: {manifest['maximum_token_length']}.",
        f"- Truncated records: {manifest['truncated_record_count']:,}.",
        f"- Maximum observed token count: {manifest['maximum_observed_token_count']:,}.",
        "",
        "## Model-Specific Preprocessing",
        "",
        "- Usernames are replaced with `@user` only for RoBERTa input.",
        "- URLs are replaced with `http` only for RoBERTa input.",
        "- Canonical tweet text is not modified.",
        "",
        "## Label Distribution",
        "",
        "| Label | Records |",
        "| --- | ---: |",
    ]
    for label in RobertaSentimentModel.LABELS:
        lines.append(f"| {label.title()} | {manifest['label_counts'].get(label, 0):,} |")
    lines.extend(["", "## Verification Checks", "", "| Check | Result |", "| --- | --- |"])
    for name, passed in manifest["checks"].items():
        lines.append(f"| `{name}` | {'passed' if passed else 'failed'} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    result = run_phase3_roberta_inference(PROJECT_ROOT)
    print(json.dumps(result, indent=2))
