# Module: user_activity_audit_model

## Architectural Role

Model boundary for empirical Phase 2 user-activity validation. It measures activity,
derives candidate thresholds, quantifies filtering trade-offs, and recommends a
threshold without producing graphs or performing downstream modeling.

## User Metrics

- `total_tweets`
- `active_days`
- `observed_span_days`
- `tweets_per_active_day` as the main threshold metric
- `tweets_per_observed_day`
- `max_tweets_single_day`

## Candidate Methods and Selection

The auditor derives P95, P97.5, P99, P99.5, IQR upper fence, extreme-IQR upper fence,
log-z, and MAD candidates. It selects the smallest candidate at or above P99 that
removes no more than 1% of users and 10% of tweets. If none meets both safeguards, it
selects the candidate at or above P99 with the smallest combined safeguard exceedance.
This rule is configurable through `ThresholdSelectionPolicy`.

The audit is Phase 2 preprocessing validation only and makes no Phase 5 modeling claim.
