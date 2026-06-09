"""Define model-layer DAOs for loading raw CSV and JSON streams into DataFrames.

This module isolates source-specific ingestion concerns behind abstract interfaces so
controller logic can coordinate readers without coupling to file format details.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from pathlib import Path
from typing import Dict, Iterator, Optional, Any

import pandas as pd
import pyarrow as pa
import pyarrow.csv as arrow_csv


class StreamReaderDAO(ABC):
    """DAO contract for loading external stream files into tabular structures."""

    @abstractmethod
    def read(self, source_path: str, options: Optional[Dict[str, Any]] = None) -> Any:
        """Read input data from disk and return a DataFrame-like object."""


class CsvStreamReader(StreamReaderDAO):
    """CSV stream reader DAO for raw export ingestion."""

    def __init__(self) -> None:
        self.invalid_row_count = 0

    def read(self, source_path: str, options: Optional[Dict[str, Any]] = None) -> Any:
        """Load CSV content using caller-provided pandas parser options."""
        path = _validate_source_path(source_path)
        return pd.read_csv(path, **_normalize_options(options))

    def iter_batches(
        self,
        source_path: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Iterator[pd.DataFrame]:
        """Yield Arrow-parsed CSV batches for large or imperfect source files."""
        path = _validate_source_path(source_path)
        parser_options = _normalize_options(options)
        columns = parser_options.pop("columns", None)
        block_size = int(parser_options.pop("block_size", 64 * 1024 * 1024))
        column_types = parser_options.pop("column_types", {})
        invalid_row_behavior = parser_options.pop("invalid_row_behavior", "error")
        newlines_in_values = bool(parser_options.pop("newlines_in_values", True))
        if parser_options:
            raise ValueError(
                f"Unsupported streaming CSV options: {sorted(parser_options)}"
            )
        if invalid_row_behavior not in {"skip", "error"}:
            raise ValueError('invalid_row_behavior must be either "skip" or "error"')

        self.invalid_row_count = 0

        def handle_invalid_row(row: Any) -> str:
            self.invalid_row_count += 1
            return invalid_row_behavior

        arrow_types = {
            name: _resolve_arrow_type(type_name)
            for name, type_name in dict(column_types).items()
        }
        reader = arrow_csv.open_csv(
            path,
            read_options=arrow_csv.ReadOptions(block_size=block_size),
            parse_options=arrow_csv.ParseOptions(
                invalid_row_handler=handle_invalid_row,
                newlines_in_values=newlines_in_values,
            ),
            convert_options=arrow_csv.ConvertOptions(
                include_columns=columns,
                column_types=arrow_types or None,
            ),
        )
        for batch in reader:
            yield batch.to_pandas()


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


def _resolve_arrow_type(type_name: Any) -> pa.DataType:
    """Resolve supported configuration-friendly Arrow type names."""
    if isinstance(type_name, pa.DataType):
        return type_name
    supported_types = {
        "string": pa.string(),
        "float64": pa.float64(),
        "int64": pa.int64(),
    }
    if type_name not in supported_types:
        raise ValueError(f"Unsupported Arrow column type: {type_name}")
    return supported_types[type_name]
