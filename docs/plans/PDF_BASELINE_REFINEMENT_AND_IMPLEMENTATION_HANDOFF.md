# PDF Baseline Refinement: Living Discussion and Implementation Handoff

Document owner: project instructor and user  
Created: 2026-07-13  
Last updated: 2026-07-14  
Status: living discussion and implementation-control document  
Reference baseline: `D:\GW_UNIVERSITY\AIS\Social_Listener\SL_2020_ori.pdf`

## 1. Purpose

This is the controlling handoff for refining the Social Listener codebase against
the original PDF research design. It is deliberately both a discussion record and
an implementation plan so that a separate implementation agent can work without
losing the reasoning, constraints, inputs, expected results, or approval state.

All future planning discussions about this refinement should be appended to this
file. Do not silently rewrite earlier decisions. Add a dated discussion entry,
update the decision register, and then update the affected work-package status.

This document does not authorize every proposed action. The decision register is
the authority for distinguishing approved work from pending discussion.

## 2. Mandatory reading order for agents

Before changing methodology, sources, datasets, phases, sentiment, topics,
reliability, or paper claims, read these files in order:

1. `D:\GW_UNIVERSITY\AIS\Social_Listener\knowledge_sources\KNOWLEDGE_SOURCE_INDEX.md`
2. `D:\GW_UNIVERSITY\AIS\Social_Listener\knowledge_sources\social_listener_dataset_source_knowledge_file.md`
3. `D:\GW_UNIVERSITY\AIS\Social_Listener\knowledge_sources\draft_dataset_grounded_sentiment_topic_scope_discussion.md`
4. This document.
5. `docs/PHASE1_DATA_STREAM_ALIGNMENT.md`
6. `docs/plans/ORIGINAL_PDF_ALIGNMENT_PLAN.md`
7. `docs/PROJECT_JOURNAL.md`
8. The source, tests, manifests, and reports for the phase being changed.

If the files disagree, prefer verified live data and newer dataset-grounded notes.

## 3. Non-negotiable research guardrails

- The currently verified raw Twitter window is `2020-10-15` through
  `2020-11-08`. The approved target for Phase 1 v2 is extension through
  `2020-11-15`, but the target dates must not be described as observed until a
  compatible source is acquired, validated, and ingested.
- The Twitter data is candidate-hashtag-centered, not a Twitter firehose or a
  population-representative public-opinion sample.
- Donald Trump's positive COVID-19 test was announced on October 2, 2020, not
  October 22. October 22 was the final presidential debate. The debate may be
  modeled as an in-window debate event and may be tagged as containing COVID-19
  policy discussion, but it must not be relabeled as Trump's diagnosis.
- High posting frequency is a representativeness or suspicious-activity indicator,
  not proof of a bot.
- Hashtag-stream membership is not the same as support, opposition, or stance.
- VADER/RoBERTa correlation and label agreement are model-comparison evidence, not
  accuracy, precision, or human ground truth.
- Missing location can make a record unavailable for state analysis without making
  it invalid for national temporal analysis.
- Phases 1, 2, 3, 4, and 5 constitute the MVP. Phase 2.5 is a post-MVP refinement.
  Existing Phase 2.5 evidence must be preserved but must not block implementation
  of the MVP. Phase 2.5 remains examination-first and must not filter, weight,
  reverse sentiment, route models, or fine-tune models without separate approval.
- Phase 5 must use restrained association and event-aligned language. It must not
  claim that Twitter sentiment caused votes or represents all voters.
- Existing generated artifacts are versioned evidence. A rerun must not silently
  erase the provenance of the v1 results.

## 4. Conversation-derived problem statement

The original PDF defines a five-phase baseline:

1. multi-source ingestion using social media, political events, and electoral
   benchmarks;
2. preprocessing, high-volume/spam-oriented filtering, duplicate handling, and
   VADER-safe normalization;
3. full-data VADER scoring with a 5,000-record Twitter-RoBERTa comparison;
4. temporal and state-level aggregation;
5. interrupted time-series analysis for H1 and state-level OLS for H2.

The live codebase has operational Phase 1, Phase 2, and Phase 3 v1 artifacts, an
examination-only Phase 2.5 package with sample and full v1 run artifacts, and no
production Phase 4 or Phase 5. Earlier work identified the PDF mismatches, but did
not fully specify the mitigations, implementation order, inputs, methods, outputs,
or completion gates.

The user has now directed that the implementation begin by rerunning a refined
Phase 1 so downstream work receives the most complete dataset that can be built
from the available inputs. In this document, "complete" means complete ingestion
of available and approved Stream A/B/C fields with auditable provenance. It does
not mean that a rerun can manufacture Twitter observations outside the source's
verified date range. The user has separately directed the project to acquire and
validate compatible Twitter coverage through November 15 before freezing Phase 1
v2.

## 5. Current progress baseline

| Phase | Current evidence | Refinement status | Consequence |
| --- | --- | --- | --- |
| Phase 1 | v1 executed on all three stream families; 1,747,542 valid Twitter rows | PDF alignment open | Phase 1 v2 rerun is the approved critical path |
| Phase 2 | v1 closed; 1,331,317 cleaned rows; approved empirical threshold 9 tweets/active day | Upstream-dependent | Retain as historical v1 evidence; regenerate after Phase 1 v2 |
| Phase 2.5 | Production package plus v1 sample and full-run artifacts exist; full manifest records 1,331,317 rows and no mitigation | Deferred refinement | Preserve as v1 evidence; do not place Phase 2.5 on the MVP critical path |
| Phase 3 | v1 closed; full VADER and 5,000-row RoBERTa comparison | Upstream-dependent | Retain as historical v1 evidence; regenerate after Phase 2 v2 |
| Phase 4 | No production implementation | Not started | Define contract only after upstream schemas are stable |
| Phase 5 | No production implementation | Not started | No H1 or H2 findings currently exist |

Controlling current Phase 3 v1 metrics are Pearson `r = 0.4708`, label agreement
`59.66%`, and likely-English sample share `68.72%`. These are agreement and
suitability diagnostics, not sentiment accuracy.

## 6. Decision register

Allowed values: `approved`, `pending discussion`, `rejected`, `superseded`.

| Decision ID | Decision | Recommendation | Status | Consequence |
| --- | --- | --- | --- | --- |
| D1 | Target time window | Preserve verified `2020-10-15` to `2020-11-08` as current evidence and acquire compatible coverage through `2020-11-15` before Phase 1 v2 | **Approved, acquisition pending** | Phase 1 v2 is blocked until extension compatibility is resolved |
| D2 | Phase 1 v2 rerun | Re-ingest Streams A/B/C with revised schemas before downstream implementation | **Approved** | Phase 1 v2 is the first implementation work package |
| D3 | Stream A retained fields | Retain all useful available account, engagement, geographic, collection, source, and lineage fields | Pending schema inspection | Determines Phase 2, 2.5, 3, and 4 inputs |
| D4 | Stream B event protocol | Use sourced UTC events with explicit eligibility, window, overlap, and boundary rules | Pending discussion | Determines H1 events and Phase 4 event matrices |
| D5 | Historical state classification | Use continuous 2012/2016 competitiveness plus a pre-registered binary battleground/safe rule | Pending discussion | Prevents leakage from using 2020 outcomes to define subgroups |
| D6 | State controls | Add a small, pre-election, source-traceable set covering age, income, and urbanization | Pending source and vintage decision | Determines H2 control vector |
| D7 | Phase 2 activity variants | Preserve empirical 9/day primary variant; add original-PDF 50/day and unfiltered sensitivity variants | Pending discussion | Allows original-spec comparison without calling it bot detection |
| D8 | Phase 2.5 placement | Treat Phases 1-5 as the MVP and move Phase 2.5 examination/refinement after MVP completion | **Approved** | Phase 2.5 cannot block Phases 4 or 5 |
| D9 | Phase 4 primary grain | Daily primary summaries plus hourly event-window summaries where coverage permits | Pending discussion | Determines H1 design and output volume |
| D10 | H1/H2 interpretation | Event-aligned association for H1 and state-level association for H2; no causal or representative-public-opinion claims | Pending explicit acceptance | Controls paper language and completion gates |
| D11 | Trump COVID/date handling | Keep October 2 as the diagnosis date; use October 22 only as the final debate, optionally tagged for COVID-policy discussion | **Instructor correction** | Prevents a historically incorrect event label |
| D12 | Phase 3 transformer coverage | Keep full-data VADER plus the reproducible 5,000-row RoBERTa comparison for the MVP; treat full-data RoBERTa as an optional post-MVP refinement | Pending explicit acceptance | Determines whether transformer inference expands beyond the PDF baseline |
| D13 | Primary novelty direction | Evaluate a target-aware, sarcasm-conditioned political sentiment/stance method against VADER and off-the-shelf Cardiff RoBERTa | Pending discussion | Would define the main post-MVP methodological contribution |
| D14 | In-domain annotation | Create a project-specific, multiply annotated set covering sentiment, target stance, sarcasm, ambiguity, and confidence | Pending scope and budget | Required for accuracy, fine-tuning, and defensible sarcasm claims |
| D15 | Sarcasm integration method | Compare post-hoc diagnostics, learned fusion, multi-task learning, and selective abstention; do not automatically flip sentiment | Pending experimental design | Determines whether sarcasm evidence improves rather than distorts sentiment |
| D16 | External benchmark role | Use TweetEval, iSarcasmEval, and P-Stance for auxiliary training/benchmarking, but require a held-out project test set for the paper's main claim | Pending dataset/license audit | Prevents cross-domain benchmark gains from being misreported as political-tweet reliability |
| D17 | Novelty timing | Complete the Phase 1-5 MVP as the reproducible baseline, then execute the novelty track before final paper submission | Pending explicit acceptance | Preserves the original PDF while allowing a publishable extension |

An implementation agent must not resolve a pending methodological decision by
guessing. It may inspect data, enumerate feasible options, or create a non-mutating
prototype, then return the evidence for instructor/user approval.

## 7. Mismatch-to-mitigation register

| PDF requirement | Current mismatch | Planned mitigation | Expected result | Decision dependency |
| --- | --- | --- | --- | --- |
| Oct 8-Nov 15 Twitter window | Current source covers Oct 15-Nov 8 | Add a source-acquisition and compatibility gate for Nov 9-15; never imply preprocessing removed those dates | A validated extension is merged, or Phase 1 remains blocked pending an explicit scope decision | D1 |
| Broad election discourse | Candidate hashtag streams with possible overlap | Preserve stream membership, measure overlap, narrow claims | Candidate-stream-centered analysis population is explicit | D3 |
| Rich Stream A schema | v1 drops useful raw metadata | Build versioned v2 canonical and lineage schemas | Downstream phases receive all available, supportable fields | D2, D3 |
| Event shocks with UTC timing and indicators | Four events but no inclusion/window contract | Versioned event registry and observation-level window construction | Only eligible, sourced events enter H1 | D4, D9 |
| October 2 diagnosis event | No matching Twitter observations; October 22 was incorrectly proposed as the diagnosis date | Keep October 2 as not testable under the current/target start date; model October 22 as the final debate, not the diagnosis | Historically correct event register | D1, D4, D11 |
| Historical battleground/safe labels | Current label uses 2020 margin | Add 2012/2016 returns and pre-outcome competitiveness | No dependent-variable leakage in subgroup definition | D5 |
| Demographic controls | Not ingested | Add approved pre-election state covariates with provenance | H2 input contains a parsimonious control matrix | D6 |
| Bot/spam rule and 50 tweets/day | Current empirical threshold is 9/day and bots are unconfirmed | Produce named activity variants and compare downstream stability | Original rule is evaluated without unsupported bot claims | D7 |
| Account-age rule | v1 drops join date | Retain available join date; audit availability before any rule | Rule availability is evidence-based | D3, D7 |
| Duplicate removal and retweet intensity | Cleaning can erase amplification evidence | Preserve pre-dedup counts, retweet intensity, and lineage | Clean rows and amplification evidence coexist | D3 |
| VADER-safe normalization | Mostly implemented; URL evidence removed | Preserve original text or pre-cleaning indicators and a separate cleaned field | Phase 2.5 can inspect evidence without changing VADER input | D3 |
| RoBERTa validates VADER precision | Comparison exists but is not ground truth | Report agreement; defer accuracy claims to human annotation | Correct terminology and reproducible comparison | D10 |
| Temporal and state matrices | Phase 4 absent | Implement coverage-aware daily/hourly/event/state aggregates | Analysis-ready Phase 5 inputs | D4, D9 |
| ITSA and OLS | Phase 5 absent | Implement diagnostics, robust uncertainty, and sensitivity analyses | Original H1/H2 are directly answered | D5, D6, D9, D10 |
| Anticipated findings in PDF | Expected results are written before testing | Treat them as hypotheses until Phase 5 evidence exists | No circular or pre-decided conclusion | D10 |

## 7.1 Evidence note: October 2 and October 22

- An October 2, 2020 memorandum and contemporaneous White House documentation
  identify President Trump's positive COVID-19 result at the beginning of October.
- The Commission on Presidential Debates identifies October 22, 2020 as the final
  Trump-Biden presidential debate.
- COVID-19 was discussed during that debate. This allows an event topic tag such as
  `debate_topic_covid`, but the observable shock remains the full debate. The model
  cannot isolate the effect of one debate topic without a different design.

Source references:

- https://www.presidency.ucsb.edu/documents/white-house-press-release-memorandum-from-the-presidents-physician
- https://www.debates.org/voter-education/debate-transcripts/october-22-2020-debate-transcript/

## 7.2 Evidence note: November 9-15 was not removed

Direct inspection of both raw CSV files produced:

| Raw file | Valid rows | Invalid CSV rows skipped | First timestamp | Last timestamp |
| --- | ---: | ---: | --- | --- |
| `hashtag_donaldtrump.csv` | 970,765 | 323 | 2020-10-15 00:00:01 UTC | 2020-11-08 23:59:56 UTC |
| `hashtag_joebiden.csv` | 776,777 | 296 | 2020-10-15 00:00:01 UTC | 2020-11-08 23:59:58 UTC |

Therefore, November 9-15 is absent from the downloaded source, not excluded by
Phase 1 or Phase 2. The Kaggle dataset card and version history describe Version 19
as ending on November 8:

- https://www.kaggle.com/datasets/manchunhui/us-election-2020-tweets

The seven missing calendar dates may contain a large number of tweets, but their
volume must not be estimated or claimed before compatible data is acquired.

## 7.3 Why Phase 3 uses 5,000 RoBERTa records

| Component | Coverage | Purpose | Training/tuning? |
| --- | ---: | --- | --- |
| VADER | All 1,331,317 Phase 2 v1 rows | Canonical full-data sentiment estimate used downstream | No |
| Twitter-RoBERTa | 5,000 candidate-by-UTC-day stratified rows | Compare a contextual transformer with VADER across every candidate/day stratum | No; inference only |
| Human-labeled tuning set | None currently | Would be required for defensible project-specific calibration or fine-tuning | Not implemented |

The number 5,000 is part of the original PDF design; it is not a universal
peer-review rule. Its peer-review value comes from transparent sampling,
representation of all 50 candidate/day strata, a fixed seed, a reproducible
checksum, documented model revision, and uncertainty estimates. The current sample
produced a narrow Pearson confidence interval while avoiding full transformer cost
on CPU.

The current model is
`cardiffnlp/twitter-roberta-base-sentiment-latest`, revision
`3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7`, run with PyTorch on CPU, batch size
16, and maximum input length 512. It was used as a pretrained comparison model;
its weights were not updated.

Fine-tuning is a different process. It requires project-specific human labels,
separate training/validation/test partitions, a documented optimization procedure,
and held-out evaluation. The 5,000 comparison rows have model outputs but no human
ground-truth labels, so they cannot by themselves support defensible tuning. Running
RoBERTa on the complete dataset would be full inference, not fine-tuning.

## 7.4 Novelty discussion: recommended central contribution

### Instructor assessment of the proposed idea

The proposed sarcasm-aware RoBERTa direction is plausible, but the paper must avoid
three weak novelty claims:

1. **Using Cardiff RoBERTa is not our fine-tuning contribution.** The current
   `twitter-roberta-base-sentiment-latest` model was trained on approximately 124
   million tweets from 2018-2021 and fine-tuned on TweetEval sentiment data. Our
   current pipeline performs inference with that existing model.
2. **A sarcasm flag does not tell us the corrected polarity.** Sarcasm can reverse,
   intensify, soften, or leave target-directed stance ambiguous. Automatically
   removing sarcastic tweets or flipping their sentiment is not defensible.
3. **An external benchmark alone cannot validate this election domain.** Better
   scores on TweetEval or iSarcasmEval would show benchmark performance, not
   reliability on candidate-hashtag political tweets under event and temporal
   shift.

The recommended central contribution is:

> **A target-aware, sarcasm-conditioned and uncertainty-aware framework for
> estimating political sentiment/stance, evaluated on in-domain human annotations
> and tested for its effect on downstream event and spatial conclusions.**

The contribution is stronger than a model leaderboard because it connects
tweet-level validity to the paper's H1 and H2 conclusions.

### Candidate research questions

| ID | Research question | Required evidence |
| --- | --- | --- |
| NRQ1 | How accurately do VADER and off-the-shelf Cardiff RoBERTa recover human-labeled target-directed sentiment and stance in candidate-hashtag tweets? | Representative held-out project annotations |
| NRQ2 | Does predicted sarcasm improve target-directed sentiment/stance performance, calibration, or selective reliability beyond the Cardiff baseline? | Sarcasm labels, learned models, ablations, confidence intervals |
| NRQ3 | Where do gains occur: sarcastic tweets, model-disagreement cases, candidates, topics, or election periods? | Pre-registered subgroup evaluation |
| NRQ4 | Do improved tweet-level predictions materially change H1 event estimates or H2 state associations? | Downstream model comparison with common inputs |
| NRQ5 | How often does candidate-hashtag stream membership disagree with human-labeled stance toward that candidate? | Target and stance annotation plus overlap audit |

### Recommended annotation target

Each annotated tweet should retain separate fields rather than a single overloaded
sentiment label:

| Annotation | Suggested values | Why it is needed |
| --- | --- | --- |
| Target | Trump, Biden, both, other, unclear | Sentiment without a target can be misleading |
| Target stance | favor, against, mixed, neutral/no stance, unclear | Measures political position rather than general emotion |
| Expressed sentiment | negative, neutral, positive, mixed/unclear | Maintains comparability with sentiment baselines |
| Intended target sentiment | negative, neutral, positive, mixed/unclear | Captures meaning after figurative language where annotators can infer it |
| Sarcasm/irony | yes, no, uncertain | Enables subgroup and conditional modeling |
| Directness | direct, indirect, unclear | Indirect political stance is a known failure mode |
| Annotator confidence | ordinal scale | Supports uncertainty and disagreement analysis |

Use at least three independent annotations per evaluation tweet where resources
permit. Preserve annotator distributions and uncertainty; do not force every
subjective case into a majority-vote truth without reporting disagreement.

### Sampling design

A publishable annotation design should contain two distinct components:

1. **Representative evaluation set:** sampled by candidate and period without
   model-based oversampling. This supports population-relevant error estimates.
2. **Challenge/training set:** oversample VADER-RoBERTa disagreement, high predicted
   sarcasm, low transformer confidence, mixed-target tweets, candidate-stream
   overlap, and event windows. This efficiently supplies difficult training cases.

The final test set must be isolated before model development. Use user-grouped
splits so the same author does not leak across training and testing. Add a temporal
holdout, such as training on pre-election annotations and testing on election-day
or post-election annotations, to measure event-period generalization.

Start with a multiply annotated pilot before committing the full budget. The pilot
must estimate class imbalance, sarcasm prevalence, annotation time, inter-annotator
agreement/disagreement, and whether the proposed labels are understandable.

### Model comparison and ablation plan

| Model ID | Method | Purpose |
| --- | --- | --- |
| B0 | VADER | Classical lexicon baseline |
| B1 | Off-the-shelf Cardiff sentiment RoBERTa | Strong social-media transformer baseline |
| B2 | In-domain fine-tuned Cardiff sentiment model | Tests value of project-specific labels without sarcasm integration |
| B3 | Separate sentiment and sarcasm models with learned logit/probability fusion | Tests whether predicted sarcasm adds information |
| B4 | Shared-encoder multi-task model with sentiment/stance and sarcasm heads | Tests joint representation learning |
| B5 | Selective model that abstains or routes uncertain/sarcastic cases | Tests reliability at controlled coverage |

Required ablations:

- B2 versus B1 isolates in-domain fine-tuning.
- B3 with predicted sarcasm versus B3 with the sarcasm feature removed isolates the
  feature's value.
- Predicted-sarcasm versus human-sarcasm (oracle) evaluation estimates how much
  error comes from the sarcasm detector.
- B4 versus matched single-task models tests whether multi-task learning helps.
- A naive polarity-flip rule may be included only as a weak baseline, not as the
  proposed method.

### Evaluation methods

Tweet-level evaluation should report:

- macro-F1 and per-class precision/recall/F1;
- balanced accuracy or MCC under class imbalance;
- Brier score and expected calibration error for probability quality;
- sarcasm AUROC/AUPRC and positive-class F1;
- selective risk-coverage curves for abstaining models;
- bootstrap confidence intervals and paired significance tests;
- results by sarcasm, candidate, target, period, topic, language suitability,
  direct/indirect stance, and model-disagreement tier.

External data may include:

- TweetEval sentiment and irony for standard Twitter baselines;
- iSarcasmEval for intended sarcasm and non-sarcastic rephrases;
- P-Stance for Trump/Biden political stance transfer.

Before use, verify licenses, text/tweet-ID availability, label compatibility, and
train/test overlap. External data may support initialization or auxiliary training,
but the principal test must remain a held-out project-specific set.

### Downstream novelty test

The most important experiment is not only whether B3/B4 beats B1. Recompute the
same Phase 4 matrices and Phase 5 specifications with each approved sentiment
variant, then compare:

- event level/slope/decay estimates and confidence intervals;
- candidate-stream sentiment margins;
- state inclusion and coverage;
- H2 coefficients and influence diagnostics;
- conclusion stability across tweet-weighted and user-weighted variants.

This supports a stronger contribution:

> Model choice and figurative-language handling may change substantive social-
> science conclusions, not merely classification scores.

### Other novelty directions ranked

| Direction | Novelty potential | Feasibility | Recommended role |
| --- | --- | --- | --- |
| Target-aware sarcasm-conditioned sentiment/stance | High if supported by new annotations and ablations | Medium | Primary method contribution |
| Candidate-hashtag versus actual stance misalignment | High and tightly grounded in this dataset | Medium | Primary empirical contribution alongside the model |
| Model-to-conclusion robustness for H1/H2 | High for interdisciplinary contribution | Medium | Required downstream validation |
| Event-topic-sentiment pathways | Medium; stronger than basic timelines but topic analysis is common | High | Secondary insight layer |
| Temporal generalization across pre/election/post periods | Medium-high when paired with annotation | Medium | Core robustness experiment |
| Annotator disagreement as political-sentiment uncertainty | High but annotation-intensive | Medium-low | Strong extension if annotation resources permit |
| Amplification/user-weighted sensitivity | Medium | High | Robustness analysis, not sole novelty claim |
| Full-dataset off-the-shelf RoBERTa inference | Low by itself | Computationally expensive | Engineering extension only |

### Expected results and interpretation rule

The following are hypotheses, not promised outcomes:

- in-domain fine-tuning may improve target-directed sentiment/stance over B1;
- sarcasm-aware fusion or multi-task learning may improve performance specifically
  on sarcastic and model-disagreement subsets;
- selective abstention may reduce error more reliably than forced correction;
- hashtag-stream membership may be an imperfect proxy for candidate stance;
- H1/H2 estimates may or may not change materially across model variants.

If the sarcasm-aware model does not improve the held-out project test, that is still
a valid finding. The project must report the failed hypothesis rather than select an
external benchmark on which the method happens to win.

Source references for the novelty discussion:

- Cardiff model card: https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest
- TweetEval: https://aclanthology.org/2020.findings-emnlp.148/
- iSarcasmEval: https://aclanthology.org/2022.semeval-1.111/
- P-Stance: https://aclanthology.org/2021.findings-acl.208/
- Political approval reliability/validity: https://aclanthology.org/2020.emnlp-main.110/
- Disagreement-aware active learning: https://aclanthology.org/2023.findings-acl.658/
- Sarcasm/sentiment multi-task evidence: https://aclanthology.org/2020.acl-main.401/

## 8. End-to-end refinement sequence

```text
Instructor/user decisions needed for the assigned work package
              |
              v
R1A - Acquire and validate compatible Nov 9-15 Twitter coverage
              |
              v
R1 - Inspect and freeze Phase 1 v2 contracts
              |
              v
R2 - Implement and execute Phase 1 v2
              |
              v
R3 - Run Phase 1 completeness EDA and approve downstream input
              |
              v
R4 - Regenerate Phase 2 variants
              |
              v
R5 - Regenerate Phase 3 sentiment comparison
              |
R7 - Implement Phase 4 matrices
              |
              v
R8 - Implement Phase 5 H1 and H2
              |
              v
R9 - PDF baseline compliance audit
              |
              v
R6 - Phase 2.5 post-MVP examination/refinement, if approved
              |
              v
Later enhancements and approved mitigations
```

## 9. Detailed work packages

### R0. Discussion closure and contract freeze

**Objective**

Resolve the decision register before material implementation diverges based on
implicit assumptions.

**Inputs**

- original PDF;
- this discussion record;
- dataset-grounded knowledge files;
- Phase 1 alignment audit;
- live raw schemas and source availability.

**Methods**

1. Inspect raw field availability and current generated artifacts.
2. Present evidence-backed choices for each pending decision.
3. Record user/instructor decisions without retroactively erasing prior proposals.
4. Freeze versioned Stream A/B/C contracts and downstream impact list.

**Expected results**

- D1-D17 have explicit states;
- Phase 1 v2 scope is implementable without hidden methodological choices;
- affected artifacts and reruns are listed;
- another agent can begin without requesting basic project context again.

**Completion gate**

All choices required for Phase 1 v2 are approved. Phase 4/5 decisions may remain
pending if they do not affect Phase 1 data preservation.

### R1A. November 9-15 source acquisition and compatibility gate

**Objective**

Acquire or identify Twitter data for November 9-15 that is sufficiently compatible
with the existing candidate-hashtag streams to extend the Phase 1 v2 analysis
window without silently changing the study population.

**Inputs**

- current Kaggle collection definition, keywords, fields, license, and version
  history;
- the two verified raw CSV files ending November 8;
- candidate extension datasets, tweet-ID archives, or approved historical
  collection sources;
- platform access, redistribution, deletion, and provenance constraints.

**Methods**

1. Search for an existing November 9-15 source using equivalent Trump/Biden hashtag
   or keyword collection rules.
2. Compare candidate source collection method, query terms, language/geography
   scope, deduplication, retweet handling, columns, timestamp semantics, and license
   with the current Kaggle streams.
3. Reject automatic merging of broader datasets such as `#Election2020` unless a
   reproducible filter can recreate a population comparable to the current
   candidate streams.
4. If only tweet IDs are available, measure hydration success, deletion bias,
   missing text/metadata, and whether the resulting fields meet the v2 schema.
5. Profile November 8/9 boundary discontinuities in volume, users, candidate balance,
   language, geography, and collection metadata.
6. Record the exact source, license, retrieval date, checksums, and compatibility
   assessment before ingestion.

**Expected results**

One of two evidence-backed outcomes:

1. a validated November 9-15 extension that is approved for Phase 1 v2; or
2. a documented incompatibility/no-source result returned to the instructor/user,
   with the MVP blocked until the time-window decision is explicitly revised.

No agent may fill the gap with synthetic tweets, estimated counts, or an
untraceable mixture of datasets.

**Completion gate**

Phase 1 v2 schema freeze cannot complete until the extension is either validated or
the user explicitly revises D1 after reviewing the acquisition evidence.

### R1. Phase 1 v2 source and schema inspection

**Objective**

Determine the most complete supportable canonical dataset before writing the v2
ingestion change.

**Inputs**

- `data/01_raw/twitter/hashtag_donaldtrump.csv`;
- `data/01_raw/twitter/hashtag_joebiden.csv`;
- `data/01_raw/political_events/political_events.csv`;
- `data/01_raw/electoral_returns/electoral_returns.csv`;
- existing Phase 1 source and tests;
- any newly approved historical returns or demographic source files.

**Methods**

1. Profile headers, types, missingness, timestamp ranges, identifier precision,
   candidate-stream overlap, row validity, and field consistency.
2. Classify fields as canonical, lineage-only, derived-later, unavailable, or
   intentionally excluded.
3. Define Stream A, B, and C schemas and validation rules.
4. Define versioned output paths or run identifiers so v1 evidence is preserved.
5. Produce an explicit downstream impact assessment.

**Expected results**

- a field-level v2 schema contract;
- confirmed raw coverage and missingness;
- a list of unavailable PDF fields such as usable replies, without fabricated
  replacements;
- a source and provenance inventory;
- a safe rerun design.

**Completion gate**

No ingestion code changes until the schema contract and output versioning strategy
are documented and reviewed.

### R2. Phase 1 v2 implementation and complete rerun

**Objective**

Produce the most complete auditable Streams A/B/C available for all downstream
phases.

**Inputs**

- approved R1 schemas;
- raw Stream A/B/C source files;
- Phase 1 ingestion modules;
- approved source extensions, if any.

**Methods**

1. Extend schema mapping without embedding source-specific policy in reusable
   readers.
2. Retain available account, engagement, geography, collection, original-text, and
   lineage fields approved in R1.
3. Normalize timestamps to UTC and preserve identifiers as strings.
4. Measure cross-stream overlap without assuming stream membership is stance.
5. Validate Stream B provenance and Stream C completeness.
6. Write Parquet outputs, schema manifests, checksums, rejection counts, coverage
   tables, reports, and figures under a new run/version identity.
7. Run focused and regression tests.

**Expected results**

- complete available-field Phase 1 v2 Parquet artifacts;
- explicit Twitter window, period coverage, and candidate-stream overlap evidence;
- sourced and schema-valid event and electoral benchmark streams;
- no silent overwrite of v1 evidence;
- downstream-ready manifests and checksums.

**Completion gate**

All Streams A/B/C pass schema, row-count, uniqueness, timestamp, coverage,
provenance, checksum, and reproducibility checks. Accepted source limitations are
documented.

### R3. Phase 1 v2 completeness EDA and approval

**Objective**

Verify the dataset before downstream preprocessing or interpretation.

**Inputs**

- Phase 1 v2 Parquet files and manifest;
- `notebooks/phase1_database_eda.ipynb`;
- approved period and event definitions.

**Methods**

1. Update the notebook only where required by the v2 schema.
2. Examine record counts, date coverage, candidate balance, missingness, user
   concentration, location coverage, overlap, event support, and electoral coverage.
3. Keep term and hashtag sections exploratory rather than final topic evidence.
4. Export a concise completeness report and list of downstream constraints.

**Expected results**

- independently inspectable evidence that Phase 1 v2 is complete relative to
  available sources;
- quantified limitations before filtering;
- an approved downstream input contract.

**Completion gate**

Instructor/user accepts the Phase 1 v2 completeness report or returns the dataset
for a bounded correction.

### R4. Phase 2 v2 regeneration and sensitivity variants

**Objective**

Regenerate preprocessing from Phase 1 v2 while separating data cleaning from
unsupported bot claims.

**Inputs**

- approved Phase 1 v2 Stream A artifacts;
- v2 original-text and amplification lineage;
- available user join dates and activity evidence;
- D7 filtering decision.

**Methods**

1. Recompute user activity from the full pre-filter dataset.
2. Preserve VADER-relevant case, punctuation, emoji, and emphasis.
3. Preserve pre-cleaning URL and amplification indicators.
4. Remove or mark malformed/empty text using auditable rules.
5. Separate exact duplicates from retweet and near-duplicate amplification.
6. Produce approved activity variants, expected to include empirical 9/day,
   original-PDF 50/day, and unfiltered datasets if D7 is approved.
7. Report user and tweet retention for every rule and variant.

**Expected results**

- reproducible Phase 2 v2 cleaned data;
- filtering variants with common schemas and independent manifests;
- retained amplification evidence;
- no claim of confirmed bot detection;
- a selected primary dataset plus sensitivity datasets.

**Completion gate**

All transformations are reproducible, all row losses are attributed, and the
primary/sensitivity selection is approved before Phase 3 regeneration.

### R5. Phase 3 v2 sentiment regeneration

**Objective**

Regenerate sentiment artifacts from the approved Phase 2 v2 primary dataset.

**Inputs**

- approved Phase 2 v2 primary cleaned Parquet;
- Phase 3 model configuration;
- existing deterministic candidate-by-day sampling method.

**Methods**

1. Validate the v2 input contract.
2. Score every primary record with VADER.
3. Draw a reproducible 5,000-record candidate-by-UTC-day stratified sample.
4. Run the pinned Twitter-RoBERTa model on the sample.
5. Report Pearson and Spearman correlation, label agreement, macro-F1 agreement,
   score differences, language suitability, and model disagreements.
6. Use agreement terminology throughout.
7. Optionally score approved Phase 2 sensitivity variants with VADER for later
   aggregate robustness; do not expand transformer inference without approval.

**Expected results**

- full Phase 3 v2 VADER dataset;
- reproducible 5,000-row RoBERTa comparison;
- internally consistent reports, manifests, figures, and metrics;
- clear separation between model agreement and human accuracy.

**Completion gate**

Every primary record has valid VADER scores, the sample is reproducible, and all
comparison outputs agree with the manifest.

### R6. Post-MVP Phase 2.5 examination and refinement

**Objective**

After the Phase 1-5 MVP compliance audit, measure limitations on the regenerated
data without applying mitigation. Existing v1 full-run artifacts are historical
evidence and do not count as a v2 examination.

**Inputs**

- Phase 2 v2 activity and cleaning evidence;
- Phase 3 v2 full VADER data and 5,000-row comparison;
- Stream B events;
- available location and amplification evidence;
- current Phase 2.5 configuration and production package.

**Methods**

1. Revalidate availability and provenance for every diagnostic.
2. Run the complete-dataset examination.
3. Keep missing model or language evidence null outside supported subsets.
4. Report separate diagnostic dimensions and affected downstream claims.
5. Keep every mitigation action pending unless separately approved.

**Expected results**

- complete-dataset limitation distributions with availability counts;
- phase-linkage matrix and mitigation decision register;
- no automatic record exclusion, weighting, sentiment correction, routing, or
  model training.

**Completion gate**

The Phase 1-5 MVP is already complete, and Phase 2.5 reports, schemas, manifests,
counts, and no-mitigation checks agree. Completion of the examination does not
approve mitigation.

### R7. Phase 4 spatial-temporal aggregation

**Objective**

Create the analysis matrices required by the original H1 and H2.

**Inputs**

- Phase 3 v2 sentiment data;
- Phase 1 v2 event registry;
- approved state-location mapping contract;
- Phase 1 v2 electoral and control data;
- approved period, grain, coverage, and event-window decisions.

**Methods**

1. Produce daily primary and approved hourly event-window aggregates.
2. Calculate tweet count, unique-user count, candidate-stream counts, mean VADER
   compound, variance/standard deviation, and coverage indicators.
3. Construct observation-level event identities, time-to-event, pre/post flags,
   and window membership from timestamps.
4. Map locations to states using explicit confidence and ambiguity categories.
5. Publish mapped, ambiguous, non-US, national-only, and missing coverage.
6. Compute candidate-stream state sentiment margins without interpreting stream
   membership as stance.
7. Apply pre-registered time/state minimum-coverage gates.
8. Carry reliability availability fields for later sensitivity analyses without
   applying unapproved weights.

**Expected results**

- canonical temporal matrix;
- event-window matrix;
- state sentiment matrix;
- state and event coverage reports;
- clean joins to Stream B and Stream C;
- Phase 5-ready inputs with explicit limitations.

**Completion gate**

All aggregates reproduce their source counts, event windows pass boundary and
overlap tests, state coverage is published, and excluded units have recorded
reasons.

### R8. Phase 5 statistical evaluation

**Objective**

Directly answer the original H1 and H2 with appropriate uncertainty and restrained
interpretation.

**Inputs**

- Phase 4 temporal and event matrices;
- Phase 4 state sentiment matrix;
- historical competitiveness and demographic controls;
- primary and approved sensitivity variants;
- pre-registered H1/H2 specifications.

**Methods for H1**

1. Verify event eligibility and sufficient pre/post support.
2. Fit segmented interrupted-time-series models for level and slope changes.
3. Use time-series-appropriate uncertainty, including autocorrelation diagnostics
   and robust errors where justified.
4. Compare approved event windows and temporal grains.
5. Report effect estimates, confidence intervals, diagnostics, and decay evidence.
6. Use event-aligned rather than definitive causal language.

**Methods for H2**

1. Fit a parsimonious national state-level OLS model first.
2. Use actual Biden-minus-Trump vote margin as the outcome and the candidate-stream
   sentiment margin as the focal predictor.
3. Add only approved, pre-election demographic controls.
4. Use heteroskedasticity-robust uncertainty, multicollinearity checks, influence
   diagnostics, residual diagnostics, and leave-one-state-out sensitivity.
5. Compare historical competitiveness groups using a pre-registered interaction or
   descriptive subgroup analysis. Do not force separate subgroup regressions when
   sample size is inadequate.
6. Compare activity, duplicate, user-weighted, or location-confidence variants only
   when approved as sensitivity analyses.

**Expected results**

- H1 event-level estimates and decay evidence or a documented null/inconclusive
  result;
- H2 association estimates, uncertainty, diagnostics, and subgroup evidence or a
  documented null/inconclusive result;
- sensitivity analysis showing whether conclusions depend on preprocessing or
  coverage choices;
- no pre-decided confirmation of the PDF's anticipated findings.

**Completion gate**

Both hypotheses are answered with estimates, assumptions, diagnostics,
uncertainty, sensitivity results, and claim-boundary review.

### R9. Original-PDF baseline compliance audit

**Objective**

Determine whether the original baseline is satisfied before enhancements begin.

**Inputs**

- original PDF requirements;
- all v2 phase manifests, reports, tests, figures, and statistical results;
- this decision and mismatch register.

**Methods**

1. Map every PDF requirement to implementation and generated evidence.
2. Classify each item as satisfied, defensibly refined, documented deviation, not
   testable, or enhancement-deferred.
3. Reconcile README, project journal, phase plans, and paper wording.
4. Identify invalidated v1 claims and preserve their historical provenance.

**Expected results**

- a requirement-to-evidence compliance matrix;
- an explicit baseline-completion decision;
- a bounded backlog for later annotation, topic modeling, weighting, fine-tuning,
  decision support, or new data acquisition.

**Completion gate**

No original-PDF requirement is silently missing, and no enhancement is presented as
a substitute for an unanswered H1 or H2.

### N0-N5. Proposed post-MVP novelty track

This track is proposed, not approved. It begins only after R9 unless D17 is changed
explicitly. Section 7.4 supplies the detailed experimental rationale.

| Package | Inputs | Methods | Expected results | Gate |
| --- | --- | --- | --- | --- |
| N0. Novelty and dataset audit | Current literature, Cardiff/TweetEval documentation, candidate external datasets, project claim boundaries | Systematic related-work matrix; dataset/license/overlap audit; pre-register novelty claim and null outcomes | Defensible gap statement and approved data sources | No implementation until the claimed gap survives the audit |
| N1. Annotation pilot and protocol | Representative and challenge samples from the v2 project data | Multi-label target/stance/sentiment/sarcasm annotation by multiple annotators; pilot agreement and prevalence analysis | Revised annotation guide, feasible budget, pilot quality report | Label definitions and adjudication/disagreement policy approved |
| N2. Final annotated corpus and baselines | Approved annotation protocol, isolated splits, VADER, Cardiff RoBERTa | Build representative test and challenge/train sets; run B0/B1; verify user-grouped and temporal splits | Human-grounded baseline metrics and error taxonomy | Test set frozen before proposed-model training |
| N3. Sarcasm-conditioned model experiments | Project annotations plus approved auxiliary datasets | Fine-tune B2; train B3/B4/B5; calibration, ablations, oracle-versus-predicted sarcasm, paired tests | Evidence for or against each proposed improvement | No claim of improvement without held-out project-test significance and calibration evidence |
| N4. Downstream conclusion robustness | Approved model variants and common Phase 4/5 contracts | Rebuild comparable aggregates and rerun H1/H2; compare estimates and conclusion stability | Evidence whether tweet-level model changes affect substantive findings | Same data coverage/specifications used across model variants |
| N5. Contribution audit and paper integration | N0-N4 outputs | Map claims to evidence; report nulls, subgroup failures, limitations, and reproducibility artifacts | Final contribution statement and enhancement appendix/artifacts | No benchmark-only result is generalized to the project population |

## 10. Agent execution rules

An implementation agent working from this document must:

1. Begin by reporting the work-package ID and applicable approved decisions.
2. Inspect the live worktree and preserve unrelated user changes.
3. Treat current v1 artifacts as immutable evidence unless an explicitly versioned
   replacement contract is approved.
4. Use production modules for reusable logic and verification runners for
   dataset-specific orchestration.
5. Add focused tests before or with material implementation changes.
6. Execute only the approved phase and its necessary verification. Do not advance
   into the next phase automatically.
7. Record actual row counts, schemas, coverage, checksums, and failure reasons.
8. Never substitute expected results for generated results.
9. Stop and return evidence when a pending decision materially affects the result.
10. Update this file's implementation log after work is verified.

## 11. Standard implementation-agent prompt

The following prompt is intended to be derived from, not used instead of, this
document. Replace the bracketed work package and scope before assigning it.

```text
You are the implementation agent for the Social Listener PDF-baseline refinement.

Workspace:
D:\GW_UNIVERSITY\AIS\Social_Listener\Env\Social_Listener_V1\UOG_AIS_SOCIAL_LISTENER

Controlling plan:
docs/plans/PDF_BASELINE_REFINEMENT_AND_IMPLEMENTATION_HANDOFF.md

Assigned work package: [R1/R2/etc.]
Approved decision IDs: [list]

First read the mandatory sources listed in section 2 of the controlling plan. Then
inspect the live code, tests, data schemas, and current worktree before changing
anything.

Implement only the assigned package. Preserve v1 generated evidence and unrelated
changes. Do not resolve pending methodological decisions by guessing. If a pending
decision blocks the assigned package, return the inspected evidence and concrete
options to the instructor.

Required report:
1. Inputs actually found and their schemas/coverage.
2. Methods implemented.
3. Files changed.
4. Tests and executions performed.
5. Actual results versus expected results.
6. Remaining limitations and pending decisions.
7. Recommended status update for the controlling plan.

Do not make claims beyond the verified candidate-hashtag dataset window. Do not call
high-volume users bots. Do not treat model agreement as accuracy. Do not apply
Phase 2.5 mitigation unless separately approved.
```

## 12. Phase 1 v2 implementation-agent prompt

Use this only after R1A resolves the November 9-15 extension gate, the R1 schema
inspection is complete, and decisions D1-D6 needed by Phase 1 are approved.

```text
Implement work package R2 from
docs/plans/PDF_BASELINE_REFINEMENT_AND_IMPLEMENTATION_HANDOFF.md.

Goal: execute a versioned Phase 1 v2 rerun that creates the most complete available
Streams A/B/C for downstream phases while preserving v1 evidence.

Inputs:
- the two raw Kaggle candidate Twitter CSV files;
- political_events.csv;
- electoral_returns.csv;
- any separately approved historical-election or demographic source files;
- the approved R1 schema contract.

Methods and constraints:
- retain only approved, actually available fields;
- preserve IDs as strings and timestamps in UTC;
- retain original-text, account, engagement, geographic, collection, source, and
  lineage fields approved by the schema contract;
- measure cross-stream overlap without calling it stance;
- write versioned Parquet outputs, manifests, checksums, reports, and figures;
- preserve v1 artifacts;
- add and run schema, coverage, provenance, uniqueness, checksum, and regression
  tests;
- do not implement downstream filtering, sentiment, reliability mitigation,
  aggregation, or statistical modeling.

Expected result: a tested, auditable Phase 1 v2 dataset and completeness evidence
that can be reviewed before Phase 2 regeneration.

Return actual row counts, date coverage, field availability, missingness, overlap,
rejections, checksums, test results, changed files, and any blocked decisions.
```

## 13. Discussion log

### 2026-07-13 - Initial PDF-alignment discussion

**User concern:** The codebase must first satisfy the original PDF ideas before
later enhancements. Earlier mismatch identification did not specify mitigations.

**Instructor response:** Classified each mismatch into implement, document as a
source limitation, replace with a defensible equivalent, or defer as an
enhancement. Identified unresolved decisions that are maintained in the live
decision register.

**Result:** The baseline must retain the original five-phase path. Phase 2.5 may
remain as examination-only, but cannot substitute for Phase 4 or Phase 5.

### 2026-07-13 - Phase 1 complete-data clarification

**User question:** Should Phase 1 be rerun to achieve the complete dataset needed by
downstream implementation?

**Instructor response:** Yes. A Phase 1 v2 rerun is necessary to preserve all useful
available Stream A metadata, formalize Stream B, and complete Stream C inputs.
However, a rerun cannot create missing dates outside the Twitter source's verified
window.

**Decision:** D2 approved. Phase 1 v2 becomes the first implementation action after
the required schema and source decisions are sufficiently resolved.

### 2026-07-13 - Living handoff requested

**User direction:** Create an agent-friendly Markdown record that continues the
discussion, contains the implementation plan, includes inputs, methods, and
expected results, and can generate prompts for a separate implementation agent.
All future discussion is to be updated in the same file.

**Result:** This document was created as the controlling living handoff.

### 2026-07-13 - Event dates, Phase 3 sampling, time extension, and MVP boundary

**Question or instruction:** The user proposed treating October 22 as Trump's
positive COVID-19 test, asked why RoBERTa used 5,000 rather than all tweets and
whether this was peer review or tuning, required extension through November 15,
and defined Phases 1-5 as the MVP with Phase 2.5 later.

**Evidence inspected:**

- raw Trump and Biden CSV timestamps and invalid-row counts;
- Kaggle dataset card and Version 19 history;
- October 2 presidential-physician documentation;
- October 22 Commission on Presidential Debates transcript;
- Phase 3 sampling and inference manifests;
- current Phase 2.5 full-run manifest.

**Instructor analysis:**

- The positive-test announcement belongs to October 2. October 22 is the final
  debate. COVID-19 was a debate topic, but this does not turn the debate into the
  diagnosis event.
- VADER ran on all 1,331,317 v1 cleaned tweets. Only pretrained Twitter-RoBERTa
  inference used the 5,000-row candidate/day stratified comparison sample.
- The number 5,000 is an original-PDF design choice, not a universal peer-review
  rule. Reproducibility, coverage, uncertainty, and transparent limitations create
  peer-review value.
- No Phase 3 tuning occurred. Full RoBERTa inference and model fine-tuning are
  distinct actions.
- The raw files end on November 8; November 9-15 was never passed into
  preprocessing and therefore was not filtered out.

**Decisions:** D1 changed to approved with acquisition pending; D8 approved; D11
recorded as an instructor factual correction. D12 remains pending explicit
acceptance.

**Implementation consequence:** R1A is now a blocking source-acquisition and
compatibility gate before Phase 1 v2. R6 Phase 2.5 moved behind R9 and is not on the
MVP critical path.

**Progress update:** No new Twitter data was acquired and no pipeline phase was
rerun. Existing Phase 2.5 full v1 artifacts were acknowledged and frozen as
post-MVP refinement evidence.

### 2026-07-14 - Novelty through target-aware sarcasm-conditioned modeling

**Question or instruction:** The user asked how to create a paper-level novelty
contribution beyond standard sentiment analysis and proposed combining Cardiff
Twitter-RoBERTa sentiment with sarcasm classification, fine-tuning, and external
benchmark evaluation.

**Evidence inspected:**

- Cardiff `twitter-roberta-base-sentiment-latest` model card;
- TweetEval benchmark and task definitions;
- iSarcasmEval intended-sarcasm task;
- P-Stance Trump/Biden political stance dataset;
- research on political-approval validity, multi-task sarcasm/sentiment learning,
  temporal shift, and disagreement-aware annotation;
- project sentiment, reliability, and dataset-scope notes.

**Instructor analysis:** Using the existing Cardiff model is off-the-shelf inference,
not a new fine-tuning contribution. A separate sarcasm probability cannot safely be
used to remove tweets or reverse polarity. External benchmarks are valuable for
auxiliary training and comparison, but cannot replace a held-out, human-annotated
test drawn from the project domain. Target stance is at least as important as
sarcasm because a tweet containing a candidate hashtag may oppose that candidate.

**Proposed direction:** Build a target-aware, sarcasm-conditioned and uncertainty-
aware sentiment/stance framework; evaluate it on project-specific multiple
annotations; and test whether model changes alter H1/H2 conclusions.

**Decision:** Added pending decisions D13-D17. No novelty method, annotation budget,
external dataset, or fine-tuning run is approved yet.

**Implementation consequence:** Added proposed post-MVP packages N0-N5. The Phase
1-5 MVP remains the active baseline path.

**Progress update:** Literature and method options were reviewed and documented.
No annotation, training, full inference, or benchmark experiment was executed.

## 14. Implementation log

| Date | Work package | Action | Evidence | Status |
| --- | --- | --- | --- | --- |
| 2026-07-13 | R0 | Living discussion and implementation handoff created | This document | In progress |
| 2026-07-13 | R2 | Phase 1 v2 rerun selected as critical path | Decision D2 | Approved, not started |
| 2026-07-13 | R1A | November 9-15 acquisition and compatibility gate added | Raw timestamp audit, Kaggle Version 19, decision D1 | Approved, not started; blocks Phase 1 v2 |
| 2026-07-13 | R6 | Phase 2.5 moved after the Phase 1-5 MVP | Decision D8; existing v1 full-run manifest preserved | Deferred until after R9 |
| 2026-07-14 | N0-N5 | Novelty candidate and experiment ladder documented | Section 7.4 and decisions D13-D17 | Proposed; awaiting discussion/approval |

## 15. Future update template

Append one entry for every material discussion or implementation event:

```markdown
### YYYY-MM-DD - Short topic

**Question or instruction:**

**Evidence inspected:**

**Instructor analysis:**

**Decision:** D# changed from [old] to [new], or no decision.

**Implementation consequence:**

**Progress update:** R# changed from [old] to [new], with evidence paths.
```

When an implementation package finishes, also update the implementation log and
the current progress baseline. Do not mark a package complete unless its stated
completion gate is satisfied.
