# LogRaven — map decoder manager Logtest output → NormalizedEvent.

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.parsers.normalizer import NormalizedEvent, normalize_entity


def _parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except ValueError:
        pass
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(s[:26], fmt)
        except ValueError:
            continue
    return None


def _extract_ip(text: str) -> str | None:
    m = re.search(
        r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
        text,
    )
    return m.group(0) if m else None


def _guess_event_type(full_log: str, rule: dict[str, Any] | None) -> str:
    low = full_log.lower()
    if "failed password" in low or "authentication failure" in low or "invalid user" in low:
        return "auth_failure"
    if "accepted password" in low or "session opened" in low:
        return "auth_success"
    if "sudo" in low:
        return "sudo"
    if rule:
        desc = (rule.get("description") or "").lower()
        gid = str(rule.get("groups") or [])
        if "web" in gid or "access" in desc:
            return "network"
    return "other"


def logtest_output_to_event(
    *,
    output: dict[str, Any],
    source_type: str,
    raw_line: str,
    line_index: int,
) -> NormalizedEvent:
    full_log = str(output.get("full_log") or raw_line)[:500]
    decoder = output.get("decoder")
    if isinstance(decoder, dict):
        decoder_name = decoder.get("name") or decoder.get("parent") or "unknown"
    else:
        decoder_name = str(decoder or "unknown")

    rule = output.get("rule") if isinstance(output.get("rule"), dict) else None
    rule_id = None
    if rule:
        rid = rule.get("id")
        rule_id = str(rid) if rid is not None else None

    ts = _parse_ts(output.get("timestamp"))
    if ts is None:
        ts = datetime.utcnow()

    # Dynamic fields may appear at top level of output (manager-dependent)
    username = None
    hostname = None
    src_ip = None
    for key in ("srcuser", "dstuser", "user", "username"):
        v = output.get(key)
        if v and isinstance(v, str):
            username = normalize_entity(v)
            break
    for key in ("hostname", "system_name"):
        v = output.get(key)
        if v and isinstance(v, str):
            hostname = v.strip() or None
            break
    for key in ("srcip", "src_ip", "source_ip"):
        v = output.get(key)
        if v and isinstance(v, str):
            src_ip = v.strip() or None
            break
    if not src_ip:
        src_ip = _extract_ip(full_log)

    event_type = _guess_event_type(full_log, rule if isinstance(rule, dict) else None)
    sev = "informational"
    if rule and isinstance(rule.get("level"), int):
        lvl = rule["level"]
        if lvl >= 12:
            sev = "high"
        elif lvl >= 8:
            sev = "medium"
        elif lvl >= 5:
            sev = "low"

    meta = {
        "decoder": decoder_name,
        "rule": rule,
        "line_index": line_index,
        "raw_output": output,
    }

    return NormalizedEvent(
        timestamp=ts,
        source_type=source_type,
        hostname=hostname,
        username=username,
        source_ip=src_ip,
        destination_ip=None,
        event_type=event_type,
        event_id=rule_id or decoder_name[:120],
        raw_message=raw_line[:500],
        flags=[],
        severity_hint=sev,
        extra_fields={"decoder_metadata": meta},
    )
