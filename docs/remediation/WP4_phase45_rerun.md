# WP4 — Phase 4 & 5 Re-run on Corrected Inputs

**Depends on**: WP2 passed (WP3 optional).
**Deliverables**: `verify/phase4/run_phase4_v3.py`, `verify/phase5/run_phase5_v3.py`, matrices under `data/03_processed/v3/`.
**Read [00_AGENT_BRIEF.md](00_AGENT_BRIEF.md) first.**

---

## Problem statement

Phases 4 and 5 are arithmetically sound but were fed corrupted inputs, and two behaviours actively hide problems.

- Every existing Phase 4/5 number was computed from a corpus where 176,260 dual-hashtag tweets had been misassigned to the Trump stream (WP1 §D1). $X_i$ — the H2 independent variable — is therefore not measuring what it claims.
- [`itsa_ols_evaluator.py:179-182`](../../src/phase5_modeling/itsa_ols_evaluator.py) silently assigns the **National** OLS result to the Battleground slot when `len(battleground_df) < 5`. A consumer reading the manifest sees a "Battleground regression" that was never run.
- The spatial matrix is built from ~20% of tweets with no representativeness treatment.

---

## T4.1 — Input rewiring

| Input | Change |
|---|---|
| Tweets | `data/02_interim/phase3_v3/twitter_sentiment_v3.parquet` |
| `sentiment_col` | **`roberta_score`** if WP2 completed, else `vader_compound` — decided by reading `roberta_inference_status`, not hardcoded |
| Location | **`state_code_resolved`** (WP1 §T1.5), not raw `state_code` |
| Candidate | **`candidate_resolved`** (WP1 §T1.1), not `candidate` |
| Electoral returns | `data/02_interim/phase1_v2/electoral_returns_v2.parquet` — keep the existing v2 parquet-first logic, which is already correct |

Outputs go to `data/03_processed/v3/`. Do not overwrite `data/03_processed/*.parquet` (rule R5).

---

## T4.2 — Handling `both` in aggregation

This restates WP1 §T1.1 and is binding:

| Matrix | `both` tweets | Rationale |
|---|---|---|
| Temporal (H1) | **Included** | H1 measures overall national sentiment over time. A dual-hashtag tweet is a genuine part of that signal. |
| Spatial $X_i$ (H2) | **Excluded** | $X_i = \bar{s}^{\text{Biden}}_i - \bar{s}^{\text{Trump}}_i$ needs a directional attribution these tweets do not carry. |

Record the `both` row count in each matrix's manifest so the exclusion is visible rather than implicit.

### Also run the sensitivity variant
Produce a second spatial matrix, `spatial_state_matrix_v3_both_split.parquet`, in which each `both` tweet contributes to **both** candidate means. Report $\beta_1$, R² and N for H2 under both treatments.

> If the H2 conclusion flips between the two treatments, that fragility **is the finding** and must be stated in the report. Do not choose whichever variant looks better.

---

## T4.3 — Dual-score matrices

Where WP2 completed, emit both `mean_sentiment_roberta` and `mean_sentiment_vader` (and the corresponding $X_i$) in every matrix. Running H1 and H2 under each score and reporting both is the cheapest available robustness check, and it makes the VADER→RoBERTa switch auditable rather than asserted.

---

## T4.4 — Remove the silent Battleground fallback

Replace [`itsa_ols_evaluator.py:179-182`](../../src/phase5_modeling/itsa_ols_evaluator.py):

```python
if len(battleground_df) >= MIN_SUBGROUP_N:
    battleground_ols = self.evaluate_h2_ols(battleground_df, "Battleground_States", ...)
else:
    battleground_ols = None          # NOT national_ols
    warnings.warn(f"Battleground N={len(battleground_df)} < {MIN_SUBGROUP_N}; no regression run.")
```

The manifest must then carry `"battleground_ols": null` with `"battleground_status": "insufficient_data"` and the actual N. Every downstream consumer — including the notebook — must handle `None` by printing "insufficient data", never by silently substituting another subgroup's numbers.

Apply the same treatment to any other subgroup fallback in that file.

---

## T4.5 — Representativeness reporting for H2

The geocoded subset is not a random sample of the corpus. Quantify the bias instead of noting it in passing:

1. For each state in the spatial matrix, record `n_tweets`, `n_users`, and the **share of national geocoded tweets**.
2. Compare that share against the state's share of the 2020 **certified total vote** (available in `electoral_returns_v2.parquet`). Report the ratio per state and the correlation across states.
3. Flag any state with fewer than 100 geocoded tweets as `"low_confidence": true`. Report how many of the 51 rows this affects, and re-run H2 excluding them as a sensitivity check.
4. Report mean `roberta_score` for geocoded vs non-geocoded tweets. **If these differ materially, geocoding is not missing-at-random** and H2's external validity is limited — say so explicitly.

Write `output/results/phase4/v3/evidence/representativeness.json`.

---

## T4.6 — H1 event windows

The event table has **4 rows** (`political_events_v2.parquet`). Keep the ±48 h window. For each event record: pre-period N, post-period N, and whether N meets the minimum for a stable segmented regression.

With 4 events and hourly data, a Bonferroni-adjusted α of 0.0125 is appropriate. **Report both raw and adjusted p-values** — do not quietly report only whichever is significant. State the multiple-comparison adjustment in the report.

---

## Acceptance criteria

| # | Criterion |
|---|---|
| A4.1 | Phase 4/5 v3 read `twitter_sentiment_v3.parquet` and `state_code_resolved` |
| A4.2 | `sentiment_col` was chosen by reading `roberta_inference_status`, not hardcoded |
| A4.3 | `both` counts appear in both temporal and spatial manifests |
| A4.4 | Both spatial variants exist, with H2 results reported for each |
| A4.5 | Battleground result is `null` + `"insufficient_data"` when N < 5 — the auditing agent will confirm it never equals the National result |
| A4.6 | `representativeness.json` contains per-state shares, vote-share ratios, and the geocoded/non-geocoded sentiment comparison |
| A4.7 | H1 reports raw **and** Bonferroni-adjusted p-values for all 4 events |
| A4.8 | Every coefficient in the manifests is traceable to a `statsmodels` result object in that run — no literals |
