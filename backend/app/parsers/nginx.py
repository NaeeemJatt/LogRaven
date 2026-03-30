# LogRaven — Nginx / Apache / IIS Web Server Access Log Parser
#
# Handles three web-server log formats transparently:
#
#   1. IIS W3C Extended Log Format
#      Header: "#Fields: date time cs-method cs-uri-stem ..."
#      Data:   "2024-01-15 08:30:01 GET /index.asp 200 10.0.0.5 ..."
#
#   2. Apache / Nginx Combined Log Format
#      "IP - user [dd/Mon/yyyy:HH:MM:SS ±ZZ] "METHOD path HTTP/x" status bytes "ref" "ua""
#
#   3. Apache Common Log Format (no referer / UA)
#      "IP - user [date] "METHOD path HTTP/x" status bytes"
#
# Format detection is done lazily at parse() time by peeking at the first
# non-blank line.  No external config required.

import re
from collections import defaultdict
from datetime import datetime, timezone

from app.parsers.base import BaseParser
from app.parsers.normalizer import NormalizedEvent, normalize_entity
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Apache/Nginx Combined / Common Format.
# Bytes field accepts "-" (no body).  Referer+UA are optional.
_COMBINED_LOG_RE = re.compile(
    r'(\S+)'            # client IP
    r' \S+ \S+'         # ident & auth
    r' \[([^\]]+)\]'    # [timestamp]
    r' "(\S+) (\S+)[^"]*"'  # "METHOD path HTTP/x.x"
    r' (\d+)'           # status
    r' (\S+)'           # bytes (may be "-")
    r'(?:\s+"([^"]*)" "([^"]*)")?'  # optional "referer" "ua"
)

_INJECTION_KEYWORDS = ("SELECT", "UNION", "DROP", "../", "..\\", "<script")


class NginxParser(BaseParser):

    def parse(self, file_path: str) -> list[NormalizedEvent]:
        if self._is_iis_w3c(file_path):
            events = self._parse_iis_w3c(file_path)
        else:
            events = self._parse_combined(file_path)
        return self._detect_patterns(events)

    # ── Format detection ─────────────────────────────────────────────────────

    def _is_iis_w3c(self, file_path: str) -> bool:
        """Return True if the file starts with IIS/W3C directive lines."""
        try:
            for line in self._stream_lines(file_path):
                stripped = line.strip()
                if not stripped:
                    continue
                return stripped.startswith("#")
        except Exception:
            pass
        return False

    # ── IIS W3C Extended Log Format ───────────────────────────────────────────

    def _parse_iis_w3c(self, file_path: str) -> list[NormalizedEvent]:
        events: list[NormalizedEvent] = []
        fields: list[str] = []
        current_date: str = ""

        for raw_line in self._stream_lines(file_path):
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith("#"):
                tag = line.lower()
                if tag.startswith("#fields:"):
                    # Normalise field names to lowercase so lookups are case-insensitive
                    fields = line[len("#fields:"):].strip().lower().split()
                elif tag.startswith("#date:"):
                    current_date = line[len("#date:"):].strip()
                continue

            if not fields:
                self._log_skip(line, "IIS W3C: no #Fields header seen yet")
                continue

            parts = line.split()
            if len(parts) < len(fields):
                self._log_skip(line, f"IIS W3C: too few columns ({len(parts)}/{len(fields)})")
                continue

            # Build a dict of field_name -> value, treating "-" as empty
            row: dict[str, str] = {
                fields[i]: ("" if parts[i] == "-" else parts[i])
                for i in range(len(fields))
            }

            # ── Timestamp ────────────────────────────────────────────────────
            date_str = row.get("date", current_date)
            time_str = row.get("time", "")
            ts_raw = f"{date_str} {time_str}".strip()
            ts = self._safe_parse_timestamp(ts_raw) if ts_raw else None
            if ts is None:
                ts = datetime.now(timezone.utc).replace(tzinfo=None)

            # ── Fields ───────────────────────────────────────────────────────
            client_ip    = row.get("c-ip") or None
            method       = row.get("cs-method", "")
            uri_stem     = row.get("cs-uri-stem", "")
            uri_query    = row.get("cs-uri-query", "")
            status       = row.get("sc-status", "0")
            username     = row.get("cs-username") or None
            # cs(User-Agent) field name is lowercased to cs(user-agent)
            user_agent   = row.get("cs(user-agent)", "")
            referer      = row.get("cs(referer)", "")
            sc_bytes     = row.get("sc-bytes") or row.get("cs-bytes") or "0"
            hostname     = row.get("s-computername") or row.get("s-sitename") or None

            request_path = f"{uri_stem}?{uri_query}" if uri_query else uri_stem

            flags = self._injection_flags(request_path)

            events.append(NormalizedEvent(
                timestamp=ts,
                source_type="web_server",
                source_ip=normalize_entity(client_ip),
                hostname=normalize_entity(hostname),
                username=normalize_entity(username),
                event_type="network",
                event_id=f"{method} {status}",
                raw_message=raw_line[:500],
                flags=flags,
                severity_hint="medium" if "injection_attempt" in flags else "informational",
                extra_fields={
                    "method":         method,
                    "request_path":   request_path,
                    "status_code":    status,
                    "response_bytes": sc_bytes,
                    "user_agent":     user_agent[:200],
                    "referer":        referer[:200],
                },
            ))

        return events

    # ── Apache / Nginx Combined (and Common) Format ───────────────────────────

    def _parse_combined(self, file_path: str) -> list[NormalizedEvent]:
        events: list[NormalizedEvent] = []

        for line in self._stream_lines(file_path):
            if not line.strip():
                continue
            m = _COMBINED_LOG_RE.match(line)
            if not m:
                self._log_skip(line, "no combined log match")
                continue

            remote_addr  = m.group(1)
            time_local   = m.group(2)
            method       = m.group(3)
            request_path = m.group(4)
            status_code  = m.group(5)
            _bytes       = m.group(6) if m.group(6) and m.group(6) != "-" else "0"
            _referer     = m.group(7) or ""
            _ua          = m.group(8) or ""

            ts = self._safe_parse_timestamp(time_local) or datetime.now(timezone.utc).replace(tzinfo=None)
            flags = self._injection_flags(request_path)

            events.append(NormalizedEvent(
                timestamp=ts,
                source_type="web_server",
                source_ip=normalize_entity(remote_addr),
                event_type="network",
                event_id=f"{method} {status_code}",
                raw_message=line[:500],
                flags=flags,
                severity_hint="medium" if "injection_attempt" in flags else "informational",
                extra_fields={
                    "method":         method or "",
                    "request_path":   request_path or "",
                    "status_code":    status_code or "",
                    "response_bytes": _bytes,
                    "user_agent":     _ua[:200],
                    "referer":        _referer[:200],
                },
            ))

        return events

    # ── Shared helpers ────────────────────────────────────────────────────────

    def _injection_flags(self, request_path: str) -> list[str]:
        flags: list[str] = []
        upper = request_path.upper()
        for kw in _INJECTION_KEYWORDS:
            if kw.upper() in upper or kw in request_path:
                flags.append("injection_attempt")
                break
        return flags

    # ── Pattern detection ─────────────────────────────────────────────────────

    def _detect_patterns(self, events: list[NormalizedEvent]) -> list[NormalizedEvent]:
        ip_times: dict[str, list[datetime]] = defaultdict(list)
        ip_4xx: dict[str, int] = defaultdict(int)

        for ev in events:
            if ev.source_ip:
                ip_times[ev.source_ip].append(ev.timestamp)
                if ev.event_id and ev.event_id.split()[-1:] and ev.event_id.split()[-1][0] == "4":
                    ip_4xx[ev.source_ip] += 1

        scanning_ips: set[str] = set()
        for ip, times in ip_times.items():
            if len(times) < 50:
                continue
            times_sorted = sorted(times)
            for i in range(len(times_sorted)):
                window = [t for t in times_sorted[i:] if (t - times_sorted[i]).total_seconds() <= 60]
                if len(window) >= 50:
                    scanning_ips.add(ip)
                    break

        spike_ips = {ip for ip, count in ip_4xx.items() if count >= 20}

        for ev in events:
            if ev.source_ip in scanning_ips and "scanning" not in ev.flags:
                ev.flags.append("scanning")
                ev.severity_hint = "high"
            if ev.source_ip in spike_ips and "4xx_spike" not in ev.flags:
                ev.flags.append("4xx_spike")
                if ev.severity_hint == "informational":
                    ev.severity_hint = "medium"

        return events
