"""Create the mandatory all-pending Phase 2.5 decision register."""

from __future__ import annotations

import pandas as pd


class MitigationRegisterBuilder:
    DECISION = "Pending. Phase 2.5 is examination-only; no mitigation is approved or executed."

    def build(self, linkage: pd.DataFrame) -> pd.DataFrame:
        result = linkage.copy()
        result["observable_evidence"] = result["risk_score"]
        result["validation_needed"] = True
        result["sensitivity_test_needed"] = True
        result["mitigation_status"] = "pending"
        result["mitigation_decision"] = self.DECISION
        return result
