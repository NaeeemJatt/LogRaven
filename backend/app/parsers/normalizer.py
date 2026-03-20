# LogRaven — NormalizedEvent Schema

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class NormalizedEvent:
    timestamp:      datetime
    source_type:    str
    hostname:       Optional[str]   = None
    username:       Optional[str]   = None
    source_ip:      Optional[str]   = None
    destination_ip: Optional[str]   = None
    event_type:     str             = "other"
    event_id:       Optional[str]   = None
    raw_message:    str             = ""
    flags:          list            = field(default_factory=list)
    severity_hint:  str             = "informational"
    extra_fields:   dict            = field(default_factory=dict)


def normalize_entity(value: str | None) -> str | None:
    """
    Normalize an entity value (IP, username, hostname) for correlation.
    Strips whitespace, lowercases, removes trailing dots.
    Returns None if value is None or empty after cleaning.
    """
    if value is None:
        return None
    cleaned = value.strip().lower().rstrip(".")
    return cleaned if cleaned else None
