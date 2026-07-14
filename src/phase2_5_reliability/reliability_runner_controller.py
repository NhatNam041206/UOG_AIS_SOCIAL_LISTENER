"""Configuration-driven, examination-only Phase 2.5 production controller."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .dataset_schema_profiler import DatasetSchemaProfiler, validate_reliability_config
from .duplicate_amplification_profiler import DuplicateAmplificationProfiler
from .mitigation_register_builder import MitigationRegisterBuilder
from .model_suitability_profiler import ModelSuitabilityProfiler
from .phase_linkage_builder import PhaseLinkageBuilder
from .reliability_report_generator import ReliabilityReportGenerator
from .sarcasm_irony_risk_profiler import SarcasmIronyRiskProfiler
from .sentiment_ambiguity_profiler import SentimentAmbiguityProfiler
from .spatial_validity_profiler import SpatialValidityProfiler
from .temporal_coverage_profiler import TemporalCoverageProfiler
from .textual_evidence_profiler import TextualEvidenceProfiler
from .user_representativeness_profiler import UserRepresentativenessProfiler


RISK_COLUMNS = [
    "textual_evidence_risk", "sentiment_ambiguity_risk", "sarcasm_irony_risk",
    "user_representativeness_risk", "duplicate_amplification_risk", "spatial_validity_risk",
    "temporal_coverage_risk", "model_suitability_risk",
]
AVAILABILITY_FIELDS = [
    "prior_url_evidence_available", "language_diagnostic_available", "roberta_diagnostic_available",
    "baseline_roberta_diagnostic_available", "location_mapping_available",
]


class ReliabilityRunnerController:
    """Orchestrate profilers while preserving every canonical input value."""

    def __init__(self, project_root: str | Path, config: dict[str, Any]) -> None:
        validate_reliability_config(config)
        self.root = Path(project_root).resolve()
        self.config = config

    def run(self) -> dict[str, Any]:
        execution = self.config["execution"]
        if execution["execute_mitigation"] is not False:
            raise ValueError("Phase 2.5 mitigation is prohibited")
        paths = self._input_paths()
        for name, path in paths["required"].items():
            if not path.exists():
                raise FileNotFoundError(f"Required Phase 2.5 input is missing ({name}): {path}")
        source = pd.read_parquet(paths["required"]["sentiment_tweets"])
        schema = DatasetSchemaProfiler(self.config["columns"]).profile(source)
        validation = pd.read_parquet(paths["required"]["roberta_validation_sample"])
        evaluation = self.select_records(source, validation)
        canonical_columns = list(source.columns)
        canonical_before = evaluation[canonical_columns].copy(deep=True)
        evaluation = self._attach_validation_diagnostics(evaluation, validation)
        user_metrics = pd.read_parquet(paths["required"]["user_activity_metrics"])
        threshold_audit = json.loads(paths["required"]["user_activity_threshold_audit"].read_text(encoding="utf-8"))
        events = pd.read_parquet(paths["required"]["political_events"])
        original_text = self._original_text_series(evaluation, paths["optional"].get("original_text_url_evidence"))
        columns = self.config["columns"]
        blocks: list[pd.DataFrame] = []
        blocks.append(TextualEvidenceProfiler(columns["text"]).profile(evaluation, original_text))
        blocks.append(SentimentAmbiguityProfiler().profile(evaluation))
        blocks.append(SarcasmIronyRiskProfiler(columns["text"]).profile(evaluation))
        user_block, threshold_summary = UserRepresentativenessProfiler(columns["user_id"]).profile(
            evaluation, user_metrics, threshold_audit
        )
        blocks.append(user_block)
        duplicate_block = DuplicateAmplificationProfiler(
            columns["text"], columns["user_id"], self.config["duplicate_proxy"]["maximum_signature_length"]
        ).profile(evaluation, self.config["provenance"]["phase2_exact_duplicates_removed"])
        blocks.append(duplicate_block)
        spatial_block = SpatialValidityProfiler(columns["user_location"]).profile(evaluation)
        blocks.append(spatial_block)
        temporal_config = self.config["temporal"]
        temporal_block, temporal_diagnostics = TemporalCoverageProfiler(
            columns["timestamp"], temporal_config["event_window_hours"], temporal_config["event_risk_horizon_hours"]
        ).profile(evaluation, events)
        blocks.append(temporal_block)
        blocks.append(ModelSuitabilityProfiler().profile(evaluation))
        scores = evaluation.copy(deep=True)
        for block in blocks:
            collisions = sorted(set(block.columns) & set(scores.columns))
            if collisions:
                raise ValueError(f"Profiler output columns collide with canonical data: {collisions}")
            scores = pd.concat([scores, block], axis=1)
        self._assert_canonical_preservation(canonical_before, scores[canonical_columns])
        self._assert_score_bounds(scores)
        linkage = PhaseLinkageBuilder().build()
        mitigation = MitigationRegisterBuilder().build(linkage)
        criterion_summary = self._criterion_summary(scores)
        availability_summary = self._availability_summary(scores)
        output_paths = self._output_paths(execution["mode"])
        for path in output_paths.values():
            path.parent.mkdir(parents=True, exist_ok=True)
        scores.to_parquet(output_paths["scores"], index=False)
        user_block.to_parquet(output_paths["user_diagnostics"], index=False)
        duplicate_block.to_parquet(output_paths["duplicate_diagnostics"], index=False)
        spatial_block.to_parquet(output_paths["location_diagnostics"], index=False)
        temporal_diagnostics.to_parquet(output_paths["temporal_diagnostics"], index=False)
        criterion_summary.to_csv(output_paths["criterion_summary"], index=False)
        availability_summary.to_csv(output_paths["availability_summary"], index=False)
        threshold_summary.to_csv(output_paths["threshold_summary"], index=False)
        linkage.to_csv(output_paths["phase_linkage"], index=False)
        mitigation.to_csv(output_paths["mitigation_register"], index=False)
        schema_manifest = {
            **schema,
            "run_mode": execution["mode"],
            "canonical_columns_preserved": True,
            "availability_fields": AVAILABILITY_FIELDS,
            "risk_columns": RISK_COLUMNS,
            "missing_evidence_policy": "null",
        }
        output_paths["schema_manifest"].write_text(json.dumps(schema_manifest, indent=2), encoding="utf-8")
        manifest = self._manifest(source, scores, availability_summary, output_paths)
        output_paths["run_manifest"].write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        report = ReliabilityReportGenerator().render(manifest, criterion_summary, availability_summary, threshold_summary)
        output_paths["report"].write_text(report, encoding="utf-8")
        return manifest

    def select_records(self, source: pd.DataFrame, validation: pd.DataFrame) -> pd.DataFrame:
        execution = self.config["execution"]
        mode = execution["mode"]
        seed = int(execution["seed"])
        if mode == "full":
            return source.reset_index(drop=True).copy()
        size_key = "smoke_size" if mode == "smoke" else "sample_size"
        selected = source.sample(n=min(int(execution[size_key]), len(source)), random_state=seed).copy()
        if mode == "sample" and execution.get("include_roberta_validation_rows_in_sample", True):
            selected = pd.concat([selected, validation], ignore_index=True, sort=False)
            selected = selected.drop_duplicates(subset=[self.config["columns"]["tweet_id"]], keep="last")
        return selected.reset_index(drop=True)

    def _attach_validation_diagnostics(
        self,
        evaluation: pd.DataFrame,
        validation: pd.DataFrame,
    ) -> pd.DataFrame:
        id_column = self.config["columns"]["tweet_id"]
        if id_column not in evaluation or id_column not in validation:
            return evaluation.copy()
        if validation[id_column].duplicated().any():
            raise ValueError("RoBERTa validation diagnostics require unique tweet IDs")
        diagnostic_columns = [
            column for column in validation.columns
            if column != id_column and column not in evaluation.columns
        ]
        if not diagnostic_columns:
            return evaluation.copy()
        diagnostics = validation[[id_column, *diagnostic_columns]].set_index(id_column)
        return evaluation.join(diagnostics, on=id_column)

    def _input_paths(self) -> dict[str, dict[str, Path | None]]:
        result: dict[str, dict[str, Path | None]] = {"required": {}, "optional": {}}
        for group in result:
            for name, value in self.config["inputs"].get(group, {}).items():
                result[group][name] = None if value is None else (self.root / value).resolve()
        return result

    def _output_paths(self, mode: str) -> dict[str, Path]:
        data = self.root / self.config["outputs"]["data_root"] / mode
        results = self.root / self.config["outputs"]["results_root"] / mode
        reports = self.root / self.config["outputs"]["reports_root"] / mode
        return {
            "scores": data / "tweet_reliability_scores.parquet",
            "user_diagnostics": data / "user_activity_diagnostics.parquet",
            "duplicate_diagnostics": data / "duplicate_amplification_diagnostics.parquet",
            "location_diagnostics": data / "location_confidence_diagnostics.parquet",
            "temporal_diagnostics": data / "temporal_coverage_diagnostics.parquet",
            "criterion_summary": results / "criterion_score_summary.csv",
            "availability_summary": results / "evidence_availability_summary.csv",
            "threshold_summary": results / "threshold_position_summary.csv",
            "phase_linkage": results / "phase_linkage_matrix.csv",
            "mitigation_register": results / "mitigation_decision_register.csv",
            "schema_manifest": results / "phase2_5_schema_manifest.json",
            "run_manifest": results / "phase2_5_run_manifest.json",
            "report": reports / "phase2_5_reliability_report.md",
        }

    def _original_text_series(self, evaluation: pd.DataFrame, path: Path | None) -> pd.Series | None:
        if path is None:
            return None
        if not path.exists():
            raise FileNotFoundError(f"Configured URL evidence input is missing: {path}")
        original = pd.read_parquet(path)
        id_column = self.config["columns"]["tweet_id"]
        text_candidates = [column for column in ("original_tweet", "tweet_original", "tweet") if column in original]
        if id_column not in original or not text_candidates or original[id_column].duplicated().any():
            raise ValueError("Original-text URL evidence requires unique tweet IDs and an original text column")
        mapping = original.set_index(id_column)[text_candidates[0]]
        return evaluation[id_column].map(mapping).set_axis(evaluation.index)

    @staticmethod
    def _assert_canonical_preservation(before: pd.DataFrame, after: pd.DataFrame) -> None:
        try:
            pd.testing.assert_frame_equal(before.reset_index(drop=True), after.reset_index(drop=True), check_dtype=True)
        except AssertionError as error:
            raise ValueError("A Phase 2.5 profiler modified canonical input values") from error

    @staticmethod
    def _assert_score_bounds(scores: pd.DataFrame) -> None:
        for column in RISK_COLUMNS:
            values = pd.to_numeric(scores[column], errors="coerce").dropna()
            if not values.between(0, 1).all():
                raise ValueError(f"Risk score is outside [0, 1]: {column}")

    @staticmethod
    def _criterion_summary(scores: pd.DataFrame) -> pd.DataFrame:
        rows = []
        for column in RISK_COLUMNS:
            values = pd.to_numeric(scores[column], errors="coerce")
            rows.append({
                "risk_score": column, "available_count": int(values.notna().sum()),
                "unavailable_count": int(values.isna().sum()),
                "mean": float(values.mean()) if values.notna().any() else None,
                "minimum": float(values.min()) if values.notna().any() else None,
                "maximum": float(values.max()) if values.notna().any() else None,
            })
        return pd.DataFrame(rows)

    @staticmethod
    def _availability_summary(scores: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame([
            {
                "evidence": column,
                "available_count": int(scores[column].fillna(False).astype(bool).sum()),
                "unavailable_count": int((~scores[column].fillna(False).astype(bool)).sum()),
            }
            for column in AVAILABILITY_FIELDS
        ])

    def _manifest(
        self,
        source: pd.DataFrame,
        scores: pd.DataFrame,
        availability: pd.DataFrame,
        output_paths: dict[str, Path],
    ) -> dict[str, Any]:
        execution = self.config["execution"]
        id_column = self.config["columns"]["tweet_id"]
        checksum = hashlib.sha256("\n".join(scores[id_column].astype(str)).encode("utf-8")).hexdigest()
        availability_counts = dict(zip(availability["evidence"], availability["available_count"]))
        return {
            "run_id": f"phase2_5_{execution['mode']}_seed{execution['seed']}",
            "run_mode": execution["mode"],
            "input_path": self.config["inputs"]["required"]["sentiment_tweets"],
            "input_row_count": int(len(source)),
            "output_row_count": int(len(scores)),
            "sample_size": None if execution["mode"] == "full" else int(execution["smoke_size" if execution["mode"] == "smoke" else "sample_size"]),
            "seed": int(execution["seed"]),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sample_row_checksum": checksum,
            "execute_mitigation": False,
            "canonical_columns_preserved": True,
            "all_mitigation_decisions": "pending",
            "phase2_prefilter_user_count": int(self.config["provenance"]["phase2_prefilter_user_count"]),
            "approved_activity_threshold": float(self.config["provenance"]["approved_activity_threshold"]),
            "availability_counts": {key: int(value) for key, value in availability_counts.items()},
            "output_paths": {name: str(path) for name, path in output_paths.items()},
            "scope_note": "Sample verification only; not full-dataset findings." if execution["mode"] != "full" else "Full mode contract defined.",
        }
