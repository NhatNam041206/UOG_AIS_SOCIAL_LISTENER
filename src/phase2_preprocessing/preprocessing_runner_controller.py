"""Controller for the ordered Phase 2 preprocessing workflow."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from .cleaning_heuristics_model import (
    BotFilter,
    CleaningPolicy,
    DuplicateFilter,
    TextCleaner,
)
from .telemetry_reporter_view import TelemetryReporterView
from ..shared.pipeline_orchestrator_controller import (
    BasePipelineOrchestrator,
    PipelineControllerError,
)


class PreprocessingRunnerController(BasePipelineOrchestrator):
    """Apply bot filtering, exact deduplication, and conservative text cleaning."""

    def __init__(
        self,
        telemetry_reporter: TelemetryReporterView,
        policy: Optional[CleaningPolicy] = None,
        text_cleaner: Optional[TextCleaner] = None,
    ) -> None:
        super().__init__()
        self._telemetry_reporter = telemetry_reporter
        self._policy = policy or CleaningPolicy()
        self._text_cleaner = text_cleaner or TextCleaner()
        self._bot_filter = BotFilter(self._policy)
        self._duplicate_filter = DuplicateFilter()

    def execute(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run preprocessing passes over records and return independent dictionaries."""
        if not isinstance(records, list) or not all(isinstance(record, dict) for record in records):
            raise TypeError("records must be a list of dictionaries")
        if not records:
            self._telemetry_reporter.reset()
            for stage_name in ("bot_filter", "exact_duplicate_filter", "text_cleaning"):
                self._telemetry_reporter.record_stage(stage_name, 0, 0)
            return []
        dataframe = pd.DataFrame(records)
        return self.execute_dataframe(dataframe).to_dict(orient="records")

    def execute_dataframe(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Run vectorized preprocessing while preserving the input column schema."""
        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError("dataframe must be a pandas DataFrame")
        self._telemetry_reporter.reset()
        return self._apply_cleaning_passes(dataframe.copy())

    def handle_exception(self, error: Exception) -> Any:
        """Wrap preprocessing failures in the shared controller error type."""
        raise PipelineControllerError(f"Phase 2 preprocessing failed: {error}") from error

    def _apply_cleaning_passes(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Apply documented rules in a deterministic, auditable sequence."""
        current = self._apply_mask("bot_filter", dataframe, self._bot_filter.retained_mask(dataframe))
        current = self._apply_mask(
            "exact_duplicate_filter",
            current,
            self._duplicate_filter.retained_mask(current, self._policy.text_key),
        )

        initial_count = len(current)
        current[self._policy.text_key] = current[self._policy.text_key].map(self._text_cleaner.clean)
        valid_mask = current[self._policy.text_key].map(self._text_cleaner.is_valid)
        current = current.loc[valid_mask].copy()
        self._telemetry_reporter.record_stage("text_cleaning", initial_count, len(current))
        return current.reset_index(drop=True)

    def _apply_mask(
        self,
        stage_name: str,
        dataframe: pd.DataFrame,
        retained_mask: pd.Series,
    ) -> pd.DataFrame:
        initial_count = len(dataframe)
        retained = dataframe.loc[retained_mask].copy()
        self._telemetry_reporter.record_stage(stage_name, initial_count, len(retained))
        return retained
