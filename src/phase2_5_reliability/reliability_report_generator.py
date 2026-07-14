"""Render an evidence-bounded Markdown report for a Phase 2.5 run."""

from __future__ import annotations

from typing import Any

import pandas as pd


def markdown_table(dataframe: pd.DataFrame) -> str:
    if dataframe.empty:
        return "_No records._"
    view = dataframe.astype(object).where(pd.notna(dataframe), "")
    lines = [
        "| " + " | ".join(map(str, view.columns)) + " |",
        "| " + " | ".join(["---"] * len(view.columns)) + " |",
    ]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |")
    return "\n".join(lines)


class ReliabilityReportGenerator:
    def render(
        self,
        manifest: dict[str, Any],
        criterion_summary: pd.DataFrame,
        availability_summary: pd.DataFrame,
        threshold_summary: pd.DataFrame,
    ) -> str:
        if manifest["run_mode"] == "full":
            scope_note = "- Full results are diagnostic findings for the Phase 2 output, not mitigation decisions."
        else:
            scope_note = "- Sample results are verification evidence and must not be cited as full-dataset findings."
        return "\n".join(
            [
                "# Phase 2.5 Production Reliability Examination Report",
                "",
                "## Scope",
                "",
                f"- Run mode: `{manifest['run_mode']}`; evaluated rows: {manifest['output_row_count']:,}.",
                "- This is candidate-hashtag-centered discourse from 2020-10-15 through 2020-11-08.",
                scope_note,
                "- No record was filtered, weighted, relabeled, sentiment-reversed, routed, or otherwise mitigated.",
                "- Every mitigation decision remains `pending`.",
                "",
                "## Criterion score availability",
                "",
                markdown_table(criterion_summary),
                "",
                "## Evidence availability",
                "",
                markdown_table(availability_summary),
                "",
                "## Approved activity-threshold provenance",
                "",
                f"- Source: Phase 2 pre-filter audit over {manifest['phase2_prefilter_user_count']:,} users.",
                f"- Approved threshold: {manifest['approved_activity_threshold']} tweets per active day.",
                markdown_table(threshold_summary.loc[threshold_summary.get('approved', False).eq(True)] if not threshold_summary.empty else threshold_summary),
                "",
                "## Duplicate and amplification layers",
                "",
                "1. Phase 2 raw exact-duplicate removal is retained as historical provenance.",
                "2. Post-cleaning exact-text convergence is counted separately.",
                "3. Normalized repetition is counted separately.",
                "4. Near-duplicate and cross-user repetition are lexical amplification proxies, not confirmed coordination.",
                "",
                "## Corrections from the notebook prototype",
                "",
                "- User activity uses the Phase 2 pre-filter audit, not the already-filtered sentiment data.",
                "- URL provenance remains unavailable because no validated original-text join is configured.",
                "- Missing language evidence remains unavailable and produces null language risk.",
                "- Missing RoBERTa evidence remains unavailable and produces null model risk.",
                "- Exact, post-cleaning, normalized, near-duplicate, and cross-user repetition layers are separated.",
                "- Availability counts are published explicitly; no missing evidence is replaced with `0.5`.",
                "",
                "## Interpretation limits",
                "",
                "- RoBERTa is model-comparison evidence, not human ground truth.",
                "- Model agreement is not accuracy, hashtag membership is not stance, and language is not location.",
                "- Rule-based sarcasm and near-duplicate signals are diagnostic proxies only.",
                "- Missing state evidence limits state analysis but does not invalidate national temporal analysis.",
                "",
            ]
        )
