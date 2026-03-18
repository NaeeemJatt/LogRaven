# LogRaven — Nginx / Apache Access Log Parser

import re
from collections import defaultdict
from datetime import datetime, timezone

from app.parsers.base import BaseParser
from app.parsers.normalizer import NormalizedEvent, normalize_entity
from app.utils.logger import get_logger

logger = get_logger(__name__)

_COMBINED_LOG_RE = re.compile(
    r'(\S+) \S+ \S+ \[([^\]]+)\] "(\S+) (\S+) \S+" (\d+) (\d+) "([^"]*)" "([^"]*)"'
)

_INJECTION_KEYWORDS = ("SELECT", "UNION", "DROP", "../", "..\\", "<script")


class NginxParser(BaseParser):

    def parse(self, file_path: str) -> list[NormalizedEvent]:
        events: list[NormalizedEvent] = []

        for line in self._stream_lines(file_path):
            if not line.strip():
                continue
            m = _COMBINED_LOG_RE.match(line)
            if not m:
                self._log_skip(line, "no combined log match")
                continue

            remote_addr, time_local, method, request_path, status_code, _bytes, _referer, _ua = m.groups()

            ts = self._safe_parse_timestamp(time_local) or datetime.now(timezone.utc).replace(tzinfo=None)

            try:
                status_int = int(status_code)
            except ValueError:
                status_int = 0

            flags: list[str] = []
            upper_path = request_path.upper()
            for kw in _INJECTION_KEYWORDS:
                if kw.upper() in upper_path or kw in request_path:
                    flags.append("injection_attempt")
                    break

            events.append(NormalizedEvent(
                timestamp=ts,
                source_type="web_server",
                source_ip=normalize_entity(remote_addr),
                event_type="network",
                event_id=f"{method} {status_code}",
                raw_message=line[:500],
                flags=flags,
                severity_hint="medium" if "injection_attempt" in flags else "informational",
            ))

        return self._detect_patterns(events)

    def _detect_patterns(self, events: list[NormalizedEvent]) -> list[NormalizedEvent]:
        # Per-IP request counts for scanning (50+ in 60s window)
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
