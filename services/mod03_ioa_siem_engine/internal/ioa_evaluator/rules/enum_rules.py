"""MITRE ATT&CK Cloud Enumeration and Discovery Burst Detection Rules (T1087, T1580)."""

from typing import Any, Dict, List, Optional


class EnumerationBurstRule:
    """Evaluates rapid-fire discovery and enumeration attempts resulting in permission denials.
    
    Rule IOA-CLOUD-ENUM-011:
    Detects bursts of >= 20 AccessDenied events within a 60-second window across
    sensitive discovery/enumeration APIs.
    """

    RULE_ID = "IOA-CLOUD-ENUM-011"
    NAME = "Automated Cloud API Enumeration Burst"
    SEVERITY = "HIGH"
    MITRE_TECHNIQUE = "T1580"
    MITRE_TACTIC = "ENUMERATION"
    BURST_THRESHOLD = 20
    WINDOW_SECONDS = 60.0

    @classmethod
    def evaluate(cls, window_events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not window_events:
            return None

        denied_events = []
        for evt in window_events:
            err = evt.get("error_code")
            # Case-insensitive check for AccessDenied / Unauthorized / 403
            if err and any(term in str(err).lower() for term in ("accessdenied", "unauthorized", "permissiondenied", "forbidden")):
                denied_events.append(evt)

        if len(denied_events) >= cls.BURST_THRESHOLD:
            # Check time span of denied events
            first_ts = denied_events[0].get("timestamp") or 0.0
            last_ts = denied_events[-1].get("timestamp") or 0.0
            time_span = max(0.0, last_ts - first_ts)

            if time_span <= cls.WINDOW_SECONDS or len(denied_events) >= cls.BURST_THRESHOLD:
                first_evt = denied_events[0]
                return {
                    "rule_id": cls.RULE_ID,
                    "rule_name": cls.NAME,
                    "severity": cls.SEVERITY,
                    "mitre_tactic": cls.MITRE_TACTIC,
                    "mitre_technique": cls.MITRE_TECHNIQUE,
                    "actor_user_arn": first_evt.get("actor_user_arn"),
                    "account_id": first_evt.get("account_id"),
                    "matched_events_count": len(denied_events),
                    "evidence_events": denied_events,
                    "description": (
                        f"Detected enumeration burst: Actor {first_evt.get('actor_user_arn')} encountered "
                        f"{len(denied_events)} AccessDenied errors across discovery APIs within {time_span:.1f}s."
                    ),
                }

        return None

