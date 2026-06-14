# Phase 3 Entry Gate: Phase 2 Input Contract Validation

Overall status: **PASSED**

## Contract Checks

| Check | Status | Detail |
| --- | --- | --- |
| `cleaned_dataset_exists` | passed | D:\GW_UNIVERSITY\AIS\Social_Listener\Env\Social_Listener_V1\UOG_AIS_SOCIAL_LISTENER\data\02_interim\twitter_cleaned.parquet |
| `phase2_manifest_exists` | passed | D:\GW_UNIVERSITY\AIS\Social_Listener\Env\Social_Listener_V1\UOG_AIS_SOCIAL_LISTENER\output\results\phase2\preprocessing_manifest.json |
| `phase2_manifest_completed` | passed | status='completed' |
| `row_count_matches_manifest` | passed | parquet=1,331,317; manifest=1,331,317 |
| `required_columns_present` | passed | none missing |
| `required_column_types_compatible` | passed | all compatible |
| `phase3_required_values_non_null` | passed | no required nulls |
| `tweet_text_non_empty` | passed | blank_count=0 |
| `tweet_text_has_valid_unicode` | passed | invalid_unicode_count=0 |
| `timestamps_valid_and_utc` | passed | invalid_count=0 |
| `candidate_values_expected` | passed | observed=['donald_trump', 'joe_biden']; unexpected=[]; missing=[] |
| `candidate_day_strata_available` | passed | strata=50; minimum_records=7,163 |

## Reported Warnings

| Item | Status | Detail |
| --- | --- | --- |
| `post_cleaning_exact_duplicate_text` | warning | count=50,561; permitted because Phase 2 deduplicates before text normalization |
| `long_text_truncation_risk` | warning | records_over_512_characters=581; token-level truncation must be measured during RoBERTa inference |
| `known_nullable_source_fields` | warning | null_counts={'user_loc': 0, 'replies': 1331317} |
| `blank_user_locations` | warning | count=404,348; treat blank strings as missing during Phase 4 spatial mapping |

## Dataset Summary

- Records: 1,331,317
- Columns: 9
- UTC coverage: 2020-10-15T00:00:01+00:00 through 2020-11-08T23:59:58+00:00
- Candidate counts: `{'donald_trump': 827734, 'joe_biden': 503583}`
- Candidate-by-day strata: 50
- Stratum size range: 7,163 to 115,014

## Entry Decision

The Phase 2 cleaned dataset satisfies the Phase 3 input contract and may proceed to sentiment scoring.
