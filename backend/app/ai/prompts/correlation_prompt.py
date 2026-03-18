# LogRaven — Correlation AI Prompt

import json

CORRELATION_SYSTEM_PROMPT = """You are a senior SOC analyst analyzing correlated security events \
that share a common entity (IP/username/hostname) across multiple log sources. \
These are NOT isolated events — they form an attack chain.

For each chain, identify:
1. The single ATT&CK technique explaining ALL events together
2. The attack narrative as a timeline in plain English
3. Severity based on combined evidence not individual events
4. All IOCs extracted from the chain

Return ONLY a JSON array. No markdown. No commentary.

Each finding must follow this exact schema:
{
  "severity": "critical|high|medium|low|informational",
  "title": "max 80 chars",
  "description": "attack timeline narrative in plain English (2-4 sentences)",
  "mitre_technique_id": "T####.### or null if not certain",
  "iocs": ["list of IPs, usernames, hostnames from the chain"],
  "remediation": "one specific actionable step",
  "confidence": 0.9
}"""


def build_correlation_prompt(chains: list) -> tuple[str, str]:
    """Returns (system_prompt, user_prompt) for correlated attack chain analysis."""
    # Serialize chains — convert any non-serializable objects
    serializable = []
    for chain in chains:
        chain_copy = dict(chain)
        if "events" in chain_copy:
            events_out = []
            for ev in chain_copy["events"]:
                if hasattr(ev, "__dict__"):
                    from datetime import datetime
                    events_out.append({
                        "timestamp": ev.timestamp.isoformat() if isinstance(ev.timestamp, datetime) else str(ev.timestamp),
                        "event_type": ev.event_type,
                        "source_type": ev.source_type,
                        "username": ev.username,
                        "source_ip": ev.source_ip,
                        "hostname": ev.hostname,
                        "event_id": ev.event_id,
                        "flags": ev.flags,
                        "severity_hint": ev.severity_hint,
                    })
                else:
                    events_out.append({k: v for k, v in ev.items() if k != "raw_message"})
            chain_copy["events"] = events_out
        serializable.append(chain_copy)

    chains_json = json.dumps(serializable, default=str)
    user_prompt = (
        f"Analyze these correlated attack chains across multiple log sources:\n\n"
        f"{chains_json}"
    )
    return CORRELATION_SYSTEM_PROMPT, user_prompt
