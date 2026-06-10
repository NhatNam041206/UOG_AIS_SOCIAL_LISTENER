# Module: telemetry_reporter_view

## Architectural Role

View boundary for Phase 2 quality telemetry.

## Behavior

`TelemetryReporterView` validates counts, computes drop rates, formats console reports,
and retains independent stage metrics for manifests, reports, and figures. Metrics are
reset at the start of each controller execution and include initial, final, dropped,
and percentage-dropped values.
