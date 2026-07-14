"""Separated exact, normalized, and near-duplicate amplification proxies."""

from __future__ import annotations

import hashlib

import pandas as pd

from .risk_score_normalizer import RiskScoreNormalizer


def normalize_text(series: pd.Series) -> pd.Series:
    result = series.fillna("").astype(str).str.lower()
    result = result.str.replace(r"https?://\S+|www\.\S+", " ", regex=True)
    result = result.str.replace(r"@\w+", "@user", regex=True)
    return result.str.replace(r"\s+", " ", regex=True).str.strip()


def stable_hash(series: pd.Series) -> pd.Series:
    return series.astype(str).map(lambda value: hashlib.sha256(value.encode("utf-8")).hexdigest())


def repetition_risk(counts: pd.Series) -> pd.Series:
    """Map no repetition (count one) to zero and rank only repeated cases."""
    numeric = pd.to_numeric(counts, errors="coerce")
    result = pd.Series(0.0, index=counts.index, dtype="float64").where(numeric.notna())
    repeated = numeric.gt(1)
    if repeated.any():
        result.loc[repeated] = RiskScoreNormalizer.percentile_rank(numeric.loc[repeated])
    return result


class DuplicateAmplificationProfiler:
    """Describe repetition while avoiding coordination or spam conclusions."""

    def __init__(self, text_column: str = "tweet", user_column: str = "user_id", signature_length: int = 160) -> None:
        self.text_column = text_column
        self.user_column = user_column
        self.signature_length = signature_length

    def profile(self, dataframe: pd.DataFrame, phase2_exact_duplicates_removed: int) -> pd.DataFrame:
        text = dataframe[self.text_column].fillna("").astype(str)
        normalized = normalize_text(text)
        near_signature = (
            normalized.str.replace(r"#\w+", "#tag", regex=True)
            .str.replace(r"\d+", "0", regex=True)
            .str.slice(0, self.signature_length)
        )
        exact_counts = text.value_counts(dropna=False)
        normalized_counts = normalized.value_counts(dropna=False)
        near_counts = near_signature.value_counts(dropna=False)
        users = dataframe[self.user_column].astype("string").fillna("__MISSING_USER_ID__")
        cross_users = pd.DataFrame({"normalized": normalized, "user": users}).groupby("normalized")["user"].nunique()
        result = pd.DataFrame(index=dataframe.index)
        result["phase2_exact_duplicates_removed"] = int(phase2_exact_duplicates_removed)
        result["post_clean_exact_duplicate_count"] = text.map(exact_counts).astype(int)
        result["normalized_repetition_count"] = normalized.map(normalized_counts).astype(int)
        result["near_duplicate_cluster_id"] = stable_hash(near_signature)
        result["near_duplicate_cluster_size"] = near_signature.map(near_counts).astype(int)
        result["cross_user_repetition_count"] = normalized.map(cross_users).astype(int)
        result["near_duplicate_evidence_type"] = "lexical signature proxy; not confirmed coordination"
        component = pd.DataFrame(index=dataframe.index)
        for column in (
            "post_clean_exact_duplicate_count", "normalized_repetition_count",
            "near_duplicate_cluster_size", "cross_user_repetition_count",
        ):
            component[column] = repetition_risk(result[column])
        result["duplicate_amplification_risk"] = RiskScoreNormalizer.available_mean(component, list(component.columns))
        return result
