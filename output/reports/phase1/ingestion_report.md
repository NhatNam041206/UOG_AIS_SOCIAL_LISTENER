# Phase 1 Ingestion Report

## Original PDF Data-Stream Contract

| PDF stream | Current inputs | Status |
|---|---|---|
| Stream A - Social media | `twitter_donald_trump`, `twitter_joe_biden` | Available with gaps |
| Stream B - Exogenous events | `political_events` | Available with gaps |
| Stream C - Electoral benchmarks | `electoral_returns` | Available with gaps |

All three PDF stream families are present. `Available with gaps` means that ingestion exists but the current dataset does not yet satisfy every original-PDF requirement. The controlling audit is `docs/PHASE1_DATA_STREAM_ALIGNMENT.md`.

## Summary

| Stream | Records | Invalid CSV Rows |
|---|---:|---:|
| political_events | 4 | 0 |
| electoral_returns | 51 | 0 |
| twitter_donald_trump | 970,765 | 323 |
| twitter_joe_biden | 776,777 | 296 |

## Twitter Coverage

- `twitter_donald_trump`: 2020-10-15T00:00:01+00:00 through 2020-11-08T23:59:56+00:00.
- `twitter_donald_trump` missing counts: `{'id': 0, 'date': 0, 'tweet': 0, 'user_id': 0, 'user_loc': 295110}`.
- `twitter_joe_biden`: 2020-10-15T00:00:01+00:00 through 2020-11-08T23:59:58+00:00.
- `twitter_joe_biden` missing counts: `{'id': 0, 'date': 0, 'tweet': 0, 'user_id': 0, 'user_loc': 233872}`.

## Electoral Benchmarks

- FEC rows: 51 states/DC.
- Swing states at the 5-point threshold: AZ, FL, GA, MI, NC, NV, PA, WI.

## Major Figures

- `output/graphs/phase1/twitter_daily_volume.png` shows how valid tweet-record volume changes by UTC day for the two candidate hashtag streams. It is retained because temporal coverage and volume variation directly affect later event and sentiment analysis.
- `output/graphs/phase1/twitter_location_coverage.png` compares usable and missing user-location text. Missing location affects 30.4% of the Donald Trump stream and 30.1% of the Joe Biden stream, which limits later state-level mapping.

## Data Quality Notes

- Kaggle CSV rows with an invalid column count were rejected and counted.
- The Kaggle dataset does not provide replies; the canonical `replies` field is null.
- The downloaded Kaggle files cover October 15 through November 8, not the broader planned October 8 through November 15 window.
- Tweet and user IDs are retained as source strings because the CSV stores them in scientific notation.
- Duplicate tweets remain untouched for Phase 2.
