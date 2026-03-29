# LogRaven — Windows Event Log Parser

import csv
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

    # ── EVTX parsing via python-evtx (XML API) ───────────────────────────────

    _EVTX_NS = "http://schemas.microsoft.com/win/2004/08/events/event"

    def _parse_evtx(self, file_path: str) -> list[NormalizedEvent]:
        import xml.etree.ElementTree as ET

        # Try python-evtx (installed as Evtx.Evtx)
        try:
            import Evtx.Evtx as evtx_lib
        except ImportError:
            logger.warning("evtx package not installed — falling back to CSV parser")
            return self._parse_csv(file_path)

        ns  = self._EVTX_NS
        tag = lambda name: "{%s}%s" % (ns, name)

        events: list[NormalizedEvent] = []
        try:
            with evtx_lib.Evtx(file_path) as log:
                for record in log.records():
                    try:
                        xml_str = record.xml()
                        root    = ET.fromstring(xml_str)

                        sys_el = root.find(tag("System"))
                        ed_el  = root.find(tag("EventData"))

                        if sys_el is None:
                            continue

                        event_id = (sys_el.findtext(tag("EventID")) or "").strip()
                        computer = sys_el.findtext(tag("Computer")) or ""
                        time_raw = ""
                        tc = sys_el.find(tag("TimeCreated"))
                        if tc is not None:
                            time_raw = tc.get("SystemTime") or ""

                        ts = self._safe_parse_timestamp(
                            time_raw.replace("Z", "").split(".")[0]
                        ) if time_raw else None
                        if ts is None:
                            ts = datetime.now(timezone.utc).replace(tzinfo=None)

                        # Collect EventData fields as a flat dict
                        extra: dict = {}
                        if ed_el is not None:
                            for d in ed_el.findall(tag("Data")):
                                name  = d.get("Name")
                                value = (d.text or "").strip()
                                if name and value and value not in ("-", "None", ""):
                                    extra[name] = value

                        username = extra.get("TargetUserName") or extra.get("SubjectUserName") or None
                        source_ip = extra.get("IpAddress") or extra.get("SourceAddress") or extra.get("WorkstationName") or None
                        if source_ip in ("-", "::1", "127.0.0.1", "LOCAL", ""):
                            source_ip = None

                        # Strip IPv6-mapped IPv4 prefix
                        if source_ip and source_ip.startswith("::ffff:"):
                            source_ip = source_ip[7:]

                        event_type = self.EVENT_TYPE_MAP.get(event_id, "other")
                        raw = xml_str[:500]

                        event = NormalizedEvent(
                            timestamp=ts,
                            source_type="windows_endpoint",
                            hostname=normalize_entity(computer),
                            username=normalize_entity(username),
                            source_ip=normalize_entity(source_ip),
                            event_type=event_type,
                            event_id=event_id,
                            raw_message=raw,
                            extra_fields=extra,
                        )
                        events.append(event)
                    except Exception as e:
                        self._log_skip(str(record)[:120], f"evtx record error: {e}")
        except Exception as e:
            logger.error("Failed to open evtx file %s: %s", file_path, e)
        return events

    # ── CSV parsing (Windows Event Viewer export) ─────────────────────────────

    def _parse_csv(self, file_path: str) -> list[NormalizedEvent]:
        events: list[NormalizedEvent] = []
        try:
            with open(file_path, "r", encoding="utf-8-sig", errors="replace") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    try:
                        event_id = str(row.get("EventID") or row.get("Event ID") or "")
                        time_raw = row.get("TimeCreated") or row.get("Date and Time") or ""
                        computer = row.get("Computer") or row.get("Source") or ""
                        username = row.get("SubjectUserName") or row.get("TargetUserName") or row.get("Account Name") or ""
                        source_ip = row.get("IpAddress") or row.get("Source Network Address") or ""

                        ts = self._safe_parse_timestamp(time_raw) or datetime.now(timezone.utc).replace(tzinfo=None)
                        if source_ip in ("-", "::1", ""):
                            source_ip = None

                        raw = str(row)[:500]
                        event_type = self.EVENT_TYPE_MAP.get(event_id.strip(), "other")

                        # Populate extra_fields from CSV columns for YAML rule matching
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

    # ── Pattern detection ─────────────────────────────────────────────────────

    def _detect_patterns(self, events: list[NormalizedEvent]) -> list[NormalizedEvent]:
        # Brute force: 5+ auth_failure from same IP within any 60s window
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

        # Lateral movement: auth_success/explicit_credential to 3+ distinct hosts
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
