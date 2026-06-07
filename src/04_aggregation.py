"""Phase 4 aggregation module for spatial and temporal feature matrices."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AggregationWindow:
    """Aggregation granularity settings."""

    frequency: str = "D"


class Aggregator:
    """Group sentiment signals into analytical matrices."""

    def build(self, records: list[dict]) -> list[dict]:
        raise NotImplementedError
