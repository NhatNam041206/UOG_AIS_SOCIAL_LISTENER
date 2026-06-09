"""Define model-layer DAOs for loading raw CSV and JSON streams into DataFrames.

This module isolates source-specific ingestion concerns behind abstract interfaces so
controller logic can coordinate readers without coupling to file format details.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from pathlib import Path
from typing import Dict, Optional, Any

import pandas as pd


class StreamReaderDAO(ABC):
    """DAO contract for loading external stream files into tabular structures."""

    @abstractmethod
    def read(self, source_path: str, options: Optional[Dict[str, Any]] = None) -> Any:
        """Read input data from disk and return a DataFrame-like object."""


class CsvStreamReader(StreamReaderDAO):
    """CSV stream reader DAO for raw export ingestion."""

    def read(self, source_path: str, options: Optional[Dict[str, Any]] = None) -> Any:
        """Load CSV content using caller-provided pandas parser options."""
        path = _validate_source_path(source_path)
        return pd.read_csv(path, **_normalize_options(options))


class JsonStreamReader(StreamReaderDAO):
    """JSON stream reader DAO for newline-delimited or standard JSON payloads."""

    def read(self, source_path: str, options: Optional[Dict[str, Any]] = None) -> Any:
        """Load JSON content using caller-provided pandas parser options."""
        path = _validate_source_path(source_path)
        return pd.read_json(path, **_normalize_options(options))


def _validate_source_path(source_path: str) -> Path:
    """Return a readable file path or raise a focused input error."""
    if not isinstance(source_path, (str, Path)):
        raise TypeError("source_path must be a string or pathlib.Path")

    path = Path(source_path)
    if not path.is_file():
        raise FileNotFoundError(f"Source file does not exist: {path}")
    return path


def _normalize_options(options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Copy parser options so readers never mutate controller-owned input."""
    if options is None:
        return {}
    if not isinstance(options, Mapping):
        raise TypeError("reader options must be a mapping")
    return dict(options)
