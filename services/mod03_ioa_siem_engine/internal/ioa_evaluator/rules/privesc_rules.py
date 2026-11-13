"""MITRE ATT&CK Privilege Escalation Detection Rules (T1078.004, T1098)."""

from typing import Any, Dict, List, Optional


class PrivilegeEscalationRule:
    """Evaluates multi-step privilege escalation sequences within the sliding window.
    
    Rule IOA-AWS-PRIVESC-004:
    Detects iam:PassRole followed by lambda:CreateFunction/InvokeFunction or ec2:RunInstances.
    """

    RULE_ID = "IOA-AWS-PRIVESC-004"
    NAME = "AWS IAM PassRole Privilege Escalation to Compute"
    SEVERITY = "CRITICAL"
    MITRE_TECHNIQUE = "T1078.004"
    MITRE_TACTIC = "PRIVILEGE_ESCALATION"

    @classmethod
    def evaluate(cls, window_events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Scans sequence of chronological events for the PassRole -> Create/Invoke execution chain."""
        if len(window_events) < 2:
            return None

        has_pass_role = False
        pass_role_time = None
        pass_role_event = None

        has_create_function = False
        has_invoke_function = False
        triggering_events = []

        for evt in window_events:
            event_name = evt.get("event_name", "")

            if event_name in ("PassRole", "iam:PassRole"):
                has_pass_role = True
                pass_role_time = evt.get("timestamp") or evt.get("event_time")
                pass_role_event = evt
                triggering_events.append(evt)

            elif has_pass_role and event_name in ("CreateFunction", "lambda:CreateFunction", "CreateFunction20150331"):
                has_create_function = True
                triggering_events.append(evt)

            elif has_pass_role and (has_create_function or event_name in ("InvokeFunction", "lambda:InvokeFunction", "RunInstances", "ec2:RunInstances")):
                has_invoke_function = True
                triggering_events.append(evt)
                # Chain complete: PassRole -> CreateFunction/RunInstances -> Invoke
                return {
                    "rule_id": cls.RULE_ID,
                    "rule_name": cls.NAME,
                    "severity": cls.SEVERITY,
                    "mitre_tactic": cls.MITRE_TACTIC,
                    "mitre_technique": cls.MITRE_TECHNIQUE,
                    "actor_user_arn": evt.get("actor_user_arn"),
                    "account_id": evt.get("account_id"),
                    "matched_events_count": len(triggering_events),
                    "evidence_events": triggering_events,
                    "description": (
                        f"Detected multi-step privilege escalation: Principal {evt.get('actor_user_arn')} "
                        f"passed an IAM role and executed compute actions ({event_name}) within 15-minute window."
                    ),
                }

        return None

