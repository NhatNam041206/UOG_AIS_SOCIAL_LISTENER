"""Phase 5: Advanced Statistical Modeling & Hypothesis Evaluation.

This module implements formal inferential statistical models to evaluate H1 and H2:
1. Hypothesis 1 (ITSA Segmented Regression): Evaluates immediate political event shocks
   (beta_2 step-change) and long-term decay (beta_3 slope-change) using segmented OLS:
   Y_t = beta_0 + beta_1 * T_t + beta_2 * D_t + beta_3 * (T_t * D_t) + epsilon_t

2. Hypothesis 2 (Stratified Spatial OLS Regression): Tests predictive validity of
   online state sentiment margins (X_i) against actual election vote margins (Y_i),
   controlling for state demographics (Z_ki):
   Y_i = beta_0 + beta_1 * X_i + sum(gamma_k * Z_ki) + epsilon_i
   Stratified by (1) National, (2) Battleground States, and (3) Safe Partisan States.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import statsmodels.api as sm


@dataclass(frozen=True)
class ITSAResult:
    """Interrupted Time Series Analysis outputs for one political event shock."""

    event_name: str
    beta_0_baseline: float
    beta_1_pre_slope: float
    beta_2_immediate_shock: float
    beta_3_post_slope_change: float
    p_value_immediate_shock: float
    p_value_post_slope_change: float
    r_squared: float
    summary_text: str


@dataclass(frozen=True)
class OLSSpatialResult:
    """OLS Spatial Regression output for a single data subgroup (National/Battleground/Safe)."""

    subgroup_name: str
    sample_size: int
    beta_1_sentiment_margin: float
    p_value_sentiment_margin: float
    r_squared: float
    adjusted_r_squared: float
    covariate_coefficients: Dict[str, float]
    summary_text: str


@dataclass(frozen=True)
class HypothesisEvaluationSummary:
    """Combined outputs for H1 and H2 statistical testing."""

    h1_itsa_results: List[ITSAResult]
    h2_national_ols: OLSSpatialResult
    h2_battleground_ols: Optional[OLSSpatialResult]
    h2_safe_ols: Optional[OLSSpatialResult]


class ITSAOLSEvaluator:
    """Evaluate H1 and H2 statistical equations with robust variance diagnostics."""

    def evaluate_h1_itsa(
        self,
        event_window_df: pd.DataFrame,
        event_name: str = "Campaign Event",
    ) -> ITSAResult:
        """Run Interrupted Time Series Analysis (ITSA) segmented regression on event timeline."""
        df = event_window_df.copy()
        required_cols = {"time_elapsed_hours", "post_event_dummy", "mean_sentiment"}
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns for ITSA: {missing}")

        df["interaction_term"] = df["time_elapsed_hours"] * df["post_event_dummy"]

        X = df[["time_elapsed_hours", "post_event_dummy", "interaction_term"]]
        X = sm.add_constant(X)
        y = df["mean_sentiment"]

        model = sm.OLS(y, X).fit(cov_type="HC1")

        params = model.params
        pvalues = model.pvalues

        return ITSAResult(
            event_name=event_name,
            beta_0_baseline=float(params.get("const", 0.0)),
            beta_1_pre_slope=float(params.get("time_elapsed_hours", 0.0)),
            beta_2_immediate_shock=float(params.get("post_event_dummy", 0.0)),
            beta_3_post_slope_change=float(params.get("interaction_term", 0.0)),
            p_value_immediate_shock=float(pvalues.get("post_event_dummy", 1.0)),
            p_value_post_slope_change=float(pvalues.get("interaction_term", 1.0)),
            r_squared=float(model.rsquared),
            summary_text=str(model.summary()),
        )

    def evaluate_h2_ols(
        self,
        spatial_df: pd.DataFrame,
        subgroup_name: str = "National",
        control_covariates: Optional[List[str]] = None,
    ) -> OLSSpatialResult:
        """Run cross-sectional OLS regression at US State level."""
        df = spatial_df.copy()

        # Auto-compute democratic margin if raw vote columns present
        if "democratic_margin_pct_2020" not in df.columns and "biden_votes" in df.columns and "trump_votes" in df.columns:
            df["democratic_margin_pct_2020"] = 100.0 * (df["biden_votes"] - df["trump_votes"]) / df["total_votes"]

        y_col = "democratic_margin_pct_2020"
        x_col = "state_sentiment_margin_Xi"

        if y_col not in df.columns or x_col not in df.columns:
            raise ValueError(f"Spatial DataFrame missing {y_col} or {x_col}. Available: {df.columns.tolist()}")

        controls = control_covariates or [
            "median_age",
            "median_income",
            "urbanization_index",
            "ba_education_pct",
            "hispanic_latino_pct",
        ]

        # Retain present controls
        available_controls = [col for col in controls if col in df.columns]

        predictors = [x_col] + available_controls
        clean_df = df.dropna(subset=[y_col] + predictors)

        if len(clean_df) < 5:
            raise ValueError(f"Insufficient observations for subgroup {subgroup_name}: {len(clean_df)}")

        X = sm.add_constant(clean_df[predictors])
        y = clean_df[y_col]

        model = sm.OLS(y, X).fit(cov_type="HC1")

        params = model.params
        pvalues = model.pvalues

        cov_coefs = {col: float(params.get(col, 0.0)) for col in available_controls}

        return OLSSpatialResult(
            subgroup_name=subgroup_name,
            sample_size=len(clean_df),
            beta_1_sentiment_margin=float(params.get(x_col, 0.0)),
            p_value_sentiment_margin=float(pvalues.get(x_col, 1.0)),
            r_squared=float(model.rsquared),
            adjusted_r_squared=float(model.rsquared_adj),
            covariate_coefficients=cov_coefs,
            summary_text=str(model.summary()),
        )

    def evaluate_all(
        self,
        event_windows_df: pd.DataFrame,
        spatial_matrix_df: pd.DataFrame,
        control_covariates: Optional[List[str]] = None,
    ) -> HypothesisEvaluationSummary:
        """Run complete Phase 5 inferential statistical evaluation for H1 and H2."""
        # H1: ITSA across events
        h1_results = []
        if not event_windows_df.empty and "event_name" in event_windows_df.columns:
            for event_name, group in event_windows_df.groupby("event_name"):
                if len(group) >= 10:
                    h1_results.append(self.evaluate_h1_itsa(group, str(event_name)))

        # H2: OLS across subgroups
        national_ols = self.evaluate_h2_ols(spatial_matrix_df, "National", control_covariates)

        battleground_df = spatial_matrix_df[
            spatial_matrix_df["historical_classification"] == "battleground"
        ]
        if len(battleground_df) >= 5:
            battleground_ols = self.evaluate_h2_ols(battleground_df, "Battleground_States", control_covariates)
        else:
            import warnings
            warnings.warn(
                f"Battleground N={len(battleground_df)} < 5; no regression run.",
                RuntimeWarning,
                stacklevel=2,
            )
            battleground_ols = None

        safe_df = spatial_matrix_df[
            spatial_matrix_df["historical_classification"].isin(["safe_red", "safe_blue"])
        ]
        if len(safe_df) >= 5:
            safe_ols = self.evaluate_h2_ols(safe_df, "Safe_States", control_covariates)
        else:
            import warnings
            warnings.warn(
                f"Safe States N={len(safe_df)} < 5; no regression run.",
                RuntimeWarning,
                stacklevel=2,
            )
            safe_ols = None

        return HypothesisEvaluationSummary(
            h1_itsa_results=h1_results,
            h2_national_ols=national_ols,
            h2_battleground_ols=battleground_ols,
            h2_safe_ols=safe_ols,
        )
