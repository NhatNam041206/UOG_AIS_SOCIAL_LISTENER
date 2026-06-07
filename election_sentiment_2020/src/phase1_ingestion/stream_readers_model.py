"""Define model-layer DAOs for loading raw CSV and JSON streams into DataFrames.

This module isolates source-specific ingestion concerns behind abstract interfaces so
controller logic can coordinate readers without coupling to file format details.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any


class StreamReaderDAO(ABC):
    """DAO contract for loading external stream files into tabular structures."""

    @abstractmethod
    def read(self, source_path: str, options: Optional[Dict[str, Any]] = None) -> Any:
        """Read input data from disk and return a DataFrame-like object."""


class CsvStreamReader(StreamReaderDAO):
    """CSV stream reader DAO for raw export ingestion."""

    def read(self, source_path: str, options: Optional[Dict[str, Any]] = None) -> Any:
        """Load CSV content from source_path into a DataFrame-like object."""
        raise NotImplementedError


class JsonStreamReader(StreamReaderDAO):
    """JSON stream reader DAO for newline-delimited or standard JSON payloads."""

    def read(self, source_path: str, options: Optional[Dict[str, Any]] = None) -> Any:
        """Load JSON content from source_path into a DataFrame-like object."""
        raise NotImplementedError
