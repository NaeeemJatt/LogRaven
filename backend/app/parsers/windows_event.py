# LogRaven — Windows Event Log Parser
#
# PURPOSE:
#   Parses Windows Event Log files (.evtx binary or CSV export).
#   Uses pyevtx-rs (pip install evtx) — 440x faster than python-evtx.
#
# LIBRARY:
#   from evtx import PyEvtxParser
#   parser = PyEvtxParser(file_path)
#   for record in parser.records_json(): ...
#
# EVENTID CLASSIFICATION MAP:
#   4625 -> auth_failure       (failed login)
#   4624 -> auth_success       (successful login)
#   4648 -> explicit_credential (RunAs / network logon with explicit creds)
#   4720 -> account_created
#   4688 -> process_exec
#   4698 -> scheduled_task_create
#   4702 -> scheduled_task_modify
#   4732 -> group_member_add
#
# DETECTION FLAGS:
#   brute_force: 5+ EventID 4625 from same IP within 60 seconds
#   lateral_movement: EventID 4648 targeting 3+ different hostnames
#
# TEST WITH: lograven/test-data/Credential_Access/*.evtx
#
# TODO Month 2 Week 3: Implement this file.

from app.parsers.base import BaseParser
from app.parsers.normalizer import NormalizedEvent


class WindowsEventParser(BaseParser):

    # EventID -> event_type mapping
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
        # TODO: Implement using from evtx import PyEvtxParser
        # Stream records via parser.records_json()
        # Apply EVENT_TYPE_MAP for classification
        # Call _detect_patterns() after parsing all events
        return []

    def _detect_patterns(self, events: list) -> list:
        # TODO: Brute force and lateral movement detection
        return events
