# Remediation Documentation Set

Instructions for an implementing agent to repair the reliability defects found in the Social Listener pipeline, plus the contract the auditing agent will verify against.

**Start here → [00_AGENT_BRIEF.md](00_AGENT_BRIEF.md)**, then read [VERIFICATION_CONTRACT.md](VERIFICATION_CONTRACT.md) before writing any code.

| Doc | Scope | Depends on |
|---|---|---|
| [00_AGENT_BRIEF.md](00_AGENT_BRIEF.md) | Rules R1–R7, environment, ground-truth figures | — |
| [WP0_environment.md](WP0_environment.md) | VADER provenance, CUDA torch, language ID install | — |
| [WP1_phase2_rebuild.md](WP1_phase2_rebuild.md) | Dual-hashtag rule, dedup key, language survey, geo recovery | WP0 |
| [WP2_phase3_roberta.md](WP2_phase3_roberta.md) | Real GPU Twitter-RoBERTa over the full corpus | WP0, WP1 |
| [WP3_phase3_sarcasm_gemini.md](WP3_phase3_sarcasm_gemini.md) | Irony model, 15 human seeds, Gemini silver, fine-tune | WP2 |
| [WP4_phase45_rerun.md](WP4_phase45_rerun.md) | Aggregation + ITSA/OLS on corrected inputs | WP2 |
| [WP5_notebook_corrections.md](WP5_notebook_corrections.md) | Rebuild the overview notebook against v3 | WP1, WP2, WP4 |
| [WP6_verification_findings_patch.md](WP6_verification_findings_patch.md) | Fix 3 defects found by independent post-WP5 audit | WP0–WP5 |
| [VERIFICATION_CONTRACT.md](VERIFICATION_CONTRACT.md) | Exactly what gets checked, and how | — |
| [AGENT_EXECUTION_LOG.md](AGENT_EXECUTION_LOG.md) | Implementing agent writes its report here | — |

## Post-WP5 audit result (2026-08-01)

WP0–WP5 were executed and independently verified by the auditing agent — including reloading both fine-tuned models in `.venv` and re-scoring 200 random rows from scratch, which matched stored values within 1e-3. **No fabrication found**; this is a real, working implementation. Three integration defects were found on top of it and are fixed in [WP6](WP6_verification_findings_patch.md): a wrong number in the WP4 log's self-check (data itself is fine), missing hourly/daily temporal matrix persistence in Phase 4, and two notebook cells that silently render nothing due to wrong file paths/key names (one of which is the N6 language chart — the direct answer to original finding #2).

## The seven findings these documents address

| # | Finding | Verdict | Where |
|---|---|---|---|
| 1 | Biden overtakes Trump in post-election tweet volume | **Genuine event signal** — race called Nov 7; needs annotation, not a fix | WP5 §N2 |
| 2 | Spanish chosen as target language without justification | **Confirmed defect** — detector cannot emit "Other"; also flags French as Spanish | WP1 §T1.4, WP5 §N6 |
| 3a | Dedup correctness | **Defect found** — 68% of removals were distinct users posting identical short text | WP1 §T1.3 |
| 3b | *(not in the original list)* Cross-stream assignment | **Severe defect** — 176,260 of 176,302 dual-hashtag tweets handed to Trump by row order | WP1 §T1.1 |
| 3c | User-volume chart contradicts the 12% funnel figure | **Notebook bug** — threshold plotted against the post-filter, sub-sampled population | WP5 §N1 |
| 4 | 20% US-mapped vs 68% unmapped; "0% other language" | **Partly structural** — US ceiling is 22.57%, ~62k rows recoverable; the 0% is a tautology | WP1 §T1.4–T1.5, WP5 §N6–N7 |
| 5 | ±0.05 sentiment threshold unjustified | **Standard is correct** (Hutto & Gilbert 2014) and empirically near-immaterial here — 37.33% of tweets score exactly 0.0 | WP5 §N4 |
| 6 | RoBERTa not running; VADER as sole source | **Confirmed, and the stated reason was false** — weights cached, GPU present, deferral claim unfounded | WP2, WP3 |

Ground-truth measurements backing every verdict above are in [00_AGENT_BRIEF.md](00_AGENT_BRIEF.md) §4.
