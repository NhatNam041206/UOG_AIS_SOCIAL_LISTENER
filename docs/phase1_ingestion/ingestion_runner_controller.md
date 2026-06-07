# Module: ingestion_runner_controller

## Architectural Role
Controller boundary for ingestion and normalization flow.

## Core Functional Objective
Reads raw streams, maps them to the shared schema, and converts timestamps to UTC for downstream preprocessing.

## Class and Method Signatures
* `IngestionRunnerController`: Master loop for source ingestion, schema mapping, and UTC normalization.
  * `__init__(self, reader: StreamReaderDAO, schema_mapper: SchemaMapperInterface) -> None`: No docstring provided.
  * `execute(self, source_path: str, options: Optional[Dict[str, Any]] = None) -> Any`: Run ingestion by reading raw streams, mapping schema, and normalizing UTC.
  * `handle_exception(self, error: Exception) -> Any`: Handle ingestion failures with phase-specific logging or re-raising.
  * `_map_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]`: Apply shared schema mapping across all raw records.
  * `_convert_timestamps_to_utc(self, dataframe: Any, timestamp_column: str) -> Any`: Normalize timestamp column values to UTC timezone semantics.
