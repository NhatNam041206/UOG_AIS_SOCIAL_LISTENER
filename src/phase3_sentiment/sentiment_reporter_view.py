"""Research figures and reporting for Phase 3 VADER scoring."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


class SentimentReporterView:
    """Render the approved VADER-stage figures and report."""

    LABEL_ORDER = ["negative", "neutral", "positive"]
    LABEL_COLORS = {
        "negative": "#D55E00",
        "neutral": "#777777",
        "positive": "#0072B2",
    }
    CANDIDATE_LABELS = {
        "donald_trump": "Donald Trump stream",
        "joe_biden": "Joe Biden stream",
    }
    CANDIDATE_COLORS = {
        "Donald Trump stream": "#D55E00",
        "Joe Biden stream": "#0072B2",
    }

    def render_vader_graphs(self, dataframe: pd.DataFrame, graph_dir: Path) -> None:
        """Write the two approved full-dataset VADER figures."""
        self._require_columns(dataframe)
        graph_dir.mkdir(parents=True, exist_ok=True)
        sns.set_theme(style="whitegrid", context="paper")
        self._sentiment_distribution(
            dataframe,
            graph_dir / "vader_sentiment_distribution.png",
        )
        self._candidate_distribution(
            dataframe,
            graph_dir / "sentiment_distribution_by_candidate.png",
        )

    def write_vader_report(self, manifest: Dict[str, Any], destination: Path) -> None:
        """Write a human-readable VADER-stage report."""
        summary = manifest["vader_summary"]
        lines = [
            "# Phase 3 VADER Sentiment Scoring Report",
            "",
            "## Stage Status",
            "",
            f"- Status: **{manifest['status']}**.",
            f"- Input records: {manifest['input_record_count']:,}.",
            f"- Output records: {manifest['output_record_count']:,}.",
            f"- VADER output validation: **{manifest['output_validation']['status']}** "
            f"({manifest['output_validation']['checks_passed']} checks passed).",
            "- RoBERTa validation remains pending; this report does not claim validated VADER accuracy.",
            "",
            "## Method",
            "",
            "- VADER scored the Phase 2 cleaned `tweet` text without additional normalization.",
            "- Capitalization, punctuation, and emoji preserved by Phase 2 remain available to VADER.",
            "- Compound scores at or below `-0.05` are negative.",
            "- Compound scores between `-0.05` and `0.05` are neutral.",
            "- Compound scores at or above `0.05` are positive.",
            "",
            "## Full-Dataset Summary",
            "",
            "| Measure | Result |",
            "| --- | ---: |",
            f"| Mean compound score | {summary['compound_mean']:.4f} |",
            f"| Standard deviation | {summary['compound_std']:.4f} |",
            f"| Minimum compound score | {summary['compound_min']:.4f} |",
            f"| Maximum compound score | {summary['compound_max']:.4f} |",
            "",
            "## Label Distribution",
            "",
            "| Label | Records | Percentage |",
            "| --- | ---: | ---: |",
        ]
        for label in self.LABEL_ORDER:
            count = summary["label_counts"].get(label, 0)
            percentage = summary["label_percentages"].get(label, 0.0)
            lines.append(f"| {label.title()} | {count:,} | {percentage:.2f}% |")
        lines.extend(
            [
                "",
                "## Major Figures",
                "",
                "1. `vader_sentiment_distribution.png` shows the full compound-score distribution and label counts.",
                "2. `sentiment_distribution_by_candidate.png` compares compound-score distributions between candidate streams.",
                "",
                "## Interpretation Boundary",
                "",
                "These are descriptive VADER outputs. Candidate-stream differences must not be interpreted as population opinion, causal effects, or validated model accuracy. The planned RoBERTa comparison is required before Phase 3 closure.",
            ]
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def render_validation_graphs(
        self,
        dataframe: pd.DataFrame,
        metrics: Dict[str, Any],
        graph_dir: Path,
    ) -> None:
        """Write the two approved VADER/RoBERTa validation figures."""
        required = {"vader_compound", "roberta_score", "vader_label", "roberta_label"}
        missing = sorted(required - set(dataframe.columns))
        if missing:
            raise ValueError(f"Required validation reporting columns are missing: {missing}")
        graph_dir.mkdir(parents=True, exist_ok=True)
        sns.set_theme(style="whitegrid", context="paper")
        self._score_comparison(
            dataframe,
            metrics,
            graph_dir / "vader_roberta_score_comparison.png",
        )
        self._confusion_matrix(
            metrics,
            graph_dir / "vader_roberta_confusion_matrix.png",
        )

    def _sentiment_distribution(self, dataframe: pd.DataFrame, destination: Path) -> None:
        figure, axes = plt.subplots(1, 2, figsize=(11.0, 4.8), gridspec_kw={"width_ratios": [1.8, 1]})
        axes[0].hist(
            dataframe["vader_compound"],
            bins=60,
            color="#4C78A8",
            edgecolor="white",
            alpha=0.9,
        )
        axes[0].axvline(-0.05, color="#D55E00", linestyle="--", linewidth=1.5, label="Negative boundary")
        axes[0].axvline(0.05, color="#0072B2", linestyle="--", linewidth=1.5, label="Positive boundary")
        axes[0].set_title("Compound Score Distribution", weight="bold")
        axes[0].set_xlabel("VADER compound score")
        axes[0].set_ylabel("Tweet records")
        axes[0].legend(frameon=True, fontsize=8)

        counts = dataframe["vader_label"].value_counts().reindex(self.LABEL_ORDER, fill_value=0)
        bars = axes[1].bar(
            [label.title() for label in self.LABEL_ORDER],
            counts.values,
            color=[self.LABEL_COLORS[label] for label in self.LABEL_ORDER],
        )
        axes[1].bar_label(bars, labels=[f"{value / len(dataframe) * 100:.1f}%" for value in counts], padding=3)
        axes[1].set_title("Label Distribution", weight="bold")
        axes[1].set_xlabel("")
        axes[1].set_ylabel("Tweet records")
        axes[1].set_ylim(bottom=0)
        figure.suptitle("Full-Dataset VADER Sentiment Distribution", weight="bold")
        self._save(
            figure,
            destination,
            "Source: Phase 2 cleaned Twitter dataset. VADER label boundaries are -0.05 and +0.05.",
        )

    def _candidate_distribution(self, dataframe: pd.DataFrame, destination: Path) -> None:
        working = dataframe[["candidate", "vader_compound"]].copy()
        working["Candidate stream"] = working["candidate"].map(self.CANDIDATE_LABELS).fillna(working["candidate"])
        figure, axis = plt.subplots(figsize=(9.2, 5.2))
        for label in self.CANDIDATE_COLORS:
            values = working.loc[working["Candidate stream"].eq(label), "vader_compound"]
            axis.hist(
                values,
                bins=60,
                range=(-1, 1),
                density=True,
                histtype="step",
                linewidth=2.0,
                color=self.CANDIDATE_COLORS[label],
                label=f"{label} (n={len(values):,})",
            )
        axis.axvline(0, color="#555555", linestyle=":", linewidth=1.2)
        axis.set_title("VADER Compound Score Distribution by Candidate Stream", weight="bold", pad=12)
        axis.set_xlabel("VADER compound score")
        axis.set_ylabel("Density")
        axis.set_xlim(-1, 1)
        axis.legend(frameon=True)
        self._save(
            figure,
            destination,
            "Source: Phase 2 cleaned Twitter dataset. Curves are density-normalized because candidate-stream record counts differ.",
        )

    def _score_comparison(
        self,
        dataframe: pd.DataFrame,
        metrics: Dict[str, Any],
        destination: Path,
    ) -> None:
        overall = metrics["overall"]
        figure, axis = plt.subplots(figsize=(7.2, 6.0))
        axis.scatter(
            dataframe["vader_compound"],
            dataframe["roberta_score"],
            alpha=0.2,
            s=14,
            color="#4C78A8",
            edgecolors="none",
        )
        coefficients = np.polyfit(dataframe["vader_compound"], dataframe["roberta_score"], 1)
        x = np.linspace(-1, 1, 200)
        axis.plot(x, coefficients[0] * x + coefficients[1], color="#D55E00", linewidth=2, label="Linear fit")
        axis.plot([-1, 1], [-1, 1], color="#777777", linestyle="--", linewidth=1.2, label="Equal scores")
        axis.set_title("VADER and RoBERTa Continuous Score Agreement", weight="bold", pad=12)
        axis.set_xlabel("VADER compound score")
        axis.set_ylabel("RoBERTa score (positive probability - negative probability)")
        axis.set_xlim(-1, 1)
        axis.set_ylim(-1, 1)
        axis.text(
            0.02,
            0.98,
            f"Pearson r = {overall['pearson_r']:.3f}\n95% CI [{overall['pearson_95_ci'][0]:.3f}, {overall['pearson_95_ci'][1]:.3f}]\nn = {overall['record_count']:,}",
            transform=axis.transAxes,
            va="top",
            bbox={"facecolor": "white", "edgecolor": "#BBBBBB", "alpha": 0.9},
        )
        axis.legend(frameon=True, loc="lower right")
        self._save(
            figure,
            destination,
            "Source: Phase 3 proportional candidate-by-UTC-day validation sample. RoBERTa is a comparison model, not human ground truth.",
        )

    def _confusion_matrix(self, metrics: Dict[str, Any], destination: Path) -> None:
        matrix = np.asarray(metrics["overall"]["confusion_matrix"], dtype=int)
        figure, axis = plt.subplots(figsize=(7.0, 5.8))
        sns.heatmap(
            matrix,
            annot=True,
            fmt="d",
            cmap="Blues",
            cbar_kws={"label": "Tweet records"},
            xticklabels=[label.title() for label in self.LABEL_ORDER],
            yticklabels=[label.title() for label in self.LABEL_ORDER],
            ax=axis,
        )
        axis.set_title("VADER and RoBERTa Label Agreement", weight="bold", pad=12)
        axis.set_xlabel("RoBERTa label")
        axis.set_ylabel("VADER label")
        self._save(
            figure,
            destination,
            f"Source: Phase 3 validation sample. Overall exact-label agreement is {100.0 * metrics['overall']['label_agreement_rate']:.2f}%.",
        )

    @staticmethod
    def _require_columns(dataframe: pd.DataFrame) -> None:
        required = {"candidate", "vader_compound", "vader_label"}
        missing = sorted(required - set(dataframe.columns))
        if missing:
            raise ValueError(f"Required VADER reporting columns are missing: {missing}")

    @staticmethod
    def _save(figure: plt.Figure, destination: Path, source_note: str) -> None:
        figure.text(0.01, 0.01, source_note, fontsize=7.5, color="#555555")
        figure.tight_layout(rect=(0, 0.06, 1, 0.96))
        figure.savefig(destination, dpi=180, bbox_inches="tight", facecolor="white")
        plt.close(figure)
