# LogRaven — Base AI Prompt Template

import json
from datetime import datetime

SYSTEM_PROMPT = """You are a senior SOC analyst and DFIR specialist with \
15 years of experience analyzing security logs.
Analyze the provided log events and return ONLY a JSON array of findings.
No markdown. No commentary. No preamble. Only the raw JSON array.

Each finding must follow this exact schema:
{
  "severity": "critical|high|medium|low|informational",
  "title": "max 80 chars",
  "description": "2-3 plain English sentences explaining what happened",
  "mitre_technique_id": "T####.### or null if not certain",
  "iocs": ["list of IPs, hashes, domains, usernames"],
  "remediation": "one specific actionable step",
  "confidence": 0.9
}

RULES:
- Return only the JSON array. Nothing else.
- NEVER hallucinate MITRE technique IDs. Use null if unsure.
- Severity must reflect actual impact not just indicator presence.
- Minimum 1 finding, maximum 20 findings per response.
- Focus on actionable findings only. Ignore pure noise."""


def _serialize_events(events: list) -> str:
    """Serialize events to compact JSON, stripping raw_message to save tokens."""
    compact = []
    for ev in events:
        # Support both NormalizedEvent dataclasses and plain dicts
        if hasattr(ev, "__dict__"):
            d = {
                "timestamp": ev.timestamp.isoformat() if isinstance(ev.timestamp, datetime) else str(ev.timestamp),
                "event_type": ev.event_type,
                "username": ev.username,
                "source_ip": ev.source_ip,
                "hostname": ev.hostname,
                "event_id": ev.event_id,
                "flags": ev.flags,
                "severity_hint": ev.severity_hint,
            }
        else:
            d = {k: v for k, v in ev.items() if k != "raw_message"}
            if "timestamp" in d and isinstance(d["timestamp"], datetime):
                d["timestamp"] = d["timestamp"].isoformat()
        compact.append(d)
    return json.dumps(compact, default=str)


def build_prompt(events: list, log_type: str) -> str:
    """Build the user message prompt for a standard log analysis."""
    events_json = _serialize_events(events)
    return (
        f"Analyze these {log_type} security log events and return findings:\n\n"
        f"{events_json}"
    )
