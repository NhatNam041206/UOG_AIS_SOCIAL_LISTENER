# Module: helpers

## Architectural Role
Model boundary for shared utility logic.

## Core Functional Objective
Normalizes timestamps into a requested timezone without coupling to phase-specific code.

## Class and Method Signatures
* `align_timestamp_timezone(timestamp: datetime, timezone: str) -> datetime`: Normalize a timestamp to the provided timezone.
