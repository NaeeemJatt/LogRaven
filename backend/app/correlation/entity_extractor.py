# LogRaven — Entity Extractor
#
# PURPOSE:
#   Extracts and normalizes shared entities across all log source files.
#   Entity normalization is CRITICAL for accurate correlation.
#   Without normalization, "10.1.1.5" and "10.1.1.5 " are different entities.
#
# ENTITIES EXTRACTED:
#   - IP addresses: from source_ip and destination_ip fields
#   - Usernames: from username field
#   - Hostnames: from hostname field
#
# NORMALIZATION RULES (applied before grouping):
#   - Lowercase all values
#   - Strip leading/trailing whitespace
#   - Strip trailing dots from hostnames (DNS artifact)
#   - Remove port numbers from IPs if present (e.g. "10.1.1.5:443" -> "10.1.1.5")

import re
from dataclasses import dataclass

from app.parsers.normalizer import NormalizedEvent, normalize_entity

# Matches IPv4 with optional port: "10.1.1.5:443" -> group(1) = "10.1.1.5"
_IP_PORT_RE = re.compile(r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):\d+$")

# Entity values that are far too generic to be meaningful correlation signals
_NOISE_VALUES = frozenset({
    "system", "local service", "network service", "anonymous logon",
    "anonymous", "nobody", "root", "administrator", "localhost",
    "127.0.0.1", "::1", "0.0.0.0", "-", "n/a", "unknown",
})


@dataclass
class EntityOccurrence:
    entity_value: str
    entity_type: str      # ip | username | hostname
    source_type: str      # which log source file
    timestamp: object     # datetime
    event: NormalizedEvent


def _normalize_ip(value: str | None) -> str | None:
    """Normalize IP address, stripping port suffix if present."""
    if value is None:
        return None
    cleaned = value.strip()
    m = _IP_PORT_RE.match(cleaned)
    if m:
        cleaned = m.group(1)
    result = cleaned.lower()
    return result if result else None


def _is_noise(value: str) -> bool:
    return value.lower() in _NOISE_VALUES


def extract_all(events_by_file: dict) -> dict:
    """
    Extract all entities from all source files.
    Returns {normalized_entity_value: [EntityOccurrence, ...]}
    """
    occurrences: dict[str, list] = {}

    for source_type, events in events_by_file.items():
        for event in events:
            _extract_from_event(event, source_type, occurrences)

    return occurrences


def _extract_from_event(
    event: NormalizedEvent,
    source_type: str,
    occurrences: dict,
) -> None:
    """Extract IP, username, and hostname entities from a single event."""
    candidates: list[tuple[str | None, str]] = [
        (_normalize_ip(event.source_ip),          "ip"),
        (_normalize_ip(event.destination_ip),     "ip"),
        (normalize_entity(event.username),        "username"),
        (normalize_entity(event.hostname),        "hostname"),
    ]

    for value, entity_type in candidates:
        if value is None or _is_noise(value):
            continue

        occ = EntityOccurrence(
            entity_value=value,
            entity_type=entity_type,
            source_type=source_type,
            timestamp=event.timestamp,
            event=event,
        )
        if value not in occurrences:
            occurrences[value] = []
        occurrences[value].append(occ)
