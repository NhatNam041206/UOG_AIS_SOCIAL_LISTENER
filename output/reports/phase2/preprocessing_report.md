# Phase 2 Preprocessing Report

## Summary

- Initial records: 1,747,542.
- Final records: 1,331,317.
- Overall retention: 76.18%.

## Stage Results

| Stage | Initial | Retained | Dropped | Drop rate |
|---|---:|---:|---:|---:|
| bot_filter | 1,747,542 | 1,525,176 | 222,366 | 12.72% |
| exact_duplicate_filter | 1,525,176 | 1,331,345 | 193,831 | 12.71% |
| text_cleaning | 1,331,345 | 1,331,317 | 28 | 0.00% |

## User-Activity Audit

- Selected threshold: `9.000` tweets per active day.
- Full decision evidence: `output/reports/phase2/user_activity_threshold_report.md`.
- Reproducible metrics: `output/results/phase2/user_activity_metrics.parquet` and `output/results/phase2/user_activity_threshold_audit.json`.

## Method and Limitations

- All records from users exceeding the selected empirical tweets-per-active-day threshold are rejected.
- Exact duplicate tweet text is removed before normalization; the first observation is retained.
- HTML and URLs are removed while capitalization, punctuation, and emoji are retained for VADER.
- No Phase 5 ITSA, OLS, model-performance, or robustness output is produced by this Phase 2 workflow.
- The account-age rule could not be applied because Phase 1 interim files do not contain `user_created_at`; Phase 1 was intentionally left unchanged.
