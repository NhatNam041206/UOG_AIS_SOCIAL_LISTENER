# Module: ingestion_runner_controller

## Architectural Role
Controller boundary for ingestion and normalization flow.

## Core Functional Objective
Acts as the Phase 1 service layer. It reads a raw stream, optionally maps its records,
selects caller-requested output fields, and converts caller-requested timestamps to UTC.
No source-specific fields are fixed in the controller.

## Class and Method Signatures
* `IngestionRunnerController`: Master loop for source ingestion, schema mapping, and UTC normalization.
  * `__init__(self, reader: StreamReaderDAO, schema_mapper: Optional[SchemaMapperInterface] = None) -> None`: Configure a format reader and an optional source-specific schema mapper.
  * `execute(self, source_path: str, options: Optional[Dict[str, Any]] = None) -> Any`: Run ingestion using caller-provided reader and transformation options.
  * `handle_exception(self, error: Exception) -> Any`: Handle ingestion failures with phase-specific logging or re-raising.
  * `_map_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]`: Apply shared schema mapping across all raw records.
  * `_convert_timestamps_to_utc(self, dataframe: Any, timestamp_column: str, errors: str = "raise") -> Any`: Normalize timestamp column values to UTC timezone semantics.

## Service Options

- `reader_options`: Mapping forwarded unchanged to the configured stream reader.
- `fields`: Optional output fields retained after schema mapping.
- `timestamp_columns`: Optional field name or sequence of fields converted to UTC.
- `timestamp_errors`: Timestamp conversion behavior, either `raise` or `coerce`.

The processing order is read, optional schema mapping, field projection, then UTC
normalization. Parser-level projection remains available through reader options such as
the CSV reader's `usecols` when early projection is desirable.
