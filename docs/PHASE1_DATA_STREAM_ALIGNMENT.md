# Phase 1 Data-Stream Alignment Audit

Status: first PDF-alignment cleanup action completed on 2026-07-13.

## Purpose

This audit maps the live Phase 1 datasets to the three-stream acquisition design in
`SL_2020_ori.pdf`. It distinguishes a missing stream from an ingested stream that
still has alignment gaps.

## Stream inventory

| PDF stream | Live source and output | Current evidence | Alignment status |
| --- | --- | --- | --- |
| Stream A - Social media | `data/01_raw/twitter/hashtag_donaldtrump.csv`, `hashtag_joebiden.csv`; outputs `data/02_interim/twitter_donald_trump.parquet`, `twitter_joe_biden.parquet` | 1,747,542 valid records; verified UTC window 2020-10-15 through 2020-11-08 | Available with gaps |
| Stream B - Exogenous events | `data/01_raw/political_events/political_events.csv`; output `data/02_interim/political_events.parquet` | 4 timestamped and sourced events with categories | Available with gaps |
| Stream C - Electoral benchmarks | `data/01_raw/electoral_returns/electoral_returns.csv`; output `data/02_interim/electoral_returns.parquet` | 51 state/DC rows with candidate totals, shares, margins, winner, and source URL | Available with gaps |

Streams B and C are therefore not absent. They were previously listed by their
implementation names rather than by the PDF's Stream B and Stream C labels.

## Gap register

### Stream A - Social media

- The verified dataset covers 2020-10-15 through 2020-11-08. It does not satisfy
  the original planned 2020-10-08 through 2020-11-15 window.
- October 2, including Donald Trump's COVID-19 diagnosis, is outside both the
  verified dataset and the original planned range.
- The source does not provide usable reply counts; `replies` is null.
- The Phase 1 interim schema drops raw fields such as `user_join_date`,
  `user_followers_count`, and source-provided geographic columns. Their selective
  preservation must be designed before re-running downstream phases.
- The two files are candidate-hashtag-centered streams, not a complete sample of
  election Twitter discourse.

### Stream B - Exogenous events

- The current register contains four events: the October 15 town halls, October
  22 debate, November 3 election day, and November 7 AP projection.
- The original PDF requires curated milestones with UTC timing, categories, and
  qualitative event indicators. The event rows satisfy the basic ingestion shape,
  but event completeness still needs a documented inclusion rule.
- The current `post_event_dummy` value is stored on each event row. Phase 4 must
  derive observation-level pre/post and event-window indicators by comparing tweet
  timestamps with each event timestamp.
- An October 2 diagnosis event cannot be analyzed without adding an earlier social
  dataset to Stream A; adding the event row alone would not create observations.

### Stream C - Electoral benchmarks

- Official state-level 2020 returns are present for 50 states and DC.
- The current `state_classification` is derived from the 2020 absolute vote margin
  using a five-point threshold. The original PDF instead planned historical
  swing/safe classification based on the 2012 and 2016 elections.
- The original Phase 5 OLS design also plans urbanization, median age, and household
  income controls. Those variables and their provenance are not currently ingested.

## Phase 1 completion gate

Phase 1 can be called PDF-aligned only when all of the following are true:

1. Streams A, B, and C have explicit schemas, sources, licenses/provenance, row
   counts, time/geographic coverage, and checksums in the Phase 1 manifest.
2. The team formally accepts the verified Stream A window or adds a compatible
   extension dataset. The project must not silently describe the current data as
   covering October 8-November 15.
3. The Stream B event inclusion rule and event-window construction contract are
   documented.
4. Stream C contains a historically derived 2012/2016 classification and the
   approved demographic controls, or the statistical specification is formally
   revised with a documented rationale.
5. Any Phase 1 schema expansion is followed by regression tests and intentional
   re-execution of affected downstream phases.

## Next Phase 1 action

Design the revised Stream A canonical schema before changing data. The decision
should identify which existing raw account/geographic fields are retained, how
missing fields such as replies and following counts are represented, and which
Phase 2/2.5/3 artifacts must be regenerated.
