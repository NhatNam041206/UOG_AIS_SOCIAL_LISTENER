# Phase 3 VADER and RoBERTa Agreement Validation Report

## Interpretation Boundary

These metrics measure agreement between VADER and RoBERTa. RoBERTa is not human ground truth, so the metrics must not be described as VADER accuracy.

## Overall Agreement

| Metric | Result |
| --- | ---: |
| Records | 5,000 |
| Pearson r | 0.5037 |
| Pearson 95% CI | [0.4828, 0.5241] |
| Pearson p-value | 4.842e-320 |
| Spearman rho | 0.4630 |
| Label agreement | 60.60% |
| Macro-F1 agreement | 0.5851 |
| Mean absolute score difference | 0.3883 |

## Language Suitability Audit

- Likely-English records: 3,436 (68.72%).
- Language identification uses deterministic `langdetect`; short social-media text may be misclassified.
- Likely-English Pearson r: 0.5453.
- Likely-English label agreement: 56.14%.

## Candidate-Level Agreement

| Candidate stream | Records | Pearson r | Label agreement |
| --- | ---: | ---: | ---: |
| `donald_trump` | 3,111 | 0.4351 | 58.18% |
| `joe_biden` | 1,889 | 0.5835 | 64.58% |

## Disagreement Audit

The 50 records with the largest continuous-score differences are stored in `D:\GW_UNIVERSITY\AIS\Social_Listener\Env\Social_Listener_V1\UOG_AIS_SOCIAL_LISTENER\output\results\phase3\sentiment_disagreements.json` for qualitative review.
