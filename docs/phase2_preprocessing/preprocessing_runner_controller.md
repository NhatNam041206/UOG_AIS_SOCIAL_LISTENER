# Module: preprocessing_runner_controller

## Architectural Role
Controller boundary for sequential preprocessing passes.

## Core Functional Objective
Coordinates bot filtering, deduplication, and telemetry reporting to produce cleaned records.

## Class and Method Signatures
* `PreprocessingRunnerController`: Controller that applies preprocessing passes in a defined sequence.
  * `__init__(self, telemetry_reporter: TelemetryReporterView) -> None`: No docstring provided.
  * `execute(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]`: Run preprocessing passes and return the cleaned dataset.
  * `handle_exception(self, error: Exception) -> Any`: Handle preprocessing failures with phase-specific reporting behavior.
  * `_apply_cleaning_passes(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]`: Apply bot filtering, deduplication, and text integrity checks sequentially.
