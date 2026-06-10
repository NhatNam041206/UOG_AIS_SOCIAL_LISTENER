# 2020 Election Sentiment Analysis

A modular, object-oriented baseline for a 5-phase sentiment analysis pipeline over 2020 election-related data.

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

- `data/01_raw/twitter/hashtag_donaldtrump.csv`
- `data/01_raw/twitter/hashtag_joebiden.csv`
- `data/01_raw/political_events/political_events.csv`
- `data/01_raw/electoral_returns/electoral_returns.csv`

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
