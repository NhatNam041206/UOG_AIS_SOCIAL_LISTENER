# WP1 — Phase 2 Rebuild (v3)

**Depends on**: WP0 passed.
**Deliverable**: `verify/phase2/run_phase2_v3.py` + supporting `src/` modules, producing `data/02_interim/phase2_v3/twitter_cleaned_v3.parquet`.
**Read [00_AGENT_BRIEF.md](00_AGENT_BRIEF.md) first.** Rule R5 applies: **do not touch any `*_v2` artifact.**

---

## Problem statement

Four defects in [`verify/phase2/run_phase2_v2.py`](../../verify/phase2/run_phase2_v2.py) corrupt every downstream result.

### D1 — Cross-stream merge silently reassigns ~176k tweets to Trump

```python
combined_raw = pd.concat([trump_df, biden_df], ignore_index=True)   # L54: Trump rows first
...
after_dedup_df = after_cleaned_df.drop_duplicates(subset=["_clean_text_temp"], keep="first")  # L80
```

221,686 distinct `tweet_id`s carry **both** `#donaldtrump` and `#joebiden`. Because Trump rows are concatenated first and `keep="first"` retains the earliest row, the dual-hashtag tweets are assigned to the Trump stream almost without exception:

| Assigned stream | Dual-hashtag tweets surviving Phase 2 v2 |
|---|---|
| `donald_trump` | **176,260** |
| `joe_biden` | **42** |

The resulting 797,853 / 482,931 split is an artifact of DataFrame row order. This directly corrupts
$X_i = \bar{s}^{\text{Biden}}_i - \bar{s}^{\text{Trump}}_i$, which is the entire H2 independent variable.

### D2 — Dedup key has no user component, so it deletes distinct users' tweets

Dedup is on cleaned text alone. On a 200,000-row sample (`random_state=0`), of 8,932 removals:

- 2,881 were the **same** `tweet_id` — correct
- **6,051 (68%) were distinct `tweet_id`s from 3,670 distinct users** — incorrect

Top removed texts: `#Trump` (592), `#Biden` (408), `#JoeBiden` (403). These are hundreds of *different people* posting the same short hashtag, collapsed into one record. Effect: $N_t$ is deflated non-uniformly, penalising short-text users and any state whose users post tersely.

### D3 — Language detection cannot emit "Other"

[`language_region_cross_analyzer.py:79-87`](../../src/phase2_preprocessing/language_region_cross_analyzer.py) `_heuristic_detect_language()` returns **only** `"English"` or `"Spanish"`. The manifest value `us_other_language_tweets: 0` is therefore a tautology, not a measurement. The accented-character branch of the regex also misfires on French:

```
États-Unis : des #élections en temps de crise…               → flagged "Spanish"
La campagne de #biden est tellement un bide…                 → flagged "Spanish"
5/5 IN FINE, #JoeBiden pourrait être le Président…           → flagged "Spanish"
```

Separately: **Spanish was never justified as the second target language.** It must be selected by measurement, not assumption.

### D4 — Recoverable US geography is discarded

68.81% of rows have an empty `state_code`, but this is not uniformly irrecoverable:

| Bucket | Rows | Recoverable? |
|---|---|---|
| `user_location` blank entirely | 528,644 (30.25%) | No |
| `country ∈ {United States, United States of America}` but `state_code` empty | **61,931** | **Yes** |
| `country ∈ {US, USA}` total (the ceiling) | 394,395 (22.57%) | — |

Also note `state_code` is **not US-only**: `ENG` (40,852), `IDF` (16,496), `ON` (11,403) are English/French/Canadian region codes. The existing classifier handles this, but reports must stop implying otherwise.

---

## T1.1 — Stream membership resolution (fixes D1)

Replace the order-dependent concat/dedup with an explicit, order-independent rule.

1. Load both Phase 1 v2 parquets.
2. Build the membership set **before** concatenating:
   ```python
   trump_ids = set(trump_df["tweet_id"])
   biden_ids = set(biden_df["tweet_id"])
   both_ids  = trump_ids & biden_ids          # expect 221,686
   ```
3. Concatenate, then **collapse to one row per `tweet_id`** (`drop_duplicates(subset=["tweet_id"])`). This is the only place where identity dedup happens.
4. Add a new column `stream_membership` with exactly three values:
   | Value | Meaning |
   |---|---|
   | `trump_only` | `tweet_id` in Trump stream only |
   | `biden_only` | `tweet_id` in Biden stream only |
   | `both` | `tweet_id` in both streams |
5. **Retain the existing `candidate` column unchanged** for lineage, but add `candidate_resolved`:
   - `trump_only` → `donald_trump`
   - `biden_only` → `joe_biden`
   - `both` → **`both`** (a real third value — do **not** pick a side)

> **Rationale for `both` as a third value.** A tweet tagged with both hashtags carries no directional stream signal. Assigning it to either candidate injects the exact bias D1 describes. Downstream (WP4), `both` tweets are **included** in national temporal aggregation (H1 measures overall sentiment, so they belong) and **excluded** from the state margin $X_i$ (H2 requires a directional attribution that these tweets do not provide). WP4 §T4.2 restates this.

**Sanity check to record**: `trump_only + biden_only + both` must equal the unique-`tweet_id` count, expected **1,522,660**.

---

## T1.2 — Activity filter (unchanged logic, corrected reporting)

Keep the existing P99.5 = 9.0 tweets/active-day threshold and `UserActivityAuditor`. Apply it **after** T1.1's identity dedup, so a dual-hashtag tweet is not counted twice toward a user's velocity.

> This ordering change will move the numbers away from the v2 baseline (2,227 users / 222,366 tweets, which were computed on the double-counted 1,747,542 rows). **That divergence is expected and correct.** Report both.

Record in evidence:
- users examined, users removed, tweets removed
- the empirical P99, P99.5, P99.9 of `tweets_per_active_day` **recomputed on the deduplicated frame**
- the same statistics computed on the raw double-counted frame, for comparison

---

## T1.3 — Text cleaning, then a corrected dedup (fixes D2)

Order: clean → drop empty → near-duplicate removal.

Cleaning stays as `TextCleaner.clean()` ([`cleaning_heuristics_model.py`](../../src/phase2_preprocessing/cleaning_heuristics_model.py)): HTML unescape, tag strip, URL strip, whitespace collapse. Capitalisation, punctuation and emoji are preserved deliberately — VADER and Twitter-RoBERTa both use them as signal. **Do not add lowercasing, stopword removal, or lemmatisation.**

### The dedup key changes to `(user_id, tweet_cleaned)`

```python
df = df.drop_duplicates(subset=["user_id", "tweet_cleaned"], keep="first")
```

This removes a user reposting identical text (genuine self-duplication / URL-variant spam) while preserving different users posting the same string.

### Report, do not remove, cross-user text repetition
Compute and record — but **do not filter on** — the count of cleaned texts shared by ≥2 distinct users, and the top 20 such texts with their distinct-user counts. This is the "many people tweeted `#Trump`" population. It is real user behaviour and belongs in the corpus; it is recorded so a reader can judge its weight.

Record in evidence: rows before/after, removed count, and the split of removals by whether the duplicate pair shared a `tweet_id`.

---

## T1.4 — Real language identification (fixes D3)

Use the WP0 backend (`fasttext` `lid.176` preferred).

1. Add `detected_language` (ISO 639-1 code, e.g. `en`, `es`, `fr`, `pt`) and `language_confidence` (float) columns, computed on `tweet_cleaned`.
2. Rows where `tweet_cleaned` has **fewer than 3 tokens** are unreliable for language ID. Label these `detected_language = "und"` (undetermined) with `language_confidence = null`. Do **not** silently default them to English — that default is what produced the fictitious 100%-English result in an earlier revision.
3. Update `LanguageRegionCrossAnalyzer` so `classify_language()` maps: `en → English`, `es → Spanish`, `und → Undetermined`, **everything else → Other**. `"Other"` must now be reachable; if it comes back 0, that is a measurement, not a structural artifact.

### The Spanish-target survey (this is the deliverable, not the code)

Produce `output/results/phase2/v3/evidence/language_survey.json` containing the **full ranked language distribution**, both corpus-wide and restricted to US-state-mapped rows:

```json
{
  "corpus_wide": [{"lang": "en", "n": 0, "pct": 0.0}, ...],
  "us_state_mapped": [{"lang": "en", "n": 0, "pct": 0.0}, ...],
  "top_non_english_us": [...],
  "threshold_pct_for_dedicated_handling": 1.0,
  "languages_above_threshold_us": ["..."]
}
```

Then write a short section in `output/reports/phase2/v3/language_target_justification.md` that answers, **from these numbers**:

- Which non-English languages actually exceed 1% of US-state-mapped tweets?
- Is Spanish among them, and at what share? (The v2 run reported 6,600 / 264,095 ≈ 2.50%, produced by a regex that also swept up French — treat that figure as unvalidated.)
- Does any other language warrant dedicated handling?

**Do not pre-commit to Spanish.** If the measured distribution says otherwise, say so. If Spanish does clear the threshold, the justification is then evidence-based and the existing retention policy stands.

> **Policy that does not change**: non-English tweets mapped to US states are **retained**, never filtered. The question this task answers is which languages need *dedicated treatment* (e.g. a multilingual sentiment model), not which to keep.

---

## T1.5 — Geographic recovery (fixes D4)

Add `state_code_resolved` and `state_code_source`. **Never overwrite the original `state_code`.**

Resolution order, first match wins:

| Priority | Source | `state_code_source` value |
|---|---|---|
| 1 | `state_code` already a valid US 2-letter code | `original_state_code` |
| 2 | `state` column matches a US state name | `state_name_match` |
| 3 | `user_location` parsed against a gazetteer (see below) **and** `country` is US or blank | `user_location_gazetteer` |
| 4 | Non-US region code (`ENG`, `IDF`, `ON`, …) or non-US country | `non_us` |
| 5 | Nothing resolves | `unmapped` |

### Gazetteer requirements
Match, case-insensitively, on the `user_location` string:
- all 50 state names + `District of Columbia`
- the 50 USPS 2-letter abbreviations **only when token-bounded and paired with a US signal** — e.g. `"Austin, TX"`, `"TX, USA"`. A bare `"CA"` is ambiguous (Canada) and must **not** match; a bare `"OR"`/`"IN"`/`"ME"`/`"OK"`/`"HI"` are English words and must not match.
- common city → state pairs are **out of scope**; do not attempt city geocoding.

Ambiguity is resolved conservatively: **when in doubt, leave it `unmapped`.** Inflating US coverage with bad matches is worse than reporting a low ceiling.

### Mandatory honesty check
Record in evidence:
```json
{
  "us_mappable_ceiling_rows": 394395,
  "us_mappable_ceiling_pct": 22.57,
  "resolved_us_rows_v3": 0,
  "resolved_us_pct_v3": 0.0,
  "gain_over_v2_pct_points": 0.0,
  "by_source": {"original_state_code": 0, "state_name_match": 0, "user_location_gazetteer": 0, "non_us": 0, "unmapped": 0}
}
```

> **If `resolved_us_pct_v3` exceeds ~25%, your gazetteer is over-matching.** The ceiling is set by how many users disclosed a US location at all. Stop and audit a random sample of 50 `user_location_gazetteer` matches by hand before proceeding.

### Manual precision check (required)
Sample 50 rows with `state_code_source == "user_location_gazetteer"`, write them with their `user_location` string and assigned code to `output/results/phase2/v3/evidence/gazetteer_sample.json`, and record how many are correct. The auditing agent will re-read these 50 rows. Report the precision honestly — a precision of 0.86 that is true is acceptable; a claimed 1.00 that is not will fail verification.

---

## T1.6 — Manifest and report

Write `output/results/phase2/v3/preprocessing_manifest_v3.json`. It must include a `v2_comparison` block placing every headline figure side by side with the v2 value, and a `deltas_explained` array of short strings naming the cause of each change (e.g. `"dedup key now includes user_id, so 6,051-per-200k cross-user removals no longer occur"`).

Regenerate `output/reports/phase2/v3/preprocessing_report_v3.md`. **Delete the v2 claim "Approximately 20.5% of tweets carry a valid US state code"** and replace it with the measured v3 figure plus the ceiling context from T1.5.

---

## Acceptance criteria

| # | Criterion |
|---|---|
| A1.1 | `stream_membership` has exactly 3 values; counts sum to the unique-`tweet_id` total (expect 1,522,660) |
| A1.2 | `candidate_resolved` contains a real `both` category; **neither** `donald_trump` nor `joe_biden` absorbs the 221,686 dual tweets |
| A1.3 | No `tweet_id` appears more than once in the v3 output |
| A1.4 | Dedup key demonstrably includes `user_id`; a text posted by 2+ distinct users survives (auditing agent will search for `#Trump` and count distinct users) |
| A1.5 | `detected_language` has ≥ 4 distinct values including at least one that is not `en`/`es`/`und` |
| A1.6 | `language_survey.json` exists with a full ranked distribution, and the justification doc cites its numbers |
| A1.7 | `state_code_source` present; `resolved_us_pct_v3` ≤ 25.0 and `gain_over_v2_pct_points` > 0 |
| A1.8 | `gazetteer_sample.json` has 50 rows with an honest precision figure |
| A1.9 | v2 artifacts under `data/02_interim/phase2_v2/` and `output/results/phase2/v2/` are byte-identical to before |
| A1.10 | No `np.random` anywhere in the new code except a documented `random_state` in the two sampling calls |
