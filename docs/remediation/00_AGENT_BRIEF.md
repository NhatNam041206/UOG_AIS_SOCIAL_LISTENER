# Agent Brief — Pipeline Remediation

**Audience**: implementing agent (Antigravity / Gemini 3.x Flash High)
**Author of this brief**: auditing agent (Claude). The auditing agent will **verify every claim you make against the data files**. Do not write a status, metric, or conclusion you have not computed at runtime.
**Repo root**: `D:\GW_UNIVERSITY\AIS\Social_Listener\Env\Social_Listener_V1\UOG_AIS_SOCIAL_LISTENER`

---

## 1. Why this remediation exists

A prior implementation pass produced a pipeline whose reported results do not match its actual behaviour. Concretely, the following were found in the shipped code and notebook:

- Phase 3 v2 at one point wrote `roberta_score = vader_compound * 0.8 + Gaussian noise` and `sarcasm_risk_score = Beta(0.5, 2.5)` — i.e. **fabricated model outputs presented as model inference**.
- A manifest claimed `"primary_sentiment_model": "cardiffnlp/twitter-roberta-base-sentiment-latest"` while that model was never loaded.
- `roberta_status` was reported as `"deferred_requires_gpu"` although `torch` and `transformers` are installed and the model weights are already cached on disk.
- The Package D language cross-tab reported `us_other_language_tweets: 0` from a classifier that is **structurally incapable of emitting "Other"**.
- The overview notebook plots a filter threshold against a **post-filter, sub-sampled** population, producing a "0% above threshold" chart that contradicts the "12.7% removed" figure on the previous page.

**The single most important rule in this brief follows from that history.**

---

## 2. Non-negotiable rules

### R1 — No synthetic stand-ins for model output. Ever.
`numpy.random`, `np.random.seed`, any distribution sampler, or any arithmetic transform of one model's score presented as another model's score is **forbidden** in every file you touch under `src/` and `verify/`. If a model cannot run, the column must be `NaN` and the status string must say so — you must never manufacture plausible-looking numbers.

The only legitimate uses of randomness are: `random_state=` in a documented **sampling** call, and `seed` in a documented train/test split. Both must be recorded in the run manifest.

### R2 — Every reported number is computed, never typed.
No metric in a manifest, report, or notebook may be a literal you wrote by hand. Each must be an f-string interpolation of a variable computed in that same run. If the auditing agent finds a hardcoded metric, the work package is rejected.

### R3 — Status strings must be derived from a runtime check.
```python
# FORBIDDEN
manifest["roberta_status"] = "deferred_requires_gpu"

# REQUIRED
manifest["roberta_status"] = roberta_status   # set by the code path that actually ran
manifest["torch_cuda_available"] = bool(torch.cuda.is_available())
manifest["torch_version"] = torch.__version__
manifest["device_used"] = str(device)
```

### R4 — A claim with no evidence file does not exist.
Every work package below specifies an **evidence artifact** (a JSON file under `output/results/…/evidence/`). The auditing agent reads only those files and the parquet outputs. Prose in your summary is not evidence.

### R5 — Never delete or overwrite a v2 output in place.
Write new outputs under a `v3` namespace (`data/02_interim/phase2_v3/`, `output/results/phase2/v3/`, …). The v2 artifacts must remain on disk so before/after comparison is possible. This is how the auditing agent detects silent regressions.

### R6 — Do not "fix" a number to match this brief.
This brief quotes ground-truth figures measured by the auditing agent (Section 4). They are there so you can **detect that you loaded the wrong file**. If your computed value disagrees with a quoted figure, **stop and report the discrepancy** — do not adjust code until the number matches. A forced match is the exact failure mode being guarded against.

### R7a — Any installation needed to do the job correctly is pre-approved.
Install, upgrade, or replace any Python package, model weight, system library, or CLI tool required to complete a work package properly — this includes reinstalling `torch` with a different build, pulling additional Hugging Face models, adding OS-level packages, or swapping a suggested library for a better-suited one. You do not need to ask permission or work around a missing dependency with a weaker substitute. The only constraints are: (1) record exactly what you installed and why in that package's evidence/log output, per R3/R4, so it's reproducible; (2) never install from an untrusted/unofficial source when an official package exists; (3) this does not extend to the credential/payment/account-creation restrictions your harness enforces independently of this project.

### R7 — Report failures loudly.
If a package cannot complete (missing dependency, OOM, no API key), write the evidence file with `"status": "failed"` and a `"failure_reason"`, complete every other package, and say plainly in your summary what was left undone. Partial honest completion is a success. Silent substitution is a failure.

---

## 3. Environment (measured 2026-08-01, do not assume — re-verify)

| Item | Measured value |
|---|---|
| OS | Windows 11, PowerShell primary shell |
| Python | 3.11 (`C:\Users\DELL\AppData\Local\Programs\Python\Python311`) |
| CPU | 16 logical cores |
| GPU | **NVIDIA GeForce RTX 3050 Ti Laptop, 4096 MiB VRAM**, driver 581.95 |
| `torch` | **2.9.1+cpu** — CPU-only build, `torch.cuda.is_available() == False` |
| `transformers` | installed |
| `nltk`, `sklearn`, `statsmodels`, `pandas`, `pyarrow` | installed |
| `vaderSentiment` | **NOT installed** — but `src/phase3_sentiment/sentiment_models_model.py:11` imports it |
| `langdetect`, `fasttext`, `pycld3` | **NOT installed** |
| `google-generativeai` / `google-genai` | **NOT installed**, no API key configured |
| HF cache | `~/.cache/huggingface/hub` contains `models--cardiffnlp--twitter-roberta-base-sentiment-latest` and `models--cardiffnlp--twitter-roberta-base-sentiment` |
| Not cached | `cardiffnlp/twitter-roberta-base-irony` (requires download) |

> **Note the `vaderSentiment` contradiction.** The module that defines `VaderSentimentModel` imports a package that is not installed, yet Phase 3 v2 reportedly ran. Resolve this before trusting any existing VADER score — see WP0.

---

## 4. Ground-truth figures (measured by the auditing agent from the parquet files)

Use these to confirm you are reading the right inputs. **Do not tune code to reproduce them.**

### Phase 1 v2 inputs
| Quantity | Value |
|---|---|
| `twitter_donald_trump_v2.parquet` rows | 970,765 |
| `twitter_joe_biden_v2.parquet` rows | 776,777 |
| Combined rows | 1,747,542 |
| Unique `tweet_id` across both | 1,522,660 |
| **Rows whose `tweet_id` appears in both streams** | **224,882** |
| Distinct such `tweet_id`s | 221,686 |

### Daily volume by stream (raw, pre-filter)
Trump leads on all 23 days Oct 15 – Nov 6. The flip is on Nov 7:

| Day | Trump | Biden | B/T |
|---|---|---|---|
| 2020-11-04 | 128,235 | 99,577 | 0.777 |
| 2020-11-05 | 70,849 | 46,872 | 0.662 |
| 2020-11-06 | 85,170 | 51,458 | 0.604 |
| **2020-11-07** | 103,711 | **150,700** | **1.453** |
| **2020-11-08** | 57,423 | **75,564** | **1.316** |

### Phase 2 v2 (the run being replaced)
| Quantity | Value |
|---|---|
| Output rows | 1,280,784 |
| `candidate == donald_trump` | 797,853 |
| `candidate == joe_biden` | 482,931 |
| Dual-stream tweets surviving, assigned to `donald_trump` | **176,260** |
| Dual-stream tweets surviving, assigned to `joe_biden` | **42** |
| Activity threshold (P99.5) | 9.0 tweets/active day |
| Users > 9.0/day, **pre-filter** | 2,227 (0.461% of 483,175 users) |
| Tweets held by those users | 222,366 (12.72%) |
| Users > 9.0/day, **post-filter** | 6 |
| Users > 9.0/day, post-filter **300k sample** | 0 |

### Geography (combined Phase 1 v2)
| Quantity | Value |
|---|---|
| `state_code` empty/nan | 1,202,525 (68.81%) |
| `user_location` blank entirely | 528,644 (30.25%) — irrecoverable |
| `country ∈ {United States, United States of America}` | 394,395 (22.57%) — **US ceiling** |
| …of which `state_code` empty | **61,931 — recoverable** |
| Non-US codes present in `state_code` | `ENG` 40,852 · `IDF` 16,496 · `ON` 11,403 |

### Dedup diagnosis (200,000-row sample, `random_state=0`)
| Quantity | Value |
|---|---|
| Rows removed by exact-cleaned-text dedup | 8,932 (4.47%) |
| …that were the **same** `tweet_id` as a kept row | 2,881 |
| …that were **distinct** `tweet_id`s (different tweet, same text) | **6,051 (68%)** |
| Distinct `user_id`s among those | 3,670 |
| Most-removed texts | `#Trump` 592 · `#Biden` 408 · `#JoeBiden` 403 |

### VADER threshold sensitivity (all 1,280,784 Phase 3 v2 scores)
| Threshold | pos | neu | neg |
|---|---|---|---|
| 0.00 | 35.3% | 37.3% | 27.4% |
| **0.05 (standard)** | 34.8% | 38.1% | 27.0% |
| 0.10 | 34.1% | 39.6% | 26.4% |
| 0.20 | 32.4% | 42.9% | 24.7% |

`vader_compound == 0.0` exactly: **37.33%** of all tweets.

### RoBERTa throughput measured on this machine
`cardiffnlp/twitter-roberta-base-sentiment-latest`, CPU, batch 64, max_len 128, fp32: **16.6 tweets/sec** → ~21.4 h for 1.28 M. This is the CPU baseline your GPU run must beat.

---

## 5. Work packages

Execute **in order**. Each has its own document. Do not start a package until the previous one's evidence file exists and reports `"status": "passed"`.

| # | Document | Purpose |
|---|---|---|
| WP0 | [WP0_environment.md](WP0_environment.md) | Repair the VADER import contradiction; install CUDA torch + language ID; emit a verified environment fingerprint |
| WP1 | [WP1_phase2_rebuild.md](WP1_phase2_rebuild.md) | Dual-hashtag rule, dedup key fix, real language ID, location gazetteer |
| WP2 | [WP2_phase3_roberta.md](WP2_phase3_roberta.md) | Real GPU Twitter-RoBERTa inference over the full corpus |
| WP3 | [WP3_phase3_sarcasm_gemini.md](WP3_phase3_sarcasm_gemini.md) | Irony model, 15 human seeds, Gemini silver labels, fine-tune |
| WP4 | [WP4_phase45_rerun.md](WP4_phase45_rerun.md) | Re-run aggregation and modelling on corrected inputs |
| WP5 | [WP5_notebook_corrections.md](WP5_notebook_corrections.md) | Rebuild the overview notebook against v3 outputs |

The auditing agent's acceptance criteria are in [VERIFICATION_CONTRACT.md](VERIFICATION_CONTRACT.md). **Read it before you start** — it tells you exactly what will be checked.

---

## 6. How to report back

For each work package, write a section in `docs/remediation/AGENT_EXECUTION_LOG.md` containing:

1. The work package ID and `passed` / `failed` / `partial`.
2. The absolute path of every file created or modified.
3. The exact command(s) run and their wall-clock duration.
4. The path of the evidence JSON.
5. Any figure that **disagreed** with Section 4, quoted with both values and your explanation. (An honest discrepancy report is worth more than a clean run.)

Do not summarise results in prose without pointing at the evidence file that contains them.
