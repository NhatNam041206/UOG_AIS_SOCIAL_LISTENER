"""Define view-layer serializers for persisted outputs and ingestion observability.

This module encapsulates Parquet write operations and ingestion metrics presentation
to keep persistence and reporting concerns out of model and controller classes.
"""

from __future__ import annotations

from typing import List, Dict, Optional, Any


class StorageSerializersView:
    """View component responsible for persistence formatting and ingestion metrics."""

    def serialize_to_parquet(self, dataframe: Any, destination_path: str) -> None:
        """Persist a DataFrame-like object to parquet format at destination_path."""
        raise NotImplementedError

    def log_ingestion_baseline_metrics(
        self,
        total_records: int,
        retained_records: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build and log baseline ingestion metrics for auditability."""
        raise NotImplementedError
