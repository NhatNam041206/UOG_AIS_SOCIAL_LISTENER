# Phase 2 v2 Preprocessing Report

Run ID: `phase2_v2_multivariable_20260731`

## Summary Metrics
- Initial Records: 1,747,542
- Selected Empirical Activity Threshold: `9.0` tweets/active day
- High-Volume User Filtered Tweets: 222,366 (12.72%)
- Exact Duplicate Filtered Tweets: 244,392 (13.98%)
- Invalid Text Filtered Tweets: 0
- Final Cleaned Retention: 1,280,784 (73.29%)

## Package D Language-Region Cross-Analysis
- Total Clean Tweets Analyzed: 1,280,784
- Language Detection Method: `heuristic_pattern_matcher`
- US State-Mapped Tweets: 264,095 (20.6%)
- US State Spanish Tweets Retained: 6,600
- US State Other Language Tweets: 0
- Unmapped Region Tweets: 878,389 (68.6%)

## Coverage Note
- Approximately 20.5% of tweets carry a valid US state code.
- Missing state codes do not invalidate national temporal (H1) analysis.
- State-level (H2) spatial regression uses geocoded subset only; selection bias should be acknowledged.