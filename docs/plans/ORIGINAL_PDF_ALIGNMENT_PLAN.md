# Original PDF Alignment and Codebase Cleanup Plan

Reference baseline: `SL_2020_ori.pdf`.

Living discussion, decisions, detailed inputs/methods/expected results, agent
handoff prompts, and implementation progress are controlled by
`docs/plans/PDF_BASELINE_REFINEMENT_AND_IMPLEMENTATION_HANDOFF.md`. This shorter
file remains the high-level alignment summary.

Controlling dataset scope: the verified candidate-hashtag Twitter data covers
2020-10-15 through 2020-11-08. The PDF's 2020-10-08 through 2020-11-15 range is a
planned range, not a description of the current data. Compatible extension through
November 15 is now an approved acquisition target, but is not verified coverage yet.

## Delivery order

The original five phases form the MVP completion path. Phase 2.5 is a post-MVP,
examination-only refinement. Existing Phase 2.5 v1 artifacts are preserved, but the
phase must not block Phase 4 or Phase 5. Phase 6 remains an enhancement and must not
substitute for completing the original hypotheses in Phase 5.

| Phase | General cleanup and alignment work | Completion gate |
| --- | --- | --- |
| 1. Multi-source acquisition and alignment | Establish an explicit Stream A/B/C contract; preserve required source metadata; document coverage and provenance; repair Stream C historical classification and controls; define Stream B inclusion rules | All three streams are schema-validated, source-traceable, and sufficient for their downstream contracts, with accepted gaps documented |
| 2. Preprocessing and filtering | Reconcile preprocessing with available metadata; implement only supportable account-age/activity rules; preserve VADER-relevant punctuation/case/emoji; audit duplicates and retweet amplification separately | Filter effects are reproducible, no heuristic is called bot detection, and the cleaned schema passes its contract |
| 3. Sentiment estimation and model comparison | Reproduce full-data VADER scoring; retain the stratified 5,000-record Twitter-RoBERTa comparison; standardize controlling metrics and terminology | Outputs are reproducible and model agreement is not reported as accuracy or human ground truth |
| 4. Spatial-temporal aggregation | Build hourly/daily count, mean, and volatility matrices; derive event windows from Stream B; create state mappings with coverage/confidence; construct candidate-stream sentiment margins | Analysis tables join cleanly to events and states, expose coverage, and do not treat hashtag membership as stance |
| 5. Statistical evaluation | Implement H1 interrupted time-series level/slope/decay tests and H2 state-level OLS; add diagnostics, demographic controls, and swing/safe subgroup analysis | Original hypotheses are directly answered with assumptions, sensitivity tests, uncertainty, and restrained interpretation |
| 2.5. Post-MVP reliability examination | Reconcile v2 artifacts; profile separate limitation dimensions; keep mitigation decisions pending unless explicitly approved | Full-run evidence, manifests, reports, and downstream risk linkages agree; no unapproved filtering or weighting occurs |
| 6. Decision-support enhancement | Translate verified Phase 5 results into reliability-aware decision support only after baseline completion | Every recommendation traces to validated Phase 5 evidence and preserves the study's claim boundaries |

## Phase 1 work package

1. **Completed - expose the three-stream contract.** Add Stream A/B/C names and
   gap status to the Phase 1 report, manifest, README, and a dedicated audit.
2. Revise the Stream A schema contract and decide which existing raw account and
   geographic fields must survive ingestion.
3. Acquire and validate compatible November 9-15 Twitter coverage before freezing
   Phase 1 v2. The current raw files end on November 8; preprocessing did not remove
   the missing dates.
4. Create a Stream B event-selection protocol and validate event completeness,
   timestamps, categories, and source provenance.
5. Extend Stream C with historically derived 2012/2016 state classification and
   approved demographic controls with reproducible sources.
6. Add stream-level schema, coverage, uniqueness, provenance, and checksum tests;
   then re-run Phase 1 and every downstream artifact affected by schema changes.

## Change-control rule

Existing generated outputs are evidence from earlier runs. Schema or source changes
must produce a new manifest/run identifier and an impact list before downstream
artifacts are replaced. This prevents a Phase 1 cleanup from silently invalidating
Phase 2, Phase 2.5, or Phase 3 results.
