# LogRaven — AI Cost Limiter
#
# PURPOSE:
#   Enforces hard per-investigation event ceiling before sending to Claude.
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
#   3. Events from correlated chains over single-source
#
# When ceiling is hit: the report notes which events were rule-only
# vs AI-analyzed, so the user understands coverage.
#
# TODO Month 3 Week 1: Implement this file.

TIER_CEILINGS = {
    "free":  2_000,
    "pro":  10_000,
    "team": 50_000,
}


def enforce_ceiling(events: list, user_tier: str) -> tuple[list, bool]:
    """
    Select events within the tier ceiling.
    Returns (selected_events, was_truncated)
    """
    ceiling = TIER_CEILINGS.get(user_tier, 2_000)
    if len(events) <= ceiling:
        return events, False

    # TODO: Implement priority-based selection
    return events[:ceiling], True
