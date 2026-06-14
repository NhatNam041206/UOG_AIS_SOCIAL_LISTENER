"""Verify the configured RoBERTa model and inference backend."""

from __future__ import annotations

import importlib.metadata
import json
import sys
from pathlib import Path
from typing import Any, Dict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


MODEL_ID = "cardiffnlp/twitter-roberta-base-sentiment"
LABELS = {0: "negative", 1: "neutral", 2: "positive"}
MAX_LENGTH = 512


def verify_roberta_setup(project_root: str | Path = ".") -> Dict[str, Any]:
    """Load the exact configured model and score a small deterministic batch."""
    root = Path(project_root).resolve()
    result_path = root / "output" / "results" / "phase3" / "roberta_setup_validation.json"
    report_path = root / "output" / "reports" / "phase3" / "roberta_setup_report.md"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID)
    model.eval()
    texts = ["I love this!", "This is terrible.", "Election update."]
    encoded = tokenizer(
        texts,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=MAX_LENGTH,
    )
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
        "model_id": MODEL_ID,
        "model_revision": getattr(model.config, "_commit_hash", None),
        "backend": "torch",
        "device": "cpu",
        "versions": {
            "torch": importlib.metadata.version("torch"),
            "transformers": importlib.metadata.version("transformers"),
            "scipy": importlib.metadata.version("scipy"),
        },
        "labels": id_to_label,
        "model_config_labels": config_labels,
        "maximum_token_length": MAX_LENGTH,
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
    output = verify_roberta_setup(PROJECT_ROOT)
    print(json.dumps(output, indent=2))
    raise SystemExit(0 if output["status"] == "passed" else 1)
