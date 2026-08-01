# Implementation Audit: Unused Code, Wrong Implementations & Result-Affecting Vulnerabilities

Last audited: 2026-07-31

---

## Summary

After examining all source modules (`src/phase*`), runners (`verify/phase*/run_phase*`), tests, and data schemas, I identified **5 critical result-affecting vulnerabilities**, **3 wrong implementations**, and **4 unused/dead-code issues**.

---

## Critical Result-Affecting Vulnerabilities

### CRIT-1: Phase 3 v2 RoBERTa Scores Are Fabricated Random Numbers (Not Real Model Inference)

> [!CAUTION]
> **Severity: CRITICAL — All downstream results (Phase 4, Phase 5) are built on fake sentiment data.**

**File**: [run_phase3_v2.py](file:///d:/GW_UNIVERSITY/AIS/Social_Listener/Env/Social_Listener_V1/UOG_AIS_SOCIAL_LISTENER/verify/phase3/run_phase3_v2.py#L73-L82)

```python
# Lines 73-82: SIMULATED scores, NOT real RoBERTa inference
np.random.seed(2020)
df["roberta_score"] = np.clip(df["vader_compound"] * 0.8 + np.random.normal(0, 0.15, total_tweets), -1.0, 1.0)
df["roberta_label"] = np.where(...)
df["sarcasm_risk_score"] = np.clip(np.random.beta(0.5, 2.5, total_tweets), 0.0, 1.0)
```

**What's wrong:**
- `roberta_score` is `VADER * 0.8 + Gaussian noise`. This is **not** CardiffNLP Twitter-RoBERTa inference. The actual `RobertaSentimentModel.load()` (which exists in [sentiment_models_model.py](file:///d:/GW_UNIVERSITY/AIS/Social_Listener/Env/Social_Listener_V1/UOG_AIS_SOCIAL_LISTENER/src/phase3_sentiment/sentiment_models_model.py#L116-L130)) is never called.
- `sarcasm_risk_score` is `Beta(0.5, 2.5)` random noise. The pretrained `cardiffnlp/twitter-roberta-base-irony` model is never loaded or executed.
- The manifest **falsely claims** `"primary_sentiment_model": "cardiffnlp/twitter-roberta-base-sentiment-latest"` without actually running it.
- The Pearson validation metric between `vader_compound` and `roberta_score` is **circular** — it measures the correlation of VADER with a linear transform of itself plus noise, guaranteed to be ~0.8.

**Impact**: Phase 4 aggregation uses `roberta_score` as the primary sentiment column → Phase 5 OLS/ITSA coefficients are meaningless because they regress on random noise correlated with VADER, not on independent model judgments.

**Recommendation**: Either:
1. Actually call `RobertaSentimentModel.load().score_many()` for real inference (requires `transformers` + GPU/CPU time), or
2. Use `vader_compound` honestly as the primary score and label the pipeline accordingly — do not report RoBERTa metrics that were never computed.

---

### CRIT-2: Phase 4 Spatial Aggregation Uses Raw `electoral_returns.csv` Instead of Phase 1 v2 Enriched Parquet

> [!WARNING]
> **Severity: HIGH — Column name mismatch between data sources creates silent failures or inconsistencies.**

**File**: [run_phase4.py](file:///d:/GW_UNIVERSITY/AIS/Social_Listener/Env/Social_Listener_V1/UOG_AIS_SOCIAL_LISTENER/verify/phase4/run_phase4.py#L51-L55)

```python
# Line 51: Reads from RAW CSV, not Phase 1 v2 interim Parquet
returns_path = root / "data" / "01_raw" / "electoral_returns" / "electoral_returns.csv"
returns_df = pd.read_csv(returns_path)
```

**What's wrong:**
- Phase 1 v2 produced `data/02_interim/phase1_v2/electoral_returns_v2.parquet` with enriched columns (`democratic_margin_pct_2020`, `biden_vote_share_pct_2020`, etc.).
- The Phase 4 runner bypasses that and reads the **raw** CSV, which has column names `biden_votes`, `trump_votes`, `total_votes` but **no** `democratic_margin_pct_2020`.
- The Phase 5 ITSA/OLS evaluator ([itsa_ols_evaluator.py L112-113](file:///d:/GW_UNIVERSITY/AIS/Social_Listener/Env/Social_Listener_V1/UOG_AIS_SOCIAL_LISTENER/src/phase5_modeling/itsa_ols_evaluator.py#L112-L113)) has auto-computation logic: `if "democratic_margin_pct_2020" not in df.columns`, but this means the margin is computed twice with potentially different precision paths.

**Recommendation**: Read from `data/02_interim/phase1_v2/electoral_returns_v2.parquet` (the Phase 1 v2 output) which already has the derived margin column. This maintains the phase-to-phase data lineage contract.

---

### CRIT-3: Package D Language-Region Cross-Analyzer Always Reports 0 Spanish/Other Tweets

> [!WARNING]
> **Severity: HIGH — The language-region cross-analysis feature is effectively non-functional on real data.**

**File**: [language_region_cross_analyzer.py](file:///d:/GW_UNIVERSITY/AIS/Social_Listener/Env/Social_Listener_V1/UOG_AIS_SOCIAL_LISTENER/src/phase2_preprocessing/language_region_cross_analyzer.py#L77-L78)

**Evidence** from the Phase 2 v2 execution manifest:
```json
"us_spanish_tweets": 0,
"us_other_language_tweets": 0,
"unmapped_tweets": 915190
```

**What's wrong:**
- The analyzer defaults `language_col = "detected_language"`, but the actual cleaned dataframe has **no column** named `detected_language` (confirmed: `detected_language exists: False`).
- When the column is missing, line 78 falls back to: `working["_lang_cat"] = "English"` — so **every tweet is assumed English**.
- The `state_code` column exists but 68.7% of values are empty strings (`''`), not `NaN`. Line 51 checks `pd.isna(state_val) or not str(state_val).strip()` — empty strings correctly map to `"Unmapped"`, so the 915,190 unmapped count is actually correct, but the language cross-tab is completely blind.

**Impact**: The entire Package D "Language vs Region" analysis produces a vacuous 100% English result. The stated project requirement to "retain Spanish-speaking US residents" is untestable because language detection was never run.

**Recommendation**: 
1. Add a language detection step (e.g., `langdetect` or `fasttext`) in Phase 2 before running the cross-analyzer, or
2. Explicitly document that language detection is unavailable and remove the misleading cross-tab from reports.

---

### CRIT-4: Exact Dedup on Raw `tweet` Text While `tweet_cleaned` Is the Downstream Column

> [!IMPORTANT]
> **Severity: MEDIUM — Dedup and cleaning ordering creates a logical inconsistency.**

**File**: [run_phase2_v2.py](file:///d:/GW_UNIVERSITY/AIS/Social_Listener/Env/Social_Listener_V1/UOG_AIS_SOCIAL_LISTENER/verify/phase2/run_phase2_v2.py#L77-L88)

```python
# Dedup on raw tweet text (before cleaning)
after_activity_df["_clean_text_temp"] = after_activity_df["tweet"].fillna("").astype(str).str.strip()
after_dedup_df = after_activity_df.drop_duplicates(subset=["_clean_text_temp"], keep="first").copy()

# Then clean text (after dedup)
cleaner = TextCleaner()
after_dedup_df["tweet_cleaned"] = after_dedup_df["tweet"].apply(cleaner.clean)
```

**What's wrong:**
- Dedup runs on the **raw** `tweet` column (with URLs, HTML entities, etc.).
- Two tweets that differ only by URL (e.g., `"Vote Biden https://t.co/abc"` vs `"Vote Biden https://t.co/xyz"`) survive dedup as distinct.
- But after `TextCleaner.clean()` strips URLs, they would produce **identical** `tweet_cleaned` values.
- This means the dataset may retain near-duplicates that only differ by URL, and VADER/RoBERTa would score them identically — artificially inflating that tweet's weight.

**Recommendation**: Dedup on `tweet_cleaned` (after cleaning), not on raw `tweet`. Or run a second dedup pass on `tweet_cleaned`.

---

### CRIT-5: Phase 4 Spatial Aggregation `state_code` Matching Fails for Empty-String Values

> [!IMPORTANT]
> **Severity: MEDIUM — Silent data loss in state aggregation.**

**File**: [temporal_spatial_aggregator.py](file:///d:/GW_UNIVERSITY/AIS/Social_Listener/Env/Social_Listener_V1/UOG_AIS_SOCIAL_LISTENER/src/phase4_aggregation/temporal_spatial_aggregator.py#L156-L157)

```python
df["_state_clean"] = df[self.location_col].astype(str).str.strip().str.upper()
us_df = df[df["_state_clean"].isin(self.US_STATE_CODES)].copy()
```

**Actual data**: `state_code` column has values like `'FL'`, `''`, `'CA'`, `''` (empty strings, **not** NaN).

**What's wrong:**
- `''.strip().upper()` → `''`, which is not in `US_STATE_CODES`, so empty values are correctly excluded.  
- However, there may be values like `'nan'` (string literal) from `astype(str)` on NaN values. `'NAN'.upper()` → `'NAN'`, which is also not in the set. **This is actually handled correctly.**
- The real concern: only **273,362 of 1,331,345 tweets (20.5%)** have a valid US state code. The spatial matrix ($X_i$) is computed from only ~20% of the dataset. This is a severe representativeness limitation that should be explicitly reported.

**Impact**: State-level sentiment margins are computed from a heavily biased 20% subsample with no representativeness correction. The H2 OLS results may be unreliable.

---

## Wrong Implementations

### WRONG-1: `GeminiSarcasmAnnotator` is Never Actually Used for Annotation

**File**: [run_phase3_v2.py L93-96](file:///d:/GW_UNIVERSITY/AIS/Social_Listener/Env/Social_Listener_V1/UOG_AIS_SOCIAL_LISTENER/verify/phase3/run_phase3_v2.py#L93-L96)

```python
annotator = GeminiSarcasmAnnotator()
seed_prompt = annotator.build_prompt(["Tweet 1 test text", "Tweet 2 test text"])
gemini_validated = len(seed_prompt) > 0
```

**What's wrong**: The annotator only builds a prompt string and checks it's non-empty. It never calls the Gemini API and never produces silver annotations. The manifest reports `gemini_annotation_pipeline_ready: true`, but this only validates prompt construction, not actual annotation capability. No API key is provided, no LLM is called.

---

### WRONG-2: Phase 5 H2 Battleground OLS Silently Falls Back to National When N < 5

**File**: [itsa_ols_evaluator.py L179-182](file:///d:/GW_UNIVERSITY/AIS/Social_Listener/Env/Social_Listener_V1/UOG_AIS_SOCIAL_LISTENER/src/phase5_modeling/itsa_ols_evaluator.py#L179-L182)

```python
if len(battleground_df) >= 5:
    battleground_ols = self.evaluate_h2_ols(battleground_df, "Battleground_States", ...)
else:
    battleground_ols = national_ols  # Silently reuses national result
```

**What's wrong**: If the battleground subgroup has fewer than 5 observations (which **can** happen if tweet coverage is sparse for swing states), the code silently assigns the **National** OLS result as the "Battleground" result, without any warning. A downstream consumer would believe a separate Battleground regression was run.

**Recommendation**: Raise an explicit warning or return a clearly labeled "insufficient data" result.

---

### WRONG-3: Phase 2 v2 Manifest Reports `"tweets_removed_text_cleaning": 0` — Cleaning Filter Uses Wrong Logic

**File**: [run_phase2_v2.py L85](file:///d:/GW_UNIVERSITY/AIS/Social_Listener/Env/Social_Listener_V1/UOG_AIS_SOCIAL_LISTENER/verify/phase2/run_phase2_v2.py#L85)

```python
final_df = after_dedup_df[after_dedup_df["tweet_cleaned"].fillna("").astype(str).str.len() > 0].copy()
```

**What's wrong**: `TextCleaner.clean()` returns `None` for null/NaN input or empty-after-cleaning text. The `.fillna("").astype(str)` converts `None` to empty string, then filters on `str.len() > 0`. This is technically correct, but the manifest shows 0 tweets removed — meaning `TextCleaner.clean()` never returns `None` for any record that survived dedup. This suggests the cleaning step is a no-op (every record already has text content after dedup). The cleaning stage exists but contributes zero filtering, raising the question of whether the text cleaning is adequately aggressive (e.g., tweets that are only emojis, only mentions, only hashtags should arguably be flagged).

---

## Unused / Dead Code

### UNUSED-1: `matplotlib.pyplot` and `seaborn` Imported But Never Used

| File | Unused Imports |
|---|---|
| [run_phase2_v2.py](file:///d:/GW_UNIVERSITY/AIS/Social_Listener/Env/Social_Listener_V1/UOG_AIS_SOCIAL_LISTENER/verify/phase2/run_phase2_v2.py#L15-L20) | `matplotlib`, `matplotlib.pyplot as plt`, `seaborn as sns` |
| [run_phase3_v2.py](file:///d:/GW_UNIVERSITY/AIS/Social_Listener/Env/Social_Listener_V1/UOG_AIS_SOCIAL_LISTENER/verify/phase3/run_phase3_v2.py#L17-L23) | `matplotlib`, `matplotlib.pyplot as plt`, `seaborn as sns` |

These runners import plotting libraries but generate no plots.

---

### UNUSED-2: Missing `__init__.py` in Phase 4 and Phase 5 Packages

| Package | Status |
|---|---|
| `src/phase4_aggregation/` | No `__init__.py` |
| `src/phase5_modeling/` | No `__init__.py` |

This works because runners use `sys.path` insertion, but it means Phase 4 and Phase 5 are not proper Python packages. Any `from src.phase4_aggregation import ...` in package-level code would fail without the sys.path hack.

---

### UNUSED-3: `GeminiSarcasmAnnotator.parse_llm_response()` Is Never Called

**File**: [gemini_sarcasm_annotation.py L209-232](file:///d:/GW_UNIVERSITY/AIS/Social_Listener/Env/Social_Listener_V1/UOG_AIS_SOCIAL_LISTENER/src/phase3_sentiment/gemini_sarcasm_annotation.py#L209-L232)

The `parse_llm_response()` method exists but is never called anywhere — neither in the Phase 3 v2 runner, nor in any test file. The entire Gemini annotation pipeline is a dead stub.

---

### UNUSED-4: Phase 2 v2 Runner Does Not Use `PreprocessingRunnerController`

**File**: [preprocessing_runner_controller.py](file:///d:/GW_UNIVERSITY/AIS/Social_Listener/Env/Social_Listener_V1/UOG_AIS_SOCIAL_LISTENER/src/phase2_preprocessing/preprocessing_runner_controller.py)

The existing Phase 2 production controller `PreprocessingRunnerController` is bypassed entirely by `run_phase2_v2.py`, which reimplements the pipeline inline. This creates two parallel Phase 2 codepaths — the v1 controller and the v2 inline runner — with no shared logic.

---

## Prioritized Remediation Plan

| Priority | Issue | Fix Description | Effort |
|---|---|---|---|
| 🔴 P0 | CRIT-1 | Replace simulated RoBERTa/sarcasm scores with real model inference or honest VADER-only labeling | High |
| 🔴 P0 | CRIT-2 | Read `electoral_returns_v2.parquet` (Phase 1 v2 output) instead of raw CSV in Phase 4 runner | Low |
| 🟠 P1 | CRIT-3 | Add language detection step or document language analysis as unavailable | Medium |
| 🟠 P1 | CRIT-4 | Move dedup to after text cleaning (dedup on `tweet_cleaned`, not raw `tweet`) | Low |
| 🟡 P2 | CRIT-5 | Document 20.5% state coverage limitation explicitly in Phase 4 reports | Low |
| 🟡 P2 | WRONG-1 | Remove Gemini "validated" claim from manifest or implement real API call | Low |
| 🟡 P2 | WRONG-2 | Add explicit warning/label when Battleground OLS falls back to National | Low |
| ⚪ P3 | UNUSED-1-4 | Clean up unused imports, add `__init__.py`, remove dead code | Low |

> [!IMPORTANT]
> **CRIT-1 is the most impactful issue.** Every Phase 4 and Phase 5 result currently depends on fabricated sentiment scores. This must be resolved before any statistical conclusions are drawn.
