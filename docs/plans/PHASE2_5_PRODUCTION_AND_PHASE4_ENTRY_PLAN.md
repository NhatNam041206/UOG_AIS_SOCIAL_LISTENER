# Phase 2.5 Production and Phase 4 Entry Plan

Plan date: 2026-07-10

Plan status: **A1-A5 production package complete; v1 full execution exists; mitigation decisions remain pending**

## Purpose

This plan reconciles the live codebase with the current knowledge-source guardrails.
It identifies the next bounded implementation work that can be executed without
turning provisional reliability indicators into unsupported filtering, weighting,
sentiment correction, model routing, or fine-tuning.

The immediate implementation target is a production-quality, examination-only
Phase 2.5. Phase 4 implementation should begin only after the Phase 2.5 runner has
published trustworthy provenance and availability information.

## Controlling Scope

- Dataset: candidate-hashtag-centered Kaggle US Election 2020 Tweets.
- Verified time window: `2020-10-15` through `2020-11-08`.
- Realistic period split:
  - pre-election: `2020-10-15` through `2020-11-02`;
  - election day: `2020-11-03`;
  - immediate post-election: `2020-11-04` through `2020-11-08`.
- Sentiment values are estimates. VADER/RoBERTa results measure model agreement, not
  human-validated accuracy.
- High-volume activity is a representativeness concern, not confirmed bot detection.
- Phase 2.5 measures limitations. It does not execute mitigation.

## Verified Starting Point

| Component | Verified state | Evidence boundary |
| --- | --- | --- |
| Phase 1 | Operationally closed; PDF-alignment cleanup active; 1,747,542 valid Twitter records | 14 tests currently pass |
| Phase 2 | Closed; 1,331,317 cleaned records; threshold `9.0` | 12 tests currently pass; 483,175-user pre-filter activity audit exists |
| Phase 2.5 | Production package implemented | Deterministic 54,812-record sample verified twice; 16 tests pass; v1 full run manifest records 1,331,317 input and output rows with no mitigation |
| Phase 3 | Closed; full VADER plus 5,000-record RoBERTa comparison | 29 tests and 7 closure checks currently pass |
| Phase 4 | No implementation | No source package, runner, tests, report, manifest, or executed artifacts |
| Phase 5 | Planned only | No statistical results may be claimed |

Current Phase 3 controlling metrics are Pearson `r = 0.4708`, 59.66% label
agreement, and 68.72% likely-English exposure in the comparison sample. The
100-record three-model run is exploratory.

## Selected Near-Term Scope

Execute the following work first:

1. productionize the eight Phase 2.5 diagnostic dimensions;
2. correct provenance and missing-availability weaknesses found in the notebook;
3. run deterministic sample verification and stop for review;
4. preserve the v1 complete-dataset examination as refinement evidence;
5. review results without choosing mitigation;
6. define Phase 4 input, coverage, period, event, and state-mapping contracts later;
7. run a dataset-first term/keyness audit before final topic claims.

Human annotation, sentiment-model fine-tuning, automated sarcasm correction,
confidence weighting, and record exclusion are outside this near-term scope.

## Work Package 1: Production Contract and Configuration

Create:

```text
configs/phase2_5_reliability.json
src/phase2_5_reliability/
verify/phase2_5/run_phase2_5.py
verify/phase2_5/tests/
```

The configuration must distinguish these inputs:

| Input | Purpose |
| --- | --- |
| `data/02_interim/twitter_sentiment.parquet` | Full tweet-level VADER and text diagnostics |
| `output/results/phase2/user_activity_metrics.parquet` | Pre-filter user-activity distributions and threshold provenance |
| `output/results/phase2/user_activity_threshold_audit.json` | Approved Phase 2 threshold trade-offs |
| `output/results/phase3/sentiment_validation_sample.parquet` | RoBERTa, language, ambiguity, and model-disagreement subset |
| `data/02_interim/political_events.parquet` | Event-window coverage diagnostics |
| Phase 1/raw text, if joined safely | Optional URL and pre-cleaning evidence only |

Required run modes:

```text
smoke   = tiny deterministic fixture or bounded data slice
sample  = reproducible notebook-comparison run
full    = all 1,331,317 sentiment records
```

Every manifest must record the mode, source row counts, score availability counts,
input checksums or stable identifiers where practical, configuration, and
`execute_mitigation = false`.

## Work Package 2: Profiler Extraction and Corrections

Implement pure or mostly pure profilers for:

| Diagnostic dimension | Production requirement |
| --- | --- |
| Textual evidence | Preserve short/hashtag/mention/emoji/punctuation indicators; mark URL evidence unavailable when original text is absent |
| Sentiment ambiguity | Keep VADER-based and RoBERTa-based components separate; preserve nulls outside the comparison subset |
| Sarcasm/irony risk | Retain rule signals as provisional proxies only; no `is_sarcastic` truth label and no sentiment inversion |
| User representativeness | Join approved pre-filter Phase 2 user metrics; do not recompute threshold evidence only from already-filtered data |
| Duplicate/amplification | Separate Phase 2 exact-duplicate removal history from residual normalized/near-duplicate patterns |
| Spatial validity | Produce transparent mapping evidence and confidence; keep language suitability separate from location |
| Temporal coverage | Measure volume, missing bins, candidate balance, and distance to curated events without smoothing or exclusions |
| Model suitability | Calculate only where RoBERTa evidence exists; report 5,000-record availability rather than imputing full coverage |

Shared utilities must handle empty, constant, skewed, and missing series without
silently converting unavailable evidence into low risk.

Do not make a global score the primary output. A reporting-only summary may remain if
its limitations are explicit, but task-specific dimensions control later tests.

## Work Package 3: Verification Before Full Execution — Complete

Minimum test groups:

1. schema inference and required/optional field behavior;
2. normalization bounds and missing-value preservation;
3. textual indicator fixtures;
4. pre-filter user-metric joins and threshold provenance;
5. exact versus normalized/near-duplicate fixtures;
6. missing, national-only, one-state, multi-state, non-US, and fictional locations;
7. event-window and missing-time-bin fixtures;
8. RoBERTa/model-disagreement availability limited to matched records;
9. mitigation register defaults;
10. row-preservation and no-mutation/no-mitigation integration tests;
11. deterministic sample-run replay;
12. required artifact and manifest contract checks.

The sample-parity gate does not require reproducing every notebook risk value if the
production correction intentionally changes a flawed proxy. Every difference must be
explained in the run report.

Current result: 16 Phase 2.5 tests pass. Two sample executions with seed `2020`
produced 54,812 rows and the identical checksum
`254420133e8e9dd1785776dd539903f6a6da967f2faf290bf1ffdb402460c1ab`.

## Work Package 4: Complete-Dataset Examination — v1 Complete

After tests and sample review passed, the production runner was executed over all
1,331,317 sentiment records.

This work package was deliberately not executed in A1-A5, but a later v1 full run
now exists. It is refinement evidence only and does not approve mitigation or change
the current Phase 1-5 MVP ordering.

Full-run acceptance gates:

- output contains exactly 1,331,317 tweet rows;
- canonical tweet IDs, dates, text, users, candidate streams, and VADER values are
  preserved;
- every published score is within `[0, 1]` where defined;
- unavailable indicators remain null and have published availability counts;
- the RoBERTa/model-suitability coverage count is reconciled to the matched Phase 3
  comparison records;
- the user-threshold section cites the 483,175-user Phase 2 pre-filter audit;
- every mitigation status remains `pending`;
- no tweet is deleted, reweighted, relabeled, sentiment-reversed, or model-routed;
- report, CSVs, Parquet data, figures, and run manifest agree.

The complete run establishes limitation distributions. It does not establish that a
high-risk record is false, invalid, automated, sarcastic, or unusable for every task.

## Work Package 5: Review Gate, Not Mitigation

Review the full results using a decision register with one row per criterion:

```text
criterion
observable_evidence
availability
affected_downstream_claim
validation_needed
sensitivity_test_needed
mitigation_status
decision
```

At this gate, `mitigation_status` remains `pending`. The review should only decide
which later evidence is required, such as manual annotation, model benchmarking,
aggregation comparison, or statistical sensitivity testing.

## Work Package 6: Phase 4 Entry Contract

Define Phase 4 before implementing aggregation:

| Contract area | Required decision/evidence |
| --- | --- |
| Temporal grain | Daily primary summaries; justify any hourly event-window analysis |
| Period labels | Use the verified pre-election/election-day/immediate-post-election split |
| Event windows | Configure pre/post windows and preserve event identity; avoid causal wording |
| Candidate streams | Report stream counts and balance; hashtag membership is not stance |
| State mapping | Publish mapped, national-only, ambiguous, non-US, and missing coverage before choosing a primary state subset |
| Reliability fields | Carry separate scores and availability flags into aggregates |
| Aggregation variants | Define tweet-weighted, user-weighted, duplicate-aware, and location-confidence variants as later sensitivity analyses, not Phase 2.5 corrections |
| Minimum coverage | Set and justify time/state sample-size gates before OLS or event interpretation |
| Outputs | Define canonical temporal, event, state, and coverage matrices plus manifest/report schemas |

Phase 4 must not call state-level sentiment representative public opinion. Missing or
weak location can exclude a record from a specific state analysis without making it
invalid for national temporal analysis.

## Work Package 7: Dataset-First Topic Audit

Before writing topic findings, produce:

```text
period_term_keyness.csv
period_hashtag_keyness.csv
topic_period_distribution.csv
topic_sentiment_summary.csv
topic_reliability_summary.csv
candidate_topic_comparison.csv
topic_review_notes.md
```

Start with period and candidate counts, n-grams, hashtags, and log-odds/keyness.
Topic modeling may follow only with coherence checks and manual label evidence.
Fraud, protest, legitimacy, lawsuits, vote counting, or topic dominance must remain
hypotheses until supported by these outputs.

## Deferred Decision Space

Only after the full diagnostics and later validation may the team consider:

- user-weighted or capped-user aggregation;
- unique-message or near-duplicate-capped aggregation;
- high-confidence state subsets or confidence-weighted spatial sensitivity;
- language-specific or multilingual sentiment models;
- manual annotation and calibration/fine-tuning;
- a validated sarcasm classifier used as a risk feature;
- no mitigation where the downstream finding is stable.

No deferred option is approved by this plan.

## Completion Definition

The A1-A5 milestone is complete when the artifact inventory, non-overwriting Phase 3
contract, JSON production contract, modular profilers, focused tests, deterministic
sample replay, explicit availability/provenance reporting, and no-mitigation checks
are verified. Those gates are now satisfied. The separate full-execution milestone
still requires a 1,331,317-row run and review; it was not executed here. Phase 4
remains in entry planning.
