# Phase 3 v2 Sentiment & Sarcasm Report

Run ID: `phase3_v2_vader_baseline_20260801`

## Sentiment Scoring
- Scored Tweets: 1,280,784
- Primary Score: VADER continuous compound `[-1.0, +1.0]` (authoritative baseline)
- RoBERTa Status: **Deferred** — requires GPU/torch environment.
  Model: `cardiffnlp/twitter-roberta-base-sentiment-latest`

## VADER Distribution
- Mean Compound: `0.0527`
- `neutral`: 488,163 tweets (38.1%)
- `positive`: 446,283 tweets (34.8%)
- `negative`: 346,338 tweets (27.0%)

## Sarcasm Risk Profiling
- Method: Heuristic linguistic proxy (pattern matching on capitalization, ellipsis, contrast phrases)
- Mean Heuristic Sarcasm Risk Score: `0.0543`
- Production Sarcasm Model: `cardiffnlp/twitter-roberta-base-irony` (deferred to GPU environment)

## Gemini Silver Annotation Pipeline
- Human Seed Set: 15 annotated examples.
- Prompt Structure Valid: Yes
- API Status: **Not Called** — requires active Gemini API key (separate annotation step).