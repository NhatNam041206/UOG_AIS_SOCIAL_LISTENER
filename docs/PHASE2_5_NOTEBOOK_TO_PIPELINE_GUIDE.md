# Phase 2.5 Notebook-to-Pipeline Transfer Guide

This guide explains how to transfer the experimental notebook
`notebooks/phase2_5_dataset_limitation_experiment.ipynb` into the production
Phase 2.5 Python implementation.

Phase 2.5 is examination-only. It measures dataset limitations and writes
diagnostic evidence. It must not delete records, correct sentiment, route models,
downweight users, or finalize mitigation decisions.

## Notebook Purpose

Use the notebook first for fast integration and quick evaluation. It:

- loads the Phase 2 cleaned dataset, or the Phase 3 sentiment dataset when
  optional VADER fields are already available;
- optionally includes the Phase 3 RoBERTa validation sample so model-disagreement
  diagnostics can be examined without treating RoBERTa as ground truth;
- infers available columns from the current project schema;
- computes provisional 0-1 risk scores for the eight Phase 2.5 criteria;
- writes the expected Phase 2.5 artifact layout under `data/02_5_reliability`,
  `output/results/phase2_5`, `output/reports/phase2_5`, and
  `output/graphs/phase2_5`;
- keeps every mitigation field marked `pending`.

The notebook defaults to a bounded sample for speed. Set `RUN_FULL_DATASET = True`
inside the configuration cell when the scoring logic is ready to run across the
complete cleaned dataset.

## Transfer Map

Move notebook sections into production modules as follows:

| Notebook section | Production module |
| --- | --- |
| Project setup, paths, column inference | `dataset_schema_profiler.py` |
| Normalization helpers | `risk_score_normalizer.py` |
| Text indicators and textual risk | `textual_usability_profiler.py` |
| Ambiguity indicators | `sentiment_ambiguity_profiler.py` |
| Sarcasm/irony indicators | `sarcasm_irony_risk_profiler.py` |
| User activity and concentration | `user_representativeness_profiler.py` |
| Duplicate and near-duplicate proxies | `duplicate_amplification_profiler.py` |
| Location confidence heuristics | `spatial_validity_profiler.py` |
| Hourly volume and event-window diagnostics | `temporal_coverage_profiler.py` |
| VADER/RoBERTa disagreement placeholders | `model_suitability_placeholder.py` |
| Summary CSVs, phase linkage, mitigation register | `phase_linkage_builder.py` and `mitigation_register_builder.py` |
| Markdown report | `reliability_report_generator.py` |
| PNG figures | `reliability_visualizer.py` |
| End-to-end orchestration | `reliability_runner_controller.py` |

## Production Directory Target

Create this module package:

```text
src/phase2_5_reliability/
```

Expected files:

```text
__init__.py
reliability_runner_controller.py
dataset_schema_profiler.py
textual_usability_profiler.py
sentiment_ambiguity_profiler.py
sarcasm_irony_risk_profiler.py
user_representativeness_profiler.py
duplicate_amplification_profiler.py
spatial_validity_profiler.py
temporal_coverage_profiler.py
model_suitability_placeholder.py
risk_score_normalizer.py
threshold_position_analyzer.py
phase_linkage_builder.py
mitigation_register_builder.py
reliability_report_generator.py
reliability_visualizer.py
```

Create the runner:

```text
verify/phase2_5/run_phase2_5.py
```

Create focused tests:

```text
verify/phase2_5/tests/
```

## Configuration Target

Move notebook constants into:

```text
configs/phase2_5_reliability.yaml
```

Recommended keys:

```yaml
input:
  cleaned_tweets_path: data/02_interim/twitter_cleaned.parquet
  sentiment_tweets_path: data/02_interim/twitter_sentiment.parquet
  roberta_validation_sample_path: output/results/phase3/sentiment_validation_sample.parquet
  prefer_phase3_sentiment_if_available: true

output:
  data_dir: data/02_5_reliability
  results_dir: output/results/phase2_5
  reports_dir: output/reports/phase2_5
  graphs_dir: output/graphs/phase2_5

columns:
  tweet_id: id
  text: tweet
  timestamp: date
  user_id: user_id
  user_location: user_loc
  candidate: candidate

execution:
  run_full_dataset: true
  random_seed: 2020

normalization:
  default_method: percentile_rank
  provisional_tier_bands: [0.25, 0.50, 0.75]

threshold_analysis:
  candidate_fixed_tweets_per_active_day: [9, 25, 50, 75, 100, 175]
  candidate_percentiles: [0.75, 0.90, 0.95, 0.99]
  mark_thresholds_as_provisional: true

mitigation:
  execute_mitigation: false
  mitigation_status_default: pending
```

Do not hard-code notebook paths in source modules once the YAML file exists.

## Output Contract

The production runner should write these data files:

```text
data/02_5_reliability/tweet_dataset_limitation_scores.parquet
data/02_5_reliability/user_activity_diagnostics.parquet
data/02_5_reliability/location_confidence_diagnostics.parquet
data/02_5_reliability/temporal_coverage_diagnostics.parquet
data/02_5_reliability/duplicate_amplification_diagnostics.parquet
data/02_5_reliability/phase2_5_schema_manifest.json
```

It should write these result files:

```text
output/results/phase2_5/dataset_limitation_summary.csv
output/results/phase2_5/criterion_score_summary.csv
output/results/phase2_5/threshold_position_summary.csv
output/results/phase2_5/risk_correlation_matrix.csv
output/results/phase2_5/candidate_balance_by_risk.csv
output/results/phase2_5/phase_linkage_matrix.csv
output/results/phase2_5/mitigation_decision_register.csv
```

It should write this report:

```text
output/reports/phase2_5/phase2_5_dataset_limitation_report.md
```

It should write the core figures:

```text
output/graphs/phase2_5/01_user_activity_distribution.png
output/graphs/phase2_5/02_textual_usability_risk_distribution.png
output/graphs/phase2_5/03_location_confidence_distribution.png
output/graphs/phase2_5/04_temporal_volume_and_event_windows.png
output/graphs/phase2_5/05_duplicate_amplification_distribution.png
output/graphs/phase2_5/06_criterion_risk_heatmap.png
```

## Extraction Order

1. Move path and column inference into `DatasetSchemaProfiler`.
2. Move `percentile_rank`, `safe_divide`, and risk tier helpers into
   `RiskScoreNormalizer`.
3. Extract one profiler at a time, starting with textual usability because later
   criteria reuse text indicators.
4. Give every profiler a simple interface:

```python
def profile(self, dataframe: pd.DataFrame, context: ReliabilityContext) -> pd.DataFrame:
    ...
```

5. Keep profilers pure where possible. They should return diagnostics rather than
   write files directly.
6. Put file writing, report writing, graph rendering, and manifest creation in
   `ReliabilityRunnerController`.
7. Add focused tests for each profiler before relying on full-run output.

## Required Guardrails

The production implementation must preserve these behaviors from the notebook:

- risk scores remain continuous 0-1 values;
- separate risk dimensions remain separate;
- every mitigation status remains `pending`;
- low-confidence records are not deleted;
- sarcastic or ambiguous tweets are not corrected;
- RoBERTa output, when available, is treated as model-comparison evidence rather
  than human truth;
- threshold summaries describe distribution positions, not final exclusion rules.

## Verification Plan

Add tests for:

- column inference with missing optional columns;
- risk normalizers on empty, constant, and skewed series;
- text indicator counts for hashtags, mentions, URLs, emoji, punctuation, and short
  text;
- user concentration metrics and top-user share calculations;
- duplicate proxy behavior on exact and normalized duplicate text;
- location confidence behavior for missing, country-only, single-state, multi-state,
  and joke locations;
- event-window and hourly spike calculations;
- mitigation register defaulting every decision to `pending`.

Then run:

```powershell
.venv\Scripts\python.exe -m unittest discover -s verify\phase2_5\tests -v
.venv\Scripts\python.exe verify\phase2_5\run_phase2_5.py
```

## Notebook Decommission Rule

After the production runner and tests are complete, keep the notebook as an
explanatory artifact only. The authoritative Phase 2.5 execution path should be
`verify/phase2_5/run_phase2_5.py`, not manual notebook execution.
