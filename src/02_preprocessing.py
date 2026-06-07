"""Phase 2 preprocessing module for bot filtering and text cleaning."""

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
