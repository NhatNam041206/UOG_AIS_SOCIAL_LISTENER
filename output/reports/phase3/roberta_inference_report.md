# Phase 3 RoBERTa Sample Inference Report

- Status: **completed**.
- Records scored: 5,000.
- Model: `cardiffnlp/twitter-roberta-base-sentiment-latest`.
- Resolved revision: `3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7`.
- Backend/device: `torch` / `cpu`.
- Batch size: 16.
- Maximum token length: 512.
- Truncated records: 0.
- Maximum observed token count: 453.

## Model-Specific Preprocessing

- Usernames are replaced with `@user` only for RoBERTa input.
- URLs are replaced with `http` only for RoBERTa input.
- Canonical tweet text is not modified.

## Label Distribution

| Label | Records |
| --- | ---: |
| Negative | 1,772 |
| Neutral | 2,287 |
| Positive | 941 |

## Verification Checks

| Check | Result |
| --- | --- |
| `all_sample_records_scored` | passed |
| `roberta_fields_complete` | passed |
| `probabilities_in_unit_interval` | passed |
| `probabilities_sum_to_one` | passed |
| `roberta_score_in_expected_range` | passed |
| `labels_expected` | passed |
