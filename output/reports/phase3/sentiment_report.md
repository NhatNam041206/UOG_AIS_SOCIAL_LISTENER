# Phase 3 VADER Sentiment Scoring Report

## Stage Status

- Status: **vader_scoring_completed**.
- Input records: 1,331,317.
- Output records: 1,331,317.
- VADER output validation: **passed** (11 checks passed).
- RoBERTa validation remains pending; this report does not claim validated VADER accuracy.

## Method

- VADER scored the Phase 2 cleaned `tweet` text without additional normalization.
- Capitalization, punctuation, and emoji preserved by Phase 2 remain available to VADER.
- Compound scores at or below `-0.05` are negative.
- Compound scores between `-0.05` and `0.05` are neutral.
- Compound scores at or above `0.05` are positive.

## Full-Dataset Summary

| Measure | Result |
| --- | ---: |
| Mean compound score | 0.0518 |
| Standard deviation | 0.4645 |
| Minimum compound score | -0.9998 |
| Maximum compound score | 1.0000 |

## Label Distribution

| Label | Records | Percentage |
| --- | ---: | ---: |
| Negative | 350,836 | 26.35% |
| Neutral | 527,371 | 39.61% |
| Positive | 453,110 | 34.03% |

## Major Figures

1. `vader_sentiment_distribution.png` shows the full compound-score distribution and label counts.
2. `sentiment_distribution_by_candidate.png` compares compound-score distributions between candidate streams.

## Interpretation Boundary

These are descriptive VADER outputs. Candidate-stream differences must not be interpreted as population opinion, causal effects, or validated model accuracy. The planned RoBERTa comparison is required before Phase 3 closure.
