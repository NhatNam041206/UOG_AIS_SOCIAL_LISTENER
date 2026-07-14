"""Link separate reliability dimensions to downstream analytical tasks."""

from __future__ import annotations

import pandas as pd


class PhaseLinkageBuilder:
    def build(self) -> pd.DataFrame:
        rows = [
            ("textual_evidence", "textual_evidence_risk", "Phase 3/4/5"),
            ("sentiment_ambiguity", "sentiment_ambiguity_risk", "Phase 3/4/5"),
            ("sarcasm_irony_proxy", "sarcasm_irony_risk", "Phase 3/4/5"),
            ("user_representativeness", "user_representativeness_risk", "Phase 4/5"),
            ("duplicate_amplification_proxy", "duplicate_amplification_risk", "Phase 4/5"),
            ("spatial_validity", "spatial_validity_risk", "Phase 4/5 state analysis"),
            ("temporal_coverage", "temporal_coverage_risk", "Phase 4/5 temporal analysis"),
            ("model_suitability", "model_suitability_risk", "Phase 3/4/5"),
        ]
        return pd.DataFrame(rows, columns=["criterion", "risk_score", "affected_phase"]).assign(
            mitigation_status="pending"
        )
