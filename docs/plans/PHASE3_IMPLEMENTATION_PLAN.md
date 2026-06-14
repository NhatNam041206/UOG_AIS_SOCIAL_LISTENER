# Phase 3 Implementation Plan: Hybrid Sentiment Extraction and Validation

Plan date: 2026-06-14

## Purpose

This plan is the implementation and verification reference for Phase 3. During
development and phase closure, completed work must be checked against this document
so that the sentiment outputs remain reproducible, methodologically defensible, and
ready for Phase 4.

## Objective

Phase 3 will:

1. validate the Phase 2 cleaned-data input contract;
2. score all cleaned tweets with VADER;
3. create a reproducible stratified random sample of 5,000 tweets;
4. score the validation sample with `cardiffnlp/twitter-roberta-base-sentiment`;
5. compare VADER and RoBERTa using Pearson correlation and supporting agreement
   metrics;
6. produce auditable results, reports, and a small set of research figures.

RoBERTa is a stronger comparison model, not human ground truth. Phase 3 will report
model agreement and disagreement without describing RoBERTa as unquestionably
correct.

## Approved Workflow

```text
twitter_cleaned.parquet
        |
        v
Validate Phase 2 input contract
        |
        v
Score all cleaned tweets with VADER
        |
        v
Create reproducible 5,000-tweet stratified sample
        |
        v
Score validation sample with RoBERTa
        |
        v
Convert both models to comparable continuous scores
        |
        v
Calculate correlation, agreement, and disagreements
        |
        v
Generate Phase 3 report, results, graphs, and manifest
```

## Ranked Components

| Rank | Component | Classification | Completion evidence |
| ---: | --- | --- | --- |
| 1 | Define sentiment schemas and score meanings | Required | Input, full-output, and validation schemas documented |
| 2 | Install and configure a RoBERTa inference backend | Required blocker | Model loads and scores a test batch |
| 3 | Full-dataset VADER scorer | Required | Every cleaned tweet receives valid VADER scores |
| 4 | Reproducible stratified sampler | Required | Fixed seed always produces the same 5,000-record sample |
| 5 | RoBERTa validation scorer | Required | Every sampled tweet receives probabilities and a label |
| 6 | Comparable continuous-score mapping | Required | Both model scores use the range `[-1, 1]` |
| 7 | Pearson validation | Required | Pearson `r`, p-value, sample size, and confidence interval recorded |
| 8 | Supporting agreement metrics | Strongly recommended | Spearman correlation, label agreement, macro-F1, and confusion matrix recorded |
| 9 | RoBERTa-specific preprocessing | Required | Usernames are normalized for model input without changing canonical tweet text |
| 10 | Reproducibility manifest | Required | Model identifier, revision, seed, versions, and parameters recorded |
| 11 | Language suitability audit | Strongly recommended | English and uncertain-language exposure documented |
| 12 | Truncation and inference audit | Strongly recommended | Truncated-record count and inference settings recorded |
| 13 | Disagreement analysis | Strongly recommended | Largest and systematic disagreements summarized |
| 14 | Research figures | Required | Approved PNG figures generated and interpreted |
| 15 | Tests, runner, and completion report | Required | Tests pass and all outputs agree |

## Input Contract

Primary input:

```text
data/02_interim/twitter_cleaned.parquet
```

The Phase 3 input-contract validator must confirm:

- the cleaned Parquet file and Phase 2 manifest exist and are readable;
- the Parquet row count equals the Phase 2 manifest final count;
- all required columns exist with compatible types;
- `tweet`, `date`, and `candidate` contain no missing values;
- tweet text is non-empty and contains no invalid replacement or surrogate
  characters;
- timestamps are valid and UTC-aware;
- candidate values are limited to the expected candidate streams;
- candidate-by-day strata exist for reproducible validation sampling.

Known limitations such as nullable `user_loc`, unavailable `replies`, long-text
truncation risk, and duplicate text created by post-deduplication cleaning must be
measured and reported without automatically failing the contract.

## Sentiment Schemas

### Full VADER Output

Output:

```text
data/02_interim/twitter_sentiment.parquet
```

Preserve all input fields and add:

| Field | Meaning |
| --- | --- |
| `vader_negative` | Negative proportion |
| `vader_neutral` | Neutral proportion |
| `vader_positive` | Positive proportion |
| `vader_compound` | Compound sentiment score from `-1` to `+1` |
| `vader_label` | `negative`, `neutral`, or `positive` |

Label thresholds:

```text
compound <= -0.05         -> negative
-0.05 < compound < 0.05  -> neutral
compound >= 0.05          -> positive
```

### Validation Output

Output:

```text
output/results/phase3/sentiment_validation_sample.parquet
```

Add:

| Field | Meaning |
| --- | --- |
| `roberta_negative_probability` | RoBERTa negative probability |
| `roberta_neutral_probability` | RoBERTa neutral probability |
| `roberta_positive_probability` | RoBERTa positive probability |
| `roberta_score` | `positive_probability - negative_probability` |
| `roberta_label` | Highest-probability RoBERTa class |
| `models_agree` | Whether VADER and RoBERTa labels agree |
| `absolute_score_difference` | Absolute difference between continuous scores |

## Sampling Strategy

Create a proportional random sample using:

```text
strata = candidate x UTC date
sample size = 5,000
fixed seed = documented in the Phase 3 manifest
```

The cleaned dataset currently contains 50 natural candidate-by-day strata. A
proportional sample preserves the source candidate and temporal distribution.
Sampling must not be based primarily on VADER labels because VADER is the model
being evaluated.

## Model Comparison

Use:

```text
VADER score   = vader_compound
RoBERTa score = positive_probability - negative_probability
```

Required metric:

- Pearson correlation, p-value, 95% confidence interval, and sample size.

Supporting metrics:

- Spearman correlation;
- label agreement rate;
- macro-F1 agreement;
- confusion matrix;
- mean absolute score difference;
- candidate-level correlation;
- daily correlation where sample size permits.

## RoBERTa Processing Requirements

- Use `cardiffnlp/twitter-roberta-base-sentiment`.
- Pin and record the resolved model revision.
- Normalize usernames to `@user` only inside the RoBERTa input adapter.
- Do not overwrite canonical tweet text or VADER input.
- Record inference backend, package versions, device, batch size, maximum token
  length, and truncation count.
- Add an explicit supported inference backend dependency before execution.

## Language Suitability Audit

Measure likely-English and uncertain/non-English exposure in the validation sample.
Report model-agreement metrics for all sampled tweets and, where feasible,
likely-English tweets separately. Do not silently remove non-English records.

## Research Figures

Generate only these major figures unless a documented finding requires another:

| Figure | Question answered |
| --- | --- |
| `vader_sentiment_distribution.png` | What is the full-dataset VADER sentiment distribution? |
| `sentiment_distribution_by_candidate.png` | How do candidate-stream sentiment distributions differ? |
| `vader_roberta_score_comparison.png` | How strongly do continuous model scores agree? |
| `vader_roberta_confusion_matrix.png` | Which sentiment labels disagree most often? |

Daily sentiment aggregation belongs primarily to Phase 4.

## Proposed Code Structure

```text
src/phase3_sentiment/
    sentiment_models_model.py
    validation_sampler_model.py
    sentiment_validation_model.py
    sentiment_runner_controller.py
    sentiment_reporter_view.py

verify/phase3/
    validate_phase2_input_contract.py
    run_phase3.py
    tests/
```

## Proposed Outputs

```text
data/02_interim/twitter_sentiment.parquet

output/results/phase3/
    phase2_input_contract_validation.json
    sentiment_manifest.json
    sentiment_validation_sample.parquet
    sentiment_validation_metrics.json

output/reports/phase3/
    phase2_input_contract_validation.md
    sentiment_report.md
    sentiment_validation_report.md

output/graphs/phase3/
    vader_sentiment_distribution.png
    sentiment_distribution_by_candidate.png
    vader_roberta_score_comparison.png
    vader_roberta_confusion_matrix.png
```

## Implementation Order

1. Validate the Phase 2 cleaned-data input contract.
2. Finalize and test sentiment schemas.
3. Add and verify the RoBERTa inference backend.
4. Implement and test full-dataset VADER scoring.
5. Implement and test the deterministic stratified sampler.
6. Implement and test the RoBERTa adapter.
7. Calculate validation and agreement metrics.
8. Generate research figures, reports, results, and the manifest.
9. Run the complete workflow and verify every closure gate.

## Phase Closure Gates

- [x] Phase 2 input contract passes.
- [x] Every cleaned tweet has valid VADER scores.
- [x] The 5,000-record sample is reproducible with documented strata and seed.
- [x] Candidate and daily sample coverage are verified.
- [ ] Every sampled record has valid RoBERTa probabilities.
- [ ] Model name, revision, preprocessing, and inference settings are recorded.
- [ ] Pearson correlation and supporting agreement metrics are calculated.
- [ ] Language and truncation limitations are documented.
- [ ] Reports, results, figures, and manifest agree.
- [ ] Phase 3 tests pass.
- [ ] The sentiment-enriched dataset is verified as ready for Phase 4.

## Execution Record

### Phase 2 Input Contract Validation

Completed: 2026-06-14

Status: **Passed**

Evidence:

- `output/results/phase3/phase2_input_contract_validation.json`
- `output/reports/phase3/phase2_input_contract_validation.md`
- `.venv\Scripts\python.exe -m unittest discover -s verify\phase3\tests -v`

The cleaned dataset is approved for Phase 3 sentiment scoring. Non-blocking warnings
were recorded for post-cleaning duplicate convergence, potential RoBERTa truncation,
unavailable replies, and blank location strings that must be handled as missing
during Phase 4.

### Full-Dataset VADER Scoring

Completed: 2026-06-14

Status: **Passed**

Evidence:

- `data/02_interim/twitter_sentiment.parquet`
- `output/results/phase3/sentiment_manifest.json`
- `output/results/phase3/vader_output_validation.json`
- `output/reports/phase3/sentiment_report.md`
- `output/graphs/phase3/vader_sentiment_distribution.png`
- `output/graphs/phase3/sentiment_distribution_by_candidate.png`
- `.venv\Scripts\python.exe -m unittest discover -s verify\phase3\tests -v`

All 1,331,317 cleaned tweets received the approved five-field VADER schema. The
output validator passed 11 checks covering row-count and source-schema preservation,
field completeness, score ranges, component-sum rounding tolerance, expected labels,
and compound-threshold consistency.

Descriptive full-dataset results:

| Label | Records | Percentage |
| --- | ---: | ---: |
| Negative | 350,836 | 26.35% |
| Neutral | 527,371 | 39.61% |
| Positive | 453,110 | 34.03% |

The mean compound score is `0.0518`. These results remain unvalidated descriptive
VADER outputs until the planned RoBERTa comparison is complete.

### Stratified Validation Sample

Completed: 2026-06-14

Status: **Passed**

Evidence:

- `output/results/phase3/sentiment_validation_sample.parquet`
- `output/results/phase3/validation_sample_manifest.json`
- `output/reports/phase3/validation_sample_report.md`
- `.venv\Scripts\python.exe verify\phase3\run_phase3_validation_sample.py`

The sample uses proportional Hamilton largest-remainder allocation across all 50
candidate-by-UTC-day strata and random selection without replacement using seed
`2020`.

| Candidate stream | Source share | Sample records | Sample share |
| --- | ---: | ---: | ---: |
| `donald_trump` | 62.17% | 3,111 | 62.22% |
| `joe_biden` | 37.83% | 1,889 | 37.78% |

All seven sample verification checks passed. Replaying the stage produced the same
source-row checksum:

```text
c3c252a98ee4111d185f28fd067fe43826a83986c170d8cbb6161e38fd62f1a4
```

The sample is ready for RoBERTa inference. Its VADER-label distribution is
descriptive only and was not used to construct the sample.

### RoBERTa Inference Setup

Completed: 2026-06-14

Status: **Passed**

Evidence:

- `output/results/phase3/roberta_setup_validation.json`
- `output/reports/phase3/roberta_setup_report.md`
- `.venv\Scripts\python.exe verify\phase3\verify_roberta_setup.py`

The exact `cardiffnlp/twitter-roberta-base-sentiment` model loaded and scored a
deterministic test batch using PyTorch on CPU.

| Setting | Value |
| --- | --- |
| Resolved model revision | `daefdd1f6ae931839bce4d0f3db0a1a4265cd50f` |
| Backend | PyTorch `2.12.0` |
| Transformers | `4.57.6` |
| Device | CPU |
| Maximum token length | 512 |
| Label mapping | `0=negative`, `1=neutral`, `2=positive` |

The model configuration exposes generic `LABEL_0`, `LABEL_1`, and `LABEL_2`
identifiers, so the documented CardiffNLP sentiment mapping is applied explicitly.
