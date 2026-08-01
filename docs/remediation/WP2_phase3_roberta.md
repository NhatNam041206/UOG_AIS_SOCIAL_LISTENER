# WP2 — Real Twitter-RoBERTa Inference (Phase 3 v3)

**Depends on**: WP0, WP1 passed.
**Deliverable**: `verify/phase3/run_phase3_v3.py` producing `data/02_interim/phase3_v3/twitter_sentiment_v3.parquet`.
**Read [00_AGENT_BRIEF.md](00_AGENT_BRIEF.md) first. Rule R1 governs this entire package.**

---

## Problem statement

This is the package where the prior implementation failed hardest, twice.

**First failure — fabrication.** An earlier `run_phase3_v2.py` contained:
```python
np.random.seed(2020)
df["roberta_score"]       = np.clip(df["vader_compound"] * 0.8 + np.random.normal(0, 0.15, n), -1, 1)
df["sarcasm_risk_score"]  = np.clip(np.random.beta(0.5, 2.5, n), 0, 1)
```
These are not model outputs. The manifest nonetheless named `cardiffnlp/twitter-roberta-base-sentiment-latest` as the primary model. A Pearson check between `vader_compound` and this `roberta_score` was reported as validation — it is circular by construction, since one is an affine transform of the other.

**Second failure — a false deferral.** The current `run_phase3_v2.py` writes `roberta_status = "deferred_requires_gpu"`. This is untrue on this machine:
- `transformers` is installed
- `cardiffnlp/twitter-roberta-base-sentiment-latest` **is already cached** at `~/.cache/huggingface/hub/models--cardiffnlp--twitter-roberta-base-sentiment-latest`
- CPU inference was measured at **16.6 tweets/sec** (batch 64, max_len 128, fp32) — slow, but working. ~21.4 h for 1.28 M.
- A CUDA-capable GPU is present; WP0 makes it usable.

The consequence: **VADER is currently the sole sentiment source**, and 37.33% of tweets score exactly `0.0` because the lexicon does not fire on them at all. That neutral mass is a lexicon coverage failure, and it is the core argument for a transformer model.

---

## T2.1 — Inference implementation

Model: `cardiffnlp/twitter-roberta-base-sentiment-latest` (3-class: `negative` / `neutral` / `positive`).

### Required preprocessing — CardiffNLP's own convention
The model was trained with user mentions and URLs replaced by placeholders. Applying it to raw text degrades accuracy. Add a dedicated function; **do not reuse `TextCleaner`, which strips URLs entirely**:

```python
def roberta_preprocess(text: str) -> str:
    out = []
    for tok in str(text).split(" "):
        if tok.startswith("@") and len(tok) > 1:
            tok = "@user"
        elif tok.startswith("http"):
            tok = "http"
        out.append(tok)
    return " ".join(out)
```
Apply to `tweet_cleaned` from the WP1 v3 parquet. Store the result in a `roberta_input_text` column so the exact model input is auditable.

### Device, precision, batching
```python
device = "cuda" if torch.cuda.is_available() else "cpu"
model  = AutoModelForSequenceClassification.from_pretrained(MODEL_ID).to(device).eval()
if device == "cuda":
    model = model.half()          # fp16 — 4 GiB VRAM requires it
torch.set_num_threads(os.cpu_count())   # matters only on the CPU path
```

| Setting | Value | Why |
|---|---|---|
| `max_length` | 128 | Tweets are ≤ 280 chars; 128 wordpieces covers essentially all. Record the truncation rate. |
| `batch_size` (GPU) | start **128**, halve on `torch.cuda.OutOfMemoryError`, floor 16 | 4 GiB is tight |
| `batch_size` (CPU) | 64 | measured baseline |
| `torch.inference_mode()` | required | disables autograd |

### Length-sorted batching (required)
Sort rows by token length before batching and restore the original order afterwards. Padding to the batch maximum is the dominant cost; sorting typically gives a 2–4× speedup with **bit-identical** results. Verify that claim rather than assuming it: assert the restored order matches the input index exactly.

### Checkpointing (required)
1.28 M rows is a long run. Write shard parquets every 50,000 rows to `data/02_interim/phase3_v3/_shards/`, and make the runner resumable by skipping completed shards. A crash at 90% must not cost the whole run.

### Output columns
| Column | Content |
|---|---|
| `roberta_prob_negative` | softmax probability |
| `roberta_prob_neutral` | softmax probability |
| `roberta_prob_positive` | softmax probability |
| `roberta_score` | `prob_positive − prob_negative`, range `[−1, 1]` — comparable in sign/scale to `vader_compound` |
| `roberta_label` | `argmax` over the three classes |
| `roberta_inference_status` | `"completed"` — set by the code path that ran, never a literal (R3) |

> `roberta_score` is a **derived convenience column**. It is a real function of real probabilities, which makes it legitimate; the fabricated version was `f(vader)`. Keep all three probabilities so any downstream consumer can recompute it.

---

## T2.2 — Honest VADER-vs-RoBERTa comparison

The previous Pearson check was circular. Replace it with genuine agreement statistics computed over the full corpus:

| Metric | Note |
|---|---|
| Pearson **and** Spearman `vader_compound` vs `roberta_score` | Report both |
| 3×3 confusion matrix `vader_label` × `roberta_label` | Raw counts |
| Cohen's κ | The headline agreement number |
| Exact-agreement rate | Fraction of rows with identical labels |
| **RoBERTa label distribution restricted to `vader_compound == 0.0`** | **The most important diagnostic in this package** |

That last row is the point of the whole exercise. 37.33% of tweets are VADER-neutral purely because the lexicon did not fire. If RoBERTa assigns a substantial share of them to `positive` or `negative`, you have quantified exactly how much signal the lexicon-only pipeline was discarding. Report it prominently.

Write these to `output/results/phase3/v3/evidence/model_agreement.json`.

### Expect and report disagreement
Do **not** treat a low κ as a bug to be tuned away. VADER and RoBERTa are different instruments; κ in the 0.3–0.5 range is a normal and publishable finding. Any tuning to raise agreement would reintroduce the circularity this package exists to remove.

---

## T2.3 — Primacy switch

From v3 onward, **`roberta_score` is the primary sentiment score** and `vader_compound` is the documented baseline comparator. Update:

- the Phase 3 v3 manifest: `"primary_sentiment_model"` must name the model **only if `roberta_inference_status == "completed"`** — assert this in code
- WP4's aggregator instantiation (`TemporalSpatialAggregator(sentiment_col=...)`)
- every report and notebook string

If RoBERTa did not complete, the primary model field must say VADER and the pipeline must be labelled accordingly. That is the honest fallback, and it is acceptable.

---

## T2.4 — Manifest

`output/results/phase3/v3/sentiment_manifest_v3.json`, all values computed at runtime:

```json
{
  "phase": "phase3_sentiment_v3",
  "device_used": "cuda",
  "torch_version": "...",
  "cuda_device_name": "...",
  "precision": "fp16",
  "batch_size_final": 128,
  "oom_backoffs": 0,
  "model_id": "cardiffnlp/twitter-roberta-base-sentiment-latest",
  "model_revision_sha": "<from the HF snapshot dir name>",
  "total_scored_tweets": 0,
  "truncated_at_128_tokens_count": 0,
  "wall_clock_seconds": 0.0,
  "throughput_tweets_per_sec": 0.0,
  "roberta_inference_status": "completed",
  "roberta_label_distribution": {},
  "vader_label_distribution": {},
  "primary_sentiment_model": "...",
  "randomness_used": "none"
}
```

`model_revision_sha` matters: it pins which weights produced these numbers.

---

## Acceptance criteria

| # | Criterion |
|---|---|
| A2.1 | **Zero** occurrences of `np.random`, `numpy.random`, `random.` in `run_phase3_v3.py` and its imports |
| A2.2 | `roberta_score` is **not** an affine function of `vader_compound`: fit `roberta ~ a·vader + b` and confirm residual std > 0.10 and R² < 0.95 |
| A2.3 | The three `roberta_prob_*` columns sum to 1.0 ± 1e-4 for every row |
| A2.4 | `roberta_score == prob_positive − prob_negative` to within 1e-6 for every row |
| A2.5 | Non-null `roberta_score` count equals the v3 row count |
| A2.6 | `device_used` is consistent with WP0's `cuda_available`; `throughput_tweets_per_sec` > 16.6 if `cuda` |
| A2.7 | `model_agreement.json` contains the `vader == 0.0` breakdown |
| A2.8 | **Spot re-inference**: the auditing agent will re-score 200 random rows and require the stored `roberta_score` to match within 1e-3. This is the primary anti-fabrication test — it cannot be passed by any synthetic score. |
