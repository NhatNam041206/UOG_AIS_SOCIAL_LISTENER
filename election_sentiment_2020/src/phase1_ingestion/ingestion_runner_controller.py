"""Define the phase 1 controller that orchestrates stream reading and normalization.

This controller-layer module coordinates reader DAOs, shared schema mapping, and
UTC timestamp conversion to prepare canonical interim datasets for preprocessing.
"""

from __future__ import annotations

from typing import List, Dict, Optional, Any

from .stream_readers_model import StreamReaderDAO
from ..shared.data_interfaces_model import SchemaMapperInterface
from ..shared.pipeline_orchestrator_controller import BasePipelineOrchestrator


class IngestionRunnerController(BasePipelineOrchestrator):
    """Master loop for source ingestion, schema mapping, and UTC normalization."""

    def __init__(self, reader: StreamReaderDAO, schema_mapper: SchemaMapperInterface) -> None:
        super().__init__()
        self._reader: StreamReaderDAO = reader
        self._schema_mapper: SchemaMapperInterface = schema_mapper

    def execute(self, source_path: str, options: Optional[Dict[str, Any]] = None) -> Any:
        """Run ingestion by reading raw streams, mapping schema, and normalizing UTC."""
        raise NotImplementedError

    def handle_exception(self, error: Exception) -> Any:
        """Handle ingestion failures with phase-specific logging or re-raising."""
        raise NotImplementedError

    def _map_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply shared schema mapping across all raw records."""
        raise NotImplementedError

    def _convert_timestamps_to_utc(self, dataframe: Any, timestamp_column: str) -> Any:
        """Normalize timestamp column values to UTC timezone semantics."""
        raise NotImplementedError
