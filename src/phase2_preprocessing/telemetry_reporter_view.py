"""View-layer formatting for Phase 2 quality telemetry."""

from __future__ import annotations

from typing import Any, Dict


class TelemetryReporterView:
    """Compute, retain, and render preprocessing stage summaries."""

    def __init__(self) -> None:
        self._stage_metrics: Dict[str, Dict[str, Any]] = {}

    @property
    def stage_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Return a copy of metrics collected during the latest execution."""
        return {name: values.copy() for name, values in self._stage_metrics.items()}

    def reset(self) -> None:
        """Clear metrics before a new preprocessing execution."""
        self._stage_metrics.clear()

    def compute_drop_rate(self, initial_count: int, final_count: int) -> float:
        """Compute percentage drop, returning 0.0 when initial_count is zero."""
        self._validate_counts(initial_count, final_count)
        return 0.0 if initial_count == 0 else 100.0 * (initial_count - final_count) / initial_count

    def record_stage(self, stage_name: str, initial_count: int, final_count: int) -> Dict[str, Any]:
        """Store and return auditable counts for one cleaning stage."""
        if not isinstance(stage_name, str) or not stage_name.strip():
            raise ValueError("stage_name must be a non-empty string")
        drop_rate = self.compute_drop_rate(initial_count, final_count)
        metrics = {
            "initial_count": initial_count,
            "final_count": final_count,
            "dropped_count": initial_count - final_count,
            "drop_rate_pct": drop_rate,
        }
        self._stage_metrics[stage_name] = metrics
        return metrics.copy()

    def format_drop_rate_report(self, stage_name: str, initial_count: int, final_count: int) -> str:
        """Build a human-readable drop-rate report string for one cleaning stage."""
        metrics = self.record_stage(stage_name, initial_count, final_count)
        return (
            f"{stage_name}: retained {final_count:,}/{initial_count:,} records; "
            f"dropped {metrics['dropped_count']:,} ({metrics['drop_rate_pct']:.2f}%)."
        )

    def print_drop_rate_report(self, stage_name: str, initial_count: int, final_count: int) -> None:
        """Print formatted drop-rate telemetry for console or notebook monitoring."""
        print(self.format_drop_rate_report(stage_name, initial_count, final_count))

    @staticmethod
    def _validate_counts(initial_count: int, final_count: int) -> None:
        if initial_count < 0 or final_count < 0:
            raise ValueError("record counts must be non-negative")
        if final_count > initial_count:
            raise ValueError("final_count cannot exceed initial_count")
