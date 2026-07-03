"""Verify the configured RoBERTa model and inference backend."""

from __future__ import annotations

import importlib.metadata
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.phase3_sentiment.sentiment_models_model import (
    RobertaSentimentModel,
    load_roberta_model_config,
)

DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "phase3_roberta_model.json"
LABELS = {index: label for index, label in enumerate(RobertaSentimentModel.LABELS)}


def verify_roberta_setup(
    project_root: str | Path = ".",
    config_path: str | Path | None = None,
) -> Dict[str, Any]:
    """Load the exact configured model and score a small deterministic batch."""
    root = Path(project_root).resolve()
    resolved_config = Path(config_path or root / "configs" / "phase3_roberta_model.json")
    config = load_roberta_model_config(resolved_config)
    result_path = root / "output" / "results" / "phase3" / "roberta_setup_validation.json"
    report_path = root / "output" / "reports" / "phase3" / "roberta_setup_report.md"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(config.model_id)
    model = AutoModelForSequenceClassification.from_pretrained(config.model_id)
    model.to(config.device)
    model.eval()
    texts = ["I love this!", "This is terrible.", "Election update."]
    encoded = tokenizer(
        texts,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=config.maximum_token_length,
    )
    encoded = {key: value.to(config.device) for key, value in encoded.items()}
    with torch.inference_mode():
        probabilities = torch.softmax(model(**encoded).logits, dim=-1).cpu().tolist()
    config_labels = {str(key): str(value) for key, value in model.config.id2label.items()}
    id_to_label = {str(key): value for key, value in LABELS.items()}
    checks = {
        "torch_available": True,
        "tokenizer_loaded": tokenizer is not None,
        "model_loaded": model is not None,
        "expected_three_labels": len(config_labels) == 3 and len(id_to_label) == 3,
        "test_batch_scored": len(probabilities) == len(texts),
        "probabilities_sum_to_one": all(abs(sum(row) - 1.0) < 1e-5 for row in probabilities),
    }
    result: Dict[str, Any] = {
        "phase": "phase3_sentiment",
        "stage": "roberta_setup",
        "status": "passed" if all(checks.values()) else "failed",
        "config_path": str(resolved_config),
        "model_id": config.model_id,
        "model_revision": getattr(model.config, "_commit_hash", None),
        "backend": "torch",
        "device": config.device,
        "versions": {
            "torch": importlib.metadata.version("torch"),
            "transformers": importlib.metadata.version("transformers"),
            "scipy": importlib.metadata.version("scipy"),
        },
        "labels": id_to_label,
        "model_config_labels": config_labels,
        "maximum_token_length": config.maximum_token_length,
        "checks": checks,
        "test_probabilities": probabilities,
    }
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    report_path.write_text(_render_report(result), encoding="utf-8")
    return result


def _render_report(result: Dict[str, Any]) -> str:
    lines = [
        "# Phase 3 RoBERTa Setup Report",
        "",
        f"- Status: **{result['status']}**.",
        f"- Model: `{result['model_id']}`.",
        f"- Resolved revision: `{result['model_revision']}`.",
        f"- Backend: `{result['backend']}` on `{result['device']}`.",
        f"- Labels: `{result['labels']}`.",
        "",
        "## Dependency Versions",
        "",
        "| Dependency | Version |",
        "| --- | --- |",
    ]
    for name, version in result["versions"].items():
        lines.append(f"| `{name}` | `{version}` |")
    lines.extend(["", "## Verification Checks", "", "| Check | Result |", "| --- | --- |"])
    for name, passed in result["checks"].items():
        lines.append(f"| `{name}` | {'passed' if passed else 'failed'} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG,
        help="Path to the RoBERTa model JSON config.",
    )
    args = parser.parse_args()
    output = verify_roberta_setup(PROJECT_ROOT, args.config)
    print(json.dumps(output, indent=2))
    raise SystemExit(0 if output["status"] == "passed" else 1)
