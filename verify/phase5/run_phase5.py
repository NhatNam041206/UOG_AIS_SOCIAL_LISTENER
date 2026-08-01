"""Execute Phase 5 Inferential Statistical Modeling & Hypothesis Evaluation.

Phase 5 evaluates:
1. Hypothesis 1 (ITSA): Event step-change (beta_2) and slope decay (beta_3).
2. Hypothesis 2 (Stratified Spatial OLS): Online sentiment margin (X_i) vs 2020 vote margin (Y_i) with demographic controls (Z_ki), stratified across National, Battleground, and Safe states.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.phase5_modeling.itsa_ols_evaluator import ITSAOLSEvaluator


PHASE5_RUN_ID = "phase5_statistical_evaluation_20260731"


def run_phase5(project_root: str | Path = ".") -> Dict[str, Any]:
    """Execute Phase 5 hypothesis testing and statistical evaluation."""
    root = Path(project_root).resolve()
    p4_processed_dir = root / "data" / "03_processed"
    report_dir = root / "output" / "reports" / "phase5"
    result_dir = root / "output" / "results" / "phase5"

    for d in (report_dir, result_dir):
        d.mkdir(parents=True, exist_ok=True)

    event_window_path = p4_processed_dir / "temporal_event_windows.parquet"
    spatial_path = p4_processed_dir / "spatial_state_matrix.parquet"

    if not spatial_path.exists():
        raise FileNotFoundError("Phase 4 spatial matrix missing. Run Phase 4 first.")

    event_windows_df = pd.read_parquet(event_window_path) if event_window_path.exists() else pd.DataFrame()
    spatial_df = pd.read_parquet(spatial_path)

    evaluator = ITSAOLSEvaluator()
    summary_eval = evaluator.evaluate_all(event_windows_df, spatial_df)

    h1_list = []
    for h1 in summary_eval.h1_itsa_results:
        h1_list.append(
            {
                "event_name": h1.event_name,
                "beta_0_baseline": h1.beta_0_baseline,
                "beta_1_pre_slope": h1.beta_1_pre_slope,
                "beta_2_immediate_shock": h1.beta_2_immediate_shock,
                "beta_3_post_slope_change": h1.beta_3_post_slope_change,
                "p_value_immediate_shock": h1.p_value_immediate_shock,
                "p_value_post_slope_change": h1.p_value_post_slope_change,
                "r_squared": h1.r_squared,
            }
        )

    def _ols_to_dict(ols: Any) -> Dict[str, Any]:
        return {
            "subgroup_name": ols.subgroup_name,
            "sample_size": ols.sample_size,
            "beta_1_sentiment_margin": ols.beta_1_sentiment_margin,
            "p_value_sentiment_margin": ols.p_value_sentiment_margin,
            "r_squared": ols.r_squared,
            "adjusted_r_squared": ols.adjusted_r_squared,
            "covariate_coefficients": ols.covariate_coefficients,
        }

    manifest = {
        "phase": "phase5_statistical_evaluation",
        "run_id": PHASE5_RUN_ID,
        "h1_itsa_events_tested": len(h1_list),
        "h1_results": h1_list,
        "h2_national_ols": _ols_to_dict(summary_eval.h2_national_ols),
        "h2_battleground_ols": _ols_to_dict(summary_eval.h2_battleground_ols),
        "h2_safe_ols": _ols_to_dict(summary_eval.h2_safe_ols),
        "output_paths": {
            "manifest": str(result_dir / "statistical_evaluation_manifest.json"),
            "report": str(report_dir / "statistical_evaluation_report.md"),
        },
    }

    (result_dir / "statistical_evaluation_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Generate Report
    report_lines = [
        "# Phase 5 Statistical Evaluation Report",
        "",
        f"Run ID: `{PHASE5_RUN_ID}`",
        "",
        "## Hypothesis 1: Interrupted Time Series Analysis (ITSA)",
        f"- Events Evaluated: {len(h1_list)}",
    ]
    for h1 in h1_list:
        report_lines.extend(
            [
                f"### Event: {h1['event_name']}",
                f"- Immediate Shock (beta_2): `{h1['beta_2_immediate_shock']:.4f}` (p-value: `{h1['p_value_immediate_shock']:.4f}`)",
                f"- Slope Change (beta_3): `{h1['beta_3_post_slope_change']:.4f}` (p-value: `{h1['p_value_post_slope_change']:.4f}`)",
                f"- Model R^2: `{h1['r_squared']:.4f}`",
            ]
        )

    nat = summary_eval.h2_national_ols
    bat = summary_eval.h2_battleground_ols
    safe = summary_eval.h2_safe_ols

    report_lines.extend(
        [
            "",
            "## Hypothesis 2: Stratified OLS Spatial Regression",
            "",
            "| Subgroup | Sample Size (N) | Sentiment Slope (beta_1) | p-value | R^2 | Adj R^2 |",
            "|---|---:|---:|---:|---:|---:|",
            f"| National | {nat.sample_size} | {nat.beta_1_sentiment_margin:.4f} | {nat.p_value_sentiment_margin:.4f} | {nat.r_squared:.4f} | {nat.adjusted_r_squared:.4f} |",
            f"| Battleground States | {bat.sample_size} | {bat.beta_1_sentiment_margin:.4f} | {bat.p_value_sentiment_margin:.4f} | {bat.r_squared:.4f} | {bat.adjusted_r_squared:.4f} |",
            f"| Safe States | {safe.sample_size} | {safe.beta_1_sentiment_margin:.4f} | {safe.p_value_sentiment_margin:.4f} | {safe.r_squared:.4f} | {safe.adjusted_r_squared:.4f} |",
        ]
    )

    (report_dir / "statistical_evaluation_report.md").write_text("\n".join(report_lines), encoding="utf-8")

    return manifest


if __name__ == "__main__":
    res = run_phase5(PROJECT_ROOT)
    print(json.dumps(res, indent=2))
