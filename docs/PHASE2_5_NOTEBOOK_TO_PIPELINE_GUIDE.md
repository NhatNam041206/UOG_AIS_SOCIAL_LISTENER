# Phase 2.5 Notebook-to-Pipeline Transfer Guide

Last reconciled with the live codebase: 2026-07-14

This guide records how the experimental notebook
`notebooks/phase2_5_dataset_limitation_experiment.ipynb` was transferred into the
production Phase 2.5 Python implementation. A1-A5 are implemented and sample-verified,
and a later v1 full run exists as refinement evidence.

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

The current recorded notebook artifacts are not a full-run baseline. They contain
54,812 distinct evaluated records after a 50,000-record random sample was combined
with the 5,000-record Phase 3 validation sample and duplicate tweet IDs were
reconciled.

## Corrections Required Before Extraction

Do not copy the notebook into production unchanged. The repository audit identified
these required corrections:

1. **User-threshold provenance:** the notebook recomputes threshold positions from
   `twitter_sentiment.parquet`, which is already filtered at `9.0` tweets per active
   day. Production threshold summaries must reuse
   `output/results/phase2/user_activity_metrics.parquet` and
   `user_activity_threshold_audit.json`, which cover the 483,175-user pre-filter
   audit.
2. **URL availability:** Phase 2 removes URLs from canonical cleaned text. URL-based
   indicators must use preserved original text when a defensible join is available;
   otherwise they must be marked unavailable rather than scored as zero risk.
3. **Language availability:** `detected_language` currently exists only in the
   5,000-record Phase 3 comparison sample. Do not treat ASCII-character share as a
   validated language detector or impute English suitability to other records.
4. **Model-suitability availability:** RoBERTa probability, entropy, confidence, and
   disagreement scores apply only to the 5,000 compared records. Full-run reports
   must retain nulls and publish availability counts.
5. **Duplicate-stage provenance:** exact duplicates were removed during Phase 2.
   Phase 2.5 should report the Phase 2 removal baseline separately from residual
   normalized or near-duplicate amplification in the cleaned data.
6. **Heuristic validation:** location confidence and rule-based sarcasm indicators
   are provisional proxies. They must not become confirmed locations, confirmed
   sarcasm labels, exclusion rules, or sentiment corrections.
7. **Global score:** the notebook's global mean risk is reporting-only. Production
   decisions must use separate, task-specific risk dimensions.

These corrections are production entry gates, not mitigation actions.

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
| VADER/RoBERTa disagreement diagnostics | `model_suitability_profiler.py` |
| Summary CSVs, phase linkage, mitigation register | `phase_linkage_builder.py` and `mitigation_register_builder.py` |
| Markdown report | `reliability_report_generator.py` |
| PNG figures | `reliability_visualizer.py` |
| End-to-end orchestration | `reliability_runner_controller.py` |

## Implemented Production Directory

Create this module package:

```text
src/phase2_5_reliability/
```

Implemented files:

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
model_suitability_profiler.py
risk_score_normalizer.py
phase_linkage_builder.py
mitigation_register_builder.py
reliability_report_generator.py
```

Create the runner:

```text
verify/phase2_5/run_phase2_5.py
```

Create focused tests:

```text
verify/phase2_5/tests/
```

## Implemented Configuration

The production contract uses the existing project JSON style and adds no YAML
dependency:

```text
configs/phase2_5_reliability.json
```

It declares the five required inputs, two optional evidence inputs, the `smoke`,
`sample`, and `full` modes, explicit availability fields, output schemas, Phase 2
provenance, and `execute_mitigation: false`. Validation rejects attempts to enable
mitigation. Full mode was defined in A1-A5 and later executed as a v1 full
examination after review.

## Output Contract

Each mode writes to a labelled directory. The approved sample writes:

```text
data/02_5_reliability/sample/tweet_reliability_scores.parquet
data/02_5_reliability/sample/user_activity_diagnostics.parquet
data/02_5_reliability/sample/location_confidence_diagnostics.parquet
data/02_5_reliability/sample/temporal_coverage_diagnostics.parquet
data/02_5_reliability/sample/duplicate_amplification_diagnostics.parquet
```

It should write these result files:

```text
output/results/phase2_5/sample/criterion_score_summary.csv
output/results/phase2_5/sample/evidence_availability_summary.csv
output/results/phase2_5/sample/threshold_position_summary.csv
output/results/phase2_5/sample/phase_linkage_matrix.csv
output/results/phase2_5/sample/mitigation_decision_register.csv
output/results/phase2_5/sample/phase2_5_schema_manifest.json
output/results/phase2_5/sample/phase2_5_run_manifest.json
```

It should write this report:

```text
output/reports/phase2_5/sample/phase2_5_reliability_report.md
```

The older unlabelled notebook artifacts remain historical prototype evidence and were
not overwritten.

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
- source row preservation for the full tweet-level output;
- null preservation and availability counts for language and RoBERTa-only fields;
- pre-filter Phase 2 provenance for activity-threshold summaries;
- proof that no profiler deletes, relabels, corrects, weights, or routes records;
- deterministic sample-mode parity before the complete-dataset run.

Then run:

```powershell
.venv\Scripts\python.exe -m unittest discover -s verify\phase2_5\tests -v
.venv\Scripts\python.exe verify\phase2_5\run_phase2_5.py --mode sample --seed 2020
```

Current verification: 16 Phase 2.5 tests pass. Two production sample executions
produced 54,812 rows and the same checksum
`254420133e8e9dd1785776dd539903f6a6da967f2faf290bf1ffdb402460c1ab`.
A later v1 full-mode run evaluated 1,331,317 rows with `execute_mitigation=false`.
Those outputs are preserved as refinement evidence and do not change the current
Phase 1-5 MVP ordering.

## Notebook Decommission Rule

The notebook is now an explanatory historical artifact. The authoritative Phase 2.5
execution path is
`verify/phase2_5/run_phase2_5.py`, not manual notebook execution.
