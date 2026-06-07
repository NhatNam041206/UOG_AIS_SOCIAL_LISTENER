# Module: storage_serializers_view

## Architectural Role
View boundary for persistence formatting and ingestion telemetry.

## Core Functional Objective
Serializes tabular outputs and publishes ingestion metrics for observability.

## Class and Method Signatures
* `StorageSerializersView`: View component responsible for persistence formatting and ingestion metrics.
  * `serialize_to_parquet(self, dataframe: Any, destination_path: str) -> None`: Persist a DataFrame-like object to parquet format at destination_path.
  * `log_ingestion_baseline_metrics(self, total_records: int, retained_records: int, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]`: Build and log baseline ingestion metrics for auditability.
