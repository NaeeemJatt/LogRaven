# LogRaven — AI Cost Limiter
#
# PURPOSE:
#   Enforces hard per-investigation event ceiling before sending to Gemini.
#   Prevents unbounded API costs regardless of file size.
#   Makes AI cost predictable: maximum $0.10-0.15 per investigation.
#
# TIER LIMITS:
#   free:  2,000 events max sent to AI
#   pro:   10,000 events max
#   team:  50,000 events max
#
# SELECTION PRIORITY (when ceiling is hit):
#   1. Flagged events (any flag in flags list) over unflagged
#   2. Higher severity_hint over lower
#   3. Re-sorted by timestamp after selection for coherent AI context

from datetime import datetime

TIER_CEILINGS = {
    "free":  2_000,
    "pro":  10_000,
    "team": 50_000,
}

_SEVERITY_ORDER = {
    "critical":      0,
    "high":          1,
    "medium":        2,
    "low":           3,
    "informational": 4,
    "deduplicated":  5,
}


def _event_priority(event) -> tuple:
    """Lower tuple = higher priority."""
    base = _SEVERITY_ORDER.get(event.severity_hint, 4)
    has_flag = len(event.flags) > 0 and "deduplicated" not in event.flags
    return (0 if has_flag else 1, base)


def enforce_ceiling(events: list, user_tier: str) -> tuple[list, bool]:
    """
    Select events within the tier ceiling using priority-based selection.
    Returns (selected_events, was_truncated).
    """
    ceiling = TIER_CEILINGS.get(user_tier, 2_000)
    if len(events) <= ceiling:
        return events, False

    sorted_events = sorted(events, key=_event_priority)
    selected = sorted_events[:ceiling]
    # Re-sort by timestamp so AI sees events in chronological order
    selected.sort(key=lambda e: e.timestamp if e.timestamp is not None else datetime.min)
    return selected, True
