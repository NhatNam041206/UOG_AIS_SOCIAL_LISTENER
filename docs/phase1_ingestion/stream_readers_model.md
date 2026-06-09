# Module: stream_readers_model

## Architectural Role
Model boundary for source-reader abstractions.

## Core Functional Objective
Abstracts CSV and JSON stream loading behind a DAO contract without embedding fixed
field-selection or transformation policy. Each concrete reader forwards caller-provided
options to the corresponding pandas parser.

## Class and Method Signatures
* `StreamReaderDAO`: DAO contract for loading external stream files into tabular structures.
  * `read(self, source_path: str, options: Optional[Dict[str, Any]] = None) -> Any`: Read input data from disk and return a DataFrame-like object.
* `CsvStreamReader`: CSV stream reader DAO for raw export ingestion.
  * `read(self, source_path: str, options: Optional[Dict[str, Any]] = None) -> Any`: Validate the source file and load CSV content using caller-provided `pandas.read_csv` options.
* `JsonStreamReader`: JSON stream reader DAO for newline-delimited or standard JSON payloads.
  * `read(self, source_path: str, options: Optional[Dict[str, Any]] = None) -> Any`: Validate the source file and load JSON content using caller-provided `pandas.read_json` options, including `lines=True` for JSONL.

## Design Boundary

Readers own file-format parsing only. Field projection, schema mapping, and timestamp
normalization belong to `IngestionRunnerController`.
