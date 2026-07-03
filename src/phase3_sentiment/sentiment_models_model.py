"""Sentiment model adapters for Phase 3."""

from __future__ import annotations

import re
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


_MENTION_PATTERN = re.compile(r"@\S+")
_URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", flags=re.IGNORECASE)
DEFAULT_TWITTER_ROBERTA_MODEL_ID = "cardiffnlp/twitter-roberta-base-sentiment-latest"


@dataclass(frozen=True)
class RobertaModelConfig:
    """Configuration for the ready-to-use CardiffNLP Twitter-RoBERTa model."""

    model_id: str = DEFAULT_TWITTER_ROBERTA_MODEL_ID
    maximum_token_length: int = 512
    batch_size: int = 16
    device: str = "cpu"

    @classmethod
    def from_dict(cls, values: Dict[str, Any]) -> "RobertaModelConfig":
        """Create a config while rejecting misspelled or unsupported keys."""
        allowed = {"model_id", "maximum_token_length", "batch_size", "device"}
        unknown = sorted(set(values) - allowed)
        if unknown:
            raise ValueError(f"Unknown RoBERTa model config keys: {unknown}")
        config = cls(**values)
        if not config.model_id.strip():
            raise ValueError("model_id must be non-empty")
        if config.maximum_token_length <= 0:
            raise ValueError("maximum_token_length must be positive")
        if config.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if not config.device.strip():
            raise ValueError("device must be non-empty")
        return config


def load_roberta_model_config(path: str | Path) -> RobertaModelConfig:
    """Load RoBERTa model settings from a JSON config file."""
    values = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(values, dict):
        raise ValueError("RoBERTa model config must be a JSON object")
    return RobertaModelConfig.from_dict(values)


class VaderSentimentModel:
    """Score text with VADER and apply the documented compound-score labels."""

    NEGATIVE_THRESHOLD = -0.05
    POSITIVE_THRESHOLD = 0.05

    def __init__(self, analyzer: SentimentIntensityAnalyzer | None = None) -> None:
        self._analyzer = analyzer or SentimentIntensityAnalyzer()

    def score(self, text: Any) -> Dict[str, float | str]:
        """Return the approved VADER schema for one non-empty text value."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError("VADER text must be a non-empty string")
        scores = self._analyzer.polarity_scores(text)
        compound = float(scores["compound"])
        return {
            "vader_negative": float(scores["neg"]),
            "vader_neutral": float(scores["neu"]),
            "vader_positive": float(scores["pos"]),
            "vader_compound": compound,
            "vader_label": self.label(compound),
        }

    def score_many(self, texts: Iterable[Any]) -> List[Dict[str, float | str]]:
        """Score text values in order."""
        return [self.score(text) for text in texts]

    @classmethod
    def label(cls, compound: float) -> str:
        """Convert a VADER compound score to the approved three-class label."""
        if compound <= cls.NEGATIVE_THRESHOLD:
            return "negative"
        if compound >= cls.POSITIVE_THRESHOLD:
            return "positive"
        return "neutral"


class RobertaSentimentModel:
    """Score tweets with the configured CardiffNLP Twitter-RoBERTa model."""

    MODEL_ID = DEFAULT_TWITTER_ROBERTA_MODEL_ID
    LABELS = ("negative", "neutral", "positive")

    def __init__(
        self,
        tokenizer: Any,
        model: Any,
        model_id: str = MODEL_ID,
        maximum_token_length: int = 512,
        device: str = "cpu",
    ) -> None:
        if maximum_token_length <= 0:
            raise ValueError("maximum_token_length must be positive")
        if not model_id.strip():
            raise ValueError("model_id must be non-empty")
        self.tokenizer = tokenizer
        self.model = model
        self.model_id = model_id
        self.maximum_token_length = maximum_token_length
        self.device = device

    @classmethod
    def load(
        cls,
        model_id: str = MODEL_ID,
        maximum_token_length: int = 512,
        device: str = "cpu",
    ) -> "RobertaSentimentModel":
        """Load the exact configured tokenizer and sequence-classification model."""
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForSequenceClassification.from_pretrained(model_id)
        model.to(device)
        model.eval()
        return cls(tokenizer, model, model_id, maximum_token_length, device)

    @staticmethod
    def normalize(text: Any) -> str:
        """Apply model-specific username and URL placeholders."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError("RoBERTa text must be a non-empty string")
        normalized = _MENTION_PATTERN.sub("@user", text)
        normalized = _URL_PATTERN.sub("http", normalized)
        return normalized

    def score_many(self, texts: Iterable[Any], batch_size: int = 16) -> List[Dict[str, Any]]:
        """Score text values in batches and return probabilities and audit fields."""
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        import torch

        normalized = [self.normalize(text) for text in texts]
        token_counts = [
            len(self.tokenizer(text, add_special_tokens=True, truncation=False)["input_ids"])
            for text in normalized
        ]
        rows: List[Dict[str, Any]] = []
        for start in range(0, len(normalized), batch_size):
            batch = normalized[start : start + batch_size]
            encoded = self.tokenizer(
                batch,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=self.maximum_token_length,
            )
            encoded = {key: value.to(self.device) for key, value in encoded.items()}
            with torch.inference_mode():
                probabilities = torch.softmax(self.model(**encoded).logits, dim=-1).cpu().tolist()
            for offset, values in enumerate(probabilities):
                negative, neutral, positive = [float(value) for value in values]
                label = self.LABELS[int(max(range(3), key=values.__getitem__))]
                token_count = token_counts[start + offset]
                rows.append(
                    {
                        "roberta_negative_probability": negative,
                        "roberta_neutral_probability": neutral,
                        "roberta_positive_probability": positive,
                        "roberta_score": positive - negative,
                        "roberta_label": label,
                        "roberta_token_count": token_count,
                        "roberta_truncated": token_count > self.maximum_token_length,
                    }
                )
        return rows
