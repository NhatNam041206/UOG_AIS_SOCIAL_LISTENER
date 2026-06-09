"""Define view-layer serializers for persisted outputs and ingestion observability.

This module encapsulates Parquet write operations and ingestion metrics presentation
to keep persistence and reporting concerns out of model and controller classes.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Dict, Iterable, Optional, Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


class StorageSerializersView:
    """View component responsible for persistence formatting and ingestion metrics."""

    def serialize_to_parquet(self, dataframe: Any, destination_path: str) -> None:
        """Persist a DataFrame-like object to parquet format at destination_path."""
        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError("dataframe must be a pandas DataFrame")
        if not isinstance(destination_path, (str, Path)):
            raise TypeError("destination_path must be a string or pathlib.Path")

        path = Path(destination_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        dataframe.to_parquet(path, index=False)

    def serialize_batches_to_parquet(
        self,
        dataframes: Iterable[pd.DataFrame],
        destination_path: str,
    ) -> int:
        """Persist DataFrame batches to one Parquet file and return row count."""
        path = Path(destination_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        writer: Optional[pq.ParquetWriter] = None
        row_count = 0
        try:
            for dataframe in dataframes:
                if not isinstance(dataframe, pd.DataFrame):
                    raise TypeError("dataframe batches must contain pandas DataFrames")
                table = pa.Table.from_pandas(dataframe, preserve_index=False)
                if writer is None:
                    writer = pq.ParquetWriter(path, table.schema)
                writer.write_table(table)
                row_count += len(dataframe)
        finally:
            if writer is not None:
                writer.close()
        if writer is None:
            raise ValueError("at least one dataframe batch is required")
        return row_count

    def log_ingestion_baseline_metrics(
        self,
        total_records: int,
        retained_records: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build and log baseline ingestion metrics for auditability."""
        if total_records < 0 or retained_records < 0:
            raise ValueError("record counts must be non-negative")
        if retained_records > total_records:
            raise ValueError("retained_records cannot exceed total_records")
        if metadata is not None and not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping")

        metrics = {
            "total_records": total_records,
            "retained_records": retained_records,
            "dropped_records": total_records - retained_records,
            "retention_rate_pct": (
                0.0 if total_records == 0 else 100.0 * retained_records / total_records
            ),
        }
        if metadata:
            metrics["metadata"] = dict(metadata)

        print(metrics)
        return metrics
