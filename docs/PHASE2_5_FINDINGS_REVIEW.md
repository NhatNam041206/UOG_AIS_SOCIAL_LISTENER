# Phase 2.5 Findings Review

Review date: 2026-07-12

## Review status

Phase 2.5 full-mode outputs are aligned with the planned examination-first purpose. The run preserved all Phase 2 records, produced separate dataset-limitation risk dimensions, reported evidence availability explicitly, and left all mitigation decisions pending.

This review is a decision memo. It does not approve filtering, weighting, relabeling, sentiment reversal, model replacement, fine-tuning, or other mitigation.

## Evidence base

| Artifact | Path |
| --- | --- |
| Full run manifest | `output/results/phase2_5/full/phase2_5_run_manifest.json` |
| Full reliability report | `output/reports/phase2_5/full/phase2_5_reliability_report.md` |
| Criterion summary | `output/results/phase2_5/full/criterion_score_summary.csv` |
| Evidence availability summary | `output/results/phase2_5/full/evidence_availability_summary.csv` |
| Threshold summary | `output/results/phase2_5/full/threshold_position_summary.csv` |
| Mitigation register | `output/results/phase2_5/full/mitigation_decision_register.csv` |
| Tweet-level diagnostic scores | `data/02_5_reliability/full/tweet_reliability_scores.parquet` |

Run boundary:

| Item | Value |
| --- | ---: |
| Input Phase 2 records | 1,331,317 |
| Phase 2.5 output records | 1,331,317 |
| Canonical fields preserved | Yes |
| Mitigation executed | No |
| Mitigation decisions | Pending |
| Verified dataset window | 2020-10-15 to 2020-11-08 |
| Dataset framing | Candidate-hashtag-centered discourse |

## Main finding

The full Phase 2.5 results support moving into a reliability-aware Phase 4 entry contract, not into direct mitigation. The strongest observed limitations are user representativeness, spatial validity, sentiment ambiguity, and temporal concentration. These risks may affect aggregation and statistical interpretation, but the current evidence does not justify deleting, reweighting, or correcting records yet.

## Criterion-level findings

| Priority | Criterion | Full-run evidence | Interpretation | Review decision |
| --- | --- | --- | --- | --- |
| Must review before Phase 4 | User representativeness | Mean risk 0.7480; 79.41% high or above; 70.70% severe. Phase 2 approved threshold was 9.0 tweets per active day, derived from the 483,175-user pre-filter audit and corresponding to p99.5. | Tweet-weighted aggregates may overrepresent highly active users. This is activity concentration evidence, not proof of bots or invalid tweets. | Carry forward as a Phase 4 and Phase 5 sensitivity dimension. Do not implement weighting or removal yet. |
| Must review before Phase 4 | Spatial validity | 926,969 records have location-mapping evidence; 404,348 do not. Among available location evidence, mean spatial risk is 0.7211 and 72.11% are high or severe. | State-level aggregation and OLS are more limited than national temporal analysis. Missing or weak location does not make a tweet unusable for national trends. | Phase 4 should separate national temporal analysis from state-level eligibility. Do not globally remove weak-location records. |
| Must review before Phase 4 | Sentiment ambiguity | Mean risk 0.6657; 64.92% high or above; 46.83% severe. | Many records have weak or ambiguous sentiment signal under current full-corpus VADER diagnostics. This is uncertainty evidence, not human-validated error. | Carry into Phase 4 summaries and later annotation planning. Do not relabel or force model replacement. |
| Must review before Phase 5 | Temporal coverage | Mean risk 0.5995; 65.18% high or above; 33.67% severe. | Tweet volume is event-sensitive and uneven across time. This can affect daily/hourly aggregation and event-shock interpretation. | Phase 4 should preserve temporal spikes and label event-window sensitivity. Do not smooth or cap volumes yet. |
| Should monitor | Textual evidence | Mean risk 0.4072; 23.90% high or above; 1.22% severe. | Textual limitations exist but are less dominant than user, spatial, ambiguity, and temporal risks. | Use as annotation and sensitivity metadata. Do not exclude short, hashtag-heavy, or mention-heavy tweets by default. |
| Should monitor | Duplicate and amplification proxy | Mean risk 0.0348; 2.23% high or above; 1.20% severe. Post-clean exact repeated text appears in 4.97% of records; near-duplicate clusters cover 12.34%; cross-user repetition appears in 4.11%. | Most records have low duplicate risk, but a long tail of repeated or near-repeated content could still affect aggregate sentiment. Repetition is not confirmed coordination. | Carry forward as an amplification-sensitivity dimension. Do not apply additional deduplication yet. |
| Evidence-limited | Model suitability | Available for 5,000 records only; mean risk 0.2247 within covered rows; 2.70% high or above; 0.00% severe. | Useful for validation evidence but not a full-corpus transformer result. RoBERTa remains comparison evidence, not ground truth. | Keep unavailable outside the 5,000 validation rows. Do not generalize to all records. |
| Evidence-limited | Sarcasm and irony proxy | Mean risk 0.0148; 0.11% high or above; 0.00% severe. | The low score reflects a weak rule-based proxy, not evidence that sarcasm is rare. | Treat as a flag for future annotation or classifier evaluation only. Do not reverse sentiment. |
| Evidence-unavailable | URL risk | 0 records have validated prior URL evidence. | URL-related risk cannot be measured from the cleaned full dataset without a validated original-text join. | Keep unavailable. Do not impute or guess URL risk. |

## Candidate-stream review

These comparisons describe candidate-hashtag stream properties only. They must not be interpreted as voter support, stance, or public opinion.

| Candidate stream | Records | Share | Notable risk pattern |
| --- | ---: | ---: | --- |
| `donald_trump` | 827,734 | 62.17% | Higher user representativeness risk than the Biden stream: mean 0.7835, 84.53% high or above. Higher spatial validity risk: mean 0.7471. |
| `joe_biden` | 503,583 | 37.83% | Higher temporal coverage risk than the Trump stream: mean 0.6414, 68.81% high or above. Slightly higher textual evidence and duplicate-amplification risk. |

Interpretation: Phase 4 should report candidate-stream coverage and risk summaries alongside sentiment aggregates. It should not use these differences to rebalance, downweight, or correct the data unless later robustness testing justifies that decision.

## Evidence availability review

| Evidence field | Available | Unavailable | Review implication |
| --- | ---: | ---: | --- |
| Location mapping | 926,969 | 404,348 | State-level analysis must be eligibility-aware. National temporal analysis remains available for all records. |
| Latest RoBERTa diagnostics | 5,000 | 1,326,317 | Model-suitability findings are validation-sample evidence only. |
| Language diagnostics | 5,000 | 1,326,317 | Language-suitability evidence is validation-sample evidence only. |
| Baseline RoBERTa diagnostics | 0 | 1,331,317 | Baseline model is not available as a current full diagnostic field. |
| Prior URL evidence | 0 | 1,331,317 | URL risk remains unavailable until original-text evidence is joined safely. |

## Alignment with expected results

| Expected result | Review status |
| --- | --- |
| Full Phase 2.5 examination runs on all Phase 2 records | Satisfied |
| Canonical Phase 2 data are preserved | Satisfied |
| Risk dimensions remain separate | Satisfied |
| Missing evidence is null or unavailable, not imputed | Satisfied |
| RoBERTa and language diagnostics remain limited to 5,000 rows | Satisfied |
| URL evidence is unavailable without validated original-text join | Satisfied |
| Phase 2 user threshold provenance uses the pre-filter audit | Satisfied |
| Duplicate layers are separated from Phase 2 exact duplicate removal history | Satisfied |
| Sarcasm and near-duplicate indicators remain proxies | Satisfied |
| Mitigation register remains pending | Satisfied |

## Recommended next actions

| Order | Action | Purpose | Mitigation status |
| ---: | --- | --- | --- |
| 1 | Create a Phase 4 reliability entry contract | Define which Phase 2.5 fields Phase 4 may consume, which fields are unavailable, and which fields are only for diagnostics. | No mitigation |
| 2 | Add Phase 4 aggregation-readiness summaries | Produce candidate-day/state eligibility summaries so aggregation quality is visible before modeling. | No mitigation |
| 3 | Define robustness variants as planned analyses | Specify future views such as full aggregation, state-eligible aggregation, user-concentration sensitivity, and duplicate-aware sensitivity. | Planning only |
| 4 | Prepare an annotation sampling plan | Target ambiguous, high textual-risk, high temporal-risk, sarcasm-proxy, duplicate-proxy, and model-disagreement records. | No model change yet |
| 5 | Decide whether URL evidence recovery is worth the effort | Either join original text safely or document URL risk as unavailable. | No imputation |

## Mitigation decision

No mitigation should be executed now.

The correct next step is a Phase 4 entry contract and aggregation-readiness design. Mitigation should remain pending until Phase 4 aggregation outputs and Phase 5 robustness tests show whether a limitation materially changes the conclusions.

