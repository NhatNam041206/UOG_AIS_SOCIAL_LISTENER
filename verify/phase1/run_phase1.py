"""Execute and verify complete Phase 1 multi-source ingestion."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.phase1_ingestion.ingestion_runner_controller import IngestionRunnerController
from src.phase1_ingestion.storage_serializers_view import StorageSerializersView
from src.phase1_ingestion.stream_readers_model import CsvStreamReader
from src.shared.data_interfaces_model import SchemaMapperInterface


TWITTER_FIELDS = [
    "id",
    "date",
    "tweet",
    "user_id",
    "user_loc",
    "retweets",
    "replies",
    "candidate",
    "source_file",
]


class PoliticalEventMapper(SchemaMapperInterface):
    """Map curated political events into the canonical event stream."""

    def map_record(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "event_id": _required_text(raw_record, "event_id"),
            "event_timestamp_utc": _required_text(
                raw_record,
                "event_timestamp_local",
            ),
            "event_timezone": _required_text(raw_record, "event_timezone"),
            "event_name": _required_text(raw_record, "event_name"),
            "event_category": _required_text(raw_record, "event_category"),
            "event_description": _required_text(raw_record, "event_description"),
            "post_event_dummy": 1,
            "source_url": _required_text(raw_record, "source_url"),
        }


class ElectoralReturnsMapper(SchemaMapperInterface):
    """Map FEC state returns and derive benchmark fields."""

    def __init__(self, swing_threshold_pct: float = 5.0) -> None:
        self.swing_threshold_pct = swing_threshold_pct

    def map_record(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        state_code = _required_text(raw_record, "state_code")
        biden_votes = _required_int(raw_record, "biden_votes")
        trump_votes = _required_int(raw_record, "trump_votes")
        total_votes = _required_int(raw_record, "total_votes")
        if biden_votes + trump_votes > total_votes:
            raise ValueError(f"Major-party votes exceed total votes for {state_code}")

        margin = 100.0 * (biden_votes - trump_votes) / total_votes
        return {
            "state_code": state_code,
            "biden_votes": biden_votes,
            "trump_votes": trump_votes,
            "total_votes": total_votes,
            "other_votes": total_votes - biden_votes - trump_votes,
            "biden_vote_share_pct": 100.0 * biden_votes / total_votes,
            "trump_vote_share_pct": 100.0 * trump_votes / total_votes,
            "democratic_margin_pct": margin,
            "absolute_margin_pct": abs(margin),
            "winner": "Biden" if margin > 0 else "Trump",
            "state_classification": (
                "swing" if abs(margin) <= self.swing_threshold_pct else "safe"
            ),
            "swing_threshold_pct": self.swing_threshold_pct,
            "source_url": _required_text(raw_record, "source_url"),
        }


def run_phase1(project_root: str | Path = ".") -> Dict[str, Any]:
    """Execute all Phase 1 streams and write structured verification artifacts."""
    root = Path(project_root).resolve()
    interim = root / "data" / "02_interim"
    graph_dir = root / "output" / "graphs" / "phase1"
    report_dir = root / "output" / "reports" / "phase1"
    result_dir = root / "output" / "results" / "phase1"
    for directory in (interim, graph_dir, report_dir, result_dir):
        directory.mkdir(parents=True, exist_ok=True)

    serializer = StorageSerializersView()
    manifest: Dict[str, Any] = {"streams": {}}
    daily_volume: Counter[tuple[str, str]] = Counter()

    event_source = root / "data" / "01_raw" / "political_events" / "political_events.csv"
    events = IngestionRunnerController(
        CsvStreamReader(),
        PoliticalEventMapper(),
    ).execute(str(event_source), {"timestamp_columns": "event_timestamp_utc"})
    serializer.serialize_to_parquet(events, interim / "political_events.parquet")
    manifest["streams"]["political_events"] = _small_stream_metrics(events, event_source)

    electoral_source = (
        root / "data" / "01_raw" / "electoral_returns" / "electoral_returns.csv"
    )
    returns = IngestionRunnerController(
        CsvStreamReader(),
        ElectoralReturnsMapper(),
    ).execute(str(electoral_source))
    serializer.serialize_to_parquet(returns, interim / "electoral_returns.parquet")
    manifest["streams"]["electoral_returns"] = _small_stream_metrics(
        returns,
        electoral_source,
    )

    twitter_sources = [
        ("donald_trump", root / "data" / "01_raw" / "twitter" / "hashtag_donaldtrump.csv"),
        ("joe_biden", root / "data" / "01_raw" / "twitter" / "hashtag_joebiden.csv"),
    ]
    for candidate, source in twitter_sources:
        reader = CsvStreamReader()
        controller = IngestionRunnerController(reader)
        metrics = _new_twitter_metrics(source)
        batches = controller.execute_batches(
            str(source),
            {
                "reader_options": {
                    "columns": [
                        "created_at",
                        "tweet_id",
                        "tweet",
                        "retweet_count",
                        "user_id",
                        "user_location",
                    ],
                    "column_types": {
                        "tweet_id": "string",
                        "user_id": "string",
                    },
                    "invalid_row_behavior": "skip",
                },
                "rename_fields": {
                    "created_at": "date",
                    "tweet_id": "id",
                    "retweet_count": "retweets",
                    "user_location": "user_loc",
                },
                "constant_fields": {
                    "replies": None,
                    "candidate": candidate,
                    "source_file": source.name,
                },
                "fields": TWITTER_FIELDS,
                "timestamp_columns": "date",
                "timestamp_errors": "coerce",
            },
        )
        observed_batches = _observe_twitter_batches(batches, metrics, daily_volume)
        output_path = interim / f"twitter_{candidate}.parquet"
        serializer.serialize_batches_to_parquet(observed_batches, output_path)
        metrics["invalid_csv_rows"] = reader.invalid_row_count
        manifest["streams"][f"twitter_{candidate}"] = metrics

    manifest["phase"] = "phase1_ingestion"
    manifest["status"] = "completed"
    manifest["original_pdf_alignment"] = _build_original_pdf_alignment(manifest)
    manifest["notes"] = [
        "Malformed Kaggle CSV rows were rejected and counted during Arrow streaming.",
        "The Kaggle source has no replies field; canonical replies values are null.",
        "The downloaded Kaggle files cover October 15 through November 8.",
        "Tweet and user IDs remain source strings because the CSV uses scientific notation.",
        "Exact duplicate tweets are retained for Phase 2 deduplication.",
    ]
    manifest_path = result_dir / "ingestion_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    _write_location_coverage_graph(
        manifest,
        graph_dir / "twitter_location_coverage.png",
    )
    _write_daily_volume_graph(daily_volume, graph_dir / "twitter_daily_volume.png")
    _write_report(manifest, returns, report_dir / "ingestion_report.md")
    return manifest


def _build_original_pdf_alignment(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Describe Phase 1 using the Stream A/B/C contract in the original PDF."""
    streams = manifest["streams"]
    return {
        "reference": "SL_2020_ori.pdf",
        "overall_status": "available_with_alignment_gaps",
        "verified_twitter_window_utc": {
            "start": "2020-10-15",
            "end": "2020-11-08",
        },
        "streams": {
            "A_social_media": {
                "status": "available_with_gaps",
                "manifest_streams": [
                    "twitter_donald_trump",
                    "twitter_joe_biden",
                ],
                "record_count": (
                    streams["twitter_donald_trump"]["record_count"]
                    + streams["twitter_joe_biden"]["record_count"]
                ),
                "gaps": [
                    "Verified coverage is 2020-10-15 through 2020-11-08, not the PDF-planned 2020-10-08 through 2020-11-15.",
                    "The source does not provide reply counts, so replies is null.",
                    "The interim schema omits useful raw account and geospatial metadata needed by later PDF checks.",
                    "The sources are candidate-hashtag-centered and do not represent all election Twitter discourse.",
                ],
            },
            "B_exogenous_events": {
                "status": "available_with_gaps",
                "manifest_streams": ["political_events"],
                "record_count": streams["political_events"]["record_count"],
                "gaps": [
                    "Only four curated milestones are currently registered.",
                    "The stored post_event_dummy is a source attribute; analysis-ready pre/post indicators must be derived against each tweet timestamp in Phase 4.",
                ],
            },
            "C_electoral_benchmarks": {
                "status": "available_with_gaps",
                "manifest_streams": ["electoral_returns"],
                "record_count": streams["electoral_returns"]["record_count"],
                "gaps": [
                    "Swing/safe classification currently uses the 2020 absolute vote margin, not the PDF-planned historical 2012/2016 classification.",
                    "The demographic control variables planned for Phase 5 are not part of the current Phase 1 dataset.",
                ],
            },
        },
    }


def _observe_twitter_batches(
    batches: Iterable[pd.DataFrame],
    metrics: Dict[str, Any],
    daily_volume: Counter[tuple[str, str]],
) -> Iterator[pd.DataFrame]:
    for dataframe in batches:
        metrics["record_count"] += len(dataframe)
        metrics["missing_counts"]["id"] += _missing_count(dataframe["id"])
        metrics["missing_counts"]["date"] += int(dataframe["date"].isna().sum())
        metrics["missing_counts"]["tweet"] += _missing_count(dataframe["tweet"])
        metrics["missing_counts"]["user_id"] += _missing_count(dataframe["user_id"])
        metrics["missing_counts"]["user_loc"] += _missing_count(dataframe["user_loc"])
        valid_dates = dataframe["date"].dropna()
        if not valid_dates.empty:
            minimum = valid_dates.min()
            maximum = valid_dates.max()
            metrics["minimum_date_utc"] = _minimum_timestamp(
                metrics["minimum_date_utc"],
                minimum,
            )
            metrics["maximum_date_utc"] = _maximum_timestamp(
                metrics["maximum_date_utc"],
                maximum,
            )
            counts = valid_dates.dt.strftime("%Y-%m-%d").value_counts()
            candidate = str(dataframe["candidate"].iloc[0])
            for date, count in counts.items():
                daily_volume[(candidate, date)] += int(count)
        yield dataframe


def _small_stream_metrics(dataframe: pd.DataFrame, source: Path) -> Dict[str, Any]:
    return {
        "source_path": str(source),
        "record_count": len(dataframe),
        "columns": dataframe.columns.tolist(),
    }


def _new_twitter_metrics(source: Path) -> Dict[str, Any]:
    return {
        "source_path": str(source),
        "record_count": 0,
        "invalid_csv_rows": 0,
        "minimum_date_utc": None,
        "maximum_date_utc": None,
        "missing_counts": {
            "id": 0,
            "date": 0,
            "tweet": 0,
            "user_id": 0,
            "user_loc": 0,
        },
        "columns": TWITTER_FIELDS,
    }


def _missing_count(series: pd.Series) -> int:
    """Count null and blank textual values consistently across parser backends."""
    missing = series.isna()
    if series.dtype == object or pd.api.types.is_string_dtype(series):
        missing = missing | series.fillna("").astype(str).str.strip().eq("")
    return int(missing.sum())


def _minimum_timestamp(current: Any, candidate: pd.Timestamp) -> str:
    value = pd.Timestamp(candidate)
    if current is None or value < pd.Timestamp(current):
        return value.isoformat()
    return str(current)


def _maximum_timestamp(current: Any, candidate: pd.Timestamp) -> str:
    value = pd.Timestamp(candidate)
    if current is None or value > pd.Timestamp(current):
        return value.isoformat()
    return str(current)


def _write_location_coverage_graph(
    manifest: Dict[str, Any],
    destination: Path,
) -> None:
    """Write a major Phase 1 data-quality figure for location availability."""
    rows = []
    for candidate, key in (
        ("Donald Trump", "twitter_donald_trump"),
        ("Joe Biden", "twitter_joe_biden"),
    ):
        stream = manifest["streams"][key]
        missing = stream["missing_counts"]["user_loc"]
        rows.extend(
            [
                {"Candidate": candidate, "Location status": "Available", "Records": stream["record_count"] - missing},
                {"Candidate": candidate, "Location status": "Missing", "Records": missing},
            ]
        )
    dataframe = pd.DataFrame(rows)
    sns.set_theme(style="whitegrid", context="paper")
    figure, axis = plt.subplots(figsize=(7.2, 4.8))
    sns.barplot(
        data=dataframe,
        x="Candidate",
        y="Records",
        hue="Location status",
        palette={"Available": "#3977C3", "Missing": "#E69F00"},
        errorbar=None,
        ax=axis,
    )
    axis.set_title("Twitter User-Location Coverage", weight="bold", pad=12)
    axis.set_xlabel("")
    axis.set_ylabel("Tweet records")
    axis.set_ylim(bottom=0)
    axis.legend(title="")
    axis.ticklabel_format(axis="y", style="plain")
    for container in axis.containers:
        axis.bar_label(container, labels=[f"{value:,.0f}" for value in container.datavalues], padding=3, fontsize=8)
    figure.text(
        0.01,
        0.01,
        "Source: Kaggle 2020 US Election Tweets. Null and blank user-location strings count as missing.",
        fontsize=7.5,
        color="#555555",
    )
    figure.tight_layout(rect=(0, 0.06, 1, 1))
    figure.savefig(destination, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def _write_daily_volume_graph(
    daily_volume: Counter[tuple[str, str]],
    destination: Path,
) -> None:
    rows = [
        {
            "Date": pd.Timestamp(date),
            "Candidate": "Donald Trump" if candidate == "donald_trump" else "Joe Biden",
            "Records": count,
        }
        for (candidate, date), count in daily_volume.items()
    ]
    dataframe = pd.DataFrame(rows).sort_values(["Date", "Candidate"])
    sns.set_theme(style="whitegrid", context="paper")
    figure, axis = plt.subplots(figsize=(9.0, 4.8))
    sns.lineplot(
        data=dataframe,
        x="Date",
        y="Records",
        hue="Candidate",
        palette={"Donald Trump": "#D94B4B", "Joe Biden": "#3977C3"},
        marker="o",
        linewidth=2,
        errorbar=None,
        ax=axis,
    )
    axis.set_title("Twitter Daily Volume", weight="bold", pad=12)
    axis.set_xlabel("Date (UTC)")
    axis.set_ylabel("Tweet records")
    axis.set_ylim(bottom=0)
    axis.legend(title="")
    axis.ticklabel_format(axis="y", style="plain")
    figure.autofmt_xdate(rotation=30, ha="right")
    figure.text(
        0.01,
        0.01,
        "Source: Kaggle 2020 US Election Tweets. Malformed CSV rows are excluded.",
        fontsize=7.5,
        color="#555555",
    )
    figure.tight_layout(rect=(0, 0.07, 1, 1))
    figure.savefig(destination, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def _write_report(
    manifest: Dict[str, Any],
    returns: pd.DataFrame,
    destination: Path,
) -> None:
    streams = manifest["streams"]
    swing_states = returns.loc[
        returns["state_classification"].eq("swing"),
        "state_code",
    ].tolist()
    lines = [
        "# Phase 1 Ingestion Report",
        "",
        "## Original PDF Data-Stream Contract",
        "",
        "| PDF stream | Current inputs | Status |",
        "|---|---|---|",
        "| Stream A - Social media | `twitter_donald_trump`, `twitter_joe_biden` | Available with gaps |",
        "| Stream B - Exogenous events | `political_events` | Available with gaps |",
        "| Stream C - Electoral benchmarks | `electoral_returns` | Available with gaps |",
        "",
        "All three PDF stream families are present. `Available with gaps` means that ingestion exists but the current dataset does not yet satisfy every original-PDF requirement. The controlling audit is `docs/PHASE1_DATA_STREAM_ALIGNMENT.md`.",
        "",
        "## Summary",
        "",
        "| Stream | Records | Invalid CSV Rows |",
        "|---|---:|---:|",
    ]
    for name, metrics in streams.items():
        lines.append(
            f"| {name} | {metrics['record_count']:,} | {metrics.get('invalid_csv_rows', 0):,} |"
        )
    lines.extend(
        [
            "",
            "## Twitter Coverage",
            "",
        ]
    )
    for name in ("twitter_donald_trump", "twitter_joe_biden"):
        metrics = streams[name]
        lines.append(
            f"- `{name}`: {metrics['minimum_date_utc']} through {metrics['maximum_date_utc']}."
        )
        lines.append(f"- `{name}` missing counts: `{metrics['missing_counts']}`.")
    lines.extend(
        [
            "",
            "## Electoral Benchmarks",
            "",
            f"- FEC rows: {len(returns)} states/DC.",
            f"- Swing states at the 5-point threshold: {', '.join(swing_states)}.",
            "",
            "## Major Figures",
            "",
            "- `output/graphs/phase1/twitter_daily_volume.png` shows how valid tweet-record volume changes by UTC day for the two candidate hashtag streams. It is retained because temporal coverage and volume variation directly affect later event and sentiment analysis.",
            (
                "- `output/graphs/phase1/twitter_location_coverage.png` compares usable "
                "and missing user-location text. Missing location affects "
                f"{100 * streams['twitter_donald_trump']['missing_counts']['user_loc'] / streams['twitter_donald_trump']['record_count']:.1f}% "
                "of the Donald Trump stream and "
                f"{100 * streams['twitter_joe_biden']['missing_counts']['user_loc'] / streams['twitter_joe_biden']['record_count']:.1f}% "
                "of the Joe Biden stream, which limits later state-level mapping."
            ),
            "",
            "## Data Quality Notes",
            "",
            "- Kaggle CSV rows with an invalid column count were rejected and counted.",
            "- The Kaggle dataset does not provide replies; the canonical `replies` field is null.",
            "- The downloaded Kaggle files cover October 15 through November 8, not the broader planned October 8 through November 15 window.",
            "- Tweet and user IDs are retained as source strings because the CSV stores them in scientific notation.",
            "- Duplicate tweets remain untouched for Phase 2.",
        ]
    )
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _required_text(record: Dict[str, Any], field: str) -> str:
    value = record.get(field)
    if value is None or not str(value).strip():
        raise ValueError(f"Required text field is missing: {field}")
    return str(value).strip()


def _required_int(record: Dict[str, Any], field: str) -> int:
    value = int(record[field])
    if value < 0:
        raise ValueError(f"Required integer field must be non-negative: {field}")
    return value


if __name__ == "__main__":
    result = run_phase1(PROJECT_ROOT)
    print(json.dumps(result, indent=2))
