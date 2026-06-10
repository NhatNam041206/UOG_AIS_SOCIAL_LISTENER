# Phase 2 User-Activity Threshold Audit

## Why an Empirical Audit Is Needed

A fixed high-volume threshold is methodologically weak because it is not tied to the observed activity distribution and may remove too much or too little data without a reproducible justification.

Raw mean plus or minus standard deviation is also unsuitable for strongly right-skewed posting frequency: a small number of highly active users pulls both the mean and standard deviation upward. The audit therefore emphasizes percentiles and robust fences, and applies the z-score method only after `log1p` transformation.

## User-Activity Summary

- Users measured: 483,175.
- Tweets measured: 1,747,542.
- Main metric: `tweets_per_active_day`.
- Median tweets per active day: 1.00.
- Maximum tweets per active day: 219.50.

## Candidate Thresholds

| Method | Threshold (tweets per active day) |
|---|---:|
| P95 | 3.000 |
| P97.5 | 4.000 |
| P99 | 6.000 |
| P99.5 | 9.000 |
| IQR upper fence | 2.667 |
| Extreme IQR fence | 3.667 |
| Log-z threshold | 4.550 |
| MAD threshold | 1.000 |

## Filtering Trade-Offs

| Method | Threshold | Users removed (n) | Users removed (%) | Tweets removed (n) | Tweets removed (%) |
|---|---:|---:|---:|---:|---:|
| P95 | 3.000 | 19,558 | 4.05% | 636,787 | 36.44% |
| P97.5 | 4.000 | 10,218 | 2.11% | 491,261 | 28.11% |
| P99 | 6.000 | 4,610 | 0.95% | 332,815 | 19.04% |
| P99.5 | 9.000 | 2,227 | 0.46% | 222,366 | 12.72% |
| IQR upper fence | 2.667 | 30,928 | 6.40% | 730,824 | 41.82% |
| Extreme IQR fence | 3.667 | 15,838 | 3.28% | 550,319 | 31.49% |
| Log-z threshold | 4.550 | 8,904 | 1.84% | 445,847 | 25.51% |
| MAD threshold | 1.000 | 159,599 | 33.03% | 1,354,893 | 77.53% |

## Selected Threshold

**Recommended threshold: 9.000 tweets per active day.**

No candidate at or above P99 met both retention safeguards; selected P99.5 because it has the smallest combined safeguard exceedance among eligible tail thresholds. At this threshold, 0.46% of users and 12.72% of tweets are removed.

The MAD candidate is feasible but not informative for this dataset because its threshold is 1.000; the mass of users at one tweet per active day makes the median absolute deviation collapse to zero.

## Major Figures

1. `activity_distribution_with_thresholds.png` shows the skewed log-activity distribution and positions the selected value against major empirical candidates.
2. `user_contribution_curve.png` shows whether tweet production is concentrated among a small share of users.
3. `derived_threshold_comparison.png` compares all candidate values rather than presenting one statistic in isolation.
4. `filtering_tradeoff_users_vs_tweets.png` makes the retention cost of each candidate explicit.
5. `daily_volume_before_after_filtering.png` checks whether the selected user filter preserves the shape of daily tweet activity needed by later phases.

## Scope Warning

**This Phase 2 audit does not validate Phase 5 modeling. Phase 5 ITSA and OLS modules have not been implemented, and this report contains no model-performance or causal-robustness claims.**

Once ITSA and OLS modules exist, this audit can support robustness testing by rerunning those models across documented candidate activity thresholds and comparing whether substantive conclusions remain stable. That future work must use real implemented models and is outside Phase 2.
