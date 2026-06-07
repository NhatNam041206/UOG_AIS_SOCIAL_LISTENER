"""Define view-layer telemetry formatters for preprocessing quality metrics.

This module encapsulates drop-rate computations and report presentation so quality
observability remains separate from controller sequencing and model heuristics.
"""

from __future__ import annotations

from typing import List, Dict, Optional, Any


class TelemetryReporterView:
    """View component for computing and rendering preprocessing drop-rate summaries."""

    def compute_drop_rate(self, initial_count: int, final_count: int) -> float:
        """Compute percentage drop, returning 0.0 when initial_count is zero."""
        raise NotImplementedError

    def format_drop_rate_report(self, stage_name: str, initial_count: int, final_count: int) -> str:
        """Build a human-readable drop-rate report string for one cleaning stage."""
        raise NotImplementedError

    def print_drop_rate_report(self, stage_name: str, initial_count: int, final_count: int) -> None:
        """Print formatted drop-rate telemetry for console or notebook monitoring."""
        raise NotImplementedError
