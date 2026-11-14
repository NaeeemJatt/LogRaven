"""MITRE ATT&CK Persistence Detection Rules (T1098)."""

from typing import Any, Dict, List, Optional


class PersistenceRule:
    """Evaluates multi-step account creation and privilege grant sequences.
    
    Rule IOA-AWS-PERSIST-002:
    Detects CreateUser or CreateAccessKey followed by AttachUserPolicy/PutUserPolicy.
    """

    RULE_ID = "IOA-AWS-PERSIST-002"
    NAME = "Backdoor Account Creation with Admin Policy Attachment"
    SEVERITY = "CRITICAL"
    MITRE_TECHNIQUE = "T1098"
    MITRE_TACTIC = "PERSISTENCE"

    @classmethod
    def evaluate(cls, window_events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        has_create_identity = False
        triggering = []

        for evt in window_events:
            event_name = evt.get("event_name", "")

            if event_name in ("CreateUser", "iam:CreateUser", "CreateAccessKey", "iam:CreateAccessKey"):
                has_create_identity = True
                triggering.append(evt)

            elif has_create_identity and event_name in (
                "AttachUserPolicy",
                "iam:AttachUserPolicy",
                "AttachRolePolicy",
                "iam:AttachRolePolicy",
                "PutUserPolicy",
                "iam:PutUserPolicy",
            ):
                triggering.append(evt)
                return {
                    "rule_id": cls.RULE_ID,
                    "rule_name": cls.NAME,
                    "severity": cls.SEVERITY,
                    "mitre_tactic": cls.MITRE_TACTIC,
                    "mitre_technique": cls.MITRE_TECHNIQUE,
                    "actor_user_arn": evt.get("actor_user_arn"),
                    "account_id": evt.get("account_id"),
                    "matched_events_count": len(triggering),
                    "evidence_events": triggering,
                    "description": (
                        f"Detected persistence backdoor: Principal {evt.get('actor_user_arn')} created "
                        f"an identity and attached administrative policies within sliding window."
                    ),
                }

        return None

