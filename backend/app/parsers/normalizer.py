# LogRaven — NormalizedEvent Schema
#
# PURPOSE:
#   Defines the single output format all LogRaven parsers produce.
#   This abstraction means the AI layer never sees raw log format differences.
#   All 4 parsers output NormalizedEvent objects regardless of input format.
#
# FIELDS:
#   timestamp     — datetime UTC (required)
#   source_type   — which parser/source produced this event
#   hostname      — machine name (nullable)
#   username      — account name (nullable, normalized: lowercase, stripped)
#   source_ip     — source IP address (nullable, normalized: stripped)
#   destination_ip — destination IP (nullable)
#   event_type    — category: auth_success/auth_failure/sudo/process_exec/network/api_call/other
#   event_id      — format-specific ID (Windows EventID, CloudTrail eventName, etc.)
#   raw_message   — original log line truncated to 500 chars
#   flags         — list of detection flags: brute_force_candidate/privilege_escalation_candidate/etc.
#   severity_hint — preliminary severity from rule engine
#
# TODO Month 2 Week 1: Implement this file.

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class NormalizedEvent:
    timestamp:      datetime
    source_type:    str
    hostname:       Optional[str]   = None
    username:       Optional[str]   = None
    source_ip:      Optional[str]   = None
    destination_ip: Optional[str]   = None
    event_type:     str             = "other"
    event_id:       Optional[str]   = None
    raw_message:    str             = ""
    flags:          list            = field(default_factory=list)
    severity_hint:  str             = "informational"
