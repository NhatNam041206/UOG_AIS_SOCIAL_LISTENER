"""Deterministic proportional sampling for Phase 3 model validation."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Tuple

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class StratifiedSampleResult:
    """Complete reproducible output from one stratified sampling operation."""

    sample: pd.DataFrame
    allocation: pd.DataFrame
    checksum_sha256: str


class ValidationSampler:
    """Create a proportional random sample across candidate and UTC-day strata."""

    SOURCE_ROW_COLUMN = "validation_source_row"
    UTC_DAY_COLUMN = "validation_utc_day"

    def __init__(
        self,
        sample_size: int = 5_000,
        random_seed: int = 2020,
        candidate_key: str = "candidate",
        timestamp_key: str = "date",
    ) -> None:
        if sample_size <= 0:
            raise ValueError("sample_size must be positive")
        self.sample_size = sample_size
        self.random_seed = random_seed
        self.candidate_key = candidate_key
        self.timestamp_key = timestamp_key

    def sample(self, dataframe: pd.DataFrame) -> StratifiedSampleResult:
        """Return a deterministic proportional sample and allocation audit."""
        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError("dataframe must be a pandas DataFrame")
        self._require_columns(dataframe)
        if self.sample_size > len(dataframe):
            raise ValueError("sample_size cannot exceed the number of records")
        if dataframe.empty:
            raise ValueError("dataframe must not be empty")

        working = dataframe.copy()
        if self.SOURCE_ROW_COLUMN in working.columns or self.UTC_DAY_COLUMN in working.columns:
            raise ValueError("validation sampling columns already exist")
        dates = pd.to_datetime(working[self.timestamp_key], utc=True, errors="coerce")
        if dates.isna().any():
            raise ValueError("timestamp column contains invalid values")
        if working[self.candidate_key].isna().any():
            raise ValueError("candidate column contains missing values")
        working[self.SOURCE_ROW_COLUMN] = np.arange(len(working), dtype=np.int64)
        working[self.UTC_DAY_COLUMN] = dates.dt.floor("D")

        allocation = self._allocate(working)
        rng = np.random.default_rng(self.random_seed)
        selected_rows = []
        grouped = working.groupby(
            [self.candidate_key, self.UTC_DAY_COLUMN],
            sort=True,
            observed=True,
        )
        for row in allocation.itertuples(index=False):
            key: Tuple[object, object] = (
                getattr(row, self.candidate_key),
                getattr(row, self.UTC_DAY_COLUMN),
            )
            group = grouped.get_group(key)
            chosen = rng.choice(
                group[self.SOURCE_ROW_COLUMN].to_numpy(),
                size=int(row.allocated_records),
                replace=False,
            )
            selected_rows.extend(chosen.tolist())

        sample = working.iloc[sorted(selected_rows)].reset_index(drop=True)
        checksum = self.checksum(sample[self.SOURCE_ROW_COLUMN])
        return StratifiedSampleResult(sample=sample, allocation=allocation, checksum_sha256=checksum)

    def _allocate(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        counts = (
            dataframe.groupby(
                [self.candidate_key, self.UTC_DAY_COLUMN],
                sort=True,
                observed=True,
            )
            .size()
            .rename("source_records")
            .reset_index()
        )
        counts["exact_allocation"] = counts["source_records"] / len(dataframe) * self.sample_size
        counts["allocated_records"] = np.floor(counts["exact_allocation"]).astype(int)
        counts["fractional_remainder"] = counts["exact_allocation"] - counts["allocated_records"]
        remaining = self.sample_size - int(counts["allocated_records"].sum())
        priority = counts.sort_values(
            ["fractional_remainder", self.candidate_key, self.UTC_DAY_COLUMN],
            ascending=[False, True, True],
        ).index[:remaining]
        counts.loc[priority, "allocated_records"] += 1
        counts["source_share_pct"] = 100.0 * counts["source_records"] / len(dataframe)
        counts["sample_share_pct"] = 100.0 * counts["allocated_records"] / self.sample_size
        return counts.sort_values([self.candidate_key, self.UTC_DAY_COLUMN]).reset_index(drop=True)

    @staticmethod
    def checksum(source_rows: pd.Series) -> str:
        """Return a stable checksum for selected source-row positions."""
        values = [int(value) for value in source_rows]
        payload = json.dumps(values, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def _require_columns(self, dataframe: pd.DataFrame) -> None:
        missing = [
            column
            for column in (self.candidate_key, self.timestamp_key)
            if column not in dataframe.columns
        ]
        if missing:
            raise ValueError(f"Required sampling columns are missing: {missing}")

