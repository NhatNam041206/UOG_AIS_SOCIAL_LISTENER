# Phase 3 Model-Artifact Inventory

Inventory date: 2026-07-10

## Verification boundary

This inventory was produced without running VADER, RoBERTa, or the three-model
comparison. Parquet row counts and schemas were read from metadata. The repository,
its Phase 3 history, and the Social Listener workspace were searched for retained
comparison artifacts; dependency and virtual-environment files were excluded.

The model evidence is comparison evidence, not human ground truth. The corpus is
candidate-hashtag-centered discourse from 2020-10-15 through 2020-11-08, not all
Twitter discourse or representative public opinion.

## Controlling classification

| Evidence class | Current path/evidence | Rows | Model and revision | Verification |
| --- | --- | ---: | --- | --- |
| Full VADER scoring | `data/02_interim/twitter_sentiment.parquet` | 1,331,317 | `vaderSentiment` 3.3.2 | Verified from Parquet metadata and manifest |
| Historical baseline-RoBERTa validation | Historical version of `output/results/phase3/sentiment_validation_sample.parquet` | 5,000 | `cardiffnlp/twitter-roberta-base-sentiment`, `daefdd1f6ae931839bce4d0f3db0a1a4265cd50f` | Verified in Git history; not the current workspace artifact |
| Current latest-RoBERTa validation | `output/results/phase3/sentiment_validation_sample.parquet` | 5,000 | `cardiffnlp/twitter-roberta-base-sentiment-latest`, `3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7` | Verified from metadata and July 3 manifests |
| Three-model comparison sample | `output/results/phase3/three_model_comparison_sample.parquet` | 100 | VADER plus both Cardiff models/revisions above | Verified sample artifact |
| Three-model full comparison | No artifact or manifest found | Unavailable | Runner supports full mode, but no verified execution evidence exists | Explicitly unavailable |

The historical 5,000-row baseline run and current 5,000-row latest run used the same
canonical validation path. Git history preserves the older version, while the
working tree contains only the July 3 latest-model artifact. The earlier baseline
run must not be described as a second current file.

## Artifact details

The machine-readable inventory at
`output/results/phase3/model_artifact_inventory.json` is authoritative for the
per-artifact fields. Important current schemas are:

- Full VADER Parquet: 14 columns; nine canonical Phase 2 columns plus five VADER
  fields (`vader_negative`, `vader_neutral`, `vader_positive`, `vader_compound`,
  `vader_label`).
- Current 5,000-row validation Parquet: 27 columns, including VADER fields,
  `detected_language`, latest-RoBERTa probabilities/score/label, agreement fields,
  token count, and truncation flag.
- Preserved 100-row comparison Parquet: 34 columns, including baseline and latest
  RoBERTa probability, score, label, token, truncation, and pairwise agreement
  fields.

All Phase 3 JSON and report artifacts are classified in the machine-readable
inventory. `models/` contains no project-retained weights or fine-tuned model. The
two Cardiff models are externally trained ready-to-use models identified by their
Hugging Face IDs and resolved revisions; the repository contains no project-specific
training or fine-tuning pipeline.

## Git history findings

- `aac4d50f92da3f4387c3ce1571ed9b4f6df2b7a4` added full VADER scoring artifacts.
- `70d5cafc5e93ec66b031895b834eb4c507be71b7a4` added the deterministic 5,000-row sample.
- `9daae3c22d487af7ddaea188ac944911e3676f74` scored the historical baseline model.
- `c02791b931a96e30f4f6498be858d15aebd99bc7` added historical agreement validation.
- `f0d208614282f68942e78335fc9a18a743d768aa` replaced the current validation outputs
  with the latest Cardiff model and added the 100-row three-model sample.

No commit or workspace file provides a verified full three-model comparison. A
historical full run may have been overwritten before commit because the previous
runner shared output paths, but that possibility is not evidence that the run or its
artifact exists.

## Methodological use

- Full VADER output remains the canonical full-corpus sentiment estimate.
- The current 5,000-row latest-RoBERTa artifact remains the primary model-agreement
  and language-suitability validation evidence.
- The 100-row three-model comparison is exploratory only.
- Historical baseline evidence documents model-version evolution; it is not a
  current second validation artifact.
- No full three-model results may be claimed until a separately named full artifact,
  manifest, row count, schema, and model revisions are verified.

No artifact was moved, modified, or overwritten during A1.
