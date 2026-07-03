# Phase 2.5 Dataset Limitation Profiling Report

## 1. Executive summary

- Run scope: notebook sample.
- Source records: 1,331,317. Evaluated records: 54,812.
- This report is diagnostic only. No mitigation action was applied.
- Highest mean risk dimensions in this run: user_representativeness_risk, spatial_validity_risk, temporal_coverage_risk.

## 2. Dataset coverage and schema

- Date range: 2020-10-15 00:00:01+00:00 to 2020-11-08 23:59:58+00:00.
- Inferred text column: `tweet`.
- Inferred user column: `user_id`.
- Inferred timestamp column: `date`.
- Inferred location column: `user_loc`.

## 3. Criterion risk summary

| risk_score | available_count | mean | median | std | min | p25 | p75 | max | high_or_severe_share_pct | severe_share_pct | dominant_tier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| textual_usability_risk | 54812 | 0.3732166313945851 | 0.36195801753526335 | 0.08375318327789662 | 0.12786172996528394 | 0.31533338632833274 | 0.42380350757394103 | 0.8103196032846475 | 7.626067284536233 | 0.009122090053273007 | moderate |
| sentiment_ambiguity_risk | 54812 | 0.5601280304823097 | 0.5760172934556098 | 0.1540616306143944 | 0.026867293455609894 | 0.43791222907392546 | 0.6909339601222765 | 0.9400420224281788 | 63.431365394439176 | 2.800481646354813 | high |
| sarcasm_irony_risk | 54812 | 0.06863574582208275 | 0.05749995438954973 | 0.05193326286456642 | 0.05749995438954973 | 0.05749995438954973 | 0.05749995438954973 | 0.7131935068963001 | 0.9632927096256294 | 0.0 | low |
| user_representativeness_risk | 54812 | 0.7589083828567398 | 0.8865902303531524 | 0.2503294206018957 | 0.3628793099847545 | 0.5635632688010358 | 0.971815675709542 | 0.9999023661842408 | 76.30810771363934 | 64.37276508793694 | severe |
| duplicate_amplification_risk | 54812 | 0.5000091220900533 | 0.4643751976452845 | 0.10845007870562874 | 0.4643751976452845 | 0.4643751976452845 | 0.4643751976452845 | 0.9968559196283052 | 12.329416916003796 | 5.533459826315405 | high |
| spatial_validity_risk | 54812 | 0.697121068379187 | 0.75 | 0.3088374870304902 | 0.09999999999999998 | 0.65 | 1.0 | 1.0 | 78.1307013062833 | 74.61322338174122 | high |
| temporal_coverage_risk | 54812 | 0.6016273608053522 | 0.6395529513888889 | 0.27314855139398164 | 0.0016666666666666668 | 0.38295717592592593 | 0.8189547164351851 | 0.9991579861111111 | 65.62249142523535 | 33.89768663796249 | high |
| model_suitability_risk | 5000 | 0.3357440690690525 | 0.3121028960332901 | 0.16353683091666446 | 0.01888312518474964 | 0.20994198867956712 | 0.4582717051879863 | 0.7802425199931942 | 1.5945413413121212 | 0.023717434138509817 | moderate |

## 4. Threshold-position analysis

| threshold_type | threshold_value | percentile_position | users_above_threshold | users_above_threshold_pct | tweets_from_users_above_threshold_pct | mitigation_status |
| --- | --- | --- | --- | --- | --- | --- |
| fixed_tweets_per_active_day | 9.0 | 0.9999937347284005 | 3 | 0.0006265271599523839 | 0.00292943003056372 | pending |
| fixed_tweets_per_active_day | 25.0 | 1.0 | 0 | 0.0 | 0.0 | pending |
| fixed_tweets_per_active_day | 50.0 | 1.0 | 0 | 0.0 | 0.0 | pending |
| fixed_tweets_per_active_day | 75.0 | 1.0 | 0 | 0.0 | 0.0 | pending |
| fixed_tweets_per_active_day | 100.0 | 1.0 | 0 | 0.0 | 0.0 | pending |
| fixed_tweets_per_active_day | 175.0 | 1.0 | 0 | 0.0 | 0.0 | pending |
| empirical_percentile | 1.0 | 0.75 | 99192 |  |  | pending |
| empirical_percentile | 2.0 | 0.9 | 25655 |  |  | pending |
| empirical_percentile | 2.25 | 0.95 | 23430 |  |  | pending |
| empirical_percentile | 4.0 | 0.99 | 4539 |  |  | pending |

## 5. Phase linkage matrix

| criterion | limitation_examined | risk_score | phase3_affected | phase4_affected | phase5_affected | mitigation_status |
| --- | --- | --- | --- | --- | --- | --- |
| Textual usability | Insufficient usable natural language | textual_usability_risk | Yes | Yes | Indirect | Pending |
| Sentiment ambiguity | Unclear or mixed polarity | sentiment_ambiguity_risk | Yes | Yes | Yes | Pending |
| Sarcasm/irony | Literal meaning may differ from intended tone | sarcasm_irony_risk | Yes | Yes | Yes | Pending |
| User representativeness | Hyperactive users may dominate tweet-weighted signals | user_representativeness_risk | Indirect | Yes | Yes | Pending |
| Duplicate/amplification | Repeated content may inflate sentiment signals | duplicate_amplification_risk | Indirect | Yes | Yes | Pending |
| Spatial validity | Weak or ambiguous state mapping | spatial_validity_risk | No | Yes | Yes | Pending |
| Temporal coverage | Event spikes or gaps may distort trends | temporal_coverage_risk | No | Yes | Yes | Pending |
| Model suitability | Models may disagree on difficult language | model_suitability_risk | Yes | Yes | Yes | Pending |

## 6. Pending mitigation decision register

| criterion | risk_score_name | mitigation_status | mitigation_decision |
| --- | --- | --- | --- |
| Textual usability | textual_usability_risk | pending | Pending. Phase 2.5 is examination-only. Decision requires review of diagnostic results and later benchmarking/statistical evidence. |
| Sentiment ambiguity | sentiment_ambiguity_risk | pending | Pending. Phase 2.5 is examination-only. Decision requires review of diagnostic results and later benchmarking/statistical evidence. |
| Sarcasm/irony | sarcasm_irony_risk | pending | Pending. Phase 2.5 is examination-only. Decision requires review of diagnostic results and later benchmarking/statistical evidence. |
| User representativeness | user_representativeness_risk | pending | Pending. Phase 2.5 is examination-only. Decision requires review of diagnostic results and later benchmarking/statistical evidence. |
| Duplicate/amplification | duplicate_amplification_risk | pending | Pending. Phase 2.5 is examination-only. Decision requires review of diagnostic results and later benchmarking/statistical evidence. |
| Spatial validity | spatial_validity_risk | pending | Pending. Phase 2.5 is examination-only. Decision requires review of diagnostic results and later benchmarking/statistical evidence. |
| Temporal coverage | temporal_coverage_risk | pending | Pending. Phase 2.5 is examination-only. Decision requires review of diagnostic results and later benchmarking/statistical evidence. |
| Model suitability | model_suitability_risk | pending | Pending. Phase 2.5 is examination-only. Decision requires review of diagnostic results and later benchmarking/statistical evidence. |

## 7. Examination limitations

- Rule-based sarcasm indicators are risk proxies, not confirmed sarcasm labels.
- Location confidence is heuristic and should be replaced or validated before state-level exclusion decisions.
- RoBERTa diagnostics, when present, measure model disagreement rather than human correctness.
- Sample-mode output is for quick evaluation and should not be cited as full-dataset evidence.

## 8. Next examination steps

- Review the generated score distributions and risk correlations.
- Transfer notebook logic into `src/phase2_5_reliability/` modules using the notebook-to-pipeline guide.
- Add focused tests before running the full production Phase 2.5 runner.
- Keep all mitigation decisions pending until diagnostics, model benchmarking, and statistical sensitivity evidence are reviewed.
