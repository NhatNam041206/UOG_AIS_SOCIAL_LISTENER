"""Phase 1 ingestion module for abstract and concrete data source loaders."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseIngestion(ABC):
    """Base interface for ingestion implementations."""

    @abstractmethod
    def load(self, source: Path) -> Any:
        """Load source records into a structured in-memory representation."""


class TwitterIngestion(BaseIngestion):
    """Example ingestion class for raw Twitter exports."""

    def load(self, source: Path) -> Any:
        raise NotImplementedError
