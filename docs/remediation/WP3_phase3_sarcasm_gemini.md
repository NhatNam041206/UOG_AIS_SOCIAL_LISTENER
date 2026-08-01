# WP3 — Sarcasm Detection, Human Seeds, Gemini Silver Labels, Fine-Tune

**Depends on**: WP2 passed.
**Deliverables**: irony scores in `twitter_sentiment_v3.parquet`; annotation datasets under `data/04_annotations/`; a fine-tuned model under `models/twitter-roberta-sentiment-ft/`.
**Read [00_AGENT_BRIEF.md](00_AGENT_BRIEF.md) first. Rule R1 governs this package as strictly as WP2.**

---

## Problem statement

The current `sarcasm_risk_score` is documented as a `"heuristic_linguistic_proxy"` (ALL-CAPS ratio, cue phrases, punctuation). Its distribution is degenerate: mean 0.054, median **0.00**, 75th percentile 0.03. It is effectively a near-constant zero column and carries almost no information. An earlier revision generated it from `np.random.beta(0.5, 2.5)` outright.

`GeminiSarcasmAnnotator` exists but is dead code — `run_phase3_v2.py` only calls `build_prompt()` and checks the string is non-empty, then records `gemini_annotation_prompt_structure_valid: true`. `parse_llm_response()` is never called anywhere in the repo. No API is contacted.

This package implements the four-stage chain as originally specified: **pretrained irony model → 15 human seeds → Gemini silver expansion → fine-tune**.

> **Staged gate.** T3.1 is self-contained and must be completed even if everything after it is blocked. T3.3 requires an API key that is **not currently configured**; if it is unavailable, complete T3.1–T3.2, mark T3.3/T3.4 `"blocked"` with the reason, and stop. Do not simulate LLM responses — that is rule R1.

---

## T3.1 — Pretrained irony classifier (replaces the heuristic)

Model: `cardiffnlp/twitter-roberta-base-irony` (binary: `non_irony` / `irony`). **Not currently cached** — it will download (~500 MB) on first use.

Reuse WP2's inference harness: same `roberta_preprocess()`, same fp16/batching/checkpointing, same device selection.

| Column | Content |
|---|---|
| `irony_prob` | P(irony), `[0, 1]` |
| `irony_label` | `irony` / `non_irony` at 0.5 |
| `irony_model_status` | `"completed"`, set by the code path that ran |

**Keep the old heuristic** as `sarcasm_risk_heuristic` for comparison, and record the Pearson/Spearman correlation between it and `irony_prob` in evidence. A near-zero correlation is the expected — and reportable — finding: it demonstrates the heuristic was not measuring irony.

### Sarcasm risk profiling, not label inversion
`irony_prob` **must not flip any sentiment label**. Irony detection at this accuracy is not reliable enough to invert a judgement. Its role is to quantify a risk surface:

- share of corpus with `irony_prob > 0.5`, and > 0.7
- mean `roberta_score` for high- vs low-irony tweets
- **the share of high-irony tweets inside each `roberta_label` class** — this is the number that tells a reader how much of the sentiment distribution is potentially inverted
- the same breakdown per candidate stream and per event window

Write to `output/results/phase3/v3/evidence/irony_profile.json`.

---

## T3.2 — 15-tweet human seed set

Build the seed file the human annotator will fill in.

1. Sample 15 tweets **stratified** across: candidate stream (trump_only / biden_only / both), `roberta_label`, and irony band (high `irony_prob` deliberately over-represented — the seeds must cover the hard cases the fine-tune is meant to learn).
2. Write `data/04_annotations/human_seed_15.jsonl` with `tweet_id`, `tweet_cleaned`, model predictions, and **empty** annotation fields:

| Field | Values |
|---|---|
| `target_candidate` | `trump` / `biden` / `both` / `neither` |
| `stance` | `pro` / `anti` / `neutral` |
| `expressed_sentiment` | `positive` / `negative` / `neutral` |
| `intended_sentiment` | `positive` / `negative` / `neutral` |
| `is_sarcastic` | `true` / `false` |
| `annotator_note` | free text |

3. Record the sampling `random_state` in the manifest (rule R1's documented-sampling exemption).

> **These 15 labels must be filled in by a human.** Do not populate them yourself, and do not generate them with any model. Write the file with empty fields and report that human annotation is pending. The seed set's entire value is that it is *not* model-generated — it is the anchor against which the Gemini labels are checked in T3.3.

---

## T3.3 — Gemini silver-standard expansion

**Gated on**: `human_seed_15.jsonl` fully annotated by a human, **and** a Gemini API key present in the environment.

1. Install the SDK: `pip install google-genai`. Read the key from `GEMINI_API_KEY`. **Never hardcode a key, never commit one.** If it is absent, mark this task `"blocked"` and stop — do not proceed to T3.4.
2. Sample **1,500** tweets, stratified as in T3.2, disjoint from the 15 seeds.
3. Few-shot prompt: the 15 human-annotated examples verbatim as demonstrations, then the target tweet. Request strict JSON matching the T3.2 schema. Reuse and finally *call* `GeminiSarcasmAnnotator.build_prompt()` and `parse_llm_response()`.
4. Log **every** raw API response to `data/04_annotations/gemini_raw_responses.jsonl` — request, response, timestamp, model name. This log is what makes the silver labels auditable.
5. Handle failures explicitly: on a parse failure or API error, record the row with `"annotation_status": "failed"` and its reason. **Never fill a failed row with a guess.** Report the success rate.
6. Output `data/04_annotations/gemini_silver_1500.jsonl`.

### Required quality gate — held-out seed agreement
Hold out 5 of the 15 human seeds from the prompt, annotate them via the API, and compute agreement against the human labels on all six fields.

Write `output/results/phase3/v3/evidence/gemini_agreement.json` with per-field agreement and the raw comparison table.

> **If agreement on `is_sarcastic` is below 0.60, stop.** Report it and do not proceed to T3.4. Fine-tuning on silver labels that disagree with the human anchor would bake the disagreement into the model — worse than not fine-tuning at all. A halt here is a successful, honest outcome.

---

## T3.4 — Fine-tune Twitter-RoBERTa

**Gated on**: T3.3 passing its agreement gate.

1. Start from `cardiffnlp/twitter-roberta-base-sentiment-latest`. Target label: `intended_sentiment` (3-class) — this is the point of the exercise, since `expressed_sentiment` is what the base model already predicts.
2. Split 1,500 silver rows **stratified** 70/15/15 train/val/test, `seed=42` recorded in the manifest. The 15 human seeds are **never** in train — they are a separate gold evaluation set.
3. Hyperparameters (4 GiB VRAM): `batch_size=16`, `gradient_accumulation_steps=2`, `lr=2e-5`, `epochs=3`, `max_length=128`, fp16, early stopping on val macro-F1. If OOM, halve batch size and double accumulation.
4. Save to `models/twitter-roberta-sentiment-ft/`.

### Mandatory three-way evaluation
Evaluate **base vs fine-tuned** on (a) the silver test split and (b) the 15 human gold seeds. Report accuracy, macro-F1, and per-class F1 for both models on both sets.

Write `output/results/phase3/v3/evidence/finetune_metrics.json`.

> **A negative result is a valid result.** 1,500 silver examples is a small fine-tuning set and degradation is a realistic outcome, especially on the 15 gold seeds. Report the honest comparison. **Do not promote the fine-tuned model to primary unless it beats the base model on the human gold seeds.** If it does not, keep the WP2 base-model scores as primary and document the negative finding — that is a legitimate contribution to the methodology write-up.

---

## Acceptance criteria

| # | Criterion |
|---|---|
| A3.1 | No `np.random` / synthetic generation in any WP3 file, except documented sampling seeds |
| A3.2 | `irony_prob` present for all v3 rows; auditing agent re-scores 200 rows and requires a match within 1e-3 |
| A3.3 | `irony_prob` is **not** a transform of `sarcasm_risk_heuristic`, `roberta_score`, or `vader_compound` (pairwise R² < 0.9) |
| A3.4 | No sentiment label was altered by irony — `roberta_label` is unchanged from WP2 |
| A3.5 | `human_seed_15.jsonl` has 15 rows; annotation fields are either human-filled or empty with `"human_annotation_pending"` reported |
| A3.6 | If T3.3 ran, `gemini_raw_responses.jsonl` line count ≥ the silver row count, and `gemini_agreement.json` reports a real per-field agreement |
| A3.7 | If T3.4 ran, `finetune_metrics.json` reports base **and** fine-tuned on **both** eval sets |
| A3.8 | Any blocked task is recorded as `"blocked"` with a reason — never silently skipped or simulated |
