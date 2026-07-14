"""Configuration and dataframe contract validation for Phase 2.5."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pandas as pd


VALID_MODES = {"smoke", "sample", "full"}


def load_reliability_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_reliability_config(config)
    return config


def validate_reliability_config(config: dict[str, Any]) -> None:
    required_sections = {"inputs", "columns", "execution", "outputs", "provenance"}
    missing = sorted(required_sections - set(config))
    if missing:
        raise ValueError(f"Missing Phase 2.5 configuration sections: {missing}")
    execution = config["execution"]
    if execution.get("mode") not in VALID_MODES:
        raise ValueError("execution.mode must be smoke, sample, or full")
    if execution.get("execute_mitigation") is not False:
        raise ValueError("Phase 2.5 rejects mitigation; execute_mitigation must be false")
    if int(execution.get("seed", -1)) < 0:
        raise ValueError("execution.seed must be a non-negative integer")
    required_inputs = config["inputs"].get("required", {})
    expected = {
        "sentiment_tweets", "user_activity_metrics", "user_activity_threshold_audit",
        "roberta_validation_sample", "political_events",
    }
    missing_inputs = sorted(expected - set(required_inputs))
    if missing_inputs:
        raise ValueError(f"Missing required input declarations: {missing_inputs}")


def with_execution_overrides(
    config: dict[str, Any],
    mode: str | None = None,
    seed: int | None = None,
) -> dict[str, Any]:
    updated = deepcopy(config)
    if mode is not None:
        updated["execution"]["mode"] = mode
    if seed is not None:
        updated["execution"]["seed"] = seed
    validate_reliability_config(updated)
    return updated


class DatasetSchemaProfiler:
    """Validate canonical columns while documenting optional evidence."""

    def __init__(self, columns: dict[str, str]) -> None:
        self.columns = columns

    def profile(self, dataframe: pd.DataFrame) -> dict[str, Any]:
        required_keys = ("tweet_id", "text", "timestamp", "user_id", "candidate")
        required_columns = [self.columns[key] for key in required_keys]
        missing = sorted(set(required_columns) - set(dataframe.columns))
        if missing:
            raise ValueError(f"Required Phase 2.5 columns are missing: {missing}")
        optional = {"user_location": self.columns.get("user_location")}
        return {
            "row_count": int(len(dataframe)),
            "columns": {column: str(dtype) for column, dtype in dataframe.dtypes.items()},
            "required_columns": required_columns,
            "missing_optional_columns": [
                value for value in optional.values() if value and value not in dataframe.columns
            ],
        }
