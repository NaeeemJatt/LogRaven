# LogRaven — Windows Event Log Parser

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone

from app.parsers.base import BaseParser
from app.parsers.normalizer import NormalizedEvent, normalize_entity
from app.utils.logger import get_logger

logger = get_logger(__name__)


class WindowsEventParser(BaseParser):

    EVENT_TYPE_MAP = {
        "4625": "auth_failure",
        "4624": "auth_success",
        "4648": "explicit_credential",
        "4720": "account_created",
        "4688": "process_exec",
        "4698": "scheduled_task",
        "4702": "scheduled_task",
        "4732": "group_modification",
    }

    def parse(self, file_path: str) -> list[NormalizedEvent]:
        if file_path.lower().endswith(".evtx"):
            events = self._parse_evtx(file_path)
        else:
            events = self._parse_csv(file_path)
        return self._detect_patterns(events)

    # -- EVTX parsing via pyevtx-rs (Rust-backed, 440x faster than python-evtx) -

    def _parse_evtx(self, file_path: str) -> list[NormalizedEvent]:
        # pyevtx-rs ships as the `evtx` package.  On Windows (case-insensitive FS)
        # `import Evtx` resolves to the same package directory.
        try:
            from Evtx import PyEvtxParser  # pyevtx-rs  (pip install evtx)
        except ImportError:
            logger.warning("pyevtx-rs (pip install evtx) not found — falling back to CSV parser")
            return self._parse_csv(file_path)

        events: list[NormalizedEvent] = []
        try:
            parser = PyEvtxParser(file_path)
            for record in parser.records_json():
                try:
                    data    = json.loads(record["data"])
                    event   = data.get("Event", {})
                    system  = event.get("System", {}) or {}
                    ev_data = event.get("EventData", {}) or {}

                    event_id = str(system.get("EventID", "")).strip()
                    computer = str(system.get("Computer") or "")

                    time_raw = (
                        (system.get("TimeCreated") or {})
                        .get("#attributes", {})
                        .get("SystemTime", "")
                    )
                    ts = (
                        self._safe_parse_timestamp(
                            time_raw.replace("Z", "").split(".")[0]
                        )
                        if time_raw
                        else None
                    )
                    if ts is None:
                        ts = datetime.now(timezone.utc).replace(tzinfo=None)

                    # EventData is a flat dict; values may be str, int, or None
                    extra: dict = {
                        k: str(v)
                        for k, v in ev_data.items()
                        if v is not None and str(v).strip() not in ("", "-", "None")
                    }

                    username  = extra.get("TargetUserName") or extra.get("SubjectUserName") or None
                    source_ip = (
                        extra.get("IpAddress")
                        or extra.get("SourceAddress")
                        or extra.get("WorkstationName")
                        or None
                    )
                    if source_ip in ("-", "::1", "127.0.0.1", "LOCAL", ""):
                        source_ip = None
                    if source_ip and source_ip.startswith("::ffff:"):
                        source_ip = source_ip[7:]

                    raw        = record["data"][:500]
                    event_type = self.EVENT_TYPE_MAP.get(event_id, "other")

                    events.append(NormalizedEvent(
                        timestamp=ts,
                        source_type="windows_endpoint",
                        hostname=normalize_entity(computer),
                        username=normalize_entity(username),
                        source_ip=normalize_entity(source_ip),
                        event_type=event_type,
                        event_id=event_id,
                        raw_message=raw,
                        extra_fields=extra,
                    ))
                except Exception as e:
                    self._log_skip(str(record)[:120], f"evtx record error: {e}")
        except Exception as e:
            logger.error("Failed to open evtx file %s: %s", file_path, e)
        return events

    # -- CSV parsing (Windows Event Viewer export) --------------------------------

    def _parse_csv(self, file_path: str) -> list[NormalizedEvent]:
        events: list[NormalizedEvent] = []
        try:
            with open(file_path, "r", encoding="utf-8-sig", errors="replace") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    try:
                        event_id  = str(row.get("EventID") or row.get("Event ID") or "")
                        time_raw  = row.get("TimeCreated") or row.get("Date and Time") or ""
                        computer  = row.get("Computer") or row.get("Source") or ""
                        username  = row.get("SubjectUserName") or row.get("TargetUserName") or row.get("Account Name") or ""
                        source_ip = row.get("IpAddress") or row.get("Source Network Address") or ""

                        ts = self._safe_parse_timestamp(time_raw) or datetime.now(timezone.utc).replace(tzinfo=None)
                        if source_ip in ("-", "::1", ""):
                            source_ip = None

                        raw        = str(row)[:500]
                        event_type = self.EVENT_TYPE_MAP.get(event_id.strip(), "other")

                        _USEFUL_CSV_FIELDS = {
                            "LogonType", "ProcessName", "CommandLine", "NewProcessName",
                            "ParentProcessName", "TaskName", "ServiceName", "GroupName",
                            "AuthenticationPackageName", "FailureReason", "PrivilegeList",
                            "SubjectUserSid", "TargetUserSid", "WorkstationName",
                        }
                        csv_extra = {
                            k: str(v)
                            for k, v in row.items()
                            if k in _USEFUL_CSV_FIELDS and v and str(v).strip() not in ("", "-", "N/A")
                        }

                        events.append(NormalizedEvent(
                            timestamp=ts,
                            source_type="windows_endpoint",
                            hostname=normalize_entity(computer),
                            username=normalize_entity(username),
                            source_ip=normalize_entity(source_ip),
                            event_type=event_type,
                            event_id=event_id.strip(),
                            raw_message=raw,
                            extra_fields=csv_extra,
                        ))
                    except Exception as e:
                        self._log_skip(str(row)[:120], f"csv row error: {e}")
        except Exception as e:
            logger.error("Failed to parse CSV %s: %s", file_path, e)
        return events

    # -- Pattern detection --------------------------------------------------------

    def _detect_patterns(self, events: list[NormalizedEvent]) -> list[NormalizedEvent]:
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

        user_hosts: dict[str, set[str]] = defaultdict(set)
        for ev in events:
            if ev.event_type in ("auth_success", "explicit_credential") and ev.username and ev.hostname:
                user_hosts[ev.username].add(ev.hostname)
        lateral_users = {u for u, hosts in user_hosts.items() if len(hosts) >= 3}

        for ev in events:
            if ev.source_ip in brute_ips and "brute_force_candidate" not in ev.flags:
                ev.flags.append("brute_force_candidate")
                ev.severity_hint = "high"
            if ev.username in lateral_users and "lateral_movement_candidate" not in ev.flags:
                ev.flags.append("lateral_movement_candidate")
                ev.severity_hint = "high"

        return events
