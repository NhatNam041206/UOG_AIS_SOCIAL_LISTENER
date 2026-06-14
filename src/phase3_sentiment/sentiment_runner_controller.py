"""Controller for schema-preserving Phase 3 sentiment scoring."""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from .sentiment_models_model import VaderSentimentModel
from ..shared.pipeline_orchestrator_controller import (
    BasePipelineOrchestrator,
    PipelineControllerError,
)


class SentimentRunnerController(BasePipelineOrchestrator):
    """Apply an injected sentiment model while preserving source fields."""

    VADER_COLUMNS = (
        "vader_negative",
        "vader_neutral",
        "vader_positive",
        "vader_compound",
        "vader_label",
    )

    def __init__(
        self,
        model: VaderSentimentModel | None = None,
        text_key: str = "tweet",
    ) -> None:
        super().__init__()
        self._model = model or VaderSentimentModel()
        self._text_key = text_key

    def execute(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Score record dictionaries without mutating the input list."""
        if not isinstance(records, list) or not all(isinstance(record, dict) for record in records):
            raise TypeError("records must be a list of dictionaries")
        return self.execute_dataframe(pd.DataFrame(records)).to_dict(orient="records")

    def execute_dataframe(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Return a copy with the approved VADER output fields appended."""
        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError("dataframe must be a pandas DataFrame")
        if self._text_key not in dataframe.columns:
            raise ValueError(f"Required sentiment column is missing: {self._text_key}")
        conflicts = [column for column in self.VADER_COLUMNS if column in dataframe.columns]
        if conflicts:
            raise ValueError(f"VADER output columns already exist: {conflicts}")
        if dataframe.empty:
            result = dataframe.copy()
            for column in self.VADER_COLUMNS:
                result[column] = pd.Series(dtype="string" if column == "vader_label" else "float64")
            return result

        invalid = dataframe[self._text_key].isna() | dataframe[self._text_key].astype("string").str.strip().eq("")
        if invalid.any():
            raise ValueError(f"VADER input contains {int(invalid.sum())} missing or blank text values")

        result = dataframe.copy()
        scores = pd.DataFrame(self._model.score_many(result[self._text_key].tolist()), index=result.index)
        for column in self.VADER_COLUMNS:
            result[column] = scores[column]
        return result

    def handle_exception(self, error: Exception) -> Any:
        """Wrap sentiment failures in the shared controller error type."""
        raise PipelineControllerError(f"Phase 3 VADER scoring failed: {error}") from error

