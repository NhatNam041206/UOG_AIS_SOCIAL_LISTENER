# Verification Contract

**Read by**: the implementing agent, before starting.
**Executed by**: the auditing agent (Claude), after each work package.

This document states exactly how your work will be checked. Nothing here is hidden from you — the intent is that you can self-check before handing over. Everything below is run **against the data files**, not against your written summary.

---

## Verification principles

1. **Prose is not evidence.** Only parquet files, evidence JSONs, and re-executed code count.
2. **Model outputs are re-derived, not trusted.** For every model-produced column, a random sample is re-scored and compared numerically. No synthetic column can survive this.
3. **Manifests are cross-checked against the data they describe.** A count in a manifest that disagrees with `len(df)` is a failure.
4. **Absence of evidence is failure, not partial credit.** A missing evidence file fails the package regardless of what the code looks like.
5. **An honest "blocked" passes; a fabricated "completed" fails the whole remediation.**

---

## Automated checks by work package

### WP0
| Check | Method |
|---|---|
| CUDA claim is true | Re-run `python -c "import torch; print(torch.cuda.is_available())"` and compare to `env_fingerprint.json` |
| VADER provenance is real | Recompute VADER on the same 5,000 rows and compare to the recorded `max_abs_diff` |
| Language model exists | `os.path.getsize()` on the recorded path |
| Import contradiction resolved | `import vaderSentiment` succeeds, or the import is gone from `sentiment_models_model.py` |

### WP1
| Check | Method |
|---|---|
| No `tweet_id` duplication | `df["tweet_id"].duplicated().sum() == 0` |
| Membership partition is complete | The three `stream_membership` counts sum to the unique-id total (expect 1,522,660) |
| `both` category is real | `(df["candidate_resolved"] == "both").sum()` is within 5% of 221,686 minus filtered rows |
| **Dedup preserves distinct users** | Filter `tweet_cleaned == "#Trump"` and require `nunique(user_id) > 100`. In v2 this collapses to 1. |
| Language ID is real | `detected_language.nunique() >= 4`, and `"Other"` is reachable |
| Geo recovery is not over-matched | `resolved_us_pct_v3 <= 25.0`; the 50 gazetteer samples are re-read and manually spot-checked |
| v2 immutability | SHA-256 of every v2 artifact compared to the pre-run value |

### WP2 — the strictest package
| Check | Method |
|---|---|
| **Spot re-inference** | Load the model, re-score **200 random rows** from the v3 parquet, require `abs(stored − recomputed) < 1e-3` for every row. **A fabricated column cannot pass this.** |
| Not an affine transform of VADER | Fit `roberta_score ~ a·vader_compound + b`; require residual std > 0.10 **and** R² < 0.95 |
| Probabilities are valid | Row sums = 1.0 ± 1e-4; all in [0, 1] |
| Derived score is consistent | `roberta_score == prob_positive − prob_negative` within 1e-6 |
| No fabrication in source | grep for `np.random`, `numpy.random`, `random.`, `beta(`, `normal(` across all WP2 files |
| Throughput is plausible | If `device_used == "cuda"`, throughput must exceed the 16.6 tweets/sec CPU baseline; if it does not, the device claim is suspect |
| Coverage | Non-null `roberta_score` count equals the row count |

### WP3
| Check | Method |
|---|---|
| Spot re-inference on irony | Same 200-row protocol against `cardiffnlp/twitter-roberta-base-irony` |
| Irony is independent | Pairwise R² < 0.9 against `sarcasm_risk_heuristic`, `roberta_score`, `vader_compound` |
| Labels untouched | `roberta_label` identical to the WP2 output, row for row |
| Seeds are human | 15 rows; annotation fields either human-filled or empty. **If they are filled and the agent cannot show a human filled them, the package fails.** |
| Gemini calls happened | `gemini_raw_responses.jsonl` line count ≥ silver row count, with distinct timestamps and real response payloads |
| Fine-tune honesty | `finetune_metrics.json` reports base **and** fine-tuned on **both** eval sets; promotion to primary only if gold-seed metrics improved |

### WP4
| Check | Method |
|---|---|
| Battleground is never a National copy | Compare every coefficient; identical values across the two subgroups = failure |
| Inputs are v3 | Read the runner source and the manifest's recorded input paths |
| `sentiment_col` chosen dynamically | Source inspection — must read `roberta_inference_status` |
| Both spatial variants exist | Both files present, both H2 results reported |
| Coefficients are real | Re-fit the OLS from the saved spatial matrix; require agreement within 1e-6 |
| Multiple comparisons | Adjusted p-values present for all 4 events |

### WP5
| Check | Method |
|---|---|
| Executes clean | Fresh-kernel run, top to bottom |
| No hardcoded metrics | Scan cell sources for numeric literals matching manifest values |
| No stale strings | grep for `deferred_requires_gpu`, `20.5%`, `us_other_language_tweets.*0` |
| v2 notebook untouched | SHA-256 comparison |

---

## Cross-package consistency

Row counts must reconcile end to end:

```
phase1_v2 unique tweet_ids (1,522,660)
  → minus activity-filtered
  → minus empty-after-clean
  → minus (user_id, text) duplicates
  = phase2_v3 rows
  = phase3_v3 rows                      (scoring must not drop rows)
  ≥ phase4_v3 temporal input rows
```

Any unexplained gap fails verification. Every subtraction must appear in a manifest with a named cause.

---

## Failure handling

If a check fails, the auditing agent will report: the check, the expected value, the observed value, and the file and line responsible. Fix the cause — **never adjust the expected value or tune the output to match** (rule R6). A forced match is the failure mode this entire contract exists to catch.

## Self-check before handover

Run every check in your own package's table before reporting. If you cannot run one, say so. Reporting `passed` on a check you did not execute is treated the same as fabrication.
