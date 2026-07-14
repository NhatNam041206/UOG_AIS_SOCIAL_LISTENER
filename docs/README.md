# Documentation Map

This folder keeps phase-level records and implementation-control documents. It no
longer stores generated per-module API notes; source files and tests are the
authority for module-level behavior.

## Start Here

Read these first when deciding what to do next:

1. `../../../../knowledge_sources/KNOWLEDGE_SOURCE_INDEX.md`
2. `../README.md`
3. `PROJECT_JOURNAL.md` if present locally
4. `AGENT_WORK_JOURNAL.md` if present locally
5. `plans/PDF_BASELINE_REFINEMENT_AND_IMPLEMENTATION_HANDOFF.md`

`PROJECT_JOURNAL.md` and `AGENT_WORK_JOURNAL.md` are local-only working files and
are ignored by Git.

## Current Core Documents

| File | Purpose |
| --- | --- |
| `EXPERIMENT_NOTEBOOKS.md` | Scope and usage notes for executable notebooks. |
| `PHASE1_DATA_STREAM_ALIGNMENT.md` | Audit of Stream A/B/C alignment against the original PDF baseline. |
| `PHASE2_COMPLETION_REPORT.md` | Phase 2 closure record and generated evidence summary. |
| `PHASE2_5_FINDINGS_REVIEW.md` | Review of the Phase 2.5 full v1 reliability examination outputs. |
| `PHASE2_5_NOTEBOOK_TO_PIPELINE_GUIDE.md` | Historical transfer guide from notebook prototype to production package. |
| `PHASE3_MODEL_ARTIFACT_INVENTORY.md` | Inventory of Phase 3 model artifacts and comparison boundaries. |
| `plans/ORIGINAL_PDF_ALIGNMENT_PLAN.md` | Phase-by-phase alignment plan for the original PDF methodology. |
| `plans/PDF_BASELINE_REFINEMENT_AND_IMPLEMENTATION_HANDOFF.md` | Current controlling refinement plan, decision register, and handoff record. |
| `plans/PHASE2_5_PRODUCTION_AND_PHASE4_ENTRY_PLAN.md` | Phase 2.5 production and Phase 4 entry context. |
| `plans/PHASE3_IMPLEMENTATION_PLAN.md` | Phase 3 implementation and closure reference. |

## Cleanup Rule

Avoid adding one markdown file per source module. Prefer updating the README,
project journal, agent work journal, a phase completion report, or a focused plan.
Generated reports under `output/reports/` should remain generated evidence, not the
primary location for planning decisions.

## Codebase Operating Rules

These rules are the default contract for future agents. Follow them unless the user
explicitly changes the phase scope.

### Architecture

- Keep the phase-oriented structure: `src/phase1_ingestion`,
  `src/phase2_preprocessing`, `src/phase2_5_reliability`,
  `src/phase3_sentiment`, `src/phase4_aggregation`, `src/phase5_modeling`,
  `src/shared`, and `src/utils`.
- Keep controllers as service/orchestration boundaries and keep model/view modules
  focused on data logic or reporting.
- Do not make a phase write into another phase's implementation folder.
- Do not silently change schemas consumed by later phases. Add or update manifests,
  compatibility checks, and tests whenever an input or output contract changes.
- Preserve v1 generated evidence when creating v2 outputs. Do not overwrite
  historical manifests or reports without an explicit versioning decision.

### Inputs

- Treat `data/01_raw/` as source evidence and `data/02_interim/` as canonical
  phase-to-phase data. Do not mutate raw files.
- The verified current Twitter window is `2020-10-15` through `2020-11-08`.
  November 9-15 is a target extension only until a compatible source is acquired
  and validated.
- Keep Twitter IDs as strings. Do not coerce them to numeric identifiers.
- Missing metadata must stay explicit. Do not infer unavailable fields such as
  `user_created_at`, language, URL evidence, or full-corpus RoBERTa diagnostics.
- Candidate hashtag stream membership is source lineage, not stance or support.

### Outputs

- Write phase data under `data/`, machine-readable outputs under
  `output/results/phaseX/`, reports under `output/reports/phaseX/`, and figures
  under `output/graphs/phaseX/`.
- Every phase execution should have a manifest that records inputs, row counts,
  configuration, generated files, limitations, and verification state.
- Reports should explain what was measured, what was not measured, and what claims
  remain unsupported.
- Figures must be few, purposeful, reproducible, and linked to a report or result
  file. Do not generate decorative or duplicate plots.

### Development Process

- Start by reading the required sources in the Start Here section and the phase plan
  or report for the work being changed.
- Inspect current code, tests, manifests, and reports before deciding the next step.
- Keep work phase-scoped. If a dependency from another phase is missing, document
  the blocker rather than inventing data or changing the other phase casually.
- Update tests or verification scripts for behavior changes.
- Update `PROJECT_JOURNAL.md` for material phase status changes when it is present
  locally. Update `AGENT_WORK_JOURNAL.md` after material work with evidence checked,
  files changed, verification, blockers, and next action.

### Verification

- Run the narrowest relevant test suite first, then broader suites if the change
  crosses phase boundaries.
- For docs-only changes, verify links/references and state that no code tests were
  run.
- For generated artifacts, reconcile row counts, schemas, manifests, reports, and
  figures before calling a phase complete.
- Do not report Phase 5 findings until Phase 5 code, outputs, diagnostics, reports,
  and verification exist.

### Audit and Commit Requests

When the user says `audit` after reviewing work:

1. Review the touched files, relevant docs, manifests, outputs, and tests.
2. Update `AGENT_WORK_JOURNAL.md` with the audit result and next action.
3. Report findings first if risks or mismatches exist.
4. Include the updated progress tracker status.

When the user says `commit` after reviewing work:

1. Update `AGENT_WORK_JOURNAL.md` and, when appropriate, `PROJECT_JOURNAL.md`.
2. Verify the working tree status and mention any unrelated existing changes.
3. Provide a concise proposed GitHub commit message.
4. Report the files changed, verification performed, and updated progress tracker.
5. Do not push. The user pushes updates.
