# LogRaven — derive Logtest log_format and synthetic location from upload context.

from __future__ import annotations

import uuid
from pathlib import Path

from app.parsers.sniff import SniffResult

# Allowed Logtest log_format values (Wazuh-compatible subset we use).
LOG_FORMAT_SYSLOG = "syslog"
LOG_FORMAT_JSON = "json"
LOG_FORMAT_IIS = "iis"


def synthetic_location(investigation_id: uuid.UUID, filename: str) -> str:
    safe = Path(filename).name.replace("..", "_")
    return f"/lograven/investigations/{investigation_id}/{safe}"


def resolve_log_format(
    *,
    source_type: str,
    sniff: SniffResult,
    filename: str,
) -> str:
    """
    Pick API log_format hint (not a named decoder — manager auto-matches inside format).
    """
    if sniff.suggested_log_format:
        return sniff.suggested_log_format

    ext = Path(filename).suffix.lower()
    if ext == ".json" or sniff.looks_like_jsonl:
        return LOG_FORMAT_JSON

    if source_type == "web_server":
        if sniff.looks_like_iis_w3c:
            return LOG_FORMAT_IIS
        # Nginx/Apache combined often still works as syslog-style free text in many setups;
        # syslog is the safer generic text bucket for Logtest.
        return LOG_FORMAT_SYSLOG

    if source_type == "cloudtrail":
        return LOG_FORMAT_JSON

    return LOG_FORMAT_SYSLOG
