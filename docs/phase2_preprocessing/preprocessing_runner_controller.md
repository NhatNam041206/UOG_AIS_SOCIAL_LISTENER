# Module: preprocessing_runner_controller

## Architectural Role

Controller boundary for the ordered Phase 2 workflow. It coordinates injected model
components and delegates telemetry presentation to `TelemetryReporterView`.

## Processing Order

1. Bot filtering.
2. Exact-text deduplication.
3. HTML and URL removal followed by invalid-text rejection.

`execute(records)` supports a list of dictionaries. `execute_dataframe(dataframe)`
provides the vectorized path used for the full dataset. Neither method mutates its
input. `run(...)` wraps failures in `PipelineControllerError`.

## Configuration

Inject a `CleaningPolicy` to change canonical field names or thresholds without
rewriting controller logic. Inject a `TextCleaner` to extend normalization while
preserving the controller's sequencing responsibility.
