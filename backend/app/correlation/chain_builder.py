# LogRaven — Chain Builder
#
# PURPOSE:
#   Groups entity occurrences into time-windowed event chains.
#   A chain = same entity appearing across multiple source types
#   within a configurable time window (default: 5 minutes = 300 seconds).
#
# CHAIN SCORING:
#   Chains spanning more source types are more significant:
#   2 source types -> severity_elevation = "high",     score = 0.70
#   3 source types -> severity_elevation = "critical",  score = 0.90
#   4+ source types -> severity_elevation = "critical", score = 1.00
#
# TIME-WINDOW ALGORITHM:
#   Occurrences are sorted by timestamp and clustered by consecutive gap:
#   if the gap between two adjacent (by time) occurrences exceeds time_window,
#   a new cluster begins. This produces non-overlapping, contiguous chains
#   that reflect real attack timelines without duplicate reporting.
#
# DICT PROTOCOL:
#   CorrelatedChain implements keys() + __getitem__ so that dict(chain) works,
#   which is required by the correlation_prompt serializer.

from dataclasses import dataclass, field
from typing import List


@dataclass
class CorrelatedChain:
    entity_value: str
    entity_type: str
    source_types: List[str]
    events: List[object]        # List[NormalizedEvent] — used by correlation_prompt
    time_span_seconds: float
    severity_elevation: str     # high | critical
    score: float

    # ── Mapping protocol so dict(chain) works in correlation_prompt ──────────

    def keys(self):
        return self.__dataclass_fields__.keys()

    def __getitem__(self, key: str):
        return getattr(self, key)


def build_chain(
    entity_value: str,
    occurrences: list,
    time_window: int = 300,
) -> List[CorrelatedChain]:
    """
    Build correlated chains from entity occurrences within a time window.

    Occurrences are sorted by timestamp and split into clusters wherever the
    gap between consecutive events exceeds time_window seconds.  Any cluster
    that spans two or more distinct source types becomes a CorrelatedChain.
    """
    if not occurrences:
        return []

    sorted_occs = _sort_by_timestamp(occurrences)
    clusters = _cluster_by_gap(sorted_occs, time_window)

    chains: List[CorrelatedChain] = []
    for cluster in clusters:
        source_types = list(dict.fromkeys(occ.source_type for occ in cluster))
        if len(source_types) < 2:
            continue

        # Use the NormalizedEvent objects so the AI prompt can serialize them
        events = [occ.event for occ in cluster]
        time_span = _span_seconds(cluster)
        severity, score = _score(len(source_types))

        chains.append(CorrelatedChain(
            entity_value=entity_value,
            entity_type=cluster[0].entity_type,
            source_types=source_types,
            events=events,
            time_span_seconds=time_span,
            severity_elevation=severity,
            score=score,
        ))

    return chains


# ── Helpers ──────────────────────────────────────────────────────────────────

def _sort_by_timestamp(occurrences: list) -> list:
    """Sort occurrences by timestamp, placing None timestamps last."""
    def _key(occ):
        ts = occ.timestamp
        if ts is None:
            return float("inf")
        try:
            return ts.timestamp()
        except Exception:
            return float("inf")

    return sorted(occurrences, key=_key)


def _cluster_by_gap(sorted_occs: list, time_window: int) -> list[list]:
    """
    Split sorted occurrences into contiguous clusters.
    A new cluster starts whenever the gap between consecutive events
    exceeds time_window seconds.
    """
    if not sorted_occs:
        return []

    clusters: list[list] = []
    current: list = [sorted_occs[0]]

    for occ in sorted_occs[1:]:
        gap = _gap_seconds(current[-1], occ)
        if gap is not None and gap <= time_window:
            current.append(occ)
        else:
            clusters.append(current)
            current = [occ]

    clusters.append(current)
    return clusters


def _gap_seconds(a, b) -> float | None:
    """Return seconds between two occurrences, or None if timestamps are invalid."""
    try:
        return (b.timestamp - a.timestamp).total_seconds()
    except Exception:
        return None


def _span_seconds(cluster: list) -> float:
    """Total seconds from first to last occurrence in a cluster."""
    try:
        return (cluster[-1].timestamp - cluster[0].timestamp).total_seconds()
    except Exception:
        return 0.0


def _score(num_source_types: int) -> tuple[str, float]:
    """Return (severity_elevation, score) for a chain spanning N source types."""
    if num_source_types >= 4:
        return "critical", 1.00
    if num_source_types == 3:
        return "critical", 0.90
    return "high", 0.70
