# 2020 Election Sentiment Analysis

A modular, object-oriented social-listening pipeline for candidate-hashtag-centered
Twitter discourse surrounding the 2020 US presidential election.

## Scope and current status

The verified Twitter source covers `2020-10-15` through `2020-11-08`. It is not a
complete Twitter firehose or a population-representative public-opinion sample.
Sentiment outputs are therefore interpreted as social-listening estimates rather
than voter sentiment ground truth or election predictions.

| Workstream | Current status |
| --- | --- |
| Phase 1 ingestion | v1 closed operationally; v2 target extension through Nov 15 approved, compatible Nov 9-15 source pending |
| Phase 2 preprocessing | Closed; complete-dataset artifacts and 12 tests verified |
| Phase 2.5 reliability examination | v1 sample and 1,331,317-row full examination artifacts exist with no mitigation; deferred until after the Phase 1-5 MVP |
| Phase 3 sentiment | Closed; complete VADER data, 5,000-record RoBERTa comparison, 29 tests and 7 closure checks verified |
| Phase 4 spatial-temporal aggregation | Planning; no production package or executed Phase 4 artifacts yet |
| Phase 5 statistical evaluation | Planned |

## Experiment notebooks

Quick, executable walkthroughs are available in `notebooks/`, including a Phase 1
database EDA notebook for completeness checks before interpretation and integrated
Phase 2/Phase 3 method notebooks. See `docs/EXPERIMENT_NOTEBOOKS.md` for their
scope and usage.

## Manual setup

1. Create and activate a virtual environment:
   - `python -m venv venv`
   - `source venv/bin/activate` (Linux/macOS) or `venv/Scripts/activate` (Windows)
2. Install dependencies:
   - `pip install -r requirements.txt`

## Phase 1 flexible ingestion

Stream readers are format adapters and do not define a fixed extraction schema.
Reader-specific pandas options and controller-owned transformation policy are supplied
when the ingestion service is executed:

```python
from src.phase1_ingestion.ingestion_runner_controller import IngestionRunnerController
from src.phase1_ingestion.stream_readers_model import CsvStreamReader

controller = IngestionRunnerController(CsvStreamReader())
dataframe = controller.run(
    "data/01_raw/tweets.csv",
    {
        "reader_options": {"encoding": "utf-8"},
        "fields": ["id", "date", "tweet", "user_loc"],
        "timestamp_columns": "date",
    },
)
```

Supported controller options:

- `reader_options`: forwarded to the configured pandas CSV or JSON reader.
- `fields`: optional output projection applied after schema mapping.
- `timestamp_columns`: optional column name or sequence of columns converted to UTC.
- `timestamp_errors`: timestamp conversion behavior, either `raise` or `coerce`.

A schema mapper can be injected into `IngestionRunnerController` when a source needs
field renaming or structural transformation. Without one, the controller operates on
the source columns directly.

## Phase 1 execution and verification

Dataset-specific configuration and verification are kept outside production modules:

```powershell
.venv\Scripts\python.exe verify\phase1\run_phase1.py
```

The complete Phase 1 run reads:

- **Stream A - Social media:** `data/01_raw/twitter/hashtag_donaldtrump.csv`
  and `data/01_raw/twitter/hashtag_joebiden.csv`.
- **Stream B - Exogenous events:**
  `data/01_raw/political_events/political_events.csv`.
- **Stream C - Electoral benchmarks:**
  `data/01_raw/electoral_returns/electoral_returns.csv`.

All three original-PDF stream families are present, but each remains available with
documented alignment gaps. See `docs/PHASE1_DATA_STREAM_ALIGNMENT.md` for the audit
and `docs/plans/ORIGINAL_PDF_ALIGNMENT_PLAN.md` for the phase-by-phase cleanup plan.
The living discussion, decision register, detailed implementation work packages,
and separate-agent prompts are maintained in
`docs/plans/PDF_BASELINE_REFINEMENT_AND_IMPLEMENTATION_HANDOFF.md`.

It writes aligned Parquet outputs to `data/02_interim/`, PNG research figures to
`output/graphs/phase1/`, a manifest to `output/results/phase1/`, and an ingestion
report to `output/reports/phase1/`.

## Phase 2 preprocessing

Phase 2 operates only on the aligned Phase 1 Twitter Parquet files. Its ordered rules
are:

1. Audit empirical user activity using `tweets_per_active_day`, percentiles, robust
   fences, a log-z threshold, and MAD.
2. Select and document a reproducible threshold at or above P99 using explicit
   retention safeguards and the smallest safeguard exceedance fallback, then reject
   all records from users above that threshold.
3. Reject accounts created within 30 days of the November 3, 2020 election whenever
   the configured `user_created_at` field is present.
4. Remove exact tweet-text duplicates, retaining the first observed record.
5. Remove HTML and URLs, then reject empty or invalid-Unicode text while preserving
   capitalization, punctuation, emoji, and emphasis marks for downstream VADER scoring.

Run the complete Phase 2 workflow:

```powershell
.venv\Scripts\python.exe verify\phase2\run_phase2.py
```

It reads `data/02_interim/twitter_donald_trump.parquet` and
`data/02_interim/twitter_joe_biden.parquet`, then writes:

- `data/02_interim/twitter_cleaned.parquet`
- `output/graphs/phase2/activity_distribution_with_thresholds.png`
- `output/graphs/phase2/user_contribution_curve.png`
- `output/graphs/phase2/derived_threshold_comparison.png`
- `output/graphs/phase2/filtering_tradeoff_users_vs_tweets.png`
- `output/graphs/phase2/daily_volume_before_after_filtering.png`
- `output/results/phase2/user_activity_metrics.parquet`
- `output/results/phase2/user_activity_threshold_audit.json`
- `output/results/phase2/preprocessing_manifest.json`
- `output/reports/phase2/user_activity_threshold_report.md`
- `output/reports/phase2/preprocessing_report.md`

The current Phase 1 interim schema does not include account-creation timestamps, so the
runner records that the 30-day account-age rule was unavailable rather than changing
Phase 1 or silently inferring account age.

This is a Phase 2 preprocessing-validation audit only. It does not create or validate
Phase 5 ITSA, OLS, model-performance, or robustness results.

Run the focused Phase 2 tests:

```powershell
.venv\Scripts\python.exe -m unittest discover -s verify\phase2\tests -v
```

## Phase 2.5 reliability examination

Phase 2.5 now has a configuration-driven production package under
`src/phase2_5_reliability/`, using `configs/phase2_5_reliability.json` and the runner
`verify/phase2_5/run_phase2_5.py`. The first approved package also adds the Phase 3
model-artifact inventory and a run-ID-separated output contract for future
three-model sample/full runs.

The production runner was first verified in deterministic sample mode:

```powershell
.venv\Scripts\python.exe verify\phase2_5\run_phase2_5.py --mode sample --seed 2020
```

The verified sample contains 54,812 distinct records: a 50,000-row random sample
combined with the existing 5,000-row RoBERTa validation sample and reconciled by
tweet ID. URL evidence is available for 0 rows because no safe original-text join is
configured; language and latest-RoBERTa evidence are each available for 5,000 rows.
Missing evidence remains null. The sample is verification evidence only and is not a
full-dataset finding.

The implemented contract is documented in
`docs/PHASE2_5_NOTEBOOK_TO_PIPELINE_GUIDE.md` and
`docs/plans/PHASE2_5_PRODUCTION_AND_PHASE4_ENTRY_PLAN.md`. A later v1 full run
manifest records 1,331,317 input and output rows, canonical-column preservation,
and `execute_mitigation=false`. Every mitigation decision remains `pending`.

The current PDF-refinement decision treats Phases 1-5 as the MVP. Existing Phase
2.5 artifacts are preserved as v1 refinement evidence, but Phase 2.5 is no longer a
gate before Phase 4. A v2 Phase 2.5 rerun or mitigation review is deferred until
after the MVP compliance audit.

Run the focused Phase 2.5 tests:

```powershell
.venv\Scripts\python.exe -m unittest discover -s verify\phase2_5\tests -v
```

The current suite contains 16 Phase 2.5 tests. Across Phases 1, 2, 3, and 2.5, 70
tests pass.

## Phase 3 VADER scoring

The first two Phase 3 entry stages validate the Phase 2 cleaned-data contract and
score the complete cleaned dataset with VADER:

```powershell
.venv\Scripts\python.exe verify\phase3\validate_phase2_input_contract.py
.venv\Scripts\python.exe verify\phase3\run_phase3_vader.py
```

The VADER stage preserves every Phase 2 field and appends:

- `vader_negative`
- `vader_neutral`
- `vader_positive`
- `vader_compound`
- `vader_label`

It writes:

- `data/02_interim/twitter_sentiment.parquet`
- `output/results/phase3/sentiment_manifest.json`
- `output/results/phase3/vader_output_validation.json`
- `output/reports/phase3/sentiment_report.md`
- `output/graphs/phase3/vader_sentiment_distribution.png`
- `output/graphs/phase3/sentiment_distribution_by_candidate.png`

These are descriptive VADER outputs. The later 5,000-record RoBERTa comparison and
Phase 3 closure stages described below are now complete.

Run the focused Phase 3 tests:

```powershell
.venv\Scripts\python.exe -m unittest discover -s verify\phase3\tests -v
```

Create the reproducible 5,000-record Phase 3 validation sample:

```powershell
.venv\Scripts\python.exe verify\phase3\run_phase3_validation_sample.py
```

The sampler uses proportional Hamilton largest-remainder allocation across candidate
stream by UTC-date strata, followed by random selection without replacement using
the fixed seed `2020`. It writes:

- `output/results/phase3/sentiment_validation_sample.parquet`
- `output/results/phase3/validation_sample_manifest.json`
- `output/reports/phase3/validation_sample_report.md`

The manifest records the complete 50-stratum allocation and a stable source-row
checksum for reproducibility.

Verify the required RoBERTa model and inference backend:

```powershell
.venv\Scripts\python.exe verify\phase3\verify_roberta_setup.py
```

The setup uses the ready CardiffNLP model configured in
`configs/phase3_roberta_model.json`, currently
`cardiffnlp/twitter-roberta-base-sentiment-latest`, with PyTorch on CPU, explicit
negative/neutral/positive label mapping, and a maximum input length of 512 tokens.

Score the validation sample with RoBERTa:

```powershell
.venv\Scripts\python.exe verify\phase3\run_phase3_roberta_inference.py
```

This appends probabilities, a comparable continuous score, label, token count, and
truncation flag to the validation-sample Parquet file. Canonical tweet text remains
unchanged.

Calculate model-agreement and language-suitability metrics:

```powershell
.venv\Scripts\python.exe verify\phase3\run_phase3_sentiment_validation.py
```

The validation reports Pearson and Spearman correlation, label agreement, macro-F1
agreement, confusion matrices, candidate/day metrics, likely-English sensitivity
metrics, and the largest score disagreements. These measure agreement between two
models; RoBERTa is not treated as human ground truth.

Generate the final validation figures and run the Phase 3 closure gate:

```powershell
.venv\Scripts\python.exe verify\phase3\close_phase3.py
```

Phase 3 closure verifies every required artifact, reconciles the final manifest,
generates the score-comparison and confusion-matrix figures, and confirms
`data/02_interim/twitter_sentiment.parquet` is ready for Phase 4.

The current July 3 Phase 3 artifacts report Pearson `r = 0.4708`, 59.66% label
agreement, and a 68.72% likely-English share on the 5,000-record validation sample.
These values measure VADER/RoBERTa agreement, not accuracy. A separate 100-record
three-model comparison is exploratory and does not replace the primary Phase 3
validation run.

Before Phase 4 implementation, the current plan is to acquire and validate the
approved November 9-15 Twitter extension, execute the versioned Phase 1-3
regeneration path, and then define the Phase 4 temporal and state contracts. Phase
2.5 is a post-MVP refinement.
