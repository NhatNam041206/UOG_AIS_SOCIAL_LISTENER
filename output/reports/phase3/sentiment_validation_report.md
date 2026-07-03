# Phase 3 VADER and RoBERTa Agreement Validation Report

## Interpretation Boundary

These metrics measure agreement between VADER and RoBERTa. RoBERTa is not human ground truth, so the metrics must not be described as VADER accuracy.

## Overall Agreement

| Metric | Result |
| --- | ---: |
| Records | 5,000 |
| Pearson r | 0.4708 |
| Pearson 95% CI | [0.4490, 0.4921] |
| Pearson p-value | 2.443e-274 |
| Spearman rho | 0.4452 |
| Label agreement | 59.66% |
| Macro-F1 agreement | 0.5842 |
| Mean absolute score difference | 0.4136 |

## Language Suitability Audit

- Likely-English records: 3,436 (68.72%).
- Language identification uses deterministic `langdetect`; short social-media text may be misclassified.
- Likely-English Pearson r: 0.5204.
- Likely-English label agreement: 55.79%.

## Candidate-Level Agreement

| Candidate stream | Records | Pearson r | Label agreement |
| --- | ---: | ---: | ---: |
| `donald_trump` | 3,111 | 0.4047 | 58.34% |
| `joe_biden` | 1,889 | 0.5449 | 61.83% |

## Disagreement Audit

The 50 records with the largest continuous-score differences are stored in `D:\GW_UNIVERSITY\AIS\Social_Listener\Env\Social_Listener_V1\UOG_AIS_SOCIAL_LISTENER\output\results\phase3\sentiment_disagreements.json` for qualitative review.
