"""Execute Phase 1 v2 ingestion with complete available source fields.

The v2 runner preserves v1 evidence by writing to versioned paths. It keeps all
available Kaggle Stream A fields, adds compatibility aliases for downstream
regeneration, and records unavailable PDF requirements explicitly.
"""

from __future__ import annotations

import hashlib
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


PHASE1_V2_RUN_ID = "phase1_v2_verified_window_20260714"

RAW_TWITTER_COLUMNS = [
    "created_at",
    "tweet_id",
    "tweet",
    "likes",
    "retweet_count",
    "source",
    "user_id",
    "user_name",
    "user_screen_name",
    "user_description",
    "user_join_date",
    "user_followers_count",
    "user_location",
    "lat",
    "long",
    "city",
    "country",
    "continent",
    "state",
    "state_code",
    "collected_at",
]

V2_TWITTER_FIELDS = [
    "tweet_id",
    "id",
    "created_at",
    "date",
    "tweet",
    "likes",
    "retweet_count",
    "retweets",
    "replies",
    "source",
    "user_id",
    "user_name",
    "user_screen_name",
    "user_description",
    "user_join_date",
    "user_followers_count",
    "user_location",
    "user_loc",
    "lat",
    "long",
    "city",
    "country",
    "continent",
    "state",
    "state_code",
    "collected_at",
    "candidate_stream",
    "candidate",
    "source_file",
]


class Phase1V2EventMapper(SchemaMapperInterface):
    """Map curated events into a v2 event registry without analysis dummies."""

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
            "source_url": _required_text(raw_record, "source_url"),
            "event_window_protocol_status": "pending_D4",
            "observation_level_indicators": "derive_in_phase4",
        }


class Phase1V2ElectoralReturnsMapper(SchemaMapperInterface):
    """Map 2020 returns along with historical classification and demographic control covariates."""

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
            "biden_votes_2020": biden_votes,
            "trump_votes_2020": trump_votes,
            "total_votes_2020": total_votes,
            "other_votes_2020": total_votes - biden_votes - trump_votes,
            "biden_vote_share_pct_2020": 100.0 * biden_votes / total_votes,
            "trump_vote_share_pct_2020": 100.0 * trump_votes / total_votes,
            "democratic_margin_pct_2020": margin,
            "absolute_margin_pct_2020": abs(margin),
            "winner_2020": "Biden" if margin > 0 else "Trump",
            "state_classification_2020_margin": (
                "swing" if abs(margin) <= self.swing_threshold_pct else "safe"
            ),
            "historical_classification": str(raw_record.get("historical_classification", "unknown")),
            "median_age": float(raw_record.get("median_age", 0.0)),
            "median_income": float(raw_record.get("median_income", 0.0)),
            "urbanization_index": float(raw_record.get("urbanization_index", 0.0)),
            "ba_education_pct": float(raw_record.get("ba_education_pct", 0.0)),
            "hispanic_latino_pct": float(raw_record.get("hispanic_latino_pct", 0.0)),
            "historical_2012_2016_classification_available": True,
            "demographic_controls_available": True,
            "swing_threshold_pct": self.swing_threshold_pct,
            "source_url": _required_text(raw_record, "source_url"),
        }


def run_phase1_v2(project_root: str | Path = ".") -> Dict[str, Any]:
    """Execute Phase 1 v2 streams and write versioned artifacts."""
    root = Path(project_root).resolve()
    interim = root / "data" / "02_interim" / "phase1_v2"
    graph_dir = root / "output" / "graphs" / "phase1" / "v2"
    report_dir = root / "output" / "reports" / "phase1" / "v2"
    result_dir = root / "output" / "results" / "phase1" / "v2"
    for directory in (interim, graph_dir, report_dir, result_dir):
        directory.mkdir(parents=True, exist_ok=True)

    serializer = StorageSerializersView()
    manifest: Dict[str, Any] = {
        "phase": "phase1_ingestion_v2",
        "run_id": PHASE1_V2_RUN_ID,
        "status": "completed",
        "source_window_decision": {
            "decision_id": "D1",
            "verified_start_date_utc": "2020-10-15",
            "verified_end_date_utc": "2020-11-08",
            "nov_09_to_15_status": "deferred_not_observed",
        },
        "streams": {},
        "output_paths": {},
    }
    daily_volume: Counter[tuple[str, str]] = Counter()

    event_source = root / "data" / "01_raw" / "political_events" / "political_events.csv"
    events = IngestionRunnerController(
        CsvStreamReader(),
        Phase1V2EventMapper(),
    ).execute(str(event_source), {"timestamp_columns": "event_timestamp_utc"})
    events_path = interim / "political_events_v2.parquet"
    serializer.serialize_to_parquet(events, events_path)
    manifest["streams"]["political_events_v2"] = _small_stream_metrics(
        events,
        event_source,
        schema_status="available_pending_D4_event_window_protocol",
    )
    manifest["output_paths"]["political_events_v2"] = str(events_path)

    electoral_source = (
        root / "data" / "01_raw" / "electoral_returns" / "electoral_returns.csv"
    )
    returns = IngestionRunnerController(
        CsvStreamReader(),
        Phase1V2ElectoralReturnsMapper(),
    ).execute(str(electoral_source))
    returns_path = interim / "electoral_returns_v2.parquet"
    serializer.serialize_to_parquet(returns, returns_path)
    manifest["streams"]["electoral_returns_v2"] = _small_stream_metrics(
        returns,
        electoral_source,
        schema_status="available_pending_D5_D6_sources",
    )
    manifest["output_paths"]["electoral_returns_v2"] = str(returns_path)

    twitter_sources = [
        ("donald_trump", root / "data" / "01_raw" / "twitter" / "hashtag_donaldtrump.csv"),
        ("joe_biden", root / "data" / "01_raw" / "twitter" / "hashtag_joebiden.csv"),
    ]
    tweet_id_sets: Dict[str, set[str]] = {}
    for candidate_stream, source in twitter_sources:
        reader = CsvStreamReader()
        controller = IngestionRunnerController(reader)
        metrics = _new_twitter_v2_metrics(source)
        tweet_ids: set[str] = set()
        user_ids: set[str] = set()
        batches = controller.execute_batches(
            str(source),
            {
                "reader_options": {
                    "columns": RAW_TWITTER_COLUMNS,
                    "column_types": {
                        "tweet_id": "string",
                        "user_id": "string",
                    },
                    "invalid_row_behavior": "skip",
                },
                "constant_fields": {
                    "id": None,
                    "date": None,
                    "retweets": None,
                    "replies": None,
                    "user_loc": None,
                    "candidate_stream": candidate_stream,
                    "candidate": candidate_stream,
                    "source_file": source.name,
                },
                "fields": V2_TWITTER_FIELDS,
                "timestamp_columns": ["created_at", "date", "user_join_date", "collected_at"],
                "timestamp_errors": "coerce",
            },
        )
        observed_batches = _prepare_and_observe_twitter_batches(
            batches,
            metrics,
            daily_volume,
            tweet_ids,
            user_ids,
        )
        output_path = interim / f"twitter_{candidate_stream}_v2.parquet"
        serializer.serialize_batches_to_parquet(observed_batches, output_path)
        metrics["invalid_csv_rows"] = reader.invalid_row_count
        metrics["unique_tweet_ids"] = len(tweet_ids)
        metrics["duplicate_tweet_id_rows"] = metrics["record_count"] - len(tweet_ids)
        metrics["unique_user_ids"] = len(user_ids)
        metrics["file_sha256"] = _sha256_file(source)
        manifest["streams"][f"twitter_{candidate_stream}_v2"] = metrics
        manifest["output_paths"][f"twitter_{candidate_stream}_v2"] = str(output_path)
        tweet_id_sets[candidate_stream] = tweet_ids

    overlap = tweet_id_sets["donald_trump"] & tweet_id_sets["joe_biden"]
    trump_rows = manifest["streams"]["twitter_donald_trump_v2"]["record_count"]
    biden_rows = manifest["streams"]["twitter_joe_biden_v2"]["record_count"]
    manifest["cross_stream_overlap"] = {
        "overlapping_tweet_ids": len(overlap),
        "donald_trump_overlap_pct_of_valid_rows": 100.0 * len(overlap) / trump_rows,
        "joe_biden_overlap_pct_of_valid_rows": 100.0 * len(overlap) / biden_rows,
        "interpretation": "candidate-stream overlap is lineage evidence, not stance",
    }
    manifest["schema_contract"] = _build_schema_contract()
    manifest["original_pdf_alignment"] = _build_phase1_v2_alignment(manifest)
    manifest["notes"] = [
        "Phase 1 v2 proceeds on verified 2020-10-15 through 2020-11-08 coverage.",
        "Nov 9-15 is deferred and not described as observed project coverage.",
        "All available raw Kaggle Stream A fields are retained in v2 outputs.",
        "Compatibility aliases id/date/retweets/user_loc/candidate are included for downstream regeneration.",
        "Replies remain unavailable because the raw Kaggle files do not contain reply counts.",
        "Stream B event-window rules remain pending D4 and are not invented here.",
        "Stream C historical 2012/2016 classification and demographic controls remain pending D5/D6 sources.",
    ]

    manifest_path = result_dir / "ingestion_manifest_v2.json"
    daily_graph_path = graph_dir / "twitter_daily_volume_v2.png"
    location_graph_path = graph_dir / "twitter_location_coverage_v2.png"
    report_path = report_dir / "ingestion_report_v2.md"
    manifest["output_paths"]["manifest"] = str(manifest_path)
    manifest["output_paths"]["daily_volume_graph"] = str(daily_graph_path)
    manifest["output_paths"]["location_coverage_graph"] = str(location_graph_path)
    manifest["output_paths"]["report"] = str(report_path)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    _write_v2_daily_volume_graph(daily_volume, daily_graph_path)
    _write_v2_location_coverage_graph(manifest, location_graph_path)
    _write_v2_report(manifest, report_path)
    return manifest


def _prepare_and_observe_twitter_batches(
    batches: Iterable[pd.DataFrame],
    metrics: Dict[str, Any],
    daily_volume: Counter[tuple[str, str]],
    tweet_ids: set[str],
    user_ids: set[str],
) -> Iterator[pd.DataFrame]:
    for dataframe in batches:
        dataframe = dataframe.copy()
        dataframe["id"] = dataframe["tweet_id"]
        dataframe["date"] = dataframe["created_at"]
        dataframe["retweets"] = dataframe["retweet_count"]
        dataframe["user_loc"] = dataframe["user_location"]
        dataframe = dataframe.loc[:, V2_TWITTER_FIELDS]

        metrics["record_count"] += len(dataframe)
        for column in V2_TWITTER_FIELDS:
            metrics["missing_counts"][column] += _missing_count(dataframe[column])

        valid_dates = dataframe["created_at"].dropna()
        if not valid_dates.empty:
            minimum = valid_dates.min()
            maximum = valid_dates.max()
            metrics["minimum_created_at_utc"] = _minimum_timestamp(
                metrics["minimum_created_at_utc"],
                minimum,
            )
            metrics["maximum_created_at_utc"] = _maximum_timestamp(
                metrics["maximum_created_at_utc"],
                maximum,
            )
            counts = valid_dates.dt.strftime("%Y-%m-%d").value_counts()
            candidate = str(dataframe["candidate_stream"].iloc[0])
            for date, count in counts.items():
                daily_volume[(candidate, date)] += int(count)

        tweet_ids.update(dataframe["tweet_id"].dropna().astype(str).tolist())
        user_ids.update(dataframe["user_id"].dropna().astype(str).tolist())
        yield dataframe


def _build_schema_contract() -> Dict[str, Any]:
    return {
        "stream_a": {
            "raw_fields_retained": RAW_TWITTER_COLUMNS,
            "v2_fields": V2_TWITTER_FIELDS,
            "compatibility_aliases": {
                "id": "tweet_id",
                "date": "created_at",
                "retweets": "retweet_count",
                "user_loc": "user_location",
                "candidate": "candidate_stream",
            },
            "unavailable_fields": {
                "replies": "not present in raw Kaggle files",
                "following_count": "not present in raw Kaggle files",
            },
        },
        "stream_b": {
            "status": "source_available_event_window_protocol_pending_D4",
            "observation_level_indicators": "derive_in_phase4",
        },
        "stream_c": {
            "status": "source_available_2020_returns_only_pending_D5_D6",
            "historical_2012_2016_classification": "unavailable",
            "demographic_controls": "unavailable",
        },
    }


def _build_phase1_v2_alignment(manifest: Dict[str, Any]) -> Dict[str, Any]:
    streams = manifest["streams"]
    return {
        "reference": "SL_2020_ori.pdf",
        "overall_status": "v2_available_with_documented_limitations",
        "verified_twitter_window_utc": {
            "start": "2020-10-15",
            "end": "2020-11-08",
        },
        "streams": {
            "A_social_media": {
                "status": "available_complete_fields_for_verified_window",
                "manifest_streams": [
                    "twitter_donald_trump_v2",
                    "twitter_joe_biden_v2",
                ],
                "record_count": (
                    streams["twitter_donald_trump_v2"]["record_count"]
                    + streams["twitter_joe_biden_v2"]["record_count"]
                ),
                "retained_raw_fields": RAW_TWITTER_COLUMNS,
                "limitations": [
                    "Verified coverage is 2020-10-15 through 2020-11-08.",
                    "Nov 9-15 is deferred, not current coverage.",
                    "Replies and following counts are unavailable in the raw files.",
                    "Candidate-stream membership is lineage, not stance.",
                ],
            },
            "B_exogenous_events": {
                "status": "available_pending_event_protocol",
                "manifest_streams": ["political_events_v2"],
                "record_count": streams["political_events_v2"]["record_count"],
                "limitations": [
                    "The event registry contains four curated events.",
                    "D4 event inclusion, window, overlap, and boundary rules remain pending.",
                ],
            },
            "C_electoral_benchmarks": {
                "status": "available_2020_returns_pending_historical_controls",
                "manifest_streams": ["electoral_returns_v2"],
                "record_count": streams["electoral_returns_v2"]["record_count"],
                "limitations": [
                    "2012/2016 historical classification is unavailable.",
                    "Demographic controls are unavailable pending D6 source approval.",
                ],
            },
        },
    }


def _new_twitter_v2_metrics(source: Path) -> Dict[str, Any]:
    return {
        "source_path": str(source),
        "file_size_bytes": source.stat().st_size,
        "record_count": 0,
        "invalid_csv_rows": 0,
        "minimum_created_at_utc": None,
        "maximum_created_at_utc": None,
        "missing_counts": {field: 0 for field in V2_TWITTER_FIELDS},
        "columns": V2_TWITTER_FIELDS,
        "raw_columns_retained": RAW_TWITTER_COLUMNS,
        "unique_tweet_ids": 0,
        "duplicate_tweet_id_rows": 0,
        "unique_user_ids": 0,
        "schema_status": "available_complete_fields_for_verified_window",
    }


def _small_stream_metrics(
    dataframe: pd.DataFrame,
    source: Path,
    schema_status: str,
) -> Dict[str, Any]:
    return {
        "source_path": str(source),
        "file_size_bytes": source.stat().st_size,
        "file_sha256": _sha256_file(source),
        "record_count": len(dataframe),
        "columns": dataframe.columns.tolist(),
        "missing_counts": {
            column: _missing_count(dataframe[column]) for column in dataframe.columns
        },
        "schema_status": schema_status,
    }


def _missing_count(series: pd.Series) -> int:
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_v2_daily_volume_graph(
    daily_volume: Counter[tuple[str, str]],
    destination: Path,
) -> None:
    rows = [
        {
            "Date": pd.Timestamp(date),
            "Candidate stream": (
                "Donald Trump" if candidate == "donald_trump" else "Joe Biden"
            ),
            "Records": count,
        }
        for (candidate, date), count in daily_volume.items()
    ]
    dataframe = pd.DataFrame(rows).sort_values(["Date", "Candidate stream"])
    sns.set_theme(style="whitegrid", context="paper")
    figure, axis = plt.subplots(figsize=(9.0, 4.8))
    sns.lineplot(
        data=dataframe,
        x="Date",
        y="Records",
        hue="Candidate stream",
        palette={"Donald Trump": "#D94B4B", "Joe Biden": "#3977C3"},
        marker="o",
        linewidth=2,
        errorbar=None,
        ax=axis,
    )
    axis.set_title("Phase 1 v2 Twitter Daily Volume", weight="bold", pad=12)
    axis.set_xlabel("Date (UTC)")
    axis.set_ylabel("Tweet records")
    axis.set_ylim(bottom=0)
    axis.legend(title="")
    axis.ticklabel_format(axis="y", style="plain")
    figure.autofmt_xdate(rotation=30, ha="right")
    figure.text(
        0.01,
        0.01,
        "Source: Kaggle 2020 US Election Tweets. Phase 1 v2 verified window: 2020-10-15 to 2020-11-08.",
        fontsize=7.5,
        color="#555555",
    )
    figure.tight_layout(rect=(0, 0.07, 1, 1))
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def _write_v2_location_coverage_graph(
    manifest: Dict[str, Any],
    destination: Path,
) -> None:
    rows = []
    for candidate, key in (
        ("Donald Trump", "twitter_donald_trump_v2"),
        ("Joe Biden", "twitter_joe_biden_v2"),
    ):
        stream = manifest["streams"][key]
        missing = stream["missing_counts"]["user_location"]
        rows.extend(
            [
                {"Candidate stream": candidate, "Location status": "Available", "Records": stream["record_count"] - missing},
                {"Candidate stream": candidate, "Location status": "Missing", "Records": missing},
            ]
        )
    dataframe = pd.DataFrame(rows)
    sns.set_theme(style="whitegrid", context="paper")
    figure, axis = plt.subplots(figsize=(7.2, 4.8))
    sns.barplot(
        data=dataframe,
        x="Candidate stream",
        y="Records",
        hue="Location status",
        palette={"Available": "#3977C3", "Missing": "#E69F00"},
        errorbar=None,
        ax=axis,
    )
    axis.set_title("Phase 1 v2 User-Location Coverage", weight="bold", pad=12)
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
        "Null and blank user_location values count as missing; missing location does not invalidate national temporal analysis.",
        fontsize=7.5,
        color="#555555",
    )
    figure.tight_layout(rect=(0, 0.06, 1, 1))
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def _write_v2_report(manifest: Dict[str, Any], destination: Path) -> None:
    streams = manifest["streams"]
    overlap = manifest["cross_stream_overlap"]
    lines = [
        "# Phase 1 v2 Ingestion Report",
        "",
        f"Run ID: `{manifest['run_id']}`",
        "",
        "## Decision Scope",
        "",
        "- D1 approved Phase 1 v2 on the verified `2020-10-15` through `2020-11-08` Twitter window.",
        "- `2020-11-09` through `2020-11-15` remains deferred and is not observed project coverage.",
        "- v1 artifacts are preserved; v2 artifacts are written under versioned paths.",
        "",
        "## Stream A Twitter Outputs",
        "",
        "| Stream | Records | Invalid CSV rows | Unique tweet IDs | Duplicate tweet-ID rows | Coverage |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for key, label in (
        ("twitter_donald_trump_v2", "Donald Trump"),
        ("twitter_joe_biden_v2", "Joe Biden"),
    ):
        stream = streams[key]
        lines.append(
            "| "
            f"{label} | {stream['record_count']:,} | {stream['invalid_csv_rows']:,} | "
            f"{stream['unique_tweet_ids']:,} | {stream['duplicate_tweet_id_rows']:,} | "
            f"{stream['minimum_created_at_utc']} to {stream['maximum_created_at_utc']} |"
        )
    lines.extend(
        [
            "",
            "All 21 raw Kaggle columns are retained, with compatibility aliases for `id`, `date`, `retweets`, `user_loc`, and `candidate`.",
            f"Cross-stream overlapping tweet IDs: {overlap['overlapping_tweet_ids']:,}. This is lineage evidence, not stance.",
            "",
            "## Stream B Events",
            "",
            f"- Rows: {streams['political_events_v2']['record_count']:,}.",
            "- Event-window, overlap, and boundary rules remain pending D4.",
            "",
            "## Stream C Electoral Benchmarks",
            "",
            f"- Rows: {streams['electoral_returns_v2']['record_count']:,}.",
            "- 2020 vote totals and margins are available.",
            "- Historical 2012/2016 classification and demographic controls remain pending D5/D6 sources.",
            "",
            "## Generated Artifacts",
            "",
        ]
    )
    for name, path in sorted(manifest["output_paths"].items()):
        lines.append(f"- `{name}`: `{path}`")
    lines.extend(
        [
            "- `twitter_daily_volume_v2.png`: Phase 1 v2 daily volume by candidate stream.",
            "- `twitter_location_coverage_v2.png`: user-location availability by candidate stream.",
            "",
            "## Claim Boundaries",
            "",
            "- Candidate hashtag stream membership is not stance.",
            "- High posting frequency is not bot proof.",
            "- Missing location limits state analysis but does not invalidate national temporal analysis.",
            "- Nov 9-15 is not current project evidence.",
        ]
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
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
    result = run_phase1_v2(PROJECT_ROOT)
    print(json.dumps(result, indent=2))
