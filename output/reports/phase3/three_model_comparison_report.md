# Phase 3 Three-Model Sentiment Comparison

## Run Configuration

- Input: `D:\GW_UNIVERSITY\AIS\Social_Listener\Env\Social_Listener_V1\UOG_AIS_SOCIAL_LISTENER\data\02_interim\twitter_sentiment.parquet`.
- Run mode: `sample`.
- Records compared: 100.
- Seed: 2020.
- Device: `cpu`.
- Batch size: 16.

## Models

| Alias | Model | Revision |
| --- | --- | --- |
| `vader` | vaderSentiment rule/lexicon model | n/a |
| `baseline_roberta` | `cardiffnlp/twitter-roberta-base-sentiment` | `daefdd1f6ae931839bce4d0f3db0a1a4265cd50f` |
| `cardiff_roberta` | `cardiffnlp/twitter-roberta-base-sentiment-latest` | `3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7` |

## Label Counts

| Model | Negative | Neutral | Positive |
| --- | ---: | ---: | ---: |
| `vader` | 24 | 37 | 39 |
| `baseline_roberta` | 37 | 50 | 13 |
| `cardiff_roberta` | 38 | 43 | 19 |

## Pairwise Agreement

| Pair | Pearson r | Spearman rho | Label agreement | Macro-F1 | Mean abs score diff |
| --- | ---: | ---: | ---: | ---: | ---: |
| `vader_vs_baseline_roberta` | 0.4922 | 0.4664 | 61.00% | 0.5843 | 0.4086 |
| `vader_vs_cardiff_roberta` | 0.4657 | 0.4738 | 61.00% | 0.6010 | 0.4263 |
| `baseline_roberta_vs_cardiff_roberta` | 0.9235 | 0.9341 | 89.00% | 0.8759 | 0.1601 |

Three-way label agreement: 57.00%.

Sample with all model outputs: `D:\GW_UNIVERSITY\AIS\Social_Listener\Env\Social_Listener_V1\UOG_AIS_SOCIAL_LISTENER\output\results\phase3\three_model_comparison_sample.parquet`.
