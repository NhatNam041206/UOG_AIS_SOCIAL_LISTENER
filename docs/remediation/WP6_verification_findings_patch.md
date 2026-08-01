# WP6 — Patch: Verification Findings from WP0–WP5

**Depends on**: WP0–WP5 (already executed).
**Read [00_AGENT_BRIEF.md](00_AGENT_BRIEF.md) and [VERIFICATION_CONTRACT.md](VERIFICATION_CONTRACT.md) first — the same rules apply, especially R2 (no hand-typed metrics), R3 (statuses derived at runtime), and R6 (never tune output to match an expected number).**

---

## Context: what the audit found

The auditing agent (Claude) independently re-ran verification against your WP0–WP5 output — not by reading your log, but by reloading the actual models in `.venv` and re-scoring 200 random rows from `twitter_sentiment_v3.parquet` from scratch, and by reading the manifests, parquets, and notebook cells directly.

**The good news, stated plainly so it's not lost**: this passed the hard part. `roberta_score` re-inference matched stored values within 1e-3 on 199/200 rows (the 200th differs by 0.0013 — fp16 rounding), `irony_prob` matched on 200/200 rows, neither is an affine transform of another column, `np.random` does not appear anywhere in the v3 code paths, the Battleground `None`-fallback fix is genuinely in the source, and the v2 artifacts are untouched. That is real, verified work — this patch is about three specific defects found on top of it, not a re-litigation of WP0–WP5.

**Three defects, all independently confirmed:**

### F1 — WP4 log self-check reports a number that contradicts its own evidence file
`docs/remediation/AGENT_EXECUTION_LOG.md`, WP4 section, self-check row `A4.3`, states:
> `` `temporal_both_row_count`: 221,686 ``

The actual file, `data/03_processed/v3/phase4_manifest_v3.json`, says:
```json
"temporal_both_row_count": 183935
```
221,686 is the **pre-filter raw overlap count** (from WP1 §T1.1 — correct in that context). 183,935 is the **post-activity-filter, post-dedup** count of `both` rows that actually reached Phase 3/4 — this is the number that belongs in the Phase 4 manifest, and it is already correctly computed and stored there. **The evidence file is right; only the log's self-check row is wrong.** This needs a log correction, not a data fix — see T6.1.

### F2 — Phase 4 never persists the hourly/daily temporal matrices
[`verify/phase4/run_phase4_v3.py:38-47`](../../verify/phase4/run_phase4_v3.py#L38-L47) builds the full `hourly` DataFrame (volume, mean/std sentiment for both RoBERTa and VADER, one row per hour across the whole Oct 15 – Nov 8 window) but only ever slices it into ±48h windows around the 4 political events before discarding it. **No `temporal_hourly_matrix_v3.parquet` or daily equivalent is ever written to disk.** Consequence: there is no v3 artifact anywhere containing the full-window national sentiment time series, so nobody downstream — including the notebook — can plot it. This needs the two matrices persisted — see T6.2.

### F3 — Two notebook cells run without error but render nothing
Both are in [`verify/phase5/create_notebook_v3.py`](../../verify/phase5/create_notebook_v3.py), which generates `notebooks/pipeline_overview_v3.ipynb`.

**Cell 1 (provenance header), lines 26, 41-42, 46:**
```python
env = load_json(ROOT / "docs/remediation/evidence/wp0_environment_fingerprint.json")   # WRONG PATH — file doesn't exist
...
print(f"Raw Tweets (Trump): {p1.get('source_files', {}).get('trump', {}).get('raw_rows')}")   # WRONG KEYS
print(f"Raw Tweets (Biden): {p1.get('source_files', {}).get('biden', {}).get('raw_rows')}")
...
print(f"Total Unique Tweets: {p2.get('total_rows_after_dedup')}")   # WRONG KEY
```
`load_json()` silently returns `{}` on a missing path, and `.get()` silently returns `None` on a missing key, so this cell executes cleanly and prints a page of blanks. It has been doing this since WP5 ran; nobody caught it because nothing crashed.

**Cell 13 (N6, the language-distribution chart — this is the chart that directly answers the "0% Other language" complaint from the original audit), lines 189-190:**
```python
lang = load_json(ROOT / "output/results/phase2/v3/evidence/language_survey.json")
if "ranked_distribution" in lang:          # this key does not exist in language_survey.json
    lang_dist = lang["ranked_distribution"]
    ...
```
The auditing agent confirmed this cell's actual saved output in the `.ipynb` is empty — the `if` is always false, so the chart never renders. This is the single most consequential bug in the patch: it silently defeats the one visualization meant to demonstrate that Package D's language detection is fixed.

---

## T6.1 — Correct the log, don't touch the data

`data/03_processed/v3/phase4_manifest_v3.json` is correct as-is. Do not change `temporal_both_row_count`.

Edit `docs/remediation/AGENT_EXECUTION_LOG.md`, WP4 section:
1. Fix the `A4.3` row to read the actual measured value (183,935), quoted directly from the file — do not hand-type it, re-read the JSON in the shell and paste its actual output.
2. Add a row to WP4's "Discrepancies against 00_AGENT_BRIEF.md §4" table:

| Quantity | Brief says | I measured | Explanation |
|---|---|---|---|
| `both` row count | 221,686 (raw, pre-filter — brief §4) | 183,935 (post-activity-filter, post-dedup, in `phase4_manifest_v3.json`) | The brief's figure is the raw cross-stream overlap before any Phase 2 filtering. 37,751 dual-hashtag tweets (17%) were removed by the same activity-volume and `(user_id, tweet_cleaned)` dedup filters applied to every other tweet. This is the expected, correctly-computed post-filter figure, not an error. |

This is exactly the kind of entry rule R6 exists for: state the discrepancy and its cause, don't paper over it.

---

## T6.2 — Persist the temporal matrices

In `verify/phase4/run_phase4_v3.py`, after the `hourly` DataFrame is built (currently ends at line 47) and before the event-window loop:

```python
hourly.to_parquet(out_dir / "temporal_hourly_matrix_v3.parquet")

daily = df_temp.assign(_day=df_temp["_datetime"].dt.floor("D")).groupby("_day").agg(
    volume=("tweet_id", "count"),
    mean_sentiment_roberta=("roberta_score", "mean"),
    std_sentiment_roberta=("roberta_score", "std"),
    mean_sentiment_vader=("vader_compound", "mean"),
    std_sentiment_vader=("vader_compound", "std"),
).reset_index().rename(columns={"_day": "timestamp_daily"})
daily["std_sentiment_roberta"] = daily["std_sentiment_roberta"].fillna(0.0)
daily["std_sentiment_vader"] = daily["std_sentiment_vader"].fillna(0.0)
daily.to_parquet(out_dir / "temporal_daily_matrix_v3.parquet")
```

Add both row counts to `phase4_manifest_v3.json` (`hourly_row_count`, `daily_row_count`), read from `len(hourly)` / `len(daily)` at runtime — not typed.

### Add one notebook cell using the new artifact
In `create_notebook_v3.py`, insert a new code cell after the existing N5 (RoBERTa) section, before N6 (language survey):

```python
daily_v3 = pd.read_parquet(ROOT / "data/03_processed/v3/temporal_daily_matrix_v3.parquet")
daily_v3["timestamp_daily"] = pd.to_datetime(daily_v3["timestamp_daily"], utc=True)

fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
axes[0].plot(daily_v3["timestamp_daily"], daily_v3["volume"], marker="o")
axes[0].axvline(pd.Timestamp("2020-11-07", tz="UTC"), color="black", linestyle="--", label="Race called for Biden")
axes[0].set_title("Daily Tweet Volume (v3, all candidate_resolved categories)")
axes[0].legend()

axes[1].plot(daily_v3["timestamp_daily"], daily_v3["mean_sentiment_roberta"], color="#2980B9", label="RoBERTa")
axes[1].plot(daily_v3["timestamp_daily"], daily_v3["mean_sentiment_vader"], color="#7F8C8D", alpha=0.7, label="VADER")
axes[1].axhline(0, color="gray", linestyle=":")
axes[1].axvline(pd.Timestamp("2020-11-07", tz="UTC"), color="black", linestyle="--")
axes[1].set_title("Daily Mean Sentiment — RoBERTa (primary) vs VADER (baseline)")
axes[1].legend()
plt.tight_layout()
plt.show()
```

Give it a one-line markdown header noting this is the full-window v3 series, distinct from N2's raw pre-filter hashtag-stream chart.

---

## T6.3 — Fix the two broken notebook cells

Both fixes go in `verify/phase5/create_notebook_v3.py`. After editing, **regenerate and re-execute the notebook** (`python verify/phase5/create_notebook_v3.py && jupyter nbconvert --to notebook --execute --inplace notebooks/pipeline_overview_v3.ipynb`) — do not hand-edit the `.ipynb` JSON directly.

### Cell 1 — provenance header (lines 26, 41-42, 46)

```python
# line 26 — correct path (this is where WP0 actually wrote it)
env = load_json(ROOT / "output/results/environment/evidence/env_fingerprint.json")
```

The fingerprint schema (per [WP0_environment.md](WP0_environment.md) §T0.4) is flat, not nested under `"environment"` — check `env.get("cuda_available")`, `env.get("python_version")`, `env.get("torch_version")`, `env.get("cuda_device_name")` directly, not `env["environment"].get(...)`. Print these instead of (or in addition to) `p3.get('device_used')`, so the header shows the environment claim independently of what Phase 3 separately reports:

```python
print("=== Environment ===")
print(f"Python: {env.get('python_version')}")
print(f"CUDA Available: {env.get('cuda_available')}")
print(f"CUDA Device: {env.get('cuda_device_name')}")
print(f"Torch: {env.get('torch_version')}")
```

```python
# lines 41-42 — real schema is p1["streams"][stream_name]["record_count"]
print(f"Raw Tweets (Trump): {p1.get('streams', {}).get('twitter_donald_trump_v2', {}).get('record_count')}")
print(f"Raw Tweets (Biden): {p1.get('streams', {}).get('twitter_joe_biden_v2', {}).get('record_count')}")
```

```python
# line 46 — real key is final_cleaned_record_count
print(f"Total Unique Tweets: {p2.get('final_cleaned_record_count')}")
```

Before finalizing, run each `.get()` chain against the real files in a shell and confirm it returns a non-`None` value. If any field still comes back `None`, the key name is still wrong — do not ship a cell that silently prints `None` a second time.

### Cell 13 — N6 language chart (lines 189-190)

`language_survey.json`'s real top-level keys are `corpus_wide`, `us_state_mapped`, `top_non_english_us`, `threshold_pct_for_dedicated_handling`, `languages_above_threshold_us` (each of the first two is a list of `{"lang": ..., "n": ..., "pct": ...}` dicts, already ranked). Replace the cell body:

```python
lang = load_json(ROOT / "output/results/phase2/v3/evidence/language_survey.json")
dist = lang.get("us_state_mapped", [])
if dist:
    top = dist[:10]
    names = [d["lang"] for d in top]
    counts = [d["n"] for d in top]

    plt.figure(figsize=(10, 4))
    sns.barplot(x=names, y=counts)
    plt.title("Top 10 Detected Languages, US-State-Mapped Tweets (v3 FastText)")
    plt.yscale("log")
    plt.ylabel("Count (log scale)")
    for i, d in enumerate(top):
        plt.text(i, d["n"], f"{d['pct']:.2f}%", ha="center", va="bottom", fontsize=8)
    plt.show()

    above = lang.get("languages_above_threshold_us", [])
    print(f"Languages clearing {lang.get('threshold_pct_for_dedicated_handling')}% of US-mapped tweets: {above}")
```

Use `us_state_mapped` (not `corpus_wide`) — the whole point of this chart, per [WP1_phase2_rebuild.md](WP1_phase2_rebuild.md) §T1.4, is the distribution *among tweets that are actually attributable to a US state*, since that's the population Package D's original claim was about.

**After regenerating**, confirm in the saved `.ipynb` that this cell's `outputs` array is non-empty and contains a `display_data` entry — the auditing agent will check this directly, the same way the empty output was caught the first time.

---

## Acceptance criteria

| # | Criterion |
|---|---|
| A6.1 | `AGENT_EXECUTION_LOG.md` WP4 section's `A4.3` row shows 183,935, matching `phase4_manifest_v3.json`, with the discrepancy explanation added |
| A6.2 | `temporal_hourly_matrix_v3.parquet` and `temporal_daily_matrix_v3.parquet` exist under `data/03_processed/v3/`, with row counts recorded in `phase4_manifest_v3.json` |
| A6.3 | The new daily-sentiment notebook cell's saved output is non-empty |
| A6.4 | Notebook cell 1 (provenance) prints real, non-`None` values for CUDA availability, torch version, both raw tweet counts, and total unique tweets — re-open the saved `.ipynb` and confirm no field reads `None` |
| A6.5 | Notebook cell 13 (N6) saved output contains a rendered chart (non-empty `outputs`), built from `us_state_mapped`, with the >1% language list printed |
| A6.6 | Full notebook re-executed top to bottom with no errors after all three fixes (`nbconvert --execute`) |
| A6.7 | No `np.random` or hand-typed metric introduced by this patch (rules R1/R2 still apply) |
| A6.8 | `notebooks/pipeline_overview.ipynb` (v2) and all `*_v2` result/report files remain untouched |
