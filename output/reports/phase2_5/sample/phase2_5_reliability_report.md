# Phase 2.5 Production Reliability Examination Report

## Scope

- Run mode: `sample`; evaluated rows: 54,812.
- This is candidate-hashtag-centered discourse from 2020-10-15 through 2020-11-08.
- Sample results are verification evidence and must not be cited as full-dataset findings.
- No record was filtered, weighted, relabeled, sentiment-reversed, routed, or otherwise mitigated.
- Every mitigation decision remains `pending`.

## Criterion score availability

| risk_score | available_count | unavailable_count | mean | minimum | maximum |
| --- | --- | --- | --- | --- | --- |
| textual_evidence_risk | 54812 | 0 | 0.4073959625629424 | 0.1902867985112749 | 0.9188460860152278 |
| sentiment_ambiguity_risk | 54812 | 0 | 0.666540752025104 | 0.0008000000000000229 | 1.0 |
| sarcasm_irony_risk | 54812 | 0 | 0.014882689921914908 | 0.0 | 0.75 |
| user_representativeness_risk | 54812 | 0 | 0.7483509274396437 | 0.31022196926579393 | 0.997277901381487 |
| duplicate_amplification_risk | 54812 | 0 | 0.017886138071955045 | 0.0 | 0.8712397636412484 |
| spatial_validity_risk | 38037 | 16775 | 0.7250308909745774 | 0.0 | 1.0 |
| temporal_coverage_risk | 54812 | 0 | 0.6026609088118714 | 0.0016666666666666668 | 0.9991579861111111 |
| model_suitability_risk | 5000 | 49812 | 0.22469862208536237 | 0.007299270557425908 | 0.5821882320418954 |

## Evidence availability

| evidence | available_count | unavailable_count |
| --- | --- | --- |
| prior_url_evidence_available | 0 | 54812 |
| language_diagnostic_available | 5000 | 49812 |
| roberta_diagnostic_available | 5000 | 49812 |
| baseline_roberta_diagnostic_available | 0 | 54812 |
| location_mapping_available | 38037 | 16775 |

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
