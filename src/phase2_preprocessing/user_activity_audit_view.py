"""Research figures and report rendering for the Phase 2 activity audit."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from .user_activity_audit_model import UserActivityAuditResult, UserActivityAuditor


class UserActivityAuditView:
    """Render the five approved audit figures and their markdown interpretation."""

    LABELS = {
        "p95": "P95",
        "p97_5": "P97.5",
        "p99": "P99",
        "p99_5": "P99.5",
        "iqr_upper_fence": "IQR upper fence",
        "extreme_iqr_upper_fence": "Extreme IQR fence",
        "log_z_threshold": "Log-z threshold",
        "mad_threshold": "MAD threshold",
    }

    def render_graphs(
        self,
        dataframe: pd.DataFrame,
        audit: UserActivityAuditResult,
        graph_dir: Path,
        user_key: str = "user_id",
        timestamp_key: str = "date",
    ) -> None:
        """Write only the five approved Phase 2 user-activity audit figures."""
        graph_dir.mkdir(parents=True, exist_ok=True)
        sns.set_theme(style="whitegrid", context="paper")
        self._activity_distribution(audit, graph_dir / "activity_distribution_with_thresholds.png")
        self._contribution_curve(audit, graph_dir / "user_contribution_curve.png")
        self._threshold_comparison(audit, graph_dir / "derived_threshold_comparison.png")
        self._tradeoff_chart(audit, graph_dir / "filtering_tradeoff_users_vs_tweets.png")
        self._daily_before_after(
            dataframe,
            audit,
            graph_dir / "daily_volume_before_after_filtering.png",
            user_key,
            timestamp_key,
        )

    def write_report(
        self,
        audit: UserActivityAuditResult,
        destination: Path,
    ) -> None:
        """Write the requested threshold decision report."""
        metrics = audit.user_metrics
        tradeoffs = audit.tradeoffs.set_index("method")
        selected = audit.selected_threshold
        selected_tradeoff = self._tradeoff_for_threshold(audit.tradeoffs, selected)
        mad_value = audit.candidate_thresholds.get("mad_threshold")
        lines = [
            "# Phase 2 User-Activity Threshold Audit",
            "",
            "## Why an Empirical Audit Is Needed",
            "",
            "A fixed high-volume threshold is methodologically weak because it is not tied to the observed activity distribution and may remove too much or too little data without a reproducible justification.",
            "",
            "Raw mean plus or minus standard deviation is also unsuitable for strongly right-skewed posting frequency: a small number of highly active users pulls both the mean and standard deviation upward. The audit therefore emphasizes percentiles and robust fences, and applies the z-score method only after `log1p` transformation.",
            "",
            "## User-Activity Summary",
            "",
            f"- Users measured: {len(metrics):,}.",
            f"- Tweets measured: {int(metrics['total_tweets'].sum()):,}.",
            "- Main metric: `tweets_per_active_day`.",
            f"- Median tweets per active day: {metrics['tweets_per_active_day'].median():.2f}.",
            f"- Maximum tweets per active day: {metrics['tweets_per_active_day'].max():.2f}.",
            "",
            "## Candidate Thresholds",
            "",
            "| Method | Threshold (tweets per active day) |",
            "|---|---:|",
        ]
        for method, threshold in audit.candidate_thresholds.items():
            lines.append(f"| {self.LABELS[method]} | {threshold:.3f} |")
        lines.extend(
            [
                "",
                "## Filtering Trade-Offs",
                "",
                "| Method | Threshold | Users removed (n) | Users removed (%) | Tweets removed (n) | Tweets removed (%) |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        for method in audit.candidate_thresholds:
            row = tradeoffs.loc[method]
            lines.append(
                f"| {self.LABELS[method]} | {row['threshold']:.3f} | "
                f"{int(row['users_removed']):,} | {row['users_removed_pct']:.2f}% | "
                f"{int(row['tweets_removed']):,} | {row['tweets_removed_pct']:.2f}% |"
            )
        lines.extend(
            [
                "",
                "## Selected Threshold",
                "",
                f"**Recommended threshold: {selected:.3f} tweets per active day.**",
                "",
                (
                    audit.selection_reason
                    +
                    f" At this threshold, {selected_tradeoff['users_removed_pct']:.2f}% of users "
                    f"and {selected_tradeoff['tweets_removed_pct']:.2f}% of tweets are removed."
                ),
                "",
                (
                    "The MAD candidate is feasible but not informative for this dataset because "
                    f"its threshold is {mad_value:.3f}; the mass of users at one tweet per active "
                    "day makes the median absolute deviation collapse to zero."
                ),
                "",
                "## Major Figures",
                "",
                "1. `activity_distribution_with_thresholds.png` shows the skewed log-activity distribution and positions the selected value against major empirical candidates.",
                "2. `user_contribution_curve.png` shows whether tweet production is concentrated among a small share of users.",
                "3. `derived_threshold_comparison.png` compares all candidate values rather than presenting one statistic in isolation.",
                "4. `filtering_tradeoff_users_vs_tweets.png` makes the retention cost of each candidate explicit.",
                "5. `daily_volume_before_after_filtering.png` checks whether the selected user filter preserves the shape of daily tweet activity needed by later phases.",
                "",
                "## Scope Warning",
                "",
                "**This Phase 2 audit does not validate Phase 5 modeling. Phase 5 ITSA and OLS modules have not been implemented, and this report contains no model-performance or causal-robustness claims.**",
                "",
                "Once ITSA and OLS modules exist, this audit can support robustness testing by rerunning those models across documented candidate activity thresholds and comparing whether substantive conclusions remain stable. That future work must use real implemented models and is outside Phase 2.",
            ]
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _activity_distribution(self, audit: UserActivityAuditResult, destination: Path) -> None:
        values = np.log1p(audit.user_metrics["tweets_per_active_day"].dropna())
        figure, axis = plt.subplots(figsize=(9.0, 5.2))
        axis.hist(values, bins=60, color="#4C78A8", alpha=0.85, edgecolor="white")
        styles = {
            "p95": ("#E69F00", "--"),
            "p99": ("#D55E00", "--"),
            "iqr_upper_fence": ("#009E73", ":"),
            "log_z_threshold": ("#CC79A7", "-."),
        }
        for method, (color, style) in styles.items():
            threshold = audit.candidate_thresholds[method]
            axis.axvline(np.log1p(threshold), color=color, linestyle=style, linewidth=1.8, label=self.LABELS[method])
        axis.axvline(
            np.log1p(audit.selected_threshold),
            color="#000000",
            linewidth=2.3,
            label=f"Selected ({audit.selected_threshold:.2f})",
        )
        axis.set_title("Distribution of User Activity with Empirical Thresholds", weight="bold", pad=12)
        axis.set_xlabel("log1p(tweets per active day)")
        axis.set_ylabel("Users")
        axis.legend(frameon=True, fontsize=8)
        self._save(figure, destination, "Source: Phase 1 aligned Twitter streams. Main metric is tweets per active UTC day.")

    def _contribution_curve(self, audit: UserActivityAuditResult, destination: Path) -> None:
        ordered = audit.user_metrics.sort_values("total_tweets")
        x = np.arange(1, len(ordered) + 1) / len(ordered) * 100.0
        y = ordered["total_tweets"].cumsum() / ordered["total_tweets"].sum() * 100.0
        figure, axis = plt.subplots(figsize=(7.2, 5.2))
        axis.plot(x, y, color="#4C78A8", linewidth=2.2, label="Observed contribution")
        axis.plot([0, 100], [0, 100], color="#777777", linestyle="--", linewidth=1.2, label="Equal contribution")
        axis.set_title("Cumulative User Contribution to Tweet Volume", weight="bold", pad=12)
        axis.set_xlabel("Cumulative users (%)")
        axis.set_ylabel("Cumulative tweets (%)")
        axis.set_xlim(0, 100)
        axis.set_ylim(0, 100)
        axis.legend(frameon=True)
        self._save(figure, destination, "Source: Phase 1 aligned Twitter streams. Users are ordered from lowest to highest total tweet contribution.")

    def _threshold_comparison(self, audit: UserActivityAuditResult, destination: Path) -> None:
        dataframe = pd.DataFrame(
            [
                {"Method": self.LABELS[method], "Threshold": threshold}
                for method, threshold in audit.candidate_thresholds.items()
            ]
        )
        figure, axis = plt.subplots(figsize=(9.2, 5.2))
        sns.barplot(data=dataframe, x="Method", y="Threshold", color="#4C78A8", errorbar=None, ax=axis)
        axis.axhline(audit.selected_threshold, color="#D55E00", linestyle="--", linewidth=1.8, label="Selected threshold")
        axis.set_title("Comparison of Empirical Activity Thresholds", weight="bold", pad=12)
        axis.set_xlabel("")
        axis.set_ylabel("Tweets per active day")
        axis.set_ylim(bottom=0)
        axis.tick_params(axis="x", rotation=25)
        axis.legend(frameon=True)
        for container in axis.containers:
            axis.bar_label(container, fmt="%.2f", padding=3, fontsize=8)
        self._save(figure, destination, "Source: Phase 1 aligned Twitter streams. Thresholds use percentiles and robust transformed-distribution diagnostics.")

    def _tradeoff_chart(self, audit: UserActivityAuditResult, destination: Path) -> None:
        dataframe = audit.tradeoffs.copy()
        dataframe["Method"] = dataframe["method"].map(self.LABELS)
        long = dataframe.melt(
            id_vars="Method",
            value_vars=["users_removed_pct", "tweets_removed_pct"],
            var_name="Measure",
            value_name="Removed (%)",
        )
        long["Measure"] = long["Measure"].map(
            {"users_removed_pct": "Users removed", "tweets_removed_pct": "Tweets removed"}
        )
        figure, axis = plt.subplots(figsize=(9.4, 5.4))
        sns.barplot(
            data=long,
            x="Method",
            y="Removed (%)",
            hue="Measure",
            palette={"Users removed": "#4C78A8", "Tweets removed": "#E69F00"},
            errorbar=None,
            ax=axis,
        )
        axis.set_title("Filtering Trade-Off: Users Versus Tweets Removed", weight="bold", pad=12)
        axis.set_xlabel("")
        axis.set_ylabel("Removed (%)")
        axis.set_ylim(bottom=0)
        axis.tick_params(axis="x", rotation=25)
        axis.legend(title="")
        self._save(figure, destination, "Source: Phase 1 aligned Twitter streams. Records from users above each candidate threshold are removed.")

    def _daily_before_after(
        self,
        dataframe: pd.DataFrame,
        audit: UserActivityAuditResult,
        destination: Path,
        user_key: str,
        timestamp_key: str,
    ) -> None:
        identities = UserActivityAuditor.user_identity(dataframe[user_key])
        removed_users = set(
            audit.user_metrics.loc[
                audit.user_metrics["tweets_per_active_day"].gt(audit.selected_threshold),
                user_key,
            ]
        )
        retained = dataframe.loc[~identities.isin(removed_users)]
        raw_daily = pd.to_datetime(dataframe[timestamp_key], utc=True, errors="coerce").dt.floor("D").value_counts()
        filtered_daily = pd.to_datetime(retained[timestamp_key], utc=True, errors="coerce").dt.floor("D").value_counts()
        daily = pd.concat(
            [raw_daily.rename("Raw"), filtered_daily.rename("Filtered")],
            axis=1,
        ).fillna(0).sort_index().reset_index(names="Date")
        long = daily.melt(id_vars="Date", var_name="Series", value_name="Tweet records")
        figure, axis = plt.subplots(figsize=(9.4, 5.2))
        sns.lineplot(
            data=long,
            x="Date",
            y="Tweet records",
            hue="Series",
            palette={"Raw": "#777777", "Filtered": "#4C78A8"},
            linewidth=2,
            errorbar=None,
            ax=axis,
        )
        axis.set_title("Daily Tweet Volume Before and After Activity Filtering", weight="bold", pad=12)
        axis.set_xlabel("Date (UTC)")
        axis.set_ylabel("Tweet records")
        axis.set_ylim(bottom=0)
        axis.legend(title="")
        figure.autofmt_xdate(rotation=30, ha="right")
        self._save(figure, destination, f"Source: Phase 1 aligned Twitter streams. Filtered series removes users above {audit.selected_threshold:.3f} tweets per active day.")

    @staticmethod
    def _tradeoff_for_threshold(tradeoffs: pd.DataFrame, threshold: float) -> pd.Series:
        matching = tradeoffs.loc[np.isclose(tradeoffs["threshold"], threshold)]
        return matching.sort_values("method").iloc[0]

    @staticmethod
    def _save(figure: plt.Figure, destination: Path, source_note: str) -> None:
        figure.text(0.01, 0.01, source_note, fontsize=7.5, color="#555555")
        figure.tight_layout(rect=(0, 0.06, 1, 1))
        figure.savefig(destination, dpi=180, bbox_inches="tight", facecolor="white")
        plt.close(figure)
