"""Task-specific location availability and state-mapping diagnostics."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd


US_STATES = {
    "AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California","CO":"Colorado",
    "CT":"Connecticut","DE":"Delaware","FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho",
    "IL":"Illinois","IN":"Indiana","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana",
    "ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan","MN":"Minnesota","MS":"Mississippi",
    "MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada","NH":"New Hampshire","NJ":"New Jersey",
    "NM":"New Mexico","NY":"New York","NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma",
    "OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota",
    "TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia","WA":"Washington",
    "WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming","DC":"District of Columbia",
}
STATE_NAMES = {name.lower(): code for code, name in US_STATES.items()}
NATIONAL = re.compile(r"^(usa|u\.?s\.?a?\.?|united states|america|united states of america)$", re.I)
FICTIONAL = re.compile(r"\b(earth|moon|mars|universe|internet|nowhere|middle of nowhere|maga country|home)\b", re.I)
NON_US = re.compile(r"\b(canada|mexico|united kingdom|uk|england|france|germany|india|australia|vietnam)\b", re.I)


def extract_states(location: str) -> list[str]:
    if not isinstance(location, str):
        return []
    lower = location.lower()
    matches = {code for name, code in STATE_NAMES.items() if re.search(rf"\b{re.escape(name)}\b", lower)}
    tokens = re.findall(r"(?<![A-Za-z])([A-Z]{2})(?![A-Za-z])", location)
    matches.update(token for token in tokens if token in US_STATES)
    return sorted(matches)


class SpatialValidityProfiler:
    """Keep missing, national, ambiguous, non-US, and fictional cases separate."""

    def __init__(self, location_column: str = "user_loc") -> None:
        self.location_column = location_column

    def profile(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        result = pd.DataFrame(index=dataframe.index)
        if self.location_column not in dataframe:
            result["location_availability"] = "unavailable_column"
            result["location_mapping_available"] = False
            result["spatial_validity_risk"] = np.nan
            return result
        raw = dataframe[self.location_column].astype("string")
        stripped = raw.str.strip()
        missing = raw.isna() | stripped.eq("")
        states = stripped.fillna("").map(extract_states)
        national = stripped.fillna("").map(lambda value: bool(NATIONAL.fullmatch(value)))
        fictional = stripped.fillna("").map(lambda value: bool(FICTIONAL.search(value)))
        non_us = stripped.fillna("").map(lambda value: bool(NON_US.search(value))) & states.map(len).eq(0)
        multi = states.map(len).gt(1)
        one = states.map(len).eq(1)
        ambiguous = ~missing & ~national & ~fictional & ~non_us & ~one
        result["location_availability"] = "available"
        result.loc[missing, "location_availability"] = "missing"
        result["location_mapping_available"] = ~missing
        result["matched_state"] = states.map(lambda values: ";".join(values) if values else pd.NA)
        result["state_mapping_confidence"] = np.nan
        result.loc[one, "state_mapping_confidence"] = 1.0
        result.loc[multi, "state_mapping_confidence"] = 0.25
        result.loc[national, "state_mapping_confidence"] = 0.0
        result.loc[ambiguous | fictional | non_us, "state_mapping_confidence"] = 0.0
        result["national_only_location"] = national
        result["ambiguous_location"] = ambiguous | multi
        result["non_us_location"] = non_us
        result["missing_location"] = missing
        result["fictional_location"] = fictional
        result["state_analysis_available"] = one
        result["national_temporal_analysis_available"] = True
        result["spatial_validity_risk"] = (1.0 - result["state_mapping_confidence"]).where(~missing)
        return result
