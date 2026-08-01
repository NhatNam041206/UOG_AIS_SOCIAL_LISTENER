# WP0 — Environment Repair & Fingerprint

**Prerequisite for**: all other work packages.
**Read [00_AGENT_BRIEF.md](00_AGENT_BRIEF.md) first**, especially rules R1–R7.

---

## Problem statement

Three environment facts block the remediation:

1. **`vaderSentiment` is not installed**, yet [`src/phase3_sentiment/sentiment_models_model.py:11`](../../src/phase3_sentiment/sentiment_models_model.py) does `from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer`. That module is currently **unimportable**. Phase 3 v2 nonetheless produced VADER columns, so either a different code path ran or the environment changed after the run. **The provenance of every existing `vader_compound` value is therefore unverified.**
2. **`torch` is the CPU-only build** (`2.9.1+cpu`) on a machine with a CUDA-capable RTX 3050 Ti. Full-corpus RoBERTa on CPU is ~21 h; on GPU it should be well under 1 h.
3. **No language identification library is installed**, so Package D falls back to a two-outcome regex.

---

## T0.1 — Resolve the VADER provenance question

**Do not skip this and do not paper over it.** Determine which analyzer produced the existing scores.

1. Confirm the import actually fails:
   ```bash
   python -c "import vaderSentiment" 
   ```
2. Inspect `src/phase3_sentiment/sentiment_models_model.py` and every caller. Determine whether `VaderSentimentModel` is reachable at all.
3. Recompute VADER for a 5,000-row sample of `data/02_interim/phase3_v2/twitter_sentiment_v2.parquet` using **NLTK's** `SentimentIntensityAnalyzer` (`nltk.sentiment.vader`, lexicon `vader_lexicon`) applied to the stored `tweet_cleaned` column, and compare against the stored `vader_compound`.

**Decide and record one of:**
- `"identical"` — max absolute difference < 1e-9 over the sample. The stored scores are NLTK-VADER and are trustworthy.
- `"mismatch"` — record the max/mean absolute difference and the number of differing rows. **Existing Phase 3 v2 scores are then of unknown provenance and WP1's output must be re-scored from scratch in WP2.**

### Standardise on one analyzer
Install the canonical package so the two implementations cannot diverge again:
```bash
pip install vaderSentiment
```
(Any recent version is fine — pin the version you actually get in the evidence fingerprint, R7a.) Then, if T0.1 found a mismatch, additionally record the max absolute difference between `vaderSentiment` and `nltk` on the same 5,000-row sample. Both wrap the same lexicon; a non-trivial difference is itself a finding worth reporting.

Whichever analyzer you standardise on, `VaderSentimentModel.NEGATIVE_THRESHOLD` / `POSITIVE_THRESHOLD` must remain **±0.05**. See [WP5](WP5_notebook_corrections.md) §N4 for why this value is correct and must not be changed.

---

## T0.2 — Install a CUDA build of PyTorch

Target: `torch.cuda.is_available() == True` on the RTX 3050 Ti.

```bash
pip uninstall -y torch torchvision torchaudio
pip install torch --index-url https://download.pytorch.org/whl/cu126
```

> If `cu126` wheels are unavailable for Python 3.11 at run time, try `cu124`, then `cu121`, or whatever current CUDA build actually installs and reports `cuda.is_available() == True` on this driver — the exact version is not the point, a working GPU build is. **Record which index URL actually succeeded.**

Verify:
```python
import torch
assert torch.cuda.is_available(), "CUDA still unavailable after reinstall"
print(torch.__version__, torch.version.cuda, torch.cuda.get_device_name(0))
print(torch.cuda.get_device_properties(0).total_memory / 1024**3, "GiB")
```

**If CUDA cannot be enabled**, do not fake it. Record `"cuda_enabled": false` with the failure reason and proceed — WP2 has a documented CPU fallback path with a longer runtime. This is an acceptable outcome; a false `true` is not.

### VRAM constraint
4 GiB is small. `roberta-base` in fp16 at `max_length=128` is comfortable, but you must leave headroom. WP2 specifies batch sizing and an OOM back-off; do not exceed it.

---

## T0.3 — Install language identification

```bash
pip install fasttext-wheel langdetect
```

Download the official compact model to `models/lid.176.ftz`:
`https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz` (~917 KB).

`fasttext` `lid.176` is the primary choice: it emits **176 language labels with confidence scores**, which is what makes an honest "Other" bucket possible. `langdetect` is the fallback if the fasttext wheel fails to build on Windows.

**If neither installs**, record the failure and set WP1's language method to `"unavailable"`. Do **not** fall back to the regex and call it language detection — the regex may remain only if it is labelled `"heuristic_two_class_regex"` everywhere, with `"Other"` explicitly reported as `null` rather than `0`.

---

## T0.4 — Emit the environment fingerprint

Write `output/results/environment/evidence/env_fingerprint.json`. **Every field must be read at runtime**, none typed by hand.

```json
{
  "status": "passed",
  "timestamp_utc": "<datetime.now(timezone.utc).isoformat()>",
  "python_version": "<sys.version>",
  "cpu_count": 16,
  "torch_version": "<torch.__version__>",
  "torch_cuda_version": "<torch.version.cuda or null>",
  "cuda_available": true,
  "cuda_device_name": "<torch.cuda.get_device_name(0) or null>",
  "cuda_total_memory_gib": 4.0,
  "cuda_install_index_url": "<the URL that actually worked, or null>",
  "transformers_version": "<transformers.__version__>",
  "vader_backend": "vaderSentiment|nltk",
  "vader_provenance_check": {
    "verdict": "identical|mismatch",
    "sample_size": 5000,
    "max_abs_diff": 0.0,
    "mean_abs_diff": 0.0,
    "n_rows_differing": 0
  },
  "language_id_backend": "fasttext_lid176|langdetect|unavailable",
  "language_id_model_path": "models/lid.176.ftz",
  "packages": { "<name>": "<version>" }
}
```

---

## Acceptance criteria

| # | Criterion |
|---|---|
| A0.1 | `env_fingerprint.json` exists and every field is present |
| A0.2 | `vader_provenance_check.verdict` is populated with a real measured `max_abs_diff` |
| A0.3 | `cuda_available` matches what a fresh `python -c "import torch; print(torch.cuda.is_available())"` returns — the auditing agent will re-run this |
| A0.4 | `import vaderSentiment` succeeds, **or** `sentiment_models_model.py` no longer imports it |
| A0.5 | If `language_id_backend != "unavailable"`, the model file exists at the recorded path with a non-zero size |
| A0.6 | No metric in the fingerprint is a hand-typed literal |
