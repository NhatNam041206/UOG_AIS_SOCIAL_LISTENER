"""Gemini API LLM-Assisted Sarcasm & Stance Silver Annotation Pipeline.

This module implements a few-shot annotation pipeline using 15 human-annotated seed
examples to expand a silver-standard dataset via the Gemini API, enabling fine-tuning
of RoBERTa for in-domain political sarcasm and candidate stance detection.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


HUMAN_SEED_EXAMPLES: List[Dict[str, Any]] = [
    {
        "tweet": "Oh brilliant, another debate where everyone talks over each other! #Election2020",
        "candidate_target": "both",
        "expressed_sentiment": "negative",
        "intended_sentiment": "negative",
        "sarcasm": True,
        "stance": "neutral",
        "confidence": 0.95,
    },
    {
        "tweet": "Joe Biden's plan for economic recovery is truly inspiring and detailed. #Biden2020",
        "candidate_target": "Joe Biden",
        "expressed_sentiment": "positive",
        "intended_sentiment": "positive",
        "sarcasm": False,
        "stance": "favor",
        "confidence": 0.98,
    },
    {
        "tweet": "Great job President Trump! Total victory tonight! #Trump2020",
        "candidate_target": "Donald Trump",
        "expressed_sentiment": "positive",
        "intended_sentiment": "positive",
        "sarcasm": False,
        "stance": "favor",
        "confidence": 0.99,
    },
    {
        "tweet": "Yeah because taxes definitely needed to go up more, fantastic idea! #Biden2020",
        "candidate_target": "Joe Biden",
        "expressed_sentiment": "positive",
        "intended_sentiment": "negative",
        "sarcasm": True,
        "stance": "against",
        "confidence": 0.92,
    },
    {
        "tweet": "Trump COVID speech was so informative, I learned absolutely nothing new.",
        "candidate_target": "Donald Trump",
        "expressed_sentiment": "positive",
        "intended_sentiment": "negative",
        "sarcasm": True,
        "stance": "against",
        "confidence": 0.94,
    },
    {
        "tweet": "Looking forward to seeing the election results on November 3rd.",
        "candidate_target": "other",
        "expressed_sentiment": "neutral",
        "intended_sentiment": "neutral",
        "sarcasm": False,
        "stance": "neutral",
        "confidence": 0.90,
    },
    {
        "tweet": "Another flawless debate performance... if you enjoy chaotic yelling. #Election2020",
        "candidate_target": "both",
        "expressed_sentiment": "positive",
        "intended_sentiment": "negative",
        "sarcasm": True,
        "stance": "against",
        "confidence": 0.91,
    },
    {
        "tweet": "Biden is leading in the key swing states according to the latest polls.",
        "candidate_target": "Joe Biden",
        "expressed_sentiment": "neutral",
        "intended_sentiment": "neutral",
        "sarcasm": False,
        "stance": "neutral",
        "confidence": 0.95,
    },
    {
        "tweet": "Trump campaign rally drew thousands in Pennsylvania today. #Trump2020",
        "candidate_target": "Donald Trump",
        "expressed_sentiment": "neutral",
        "intended_sentiment": "neutral",
        "sarcasm": False,
        "stance": "favor",
        "confidence": 0.92,
    },
    {
        "tweet": "Oh sure, politicians always keep 100% of their promises, totally trustworthy!",
        "candidate_target": "other",
        "expressed_sentiment": "positive",
        "intended_sentiment": "negative",
        "sarcasm": True,
        "stance": "against",
        "confidence": 0.96,
    },
    {
        "tweet": "Voting line was long but totally worth it to cast my ballot for Biden!",
        "candidate_target": "Joe Biden",
        "expressed_sentiment": "positive",
        "intended_sentiment": "positive",
        "sarcasm": False,
        "stance": "favor",
        "confidence": 0.97,
    },
    {
        "tweet": "Four more years of economic prosperity with Trump! #MAGA2020",
        "candidate_target": "Donald Trump",
        "expressed_sentiment": "positive",
        "intended_sentiment": "positive",
        "sarcasm": False,
        "stance": "favor",
        "confidence": 0.99,
    },
    {
        "tweet": "Wow, what a mature and constructive discussion between both candidates...",
        "candidate_target": "both",
        "expressed_sentiment": "positive",
        "intended_sentiment": "negative",
        "sarcasm": True,
        "stance": "against",
        "confidence": 0.93,
    },
    {
        "tweet": "Make sure you check your voter registration status before the deadline.",
        "candidate_target": "other",
        "expressed_sentiment": "neutral",
        "intended_sentiment": "neutral",
        "sarcasm": False,
        "stance": "neutral",
        "confidence": 0.98,
    },
    {
        "tweet": "Love waking up to more political attack ads on TV, just wonderful.",
        "candidate_target": "both",
        "expressed_sentiment": "positive",
        "intended_sentiment": "negative",
        "sarcasm": True,
        "stance": "against",
        "confidence": 0.94,
    },
]


@dataclass(frozen=True)
class SilverAnnotationResult:
    """Structure for an LLM-annotated tweet record."""

    tweet: str
    candidate_target: str
    expressed_sentiment: str
    intended_sentiment: str
    sarcasm: bool
    stance: str
    confidence: float


class GeminiSarcasmAnnotator:
    """Few-shot LLM annotator leveraging Gemini API for silver dataset generation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        seed_examples: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.api_key = api_key
        self.seed_examples = seed_examples or HUMAN_SEED_EXAMPLES

    def build_prompt(self, tweets: List[str]) -> str:
        """Construct a structured few-shot prompt with human seed examples."""
        prompt_parts = [
            "You are an expert political discourse linguist specializing in US election tweets.",
            "Analyze each provided tweet and determine:",
            "1. candidate_target: 'Donald Trump', 'Joe Biden', 'both', or 'other'",
            "2. expressed_sentiment: 'positive', 'negative', or 'neutral'",
            "3. intended_sentiment: 'positive', 'negative', or 'neutral' (accounting for sarcasm)",
            "4. sarcasm: true or false",
            "5. stance: 'favor', 'against', or 'neutral'",
            "6. confidence: float between 0.0 and 1.0",
            "",
            "### FEW-SHOT SEED EXAMPLES (HUMAN ANNOTATED):",
        ]

        for idx, seed in enumerate(self.seed_examples, start=1):
            prompt_parts.append(f"Example {idx}:")
            prompt_parts.append(f"Tweet: \"{seed['tweet']}\"")
            prompt_parts.append(
                f"Output: {json.dumps(seed, ensure_ascii=False)}"
            )
            prompt_parts.append("")

        prompt_parts.append("### TWEETS TO ANNOTATE:")
        for idx, text in enumerate(tweets, start=1):
            prompt_parts.append(f"Tweet {idx}: \"{text}\"")

        prompt_parts.append("")
        prompt_parts.append("Return ONLY a valid JSON array of objects matching the output schema.")
        return "\n".join(prompt_parts)

    def parse_llm_response(self, raw_response: str) -> List[SilverAnnotationResult]:
        """Parse raw JSON output from LLM into structured dataclasses."""
        cleaned = raw_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        parsed = json.loads(cleaned)
        results = []
        for item in parsed:
            results.append(
                SilverAnnotationResult(
                    tweet=str(item.get("tweet", "")),
                    candidate_target=str(item.get("candidate_target", "other")),
                    expressed_sentiment=str(item.get("expressed_sentiment", "neutral")),
                    intended_sentiment=str(item.get("intended_sentiment", "neutral")),
                    sarcasm=bool(item.get("sarcasm", False)),
                    stance=str(item.get("stance", "neutral")),
                    confidence=float(item.get("confidence", 0.90)),
                )
            )
        return results
