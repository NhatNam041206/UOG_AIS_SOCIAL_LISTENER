# Module: pipeline_orchestrator_controller

## Architectural Role
Controller boundary for guarded pipeline execution.

## Core Functional Objective
Provides reusable run, execute, and exception handling scaffolding for phase-specific orchestrators.

## Class and Method Signatures
* `PipelineControllerError`: Base exception type for pipeline controller-level failures.
* `BasePipelineOrchestrator`: Abstract orchestrator with a reusable guarded execution loop.
  * `__init__(self) -> None`: No docstring provided.
  * `run(self, *args: Any, **kwargs: Any) -> Any`: Execute the controller flow and dispatch failures to a handler hook.
  * `execute(self, *args: Any, **kwargs: Any) -> Any`: Implement the concrete phase execution loop.
  * `handle_exception(self, error: Exception) -> Any`: Implement phase-specific recovery, logging, or propagation strategy.
