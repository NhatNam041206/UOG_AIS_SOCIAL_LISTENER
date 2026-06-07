#!/usr/bin/env python3
"""Create the baseline 2020 election sentiment project structure."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path("./")

DIRECTORIES = [
    PROJECT_ROOT / "data" / "01_raw",
    PROJECT_ROOT / "data" / "02_interim",
    PROJECT_ROOT / "data" / "03_processed",
    PROJECT_ROOT / "src" / "utils",
    PROJECT_ROOT / "notebooks",
]

FILES = {
    PROJECT_ROOT / ".gitignore": '''# Python cache and virtual environments
__pycache__/
*.py[cod]
venv/

# Data artifacts
data/**
!data/.gitkeep

# Notebook metadata
notebooks/.ipynb_checkpoints/
''',
    PROJECT_ROOT / "requirements.txt": '''pandas>=1.5.0,<3.0.0
numpy>=1.24.0,<3.0.0
vaderSentiment>=3.3.2,<4.0.0
transformers>=4.30.0,<5.0.0
statsmodels>=0.14.0,<1.0.0
scikit-learn>=1.3.0,<2.0.0
pyarrow>=14.0.0,<20.0.0
''',
    PROJECT_ROOT / "README.md": '''# 2020 Election Sentiment Analysis

A modular, object-oriented baseline for a 5-phase sentiment analysis pipeline over 2020 election-related data.

## Manual setup

1. Create and activate a virtual environment:
   - `python -m venv venv`
   - `source venv/bin/activate` (Linux/macOS) or `venv/Scripts/activate` (Windows)
2. Install dependencies:
   - `pip install -r requirements.txt`
''',
    PROJECT_ROOT / "data" / ".gitkeep": "",
    PROJECT_ROOT / "src" / "__init__.py": '"""Core package for the election sentiment pipeline."""\n',
    PROJECT_ROOT / "src" / "utils" / "__init__.py": '"""Utility helpers shared across all pipeline phases."""\n',
    PROJECT_ROOT / "src" / "utils" / "helpers.py": '''"""Utility helpers for cross-phase concerns such as timezone alignment."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def align_timestamp_timezone(timestamp: datetime, timezone: str) -> datetime:
    """Normalize a timestamp to the provided timezone."""
    try:
        target_tz = ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown timezone: {timezone}") from exc

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=ZoneInfo("UTC"))
    return timestamp.astimezone(target_tz)
''',
    PROJECT_ROOT / "src" / "01_ingestion.py": '''"""Phase 1 ingestion module for abstract and concrete data source loaders."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseIngestion(ABC):
    """Base interface for ingestion implementations."""

    @abstractmethod
    def load(self, source: Path) -> Any:
        """Load source records into a structured in-memory representation."""


class TwitterIngestion(BaseIngestion):
    """Example ingestion class for raw Twitter exports."""

    def load(self, source: Path) -> Any:
        raise NotImplementedError
''',
    PROJECT_ROOT / "src" / "02_preprocessing.py": '''"""Phase 2 preprocessing module for bot filtering and text cleaning."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PreprocessingConfig:
    """Configuration options for preprocessing heuristics."""

    remove_bots: bool = True
    normalize_text: bool = True


class Preprocessor:
    """Apply deterministic preprocessing to ingested social content."""

    def run(self, records: list[dict]) -> list[dict]:
        raise NotImplementedError
''',
    PROJECT_ROOT / "src" / "03_sentiment.py": '''"""Phase 3 sentiment module for lexicon scoring and validation steps."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SentimentScore:
    """Container for sentiment score outputs."""

    compound: float


class SentimentAnalyzer:
    """Compute and validate sentiment signals from cleaned text."""

    def analyze(self, text: str) -> SentimentScore:
        raise NotImplementedError
''',
    PROJECT_ROOT / "src" / "04_aggregation.py": '''"""Phase 4 aggregation module for spatial and temporal feature matrices."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AggregationWindow:
    """Aggregation granularity settings."""

    frequency: str = "D"


class Aggregator:
    """Group sentiment signals into analytical matrices."""

    def build(self, records: list[dict]) -> list[dict]:
        raise NotImplementedError
''',
    PROJECT_ROOT / "src" / "05_modeling.py": '''"""Phase 5 modeling module for statistical and regression workflows."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModelingConfig:
    """High-level modeling options."""

    target_column: str = "sentiment"


class ModelEngine:
    """Train and evaluate downstream election sentiment models."""

    def train(self, features: list[dict]) -> None:
        raise NotImplementedError
''',
}


def create_structure() -> None:
    """Create all required directories and files."""
    for directory in DIRECTORIES:
        directory.mkdir(parents=True, exist_ok=True)

    for file_path, content in FILES.items():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    create_structure()
    print(f"Created baseline structure under: {PROJECT_ROOT}")
