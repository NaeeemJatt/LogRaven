# LogRaven — align file lines to NormalizedEvent rows for PlayParser preview.

from __future__ import annotations

import copy
import json
from typing import Any, Literal

from app.parsers.normalizer import NormalizedEvent

MatchKind = Literal["exact", "substring", "index", "none"]


def normalized_event_to_preview_dict(ev: NormalizedEvent, *, extra_fields_max_json: int = 4000) -> dict[str, Any]:
    """Flat JSON-serializable dict; caps extra_fields size (drops heavy decoder raw_output)."""
    ts = ev.timestamp.isoformat() if ev.timestamp else None
    extra = _truncate_extra_fields(ev.extra_fields or {}, max_json=extra_fields_max_json)
    return {
        "timestamp": ts,
        "source_type": ev.source_type,
        "hostname": ev.hostname,
        "username": ev.username,
        "source_ip": ev.source_ip,
        "destination_ip": ev.destination_ip,
        "event_type": ev.event_type,
        "event_id": ev.event_id,
        "severity_hint": ev.severity_hint or "informational",
        "raw_message": (ev.raw_message or "")[:2000],
        "flags": list(ev.flags) if ev.flags else [],
        "extra_fields": extra,
    }


def _truncate_extra_fields(d: dict[str, Any], *, max_json: int) -> dict[str, Any]:
    if not d:
        return {}
    out = copy.deepcopy(d)
    meta = out.get("decoder_metadata")
    if isinstance(meta, dict) and "raw_output" in meta:
        meta = dict(meta)
        ro = meta.get("raw_output")
        if isinstance(ro, dict):
            meta["raw_output"] = {"_truncated": True, "keys": list(ro.keys())[:30]}
        else:
            meta["raw_output"] = None
        out["decoder_metadata"] = meta
    try:
        s = json.dumps(out, default=str)
    except (TypeError, ValueError):
        return {"_error": "extra_fields not serializable"}
    if len(s) <= max_json:
        return out
    return {"_truncated": True, "preview": s[:max_json] + "…"}


def align_lines_to_events(lines: list[str], events: list[NormalizedEvent]) -> list[tuple[MatchKind, NormalizedEvent | None]]:
    """
    For each line, pick best-matching event. Unused pool for exact/substring; index fallback when counts match.
    """
    n_lines = len(lines)
    n_ev = len(events)
    if n_lines == 0:
        return []

    unused: set[int] = set(range(n_ev))
    result: list[tuple[MatchKind, NormalizedEvent | None]] = []

    for i, line in enumerate(lines):
        ls = line.rstrip()
        chosen_j: int | None = None
        kind: MatchKind = "none"

        for j in sorted(unused):
            rm = (events[j].raw_message or "").rstrip()
            if rm == ls:
                chosen_j = j
                kind = "exact"
                break

        if chosen_j is None and ls:
            for j in sorted(unused):
                rm = (events[j].raw_message or "").rstrip()
                if ls in rm:
                    chosen_j = j
                    kind = "substring"
                    break

        if chosen_j is not None:
            unused.discard(chosen_j)
            result.append((kind, events[chosen_j]))
            continue

        if n_lines == n_ev and i < n_ev:
            result.append(("index", events[i]))
            continue

        result.append(("none", None))

    return result


def build_preview_rows_for_parser(
    lines: list[str],
    events: list[NormalizedEvent],
    *,
    raw_max_chars: int,
) -> list[dict[str, Any]]:
    pairs = align_lines_to_events(lines, events)
    rows: list[dict[str, Any]] = []
    for idx, line in enumerate(lines):
        match_kind, ev = pairs[idx]
        raw = line if len(line) <= raw_max_chars else line[:raw_max_chars] + "…"
        parsed = normalized_event_to_preview_dict(ev) if ev else None
        rows.append(
            {
                "line_no": idx + 1,
                "raw": raw,
                "parsed": parsed,
                "match": match_kind,
            }
        )
    return rows


def build_preview_rows_for_decoder(lines: list[str], events: list[NormalizedEvent], *, raw_max_chars: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, line in enumerate(lines):
        raw = line if len(line) <= raw_max_chars else line[:raw_max_chars] + "…"
        ev = events[idx] if idx < len(events) else None
        match_kind: MatchKind = "exact" if ev else "none"
        parsed = normalized_event_to_preview_dict(ev) if ev else None
        rows.append(
            {
                "line_no": idx + 1,
                "raw": raw,
                "parsed": parsed,
                "match": match_kind,
            }
        )
    return rows
