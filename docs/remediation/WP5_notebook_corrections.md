# WP5 — Overview Notebook Corrections

**Depends on**: WP1, WP2, WP4 passed.
**Deliverable**: `notebooks/pipeline_overview_v3.ipynb` (new file — leave `pipeline_overview.ipynb` in place per rule R5).
**Read [00_AGENT_BRIEF.md](00_AGENT_BRIEF.md) first.**

---

## Problem statement

The notebook is the artifact a reader will actually judge the project by, and several of its cells make claims the data does not support. Each correction below is numbered `N#` and must be implemented.

---

## N1 — The user-activity chart contradicts the funnel (cell 8)

Cell 6 reports 12.72% of tweets removed by the >9.0/day activity filter. Cell 8 then plots a histogram with the threshold line and shows **nothing above it**, implying 0%. Both are arithmetically correct; they are computed on different populations:

| Computation | Users > 9.0/day |
|---|---|
| Pre-filter, full data | **2,227** (0.461% of 483,175 users, holding **222,366 tweets = 12.72%**) |
| Post-filter, full data | 6 |
| Post-filter, **300k sample** (what cell 8 does) | **0** (max 8.0) |

Cell 8 loads `twitter_cleaned_v2.parquet` — already filtered — then `.sample(300_000)`, which further shrinks each user's tweets-per-active-day. It plots the *result* of the filter against the threshold that produced it.

**Fix**: recompute the histogram from the **Phase 1 v2 concatenation, pre-filter, full data**. Overlay the removed region and annotate it with the true counts. Add a second panel showing the post-filter distribution, labelled as such. Add a caption stating that 0.46% of *users* held 12.72% of *tweets* — the disproportion is the actual finding and it is currently invisible.

---

## N2 — Phase 1: the post-election volume flip needs an explanation

Cell 4's daily chart shows Biden overtaking Trump on Nov 7–8. A reader will suspect ingestion drift. It is not:

| Day | Trump | Biden | B/T |
|---|---|---|---|
| Oct 15 – Nov 6 | leads all 23 days | — | 0.54 – 0.93 |
| **Nov 7** | 103,711 | **150,700** | **1.453** |
| **Nov 8** | 57,423 | **75,564** | **1.316** |

The race was called for Biden by AP and the major networks on the morning of **7 November 2020**. The flip is a genuine event response, measured in the raw pre-filter parquets, and it is a usable H1 validation case.

**Fix**: annotate Nov 7 on the chart, add a B/T ratio subplot, and state in markdown that the flip is an event signal rather than a collection artifact — with the caveat that Nov 9–15 is absent because the Kaggle source (Version 19) stopped collecting on Nov 8, so the decay of that spike is unobserved.

---

## N3 — Phase 2: the cross-stream assignment bias must be disclosed

Cell 5's markdown describes the dedup fix but omits that `keep="first"` on a Trump-first concat handed **176,260 of 176,302** surviving dual-hashtag tweets to the Trump stream (42 to Biden).

**Fix**: replace with the WP1 `stream_membership` breakdown — `trump_only` / `biden_only` / `both` with real counts — and state plainly that the v2 797,853 / 482,931 split was an artifact of row order, now corrected. Show the v2 → v3 comparison.

---

## N4 — Phase 3: justify the ±0.05 threshold instead of asserting it

Cell 10 states the thresholds without provenance. Two facts must appear:

**Provenance.** ±0.05 on the compound score is the standard from Hutto & Gilbert (2014), *"VADER: A Parsimonious Rule-based Model for Sentiment Analysis of Social Media Text"* (ICWSM-14), and is the documented convention in the official `vaderSentiment` README and NLTK's implementation. It is not a project invention. Cite it.

**Sensitivity, measured on this corpus (1,280,784 rows):**

| Threshold | pos | neu | neg |
|---|---|---|---|
| 0.00 | 35.3% | 37.3% | 27.4% |
| **0.05** | 34.8% | 38.1% | 27.0% |
| 0.10 | 34.1% | 39.6% | 26.4% |
| 0.20 | 32.4% | 42.9% | 24.7% |

**37.33% of tweets score exactly `0.0`.** The band `(0, 0.05)` therefore holds only ~0.5% of the corpus, and moving the threshold anywhere in `[0, 0.1]` shifts labels by under 1.5 percentage points. **The threshold choice is close to immaterial here.**

**Fix**: add the citation, add a sensitivity table computed at runtime (not the literals above — recompute them, R2), and add a plot of the compound distribution with the spike at 0.0 made visible. Add a markdown note that the 37% neutral mass is a lexicon *coverage* limit, not a finding that 37% of political tweets are neutral — and point at WP2's RoBERTa breakdown of those same rows as the resolution.

---

## N5 — Phase 3: RoBERTa status was false

Cell 10 claims `"deferred_requires_gpu"`. `transformers` was installed, the weights were already cached, and CPU inference ran at 16.6 tweets/sec in testing.

**Fix**: remove the deferral language entirely. Report the real WP2 run — device, precision, throughput, wall clock — and add the VADER-vs-RoBERTa agreement panel: confusion matrix, Cohen's κ, and the RoBERTa label breakdown of the `vader_compound == 0.0` rows.

---

## N6 — Phase 2: the language section needs a survey, not an assumption

Cell 5 asserts Spanish as the target language and cell 9 plots `us_other_language_tweets: 0`. The v2 detector returns **only** `"English"` or `"Spanish"` — `"Other"` is unreachable, so the 0 is structural. The regex also flags French as Spanish (verified on French-language tweets in the corpus).

**Fix**: plot the **full ranked language distribution** from WP1's `language_survey.json`, restricted to US-state-mapped tweets. State which languages actually clear 1%. Present Spanish as the outcome of that survey if the data supports it — and if the measured share differs from the v2 figure of 2.50%, say so and explain that the v2 number came from a detector that swept in French.

---

## N7 — Phase 4: geography, with the ceiling made explicit

Cell 17 says "only ~20.5% of tweets carry a valid `state_code`", which reads as a fixable gap. It is mostly not:

| Bucket | Rows | Recoverable |
|---|---|---|
| `user_location` blank entirely | 528,644 (30.25%) | No |
| `country ∈ {US, USA}` but `state_code` empty | 61,931 | **Yes** |
| `country ∈ {US, USA}` total — **the ceiling** | 394,395 (**22.57%**) | — |

Also, `state_code` is not US-only: `ENG` 40,852, `IDF` 16,496, `ON` 11,403.

**Fix**: replace the three-bar chart with a waterfall showing the ceiling, the recovered rows, and the irrecoverable remainder. Break "Non-US" out by top region codes. State that H2 is a geocoded-subset analysis with a ~23% ceiling that no amount of parsing will lift — and show WP4's representativeness comparison against state vote shares.

---

## N8 — Phase 5: handle the null Battleground result

Cell 20 does `if len(bg_df) >= 5`, but the underlying evaluator silently substitutes the National result in the same situation. After WP4 the result may be `None`.

**Fix**: print `"Battleground: insufficient data (N=…)"` when the result is null. Never display a National coefficient under a Battleground label. Add Bonferroni-adjusted p-values alongside raw ones for the 4 H1 events, and note the adjustment in the markdown.

---

## N9 — Rewrite the limitations table (cell 24)

The current table understates several issues. Replace with, at minimum:

| # | Limitation | Status after remediation |
|---|---|---|
| 1 | RoBERTa deferred | **Resolved** — real GPU inference, WP2 |
| 2 | Dual-hashtag tweets misassigned to Trump | **Resolved** — `both` category, WP1 |
| 3 | Dedup deleted distinct users' identical short texts | **Resolved** — key now `(user_id, text)`, WP1 |
| 4 | Language detector could not emit "Other" | **Resolved** — fasttext lid.176, WP1 |
| 5 | US geocoding ceiling ~22.6% | **Structural** — quantified, not fixable |
| 6 | `candidate` = hashtag stream ≠ political stance | **Structural** — inherent to the source |
| 7 | Nov 9–15 unobserved; post-call spike decay unmeasured | **Structural** — Kaggle collection boundary |
| 8 | 4 events, hourly data → limited ITSA power | **Structural** — Bonferroni-adjusted |
| 9 | Silver labels are LLM-generated, anchored on only 15 human seeds | **Structural** — report agreement, WP3 |

Every "Resolved" row must link to the evidence file that demonstrates it.

---

## N10 — Provenance header

Add a cell near the top that loads every v3 manifest and prints: run IDs, model IDs + revision SHAs, device used, row counts at each phase boundary, and the WP0 environment fingerprint. A reader should be able to see what actually ran without leaving the notebook.

---

## Acceptance criteria

| # | Criterion |
|---|---|
| A5.1 | Notebook executes top to bottom with no errors on a clean kernel |
| A5.2 | Every number displayed is computed in-notebook from a v3 artifact — **no hardcoded literals** (rule R2) |
| A5.3 | N1's histogram is built from pre-filter Phase 1 v2 data, full population, not a sample |
| A5.4 | No cell contains the string `deferred_requires_gpu` |
| A5.5 | The language chart shows > 2 categories with a real "Other" |
| A5.6 | The limitations table separates "Resolved" from "Structural" and links to evidence |
| A5.7 | Outputs are saved in the committed `.ipynb` so results are visible without re-execution |
| A5.8 | `notebooks/pipeline_overview.ipynb` (v2) is unmodified |
