# Module: telemetry_reporter_view

## Architectural Role
View boundary for preprocessing quality summaries.

## Core Functional Objective
Computes and formats stage-level drop-rate telemetry for monitoring.

## Class and Method Signatures
* `TelemetryReporterView`: View component for computing and rendering preprocessing drop-rate summaries.
  * `compute_drop_rate(self, initial_count: int, final_count: int) -> float`: Compute percentage drop, returning 0.0 when initial_count is zero.
  * `format_drop_rate_report(self, stage_name: str, initial_count: int, final_count: int) -> str`: Build a human-readable drop-rate report string for one cleaning stage.
  * `print_drop_rate_report(self, stage_name: str, initial_count: int, final_count: int) -> None`: Print formatted drop-rate telemetry for console or notebook monitoring.
