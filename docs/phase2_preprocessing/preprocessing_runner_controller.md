# Module: preprocessing_runner_controller

## Architectural Role

Controller boundary for the ordered Phase 2 workflow. It coordinates injected model
components and delegates telemetry presentation to `TelemetryReporterView`.

## Processing Order

1. User-level activity filtering using the audit-selected threshold, plus available
   account-age or bot-score rules.
2. Exact-text deduplication.
3. HTML and URL removal followed by invalid-text rejection.

`execute(records)` supports a list of dictionaries. `execute_dataframe(dataframe)`
provides the vectorized path used for the full dataset. Neither method mutates its
input. `run(...)` wraps failures in `PipelineControllerError`.

## Configuration

Inject a `CleaningPolicy` containing the empirically selected
`maximum_tweets_per_active_day`; no fixed activity threshold is embedded in the
controller. Inject a `TextCleaner` to extend normalization while preserving the
controller's sequencing responsibility.
