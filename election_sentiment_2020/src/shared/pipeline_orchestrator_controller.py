"""Define shared controller-level orchestration loops and exception handling contracts.

This controller-layer module provides abstract execution flow definitions so concrete
phase controllers can remain small, testable, and consistent with the MVC suffix rules.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any


class PipelineControllerError(Exception):
    """Base exception type for pipeline controller-level failures."""


class BasePipelineOrchestrator(ABC):
    """Abstract orchestrator with a reusable guarded execution loop."""

    def __init__(self) -> None:
        self._last_error: Optional[Exception] = None

    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the controller flow and dispatch failures to a handler hook."""
        try:
            return self.execute(*args, **kwargs)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as exc:  # pragma: no cover - skeleton behavior
            self._last_error = exc
            return self.handle_exception(exc)

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Implement the concrete phase execution loop."""

    @abstractmethod
    def handle_exception(self, error: Exception) -> Any:
        """Implement phase-specific recovery, logging, or propagation strategy."""
