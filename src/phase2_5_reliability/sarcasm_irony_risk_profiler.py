"""Rule-based sarcasm/irony indicators that remain explicit proxies."""

from __future__ import annotations

import pandas as pd


class SarcasmIronyRiskProfiler:
    """Expose heuristic evidence without asserting confirmed sarcasm."""

    MARKERS = r"\b(yeah right|sure jan|totally|as always|great job|nice job|lol|lmao|smh)\b"

    def __init__(self, text_column: str = "tweet") -> None:
        self.text_column = text_column

    def profile(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        text = dataframe[self.text_column].fillna("").astype(str)
        result = pd.DataFrame(index=dataframe.index)
        marker = text.str.count(self.MARKERS, flags=2)
        eye_roll = text.str.contains("🙄", regex=False, na=False)
        quoted_positive = text.str.contains(r'["“”](?:great|genius|leader|honest)["“”]', case=False, regex=True, na=False)
        contrast = text.str.contains(r"\b(?:but|however|yeah right)\b", case=False, regex=True, na=False)
        result["sarcasm_marker_count"] = marker
        result["rule_based_sarcasm_indicator"] = (
            (marker.gt(0).astype(float) + eye_roll.astype(float) + quoted_positive.astype(float) + contrast.astype(float)) / 4.0
        ).clip(0, 1)
        result["sarcasm_evidence_available"] = True
        result["sarcasm_irony_risk"] = result["rule_based_sarcasm_indicator"]
        result["sarcasm_proxy_note"] = "heuristic proxy; not confirmed sarcasm"
        return result
