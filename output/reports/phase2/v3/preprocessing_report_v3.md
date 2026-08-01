# Phase 2 v3 Preprocessing Report

Run ID: `phase2_v3_multivariable_20260801`

## Summary Metrics
- Initial Distinct Tweets: 1,522,660
- Stream Membership: {'trump_only': 747737, 'biden_only': 553237, 'both': 221686}
- Selected Empirical Activity Threshold: `7.0` tweets/active day
- High-Volume User Filtered Tweets: 201,561
- Cross-User Dedup Filtered Tweets: 23,346
- Invalid Text Filtered Tweets: 0
- Final Cleaned Retention: 1,297,753

## Package D Language-Region Cross-Analysis
- Total Clean Tweets Analyzed: 1,297,753
- Language Detection Method: `explicit_column`
- US State-Mapped Tweets: 291,711 (22.5%)
- US State Spanish Tweets Retained: 7,201
- US State Other Language Tweets: 9,801
- Unmapped Region Tweets: 1,006,042 (77.5%)

## Coverage Note
- 22.5% of tweets carry a valid US state code (ceiling: 22.8% based on country fields).
- Missing state codes do not invalidate national temporal (H1) analysis.
- State-level (H2) spatial regression uses geocoded subset only; selection bias should be acknowledged.