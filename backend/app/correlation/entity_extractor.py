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
#
# MAIN FUNCTION:
#   extract_all(events_by_file) -> dict[entity_value, List[EntityOccurrence]]
#
# TODO Month 3 Week 1: Implement this file.

from app.parsers.normalizer import NormalizedEvent
from dataclasses import dataclass


@dataclass
class EntityOccurrence:
    entity_value: str
    entity_type: str    # ip | username | hostname
    source_type: str    # which log source file
    timestamp: object   # datetime
    event: NormalizedEvent


def extract_all(events_by_file: dict) -> dict:
    """
    Extract all entities from all source files.
    Returns {normalized_entity_value: [EntityOccurrence, ...]}
    """
    # TODO: Implement entity extraction with normalization
    return {}
