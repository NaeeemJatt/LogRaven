# LogRaven — Parse quality heuristics (post-parse, not “max events wins”)

from dataclasses import dataclass, field
from datetime import datetime

from app.parsers.normalizer import NormalizedEvent

_TS_YEAR_MIN = 1990
_TS_YEAR_MAX = 2037


@dataclass
class ParseQualityResult:
    """Heuristic quality of a parser output for fallback decisions."""

    score: float
    valid_timestamp_ratio: float
    structured_ratio: float
    event_count: int
    warnings: list[str] = field(default_factory=list)


def _timestamp_plausible(ts: datetime) -> bool:
    if ts is None:
        return False
    y = ts.year
    return _TS_YEAR_MIN <= y <= _TS_YEAR_MAX


def _event_structured(ev: NormalizedEvent) -> bool:
    if ev.event_type and ev.event_type != "other":
        return True
    if ev.source_ip or ev.username or ev.hostname:
        return True
    if ev.event_id:
        return True
    return False


def assess_parse_quality(events: list[NormalizedEvent]) -> ParseQualityResult:
    """
    Score 0–1 from timestamp plausibility and structured-field coverage.
    Used to pick among detector candidates when the first choice is a poor fit.
    """
    warnings: list[str] = []
    n = len(events)
    if n == 0:
        return ParseQualityResult(
            score=0.0,
            valid_timestamp_ratio=0.0,
            structured_ratio=0.0,
            event_count=0,
            warnings=["no_events"],
        )

    valid_ts = sum(1 for e in events if _timestamp_plausible(e.timestamp))
    valid_timestamp_ratio = valid_ts / n
    structured = sum(1 for e in events if _event_structured(e))
    structured_ratio = structured / n

    # Weight timestamps slightly lower than structure — wrong parsers often still
    # fabricate ordered timestamps from bogus fields.
    score = 0.42 * valid_timestamp_ratio + 0.58 * structured_ratio

    if valid_timestamp_ratio < 0.15 and n >= 5:
        warnings.append("low_timestamp_coverage")
    if structured_ratio < 0.1 and n >= 10:
        warnings.append("mostly_unstructured_events")

    return ParseQualityResult(
        score=max(0.0, min(1.0, score)),
        valid_timestamp_ratio=valid_timestamp_ratio,
        structured_ratio=structured_ratio,
        event_count=n,
        warnings=warnings,
    )


# Primary candidate is kept if score >= this; otherwise try next ranked type.
PARSE_QUALITY_SUFFICIENT = 0.32
