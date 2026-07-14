# Phase 1 v2 Ingestion Report

Run ID: `phase1_v2_verified_window_20260714`

## Decision Scope

- D1 approved Phase 1 v2 on the verified `2020-10-15` through `2020-11-08` Twitter window.
- `2020-11-09` through `2020-11-15` remains deferred and is not observed project coverage.
- v1 artifacts are preserved; v2 artifacts are written under versioned paths.

## Stream A Twitter Outputs

| Stream | Records | Invalid CSV rows | Unique tweet IDs | Duplicate tweet-ID rows | Coverage |
|---|---:|---:|---:|---:|---|
| Donald Trump | 970,765 | 323 | 969,423 | 1,342 | 2020-10-15T00:00:01+00:00 to 2020-11-08T23:59:56+00:00 |
| Joe Biden | 776,777 | 296 | 774,923 | 1,854 | 2020-10-15T00:00:01+00:00 to 2020-11-08T23:59:58+00:00 |

All 21 raw Kaggle columns are retained, with compatibility aliases for `id`, `date`, `retweets`, `user_loc`, and `candidate`.
Cross-stream overlapping tweet IDs: 221,686. This is lineage evidence, not stance.

## Stream B Events

- Rows: 4.
- Event-window, overlap, and boundary rules remain pending D4.

## Stream C Electoral Benchmarks

- Rows: 51.
- 2020 vote totals and margins are available.
- Historical 2012/2016 classification and demographic controls remain pending D5/D6 sources.

## Generated Artifacts

- `daily_volume_graph`: `D:\GW_UNIVERSITY\AIS\Social_Listener\Env\Social_Listener_V1\UOG_AIS_SOCIAL_LISTENER\output\graphs\phase1\v2\twitter_daily_volume_v2.png`
- `electoral_returns_v2`: `D:\GW_UNIVERSITY\AIS\Social_Listener\Env\Social_Listener_V1\UOG_AIS_SOCIAL_LISTENER\data\02_interim\phase1_v2\electoral_returns_v2.parquet`
- `location_coverage_graph`: `D:\GW_UNIVERSITY\AIS\Social_Listener\Env\Social_Listener_V1\UOG_AIS_SOCIAL_LISTENER\output\graphs\phase1\v2\twitter_location_coverage_v2.png`
- `manifest`: `D:\GW_UNIVERSITY\AIS\Social_Listener\Env\Social_Listener_V1\UOG_AIS_SOCIAL_LISTENER\output\results\phase1\v2\ingestion_manifest_v2.json`
- `political_events_v2`: `D:\GW_UNIVERSITY\AIS\Social_Listener\Env\Social_Listener_V1\UOG_AIS_SOCIAL_LISTENER\data\02_interim\phase1_v2\political_events_v2.parquet`
- `report`: `D:\GW_UNIVERSITY\AIS\Social_Listener\Env\Social_Listener_V1\UOG_AIS_SOCIAL_LISTENER\output\reports\phase1\v2\ingestion_report_v2.md`
- `twitter_donald_trump_v2`: `D:\GW_UNIVERSITY\AIS\Social_Listener\Env\Social_Listener_V1\UOG_AIS_SOCIAL_LISTENER\data\02_interim\phase1_v2\twitter_donald_trump_v2.parquet`
- `twitter_joe_biden_v2`: `D:\GW_UNIVERSITY\AIS\Social_Listener\Env\Social_Listener_V1\UOG_AIS_SOCIAL_LISTENER\data\02_interim\phase1_v2\twitter_joe_biden_v2.parquet`
- `twitter_daily_volume_v2.png`: Phase 1 v2 daily volume by candidate stream.
- `twitter_location_coverage_v2.png`: user-location availability by candidate stream.

## Claim Boundaries

- Candidate hashtag stream membership is not stance.
- High posting frequency is not bot proof.
- Missing location limits state analysis but does not invalidate national temporal analysis.
- Nov 9-15 is not current project evidence.
