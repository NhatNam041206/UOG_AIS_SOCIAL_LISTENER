"""Utility helpers for cross-phase concerns such as timezone alignment."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def align_timestamp_timezone(timestamp: datetime, timezone: str) -> datetime:
    """Normalize a timestamp to the provided timezone."""
    try:
        target_tz = ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown timezone: {timezone}") from exc

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=ZoneInfo("UTC"))
    return timestamp.astimezone(target_tz)
