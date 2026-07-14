# Phase 2.5 Production Reliability Examination Report

## Scope

- Run mode: `full`; evaluated rows: 1,331,317.
- This is candidate-hashtag-centered discourse from 2020-10-15 through 2020-11-08.
- Full results are diagnostic findings for the Phase 2 output, not mitigation decisions.
- No record was filtered, weighted, relabeled, sentiment-reversed, routed, or otherwise mitigated.
- Every mitigation decision remains `pending`.

## Criterion score availability

| risk_score | available_count | unavailable_count | mean | minimum | maximum |
| --- | --- | --- | --- | --- | --- |
| textual_evidence_risk | 1331317 | 0 | 0.4072017283136423 | 0.18999860664289572 | 0.9189314666103816 |
| sentiment_ambiguity_risk | 1331317 | 0 | 0.6657250627761833 | 0.0 | 1.0 |
| sarcasm_irony_risk | 1331317 | 0 | 0.014815404595599695 | 0.0 | 0.75 |
| user_representativeness_risk | 1331317 | 0 | 0.7479779055589911 | 0.31022196926579393 | 0.997277901381487 |
| duplicate_amplification_risk | 1331317 | 0 | 0.034846321349460724 | 0.0 | 0.9601014510157735 |
| spatial_validity_risk | 926969 | 404348 | 0.7211384630985502 | 0.0 | 1.0 |
| temporal_coverage_risk | 1331317 | 0 | 0.599453386519615 | 0.0016666666666666668 | 0.9991666666666666 |
| model_suitability_risk | 5000 | 1326317 | 0.22469862208536243 | 0.007299270557425908 | 0.5821882320418954 |

## Evidence availability

| evidence | available_count | unavailable_count |
| --- | --- | --- |
| prior_url_evidence_available | 0 | 1331317 |
| language_diagnostic_available | 5000 | 1326317 |
| roberta_diagnostic_available | 5000 | 1326317 |
| baseline_roberta_diagnostic_available | 0 | 1331317 |
| location_mapping_available | 926969 | 404348 |

## Approved activity-threshold provenance

- Source: Phase 2 pre-filter audit over 483,175 users.
- Approved threshold: 9.0 tweets per active day.
| method | threshold | users_removed | users_removed_pct | tweets_removed | tweets_removed_pct | approved | provenance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| p99_5 | 9.0 | 2227 | 0.4609096083 | 222366 | 12.724501042 | True | Phase 2 pre-filter user audit |

## Duplicate and amplification layers

1. Phase 2 raw exact-duplicate removal is retained as historical provenance.
2. Post-cleaning exact-text convergence is counted separately.
3. Normalized repetition is counted separately.
4. Near-duplicate and cross-user repetition are lexical amplification proxies, not confirmed coordination.

## Corrections from the notebook prototype

- User activity uses the Phase 2 pre-filter audit, not the already-filtered sentiment data.
- URL provenance remains unavailable because no validated original-text join is configured.
- Missing language evidence remains unavailable and produces null language risk.
- Missing RoBERTa evidence remains unavailable and produces null model risk.
- Exact, post-cleaning, normalized, near-duplicate, and cross-user repetition layers are separated.
- Availability counts are published explicitly; no missing evidence is replaced with `0.5`.

## Interpretation limits

- RoBERTa is model-comparison evidence, not human ground truth.
- Model agreement is not accuracy, hashtag membership is not stance, and language is not location.
- Rule-based sarcasm and near-duplicate signals are diagnostic proxies only.
- Missing state evidence limits state analysis but does not invalidate national temporal analysis.
