# LogRaven — Rule Schema
# Pydantic models describing the YAML rule format.
# Supported match types: simple (per-event) and threshold (time-windowed).

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, field_validator


class SimpleCondition(BaseModel):
    """A single field-level condition inside a simple rule."""

    field: str
    """NormalizedEvent attribute name or 'extra.<key>' for extra_fields."""

    op: Literal[
        "eq", "neq", "contains", "contains_any", "contains_all",
        "startswith", "endswith", "re", "in", "exists", "not_exists",
    ]
    """Comparison operator."""

    value:  Optional[str]       = None
    """Single string value (for eq / neq / contains / startswith / endswith / re)."""

    values: Optional[list[str]] = None
    """List of strings (for contains_any / contains_all / in)."""

    negate: bool = False
    """Invert the result of this condition."""

    @field_validator("values", mode="before")
    @classmethod
    def coerce_values(cls, v):
        """Accept a comma-separated string as a values list."""
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v


class SimpleMatch(BaseModel):
    """Match a rule against individual events."""

    type: Literal["simple"]
    log_type:        Optional[str] = None
    """Filter to events whose source_type equals this value."""

    conditions:      list[SimpleCondition]
    condition_logic: Literal["and", "or"] = "and"


class ThresholdMatch(BaseModel):
    """Match a rule when N events from the same group occur within a time window."""

    type: Literal["threshold"]
    log_type:       Optional[str] = None
    event_type:     Optional[str] = None
    """Pre-filter: only consider events of this event_type."""

    group_by:       str
    """NormalizedEvent field to group by (e.g. source_ip, username)."""

    count:          int
    """Minimum number of events in the window to trigger."""

    window_seconds: int
    """Sliding window size in seconds."""


class RuleDefinition(BaseModel):
    """A complete LogRaven detection rule loaded from a YAML file."""

    id:                   str
    title:                str
    source:               str           = "lograven"
    log_type:             Optional[str] = None
    severity:             str           = "medium"
    mitre_technique_id:   Optional[str] = None
    mitre_tactic:         Optional[str] = None
    flag:                 Optional[str] = None
    """Flag string appended to event.flags on match (underscores, no spaces)."""

    description:          str           = ""
    enabled:              bool          = True
    requires_sysmon:      bool          = False
    """Skip rule if Sysmon is not installed (YAML converter marks these)."""

    match: SimpleMatch | ThresholdMatch
