# LogRaven — Linux Syslog / auth.log Parser

import re
from collections import defaultdict
from datetime import datetime, timezone

from app.parsers.base import BaseParser
from app.parsers.normalizer import NormalizedEvent, normalize_entity
from app.utils.logger import get_logger

logger = get_logger(__name__)

_PATTERNS = [
    re.compile(r"^(\w{3}\s+\d+\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+(\S+?)(?:\[(\d+)\])?:\s+(.*)$"),
    re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^\s]*)\s+(\S+)\s+(\S+?)(?:\[(\d+)\])?:\s+(.*)$"),
    re.compile(r"^(\w{3}\s+\d+\s+\d{4}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+(\S+?)(?:\[(\d+)\])?:\s+(.*)$"),
    re.compile(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+(\S+?)(?:\[(\d+)\])?:\s+(.*)$"),
    re.compile(r"^.*?(sshd|sudo|PAM|su|login|passwd)\[?(\d+)?\]?:?\s+(.*)$"),
]

_RE_USERNAME_FROM = re.compile(r"for (?:invalid user )?(\S+) from")
_RE_USERNAME_USER = re.compile(r"user=(\S+)")
_RE_USERNAME_FOR  = re.compile(r"for user (\S+)")
_RE_SOURCE_IP     = re.compile(r"from (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")


def _best_pattern(sample_lines: list[str]) -> re.Pattern | None:
    if not sample_lines:
        return None
    best_idx, best_count = 0, 0
    for i, pat in enumerate(_PATTERNS):
        count = sum(1 for ln in sample_lines if pat.match(ln))
        if count > best_count:
            best_count, best_idx = count, i
    if best_count == 0:
        return None
    return _PATTERNS[best_idx]


def _classify_event(process: str, message: str) -> str:
    proc = (process or "").lower()
    msg  = (message or "").lower()
    if "sshd" in proc:
        if "failed" in msg or "failure" in msg or "invalid user" in msg:
            return "auth_failure"
        if "accepted" in msg:
            return "auth_success"
    if "sudo" in proc:
        return "sudo"
    if "useradd" in proc or "useradd" in msg:
        return "account_created"
    return "other"


class SyslogParser(BaseParser):

    def parse(self, file_path: str) -> list[NormalizedEvent]:
        # Sample first 200 lines to select best pattern
        sample: list[str] = []
        for i, line in enumerate(self._stream_lines(file_path)):
            if i >= 200:
                break
            if line.strip():
                sample.append(line)

        pattern = _best_pattern(sample)

        events: list[NormalizedEvent] = []
        current_year = datetime.now().year

        for line in self._stream_lines(file_path):
            if not line.strip():
                continue
            event = self._parse_line(line, pattern, current_year)
            if event:
                events.append(event)

        return self._detect_patterns(events)

    def _parse_line(self, line: str, pattern: re.Pattern | None, current_year: int) -> NormalizedEvent | None:
        if pattern is None:
            return None

        m = pattern.match(line)
        if not m:
            self._log_skip(line, "no pattern match")
            return None

        groups = m.groups()

        # Minimal pattern (pattern 5) — only keyword + pid + message
        if len(groups) == 3:
            process, pid, message = groups
            hostname = None
            ts_raw = None
        else:
            ts_raw, hostname, process, pid, message = groups

        # Timestamp
        if ts_raw:
            # RFC3164 has no year — prepend current year so strptime works
            if re.match(r"^\w{3}\s+\d", ts_raw) and str(current_year) not in ts_raw:
                ts_raw_with_year = f"{ts_raw.split()[0]} {ts_raw.split()[1]} {current_year} {ts_raw.split()[2]}"
                ts = self._safe_parse_timestamp(ts_raw_with_year)
                if ts is None:
                    ts = self._safe_parse_timestamp(ts_raw)
            else:
                ts = self._safe_parse_timestamp(ts_raw)
        else:
            ts = None

        if ts is None:
            ts = datetime.now(timezone.utc).replace(tzinfo=None)

        # Extract fields from message
        username = None
        for rex in (_RE_USERNAME_FROM, _RE_USERNAME_USER, _RE_USERNAME_FOR):
            mu = rex.search(message or "")
            if mu:
                username = mu.group(1)
                break

        ms = _RE_SOURCE_IP.search(message or "")
        source_ip = ms.group(1) if ms else None

        event_type = _classify_event(process or "", message or "")

        return NormalizedEvent(
            timestamp=ts,
            source_type="linux_endpoint",
            hostname=normalize_entity(hostname),
            username=normalize_entity(username),
            source_ip=normalize_entity(source_ip),
            event_type=event_type,
            event_id=process,
            raw_message=line[:500],
            extra_fields={
                "process": process or "",
                "pid":     pid or "",
                "message": (message or "")[:300],
            },
        )

    def _detect_patterns(self, events: list[NormalizedEvent]) -> list[NormalizedEvent]:
        # Brute force: 5+ auth_failure from same IP in 60s window
        ip_failures: dict[str, list[datetime]] = defaultdict(list)
        for ev in events:
            if ev.event_type == "auth_failure" and ev.source_ip:
                ip_failures[ev.source_ip].append(ev.timestamp)

        brute_ips: set[str] = set()
        for ip, times in ip_failures.items():
            times_sorted = sorted(times)
            for i in range(len(times_sorted)):
                window = [t for t in times_sorted[i:] if (t - times_sorted[i]).total_seconds() <= 60]
                if len(window) >= 5:
                    brute_ips.add(ip)
                    break

        for ev in events:
            if ev.source_ip in brute_ips and "brute_force_candidate" not in ev.flags:
                ev.flags.append("brute_force_candidate")
                ev.severity_hint = "high"
            if ev.event_type == "sudo" and "privilege_escalation_candidate" not in ev.flags:
                ev.flags.append("privilege_escalation_candidate")
                ev.severity_hint = "medium"
            if ev.event_type == "account_created" and "account_modification" not in ev.flags:
                ev.flags.append("account_modification")
                ev.severity_hint = "medium"

        return events
