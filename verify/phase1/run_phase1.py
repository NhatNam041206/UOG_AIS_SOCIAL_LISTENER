"""Execute and verify complete Phase 1 multi-source ingestion."""

from __future__ import annotations

import html
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator

import pandas as pd

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
    manifest["notes"] = [
        "Malformed Kaggle CSV rows were rejected and counted during Arrow streaming.",
        "The Kaggle source has no replies field; canonical replies values are null.",
        "The downloaded Kaggle files cover October 15 through November 8.",
        "Tweet and user IDs remain source strings because the CSV uses scientific notation.",
        "Exact duplicate tweets are retained for Phase 2 deduplication.",
    ]
    manifest_path = result_dir / "ingestion_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    _write_record_count_graph(manifest, graph_dir / "record_counts.svg")
    _write_daily_volume_graph(daily_volume, graph_dir / "twitter_daily_volume.svg")
    _write_report(manifest, returns, report_dir / "ingestion_report.md")
    return manifest


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


def _write_record_count_graph(manifest: Dict[str, Any], destination: Path) -> None:
    labels = list(manifest["streams"])
    values = [manifest["streams"][label]["record_count"] for label in labels]
    _write_bar_svg(labels, values, "Phase 1 Record Counts", destination)


def _write_daily_volume_graph(
    daily_volume: Counter[tuple[str, str]],
    destination: Path,
) -> None:
    dates = sorted({date for _, date in daily_volume})
    candidates = ["donald_trump", "joe_biden"]
    width, height = 1200, 650
    left, top, chart_width, chart_height = 90, 70, 1050, 480
    maximum = max(daily_volume.values(), default=1)
    colors = {"donald_trump": "#D94B4B", "joe_biden": "#3977C3"}
    elements = [_svg_header(width, height), '<rect width="100%" height="100%" fill="white"/>']
    elements.append('<text x="600" y="35" text-anchor="middle" font-size="22">Twitter Daily Volume</text>')
    elements.append(f'<line x1="{left}" y1="{top + chart_height}" x2="{left + chart_width}" y2="{top + chart_height}" stroke="#333"/>')
    elements.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_height}" stroke="#333"/>')
    for candidate in candidates:
        points = []
        for index, date in enumerate(dates):
            x = left + (index * chart_width / max(len(dates) - 1, 1))
            y = top + chart_height - daily_volume[(candidate, date)] * chart_height / maximum
            points.append(f"{x:.1f},{y:.1f}")
        elements.append(
            f'<polyline points="{" ".join(points)}" fill="none" stroke="{colors[candidate]}" stroke-width="3"/>'
        )
    for index, date in enumerate(dates):
        if index % 4 == 0 or index == len(dates) - 1:
            x = left + (index * chart_width / max(len(dates) - 1, 1))
            elements.append(f'<text x="{x:.1f}" y="580" font-size="11" text-anchor="end" transform="rotate(-35 {x:.1f} 580)">{html.escape(date)}</text>')
    elements.append('<text x="930" y="42" fill="#D94B4B">Donald Trump</text>')
    elements.append('<text x="1040" y="42" fill="#3977C3">Joe Biden</text>')
    elements.append("</svg>")
    destination.write_text("\n".join(elements), encoding="utf-8")


def _write_bar_svg(
    labels: list[str],
    values: list[int],
    title: str,
    destination: Path,
) -> None:
    width, height = 1000, 620
    left, top, chart_height = 110, 70, 430
    bar_width, gap = 130, 70
    maximum = max(values, default=1)
    elements = [_svg_header(width, height), '<rect width="100%" height="100%" fill="white"/>']
    elements.append(f'<text x="500" y="35" text-anchor="middle" font-size="22">{html.escape(title)}</text>')
    elements.append(f'<line x1="{left}" y1="{top + chart_height}" x2="930" y2="{top + chart_height}" stroke="#333"/>')
    for index, (label, value) in enumerate(zip(labels, values)):
        x = left + 50 + index * (bar_width + gap)
        bar_height = value * chart_height / maximum
        y = top + chart_height - bar_height
        elements.append(f'<rect x="{x}" y="{y:.1f}" width="{bar_width}" height="{bar_height:.1f}" fill="#3977C3"/>')
        elements.append(f'<text x="{x + bar_width / 2}" y="{y - 8:.1f}" text-anchor="middle" font-size="13">{value:,}</text>')
        elements.append(f'<text x="{x + bar_width / 2}" y="535" text-anchor="middle" font-size="12">{html.escape(label)}</text>')
    elements.append("</svg>")
    destination.write_text("\n".join(elements), encoding="utf-8")


def _svg_header(width: int, height: int) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'


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
