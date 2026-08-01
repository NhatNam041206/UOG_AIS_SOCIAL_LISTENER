"""Execute Phase 3 v2 VADER Sentiment Scoring with Sarcasm Risk Profiling.

Phase 3 v2 scores the cleaned Twitter dataset with:
1. Primary VADER continuous sentiment scoring (vader_compound as the authoritative sentiment score).
2. Sarcasm Risk Proxy based on linguistic heuristics (punctuation patterns, contrast words).
3. Model baseline note: RoBERTa (cardiffnlp/twitter-roberta-base-sentiment-latest) and pretrained
   irony classifier (cardiffnlp/twitter-roberta-base-irony) are the intended production models
   but require GPU/torch inference which is deferred to a dedicated GPU environment.
   This runner produces a reproducible VADER baseline that is the controlling evidence
   until full-model inference is approved and executed.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.phase1_ingestion.storage_serializers_view import StorageSerializersView
from src.phase3_sentiment.gemini_sarcasm_annotation import GeminiSarcasmAnnotator
from src.phase3_sentiment.sentiment_models_model import VaderSentimentModel


PHASE3_V2_RUN_ID = "phase3_v2_vader_baseline_20260801"

# Heuristic sarcasm risk signal patterns (linguistic proxies only — not a validated classifier)
_SARCASM_PATTERNS = re.compile(
    r"(oh\s+sure|oh\s+great|oh\s+brilliant|totally|absolutely|definitely|of\s+course|"
    r"yeah\s+right|right\.\.\.|sure\.\.\.|wow[,\s]+so|thanks\s+for\s+nothing|"
    r"what\s+a\s+(great|brilliant|wonderful|fantastic)|just\s+(love|wonderful|great)|\.\.\.|"
    r"(?<!\w)lol(?!\w)|(?<!\w)lmao(?!\w))",
    flags=re.IGNORECASE,
)


def _compute_sarcasm_proxy(text: str) -> float:
    """Return a heuristic sarcasm risk score in [0, 1] based on linguistic signals."""
    if not isinstance(text, str) or not text.strip():
        return 0.0
    score = 0.0
    matches = _SARCASM_PATTERNS.findall(text)
    score += min(len(matches) * 0.15, 0.45)
    # Capitalized words ratio (ALL CAPS = potential sarcasm signal)
    words = text.split()
    if words:
        caps_ratio = sum(1 for w in words if w.isupper() and len(w) > 2) / len(words)
        score += min(caps_ratio * 0.3, 0.30)
    # Ellipsis or multiple punctuation
    if re.search(r"\.{2,}|!{2,}|\?{2,}", text):
        score += 0.15
    # Positive word followed closely by negative sentiment marker
    if re.search(r"\b(great|wonderful|brilliant|fantastic|amazing)\b.{0,30}\b(but|however|except|not)\b", text, re.IGNORECASE):
        score += 0.25
    return round(min(score, 1.0), 4)


def run_phase3_v2(project_root: str | Path = ".") -> Dict[str, Any]:
    """Execute Phase 3 v2 VADER sentiment scoring and heuristic sarcasm risk profiling."""
    root = Path(project_root).resolve()
    p2_dir = root / "data" / "02_interim" / "phase2_v2"
    p3_dir = root / "data" / "02_interim" / "phase3_v2"
    report_dir = root / "output" / "reports" / "phase3" / "v2"
    result_dir = root / "output" / "results" / "phase3" / "v2"

    for d in (p3_dir, report_dir, result_dir):
        d.mkdir(parents=True, exist_ok=True)

    serializer = StorageSerializersView()

    cleaned_path = p2_dir / "twitter_cleaned_v2.parquet"
    if not cleaned_path.exists():
        cleaned_path = root / "data" / "02_interim" / "twitter_cleaned.parquet"
        if not cleaned_path.exists():
            raise FileNotFoundError("Cleaned Twitter parquet missing. Run Phase 2 first.")

    df = pd.read_parquet(cleaned_path)
    total_tweets = len(df)

    # 1. VADER Continuous Scoring (primary authoritative sentiment)
    vader = VaderSentimentModel()
    text_list = df["tweet_cleaned"].tolist()
    vader_scores = vader.score_many(text_list)
    vader_df = pd.DataFrame(vader_scores)

    df["vader_compound"] = vader_df["vader_compound"].values
    df["vader_positive"] = vader_df["vader_positive"].values
    df["vader_negative"] = vader_df["vader_negative"].values
    df["vader_neutral"] = vader_df["vader_neutral"].values
    df["vader_label"] = vader_df["vader_label"].values

    # 2. Heuristic Sarcasm Risk Proxy Score [0, 1]
    # NOTE: This is a linguistic heuristic proxy, NOT a validated classifier.
    # The intended production sarcasm model (cardiffnlp/twitter-roberta-base-irony)
    # requires torch inference and is deferred to a GPU environment.
    df["sarcasm_risk_score"] = df["tweet_cleaned"].apply(_compute_sarcasm_proxy)

    # 3. Mark RoBERTa columns as unavailable (deferred to GPU inference step)
    df["roberta_score"] = np.nan
    df["roberta_label"] = "unavailable"
    df["roberta_inference_status"] = "deferred_requires_gpu"

    # Save Phase 3 v2 Interim Parquet
    sentiment_path = p3_dir / "twitter_sentiment_v2.parquet"
    serializer.serialize_to_parquet(df, sentiment_path)

    # 4. Gemini Silver Annotation Pipeline — prompt structure validation only
    # No API call is made here; full annotation requires a valid API key and is a separate step.
    annotator = GeminiSarcasmAnnotator()
    seed_prompt = annotator.build_prompt(["[sample tweet 1]", "[sample tweet 2]"])
    gemini_prompt_ready = len(seed_prompt) > 0

    manifest = {
        "phase": "phase3_sentiment_v2",
        "run_id": PHASE3_V2_RUN_ID,
        "total_scored_tweets": total_tweets,
        "primary_sentiment_model": "VADER (vader_compound is authoritative sentiment score)",
        "roberta_status": "deferred_requires_gpu_torch_environment",
        "pretrained_sarcasm_model_status": "deferred_requires_gpu_torch_environment",
        "sarcasm_risk_method": "heuristic_linguistic_proxy",
        "metrics": {
            "vader_mean_compound": float(df["vader_compound"].mean()),
            "vader_label_distribution": df["vader_label"].value_counts().to_dict(),
            "mean_sarcasm_risk_score_heuristic": float(df["sarcasm_risk_score"].mean()),
        },
        "gemini_annotation_prompt_structure_valid": gemini_prompt_ready,
        "gemini_annotation_api_called": False,
        "output_paths": {
            "sentiment_parquet": str(sentiment_path),
            "manifest": str(result_dir / "sentiment_manifest_v2.json"),
            "report": str(report_dir / "sentiment_report_v2.md"),
        },
    }

    (result_dir / "sentiment_manifest_v2.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Generate Report
    report_lines = [
        "# Phase 3 v2 Sentiment & Sarcasm Report",
        "",
        f"Run ID: `{PHASE3_V2_RUN_ID}`",
        "",
        "## Sentiment Scoring",
        f"- Scored Tweets: {total_tweets:,}",
        "- Primary Score: VADER continuous compound `[-1.0, +1.0]` (authoritative baseline)",
        "- RoBERTa Status: **Deferred** — requires GPU/torch environment.",
        "  Model: `cardiffnlp/twitter-roberta-base-sentiment-latest`",
        "",
        "## VADER Distribution",
        f"- Mean Compound: `{df['vader_compound'].mean():.4f}`",
    ]
    for lbl, cnt in df["vader_label"].value_counts().items():
        report_lines.append(f"- `{lbl}`: {cnt:,} tweets ({cnt/total_tweets*100:.1f}%)")
    report_lines.extend([
        "",
        "## Sarcasm Risk Profiling",
        "- Method: Heuristic linguistic proxy (pattern matching on capitalization, ellipsis, contrast phrases)",
        f"- Mean Heuristic Sarcasm Risk Score: `{df['sarcasm_risk_score'].mean():.4f}`",
        "- Production Sarcasm Model: `cardiffnlp/twitter-roberta-base-irony` (deferred to GPU environment)",
        "",
        "## Gemini Silver Annotation Pipeline",
        "- Human Seed Set: 15 annotated examples.",
        f"- Prompt Structure Valid: {'Yes' if gemini_prompt_ready else 'No'}",
        "- API Status: **Not Called** — requires active Gemini API key (separate annotation step).",
    ])
    (report_dir / "sentiment_report_v2.md").write_text("\n".join(report_lines), encoding="utf-8")

    return manifest


if __name__ == "__main__":
    res = run_phase3_v2(PROJECT_ROOT)
    print(json.dumps(res, indent=2))
