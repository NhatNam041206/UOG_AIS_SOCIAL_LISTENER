# Implementation Plan: Refined Baseline Architecture & Sarcasm Enrichment Pipeline

This document updates the project technical roadmap based on your refined requirements:
1. Investigation of the Twitter date window boundary.
2. Multivariable activity factor analysis for preprocessing.
3. Primary Twitter-RoBERTa sentiment engine & pretrained irony/sarcasm classifier integration.
4. Plain-language architectural breakdown of Phase 4 and Phase 5.
5. Human seed (15 tweets) + Gemini API LLM-assisted annotation pipeline for RoBERTa fine-tuning.

---

## 1. Executive Summary & Clarifications

### Date Window Clarification (Investigation Result)
* **Raw Source Download (`data/01_raw/twitter/`)**: The downloaded raw Kaggle files (`hashtag_donaldtrump.csv` and `hashtag_joebiden.csv`) contain **1,747,542 raw rows**.
* **Timestamp Range in Raw Data**:
  * Earliest timestamp: `2020-10-15 00:00:01 UTC`
  * Latest timestamp: `2020-11-08 23:59:58 UTC`
* **Preprocessing Impact (`data/02_interim/twitter_cleaned.parquet`)**:
  * Input raw rows: 1,747,542 (spanning Oct 15 – Nov 8).
  * High-volume user filtering (>9.0 tweets/day): $-222,366$ rows (12.72%).
  * Exact duplicate removal: $-193,831$ rows (11.09%).
  * Text cleaning (invalid text): $-28$ rows (0.0016%).
  * Cleaned output rows: **1,331,317 rows (76.18% retention)**.
* **Finding**: Preprocessing **did not wipe out entire weeks or months**. All 25 calendar days (Oct 15 to Nov 8) remain densely populated. The absence of Oct 8–14 and Nov 9–15 is strictly a Kaggle source collection boundary (Kaggle Version 19 ended on Nov 8).

### 1.5 Codebase Alignment Check & Gap Analysis
Before modifying or running code, an evaluation of existing `src/` implementations against the project's research flow revealed the following alignment states:

| Pipeline Phase | Current Implementation | Alignment Score | Primary Gaps & Action Required |
| --- | --- | ---: | --- |
| **Phase 1: Ingestion** | `stream_readers_model.py`, `ingestion_runner_controller.py` | **85%** | **Gap**: `electoral_returns.csv` has 2020 vote returns but lacks historical 2012/2016 battleground labels and state demographic controls ($Z_{ki}$). Action: Enrich Stream C schema. |
| **Phase 2: Preprocessing** | `user_activity_audit_model.py`, `cleaning_heuristics_model.py` | **70%** | **Gap**: Activity audit uses single velocity metric; lacks active span ($\text{last\_tweet} - \text{first\_tweet}$) and account creation age (`user_join_date`). Lacks Region vs. Language cross-tabulation. Action: Refine auditor and add region-language analyzer. |
| **Phase 3: Sentiment & Sarcasm** | `sentiment_models_model.py`, `sentiment_runner_controller.py` | **60%** | **Gap**: RoBERTa used only on 5,000 validation sample; lacks pretrained sarcasm classifier (`cardiffnlp/twitter-roberta-base-irony`) and LLM silver annotation script. Action: Re-orient RoBERTa as primary engine and add sarcasm profiling. |
| **Phase 4: Aggregation** | `src/phase4_aggregation/` (Empty) | **0%** | **Gap**: No code exists for temporal hourly/daily matrix ($N_t, \mu_t, \sigma_t$) or spatial candidate sentiment margin matrix ($X_i$). Action: Implement `temporal_spatial_aggregator.py`. |
| **Phase 5: Modeling** | `src/phase5_modeling/` (Empty) | **0%** | **Gap**: No code exists for Interrupted Time Series Analysis (ITSA) for H1 or OLS Spatial Regression with demographic controls ($Z_{ki}$) for H2. Action: Implement `itsa_ols_evaluator.py`. |


---

## 2. Refined Work Packages

### Package A: Preprocessing & Activity Factor Analysis
* Expand user activity metrics beyond posting velocity ($\text{tweets} / \text{active days}$) to include:
  * **Active Time Span** ($\text{last\_tweet\_time} - \text{first\_tweet\_time}$).
  * **Account Age at Election** (`user_join_date`, available in raw Kaggle columns).
  * **Follower Ratio & Posting Velocity during Campaign**.
* Evaluate threshold sensitivity across Unfiltered, P99.5 ($9.0$ tweets/day), P99 ($6.0$ tweets/day), and original PDF ($50.0$ tweets/day).

### Package B: Primary Deep Learning (RoBERTa) & Sarcasm Profiling Engine
* **Primary Sentiment Model**: Load `cardiffnlp/twitter-roberta-base-sentiment-latest` as the primary sentiment engine for scoring tweets.
* **Pretrained Sarcasm Classifier**: Load `cardiffnlp/twitter-roberta-base-irony` to score all tweets for continuous **Sarcasm/Irony Risk** $[0, 1]$.
* **Secondary VADER Role**: Retain VADER compound scores as a baseline comparison benchmark.

### Package C: Gemini API Semi-Supervised Sarcasm Annotation & Fine-Tuning Pipeline
1. **Human Seed Set**: Select and manually annotate 15 representative tweets for target candidate, stance, sentiment, and sarcasm.
2. **Gemini API LLM Expansion**:
   * Build a Python script using the Gemini API to perform few-shot annotation on a 1,000–2,000 tweet sample.
   * Generate a silver-standard dataset with target stance, expressed sentiment, intended sentiment, and sarcasm label.
3. **RoBERTa Fine-Tuning**: Fine-tune Twitter-RoBERTa on this LLM-expanded dataset and evaluate accuracy gains over off-the-shelf baselines.

### Package D: Region vs. Tweet Language Comparative Analysis
* **Avoid Language-Based Exclusion**: Do not automatically filter out non-English tweets (e.g. Spanish tweets), as many US voters/residents in states like Texas, Florida, California, and Arizona post in Spanish.
* **Cross-Tabulation Matrix**: Build a 2D matrix comparing **Geocoded User Region** (US State, Non-US, Unmapped) vs. **Detected Language** (English, Spanish, Other).
* **State Sentiment Inclusion**: Non-English tweets mapped to US states are retained for state-level candidate sentiment margins ($X_i$) and national temporal timelines ($H1$).
* **Demographic Sensitivity**: Evaluate whether multilingual sentiment distributions correlate with state Latino/Hispanic demographic percentages in Phase 5 regression models.


---

## 3. Simplified Explanation of Phase 4 and Phase 5

```
+-----------------------------------------------------------------------------+
|                                RAW TWEETS                                   |
|                  (1.33 Million Tweets: Oct 15 - Nov 8, 2020)                |
+------------------------------------+----------------------------------------+
                                     |
                                     v
+-----------------------------------------------------------------------------+
|               PHASE 4: SPATIAL-TEMPORAL MATRIX AGGREGATION                  |
|                        (Building the Data Grids)                            |
+------------------------------------+----------------------------------------+
                  |                                    |
                  v                                    v
   [ TEMPORAL MATRIX (For H1) ]          [ SPATIAL MATRIX (For H2) ]
   - Groups tweets by Hour/Day           - Maps users to US States (PA, TX, CA)
   - Measures Hourly Mean Sentiment       - Calculates State Sentiment Margin:
     & Polarization (Std Dev)               Xi = Mean(Biden) - Mean(Trump)
                                     |
                                     v
+-----------------------------------------------------------------------------+
|                   PHASE 5: ADVANCED STATISTICAL MODELING                    |
|                        (Testing Real-World Impacts)                         |
+------------------------------------+----------------------------------------+
                  |                                    |
                  v                                    v
   [ H1: ITSA SEGMENTED REGRESSION ]     [ H2: STATE OLS SPATIAL REGRESSION ]
   - Did debates/shocks cause sudden     - Do state online sentiment margins
     sentiment jumps (beta_2)?             correlate with actual vote margins (Yi)?
   - How fast did sentiment decay        - Is the correlation stronger in
     back to baseline (beta_3)?            Battleground (Swing) vs Safe states?
```

### Phase 4 (Spatial-Temporal Aggregation): Building the Master Data Grids
* **Analogy**: Organizing 1.33 million loose tweets into two clear spreadsheets:
  1. **Temporal Matrix (Time Grid)**: Collects tweets for each hour and day. On October 22 at 9:00 PM (Debate time), it calculates the average sentiment ($+0.15$ vs $-0.30$) and opinion polarization (variance).
  2. **Spatial Matrix (State Grid)**: Groups tweets by US state and calculates the **Candidate Sentiment Margin**:
     $$X_i = \text{Mean Sentiment}_{\text{Biden}, i} - \text{Mean Sentiment}_{\text{Trump}, i}$$
     *Example*: In Pennsylvania (PA), if Biden sentiment is $+0.25$ and Trump is $+0.10$, PA Sentiment Margin is $+0.15$.

### Phase 5 (Statistical Evaluation): Testing Real-World Hypotheses
* **H1: Interrupted Time Series Analysis (ITSA)**:
  * Tests if key political events (e.g., debates) cause an immediate sentiment "jump" ($\beta_2$) and measures how many hours it takes to return to baseline (decay slope $\beta_3$).
* **H2: Ordinary Least Squares (OLS) Spatial Regression**:
  * Tests whether state Twitter sentiment margins ($X_i$) predict actual Election Day voting margins ($Y_i$), controlling for state median age, income, and urbanization ($Z_{ki}$).
  * Compares predictive accuracy in **Battleground Swing States** (PA, MI, WI) vs **Safe States** (CA, WY).

---

## 4. Proposed Changes to Codebase

### Component 1: Source & Preprocessing Diagnostics (`src/phase2_preprocessing`)
#### [MODIFY] [user_activity_auditor.py](file:///d:/GW_UNIVERSITY/AIS/Social_Listener/Env/Social_Listener_V1/UOG_AIS_SOCIAL_LISTENER/src/phase2_preprocessing/user_activity_auditor.py)
* Add active time span ($\text{last\_tweet} - \text{first\_tweet}$) and account creation age (`user_join_date`) to user diagnostic features.

#### [NEW] [language_region_cross_analyzer.py](file:///d:/GW_UNIVERSITY/AIS/Social_Listener/Env/Social_Listener_V1/UOG_AIS_SOCIAL_LISTENER/src/phase2_preprocessing/language_region_cross_analyzer.py)
* Implement language detection cross-tabulated with user state/region. Retain US-geocoded Spanish/non-English tweets for state aggregation.


### Component 2: Primary Sentiment & Sarcasm Engine (`src/phase3_sentiment`)
#### [MODIFY] [roberta_sentiment_engine.py](file:///d:/GW_UNIVERSITY/AIS/Social_Listener/Env/Social_Listener_V1/UOG_AIS_SOCIAL_LISTENER/src/phase3_sentiment/roberta_sentiment_engine.py)
* Integrate primary Twitter-RoBERTa sentiment model and `cardiffnlp/twitter-roberta-base-irony` pretrained sarcasm classifier.

#### [NEW] [gemini_sarcasm_annotation.py](file:///d:/GW_UNIVERSITY/AIS/Social_Listener/Env/Social_Listener_V1/UOG_AIS_SOCIAL_LISTENER/src/phase3_sentiment/gemini_sarcasm_annotation.py)
* Implement few-shot Gemini API script for LLM-assisted silver-standard sarcasm/stance annotation using 15 human seed examples.

### Component 3: Matrix Aggregation & Modeling (`src/phase4_aggregation`, `src/phase5_modeling`)
#### [NEW] [temporal_spatial_aggregator.py](file:///d:/GW_UNIVERSITY/AIS/Social_Listener/Env/Social_Listener_V1/UOG_AIS_SOCIAL_LISTENER/src/phase4_aggregation/temporal_spatial_aggregator.py)
* Implement temporal hourly/daily aggregation and state-level candidate sentiment margin calculations ($X_i$).

#### [NEW] [itsa_ols_evaluator.py](file:///d:/GW_UNIVERSITY/AIS/Social_Listener/Env/Social_Listener_V1/UOG_AIS_SOCIAL_LISTENER/src/phase5_modeling/itsa_ols_evaluator.py)
* Implement ITSA segmented regression for H1 and OLS spatial regression for H2.

---

## 5. Verification Plan

### Automated Tests
* Unit tests for multivariable user activity calculation (active span, account age).
* Integration test for pretrained RoBERTa sentiment and irony classifier outputs.
* Test for Phase 4 temporal matrix dimensions and spatial state margin calculations.
* Test for Phase 5 ITSA and OLS regression coefficient outputs.

### Manual Verification
* Inspect generated sarcasm distribution plots (`output/graphs/phase3/sarcasm_rate_distribution.png`).
* Reconcile Gemini API silver-standard label agreement against 15 human seed tweets.
* Verify Phase 4 state location mapping against FEC 2020 certified election returns.
