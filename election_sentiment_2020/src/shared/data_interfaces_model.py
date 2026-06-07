"""Define shared data contracts and schema templates for all pipeline phases.

This model-layer module centralizes abstract interfaces that enforce typed boundaries
between data access, schema mapping, and validation responsibilities.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any


class RecordSchemaTemplate(ABC):
    """Abstract schema contract describing required fields and validation behavior."""

    @abstractmethod
    def required_fields(self) -> List[str]:
        """Return the mandatory column names expected by downstream modules."""

    @abstractmethod
    def validate(self, record: Dict[str, Any]) -> bool:
        """Return True when an input record conforms to the schema template."""


class SchemaMapperInterface(ABC):
    """Abstract mapper for normalizing raw provider payloads into shared schema format."""

    @abstractmethod
    def map_record(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform one raw record into the canonical schema representation."""


class DataFrameProvider(ABC):
    """Abstract provider for exposing typed tabular datasets to controllers."""

    @abstractmethod
    def load(self, source: str, options: Optional[Dict[str, Any]] = None) -> Any:
        """Load source data into a DataFrame-like object."""
