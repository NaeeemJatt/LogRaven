# LogRaven — heuristic comparison native parsers vs decoder output (PlayParser).

from __future__ import annotations

from app.parsers.normalizer import NormalizedEvent


def compare_event_streams(
    native_events: list[NormalizedEvent],
    decoder_events: list[NormalizedEvent],
    *,
    sample_limit: int = 20,
) -> dict:
    """
    Best-effort metrics when both paths produced events (not necessarily 1:1 with lines).
    """
    n_n = len(native_events)
    n_d = len(decoder_events)
    ts_match = 0
    ip_match = 0
    checked = 0
    lim = min(sample_limit, n_n, n_d)
    for i in range(lim):
        a = native_events[i]
        b = decoder_events[i]
        checked += 1
        if a.timestamp and b.timestamp and abs((a.timestamp - b.timestamp).total_seconds()) < 2:
            ts_match += 1
        if (a.source_ip or "").strip() and (a.source_ip or "").strip() == (b.source_ip or "").strip():
            ip_match += 1

    return {
        "native_event_count": n_n,
        "decoder_event_count": n_d,
        "count_delta": n_d - n_n,
        "sample_pairs_compared": checked,
        "timestamp_agreement_ratio": (ts_match / checked) if checked else 0.0,
        "source_ip_agreement_ratio": (ip_match / checked) if checked else 0.0,
    }
