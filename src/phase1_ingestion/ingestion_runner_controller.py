"""Define the phase 1 controller that orchestrates stream reading and normalization.

This controller-layer module coordinates reader DAOs, shared schema mapping, and
UTC timestamp conversion to prepare canonical interim datasets for preprocessing.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Iterator, List, Dict, Optional, Any, Literal

import pandas as pd

from .stream_readers_model import StreamReaderDAO
from ..shared.data_interfaces_model import SchemaMapperInterface
from ..shared.pipeline_orchestrator_controller import (
    BasePipelineOrchestrator,
    PipelineControllerError,
)


class IngestionRunnerController(BasePipelineOrchestrator):
    """Master loop for source ingestion, schema mapping, and UTC normalization."""

    def __init__(
        self,
        reader: StreamReaderDAO,
        schema_mapper: Optional[SchemaMapperInterface] = None,
    ) -> None:
        super().__init__()
        self._reader: StreamReaderDAO = reader
        self._schema_mapper: Optional[SchemaMapperInterface] = schema_mapper

    def execute(self, source_path: str, options: Optional[Dict[str, Any]] = None) -> Any:
        """Read a source and apply caller-configured mapping, projection, and UTC conversion.

        Supported service options:
        - ``reader_options``: options forwarded to the configured stream reader.
        - ``fields``: output columns retained after optional schema mapping.
        - ``timestamp_columns``: one column name or a sequence converted to UTC.
        - ``timestamp_errors``: pandas conversion behavior; defaults to ``"raise"``.
        """
        service_options = self._normalize_service_options(options)
        dataframe = self._reader.read(source_path, service_options["reader_options"])
        self._validate_dataframe(dataframe)
        return self._transform_dataframe(dataframe, service_options)

    def execute_batches(
        self,
        source_path: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Iterator[pd.DataFrame]:
        """Yield transformed DataFrame batches from a streaming-capable reader."""
        if not hasattr(self._reader, "iter_batches"):
            raise TypeError("configured stream reader does not support batch ingestion")

        service_options = self._normalize_service_options(options)
        for dataframe in self._reader.iter_batches(  # type: ignore[attr-defined]
            source_path,
            service_options["reader_options"],
        ):
            self._validate_dataframe(dataframe)
            yield self._transform_dataframe(dataframe, service_options)

    def _transform_dataframe(
        self,
        dataframe: pd.DataFrame,
        service_options: Dict[str, Any],
    ) -> pd.DataFrame:
        """Apply controller-owned mapping, renaming, constants, projection, and UTC."""
        if self._schema_mapper is not None:
            dataframe = pd.DataFrame(self._map_records(dataframe.to_dict(orient="records")))

        if service_options["rename_fields"]:
            dataframe = dataframe.rename(columns=service_options["rename_fields"])
        for field, value in service_options["constant_fields"].items():
            dataframe[field] = value
        dataframe = self._select_fields(dataframe, service_options["fields"])
        for timestamp_column in service_options["timestamp_columns"]:
            dataframe = self._convert_timestamps_to_utc(
                dataframe,
                timestamp_column,
                errors=service_options["timestamp_errors"],
            )
        return dataframe

    def handle_exception(self, error: Exception) -> Any:
        """Handle ingestion failures with phase-specific logging or re-raising."""
        raise PipelineControllerError(f"Phase 1 ingestion failed: {error}") from error

    def _map_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply shared schema mapping across all raw records."""
        if self._schema_mapper is None:
            return records
        return [self._schema_mapper.map_record(record) for record in records]

    def _convert_timestamps_to_utc(
        self,
        dataframe: Any,
        timestamp_column: str,
        errors: Literal["raise", "coerce"] = "raise",
    ) -> Any:
        """Normalize timestamp column values to UTC timezone semantics."""
        if timestamp_column not in dataframe.columns:
            raise ValueError(f"Timestamp column is missing: {timestamp_column}")

        converted = dataframe.copy()
        converted[timestamp_column] = pd.to_datetime(
            converted[timestamp_column],
            utc=True,
            errors=errors,
        )
        return converted

    def _select_fields(self, dataframe: Any, fields: Optional[List[str]]) -> Any:
        """Retain caller-selected output fields without embedding a fixed schema."""
        if fields is None:
            return dataframe

        missing_fields = [field for field in fields if field not in dataframe.columns]
        if missing_fields:
            raise ValueError(f"Requested fields are missing: {missing_fields}")
        return dataframe.loc[:, fields].copy()

    def _normalize_service_options(
        self,
        options: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Validate and normalize controller-owned ingestion options."""
        if options is None:
            options = {}
        if not isinstance(options, Mapping):
            raise TypeError("ingestion options must be a mapping")

        supported_options = {
            "reader_options",
            "fields",
            "rename_fields",
            "constant_fields",
            "timestamp_columns",
            "timestamp_errors",
        }
        unknown_options = set(options) - supported_options
        if unknown_options:
            raise ValueError(f"Unsupported ingestion options: {sorted(unknown_options)}")

        reader_options = options.get("reader_options", {})
        if not isinstance(reader_options, Mapping):
            raise TypeError("reader_options must be a mapping")
        rename_fields = options.get("rename_fields", {})
        if not isinstance(rename_fields, Mapping):
            raise TypeError("rename_fields must be a mapping")
        constant_fields = options.get("constant_fields", {})
        if not isinstance(constant_fields, Mapping):
            raise TypeError("constant_fields must be a mapping")

        fields = self._normalize_column_names(options.get("fields"), "fields")
        timestamp_columns = self._normalize_column_names(
            options.get("timestamp_columns"),
            "timestamp_columns",
        ) or []

        timestamp_errors = options.get("timestamp_errors", "raise")
        if timestamp_errors not in {"raise", "coerce"}:
            raise ValueError('timestamp_errors must be either "raise" or "coerce"')

        return {
            "reader_options": dict(reader_options),
            "fields": fields,
            "rename_fields": dict(rename_fields),
            "constant_fields": dict(constant_fields),
            "timestamp_columns": timestamp_columns,
            "timestamp_errors": timestamp_errors,
        }

    @staticmethod
    def _normalize_column_names(value: Any, option_name: str) -> Optional[List[str]]:
        """Normalize one-or-many column names into a list."""
        if value is None:
            return None
        if isinstance(value, str):
            return [value]
        if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
            raise TypeError(f"{option_name} must be a column name or a sequence of names")

        names = list(value)
        if not all(isinstance(name, str) and name for name in names):
            raise TypeError(f"{option_name} must contain non-empty strings")
        if len(names) != len(set(names)):
            raise ValueError(f"{option_name} must not contain duplicate names")
        return names

    @staticmethod
    def _validate_dataframe(dataframe: Any) -> None:
        """Enforce the DataFrame return contract at the service boundary."""
        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError("stream reader must return a pandas DataFrame")
