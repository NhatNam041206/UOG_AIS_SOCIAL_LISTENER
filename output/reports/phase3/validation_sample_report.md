# Phase 3 Stratified Validation Sample Report

## Stage Status

- Status: **completed**.
- Source records: 1,331,317.
- Sample records: 5,000.
- Random seed: `2020`.
- Sample checksum: `c3c252a98ee4111d185f28fd067fe43826a83986c170d8cbb6161e38fd62f1a4`.

## Method

- Strata: candidate stream by UTC date.
- Allocation: proportional Hamilton largest-remainder allocation.
- Selection: random without replacement using a fixed seed.
- VADER labels are not used for stratification because VADER is the model being validated.

## Candidate Representation

| Candidate stream | Source records | Source share | Sample records | Sample share |
| --- | ---: | ---: | ---: | ---: |
| `donald_trump` | 827,734 | 62.17% | 3,111 | 62.22% |
| `joe_biden` | 503,583 | 37.83% | 1,889 | 37.78% |

## Verification Checks

| Check | Result |
| --- | --- |
| `sample_size_exact` | passed |
| `source_rows_unique` | passed |
| `all_source_rows_in_range` | passed |
| `all_source_strata_represented` | passed |
| `allocation_matches_sample` | passed |
| `stored_row_count_matches` | passed |
| `stored_checksum_matches` | passed |

## Decision

The validation sample is reproducible and preserves candidate-by-day source representation. It is ready for RoBERTa inference.
