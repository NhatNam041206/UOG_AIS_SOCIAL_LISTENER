# Phase 3 v3 Sentiment Report
Primary model: cardiffnlp/twitter-roberta-base-sentiment-latest
Throughput: 599.35 tweets/sec on cuda
Agreement with VADER:
{
  "pearson_r": 0.4814403048263494,
  "spearman_r": 0.4568677612462697,
  "cohen_kappa": 0.3836344127380338,
  "exact_agreement_rate": 0.5919315925295492,
  "confusion_matrix": {
    "labels": [
      "negative",
      "neutral",
      "positive"
    ],
    "matrix": [
      [
        237319,
        89731,
        14227
      ],
      [
        94486,
        360859,
        56594
      ],
      [
        131012,
        143522,
        170003
      ]
    ]
  },
  "roberta_distribution_when_vader_zero": {
    "neutral": 357950,
    "negative": 88348,
    "positive": 55686
  }
}