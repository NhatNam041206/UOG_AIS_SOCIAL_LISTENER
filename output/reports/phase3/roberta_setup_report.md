# Phase 3 RoBERTa Setup Report

- Status: **passed**.
- Model: `cardiffnlp/twitter-roberta-base-sentiment`.
- Resolved revision: `daefdd1f6ae931839bce4d0f3db0a1a4265cd50f`.
- Backend: `torch` on `cpu`.
- Labels: `{'0': 'negative', '1': 'neutral', '2': 'positive'}`.

## Dependency Versions

| Dependency | Version |
| --- | --- |
| `torch` | `2.12.0` |
| `transformers` | `4.57.6` |
| `scipy` | `1.17.1` |

## Verification Checks

| Check | Result |
| --- | --- |
| `torch_available` | passed |
| `tokenizer_loaded` | passed |
| `model_loaded` | passed |
| `expected_three_labels` | passed |
| `test_batch_scored` | passed |
| `probabilities_sum_to_one` | passed |
