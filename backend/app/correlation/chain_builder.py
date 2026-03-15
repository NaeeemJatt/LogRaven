# LogRaven — Chain Builder
#
# PURPOSE:
#   Groups entity occurrences into time-windowed event chains.
#   A chain = same entity appearing across multiple source types
#   within a configurable time window (default: 5 minutes = 300 seconds).
#
# MAIN FUNCTION:
#   build_chain(entity_value, occurrences, time_window=300) -> List[CorrelatedChain]
#
# CHAIN SCORING:
#   Chains spanning more source types are more significant:
#   2 source types -> severity_elevation = "high"
#   3+ source types -> severity_elevation = "critical"
#
# EXAMPLE CHAIN:
#   Entity: IP 185.220.101.42
#   Occurrences:
#     - windows_endpoint: powershell.exe spawn at 14:02:08
#     - firewall: blocked outbound 443 at 14:02:11
#     - cloudtrail: AssumeRole API at 14:02:15
#   All within 300-second window -> CorrelatedChain with Critical elevation
#
# TODO Month 3 Week 1: Implement this file.

from dataclasses import dataclass, field
from typing import List


@dataclass
class CorrelatedChain:
    entity_value: str
    entity_type: str
    source_types: List[str]
    events: List[object]        # List[EntityOccurrence]
    time_span_seconds: float
    severity_elevation: str     # high | critical
    score: float


def build_chain(entity_value: str, occurrences: list, time_window: int = 300) -> List[CorrelatedChain]:
    """
    Build correlated chains from entity occurrences within a time window.
    Returns list of CorrelatedChain objects.
    """
    # TODO: Implement chain building with time window grouping
    return []
