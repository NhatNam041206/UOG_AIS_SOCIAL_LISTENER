# Phase 2 Preprocessing Report

## Summary

- Initial records: 1,747,542.
- Final records: 1,462,744.
- Overall retention: 83.70%.

## Stage Results

| Stage | Initial | Retained | Dropped | Drop rate |
|---|---:|---:|---:|---:|
| bot_filter | 1,747,542 | 1,686,645 | 60,897 | 3.48% |
| exact_duplicate_filter | 1,686,645 | 1,462,772 | 223,873 | 13.27% |
| text_cleaning | 1,462,772 | 1,462,744 | 28 | 0.00% |

## Major Figure

- `output/graphs/phase2/preprocessing_attrition.png` shows retained records after each ordered rule and makes the effect of bot filtering, exact deduplication, and invalid-text rejection auditable.

## Method and Limitations

- Users exceeding 50 records on a UTC day are rejected for that day.
- Exact duplicate tweet text is removed before normalization; the first observation is retained.
- HTML and URLs are removed while capitalization, punctuation, and emoji are retained for VADER.
- The account-age rule could not be applied because Phase 1 interim files do not contain `user_created_at`; Phase 1 was intentionally left unchanged.
