"""Pre-flight IAM Policy Simulator and Health Verification (FR-MOD1-04, TC-MOD1-003)."""

import asyncio
import inspect
from typing import Any, Dict, List, Optional
import boto3
from botocore.exceptions import ClientError


# Mandatory actions for full LogRaven IOM (Indicator of Misconfiguration) & IOA (Indicator of Attack) operation
REQUIRED_ACTIONS = [
    "s3:GetEncryptionConfiguration",
    "s3:GetBucketPublicAccessBlock",
    "s3:GetBucketPolicyStatus",
    "kms:GetKeyRotationStatus",
    "iam:SimulatePrincipalPolicy",
    "events:PutEvents",
]


class PolicySimulator:
    """Validates effective IAM permissions on the assumed role using iam:SimulatePrincipalPolicy."""

    def __init__(self, iam_client: Optional[Any] = None):
        self._iam_client = iam_client

    def _get_iam_client(self, session_credentials: Optional[Dict[str, Any]] = None):
        if self._iam_client is not None:
            return self._iam_client
        if session_credentials:
            return boto3.client(
                "iam",
                aws_access_key_id=session_credentials.get("access_key_id"),
                aws_secret_access_key=session_credentials.get("secret_access_key"),
                aws_session_token=session_credentials.get("session_token"),
            )
        return boto3.client("iam")

    async def verify_permissions(
        self,
        role_arn: str,
        session_credentials: Optional[Dict[str, Any]] = None,
        actions_to_test: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Runs simulate_principal_policy across required security audit actions.
        
        Returns validation summary with status, iom_ready, ioa_stream_ready, missing_permissions.
        """
        actions = actions_to_test or REQUIRED_ACTIONS
        iam = self._get_iam_client(session_credentials)

        try:
            res = iam.simulate_principal_policy(
                PolicySourceArn=role_arn,
                ActionNames=actions,
            )
            if inspect.iscoroutine(res):
                res = await res
            eval_results = res.get("EvaluationResults", [])
        except ClientError as e:
            # If iam:SimulatePrincipalPolicy itself is denied or role invalid
            code = e.response.get("Error", {}).get("Code", "")
            msg = e.response.get("Error", {}).get("Message", "")
            return {
                "status": "ERROR",
                "iom_ready": False,
                "ioa_stream_ready": False,
                "missing_permissions": actions,
                "error_code": code,
                "message": msg,
            }

        allowed_actions = set()
        for res in eval_results:
            decision = res.get("EvalDecision", "")
            action_name = res.get("EvalActionName", "")
            if decision in ("allowed", "implicitDenyAllowed"):
                allowed_actions.add(action_name)

        missing = [a for a in actions if a not in allowed_actions]

        # Determine readiness flags
        ioa_stream_ready = "events:PutEvents" not in missing
        # IOM is ready if basic read permissions exist
        iom_missing = [a for a in missing if a != "events:PutEvents"]
        iom_ready = len(iom_missing) == 0

        if not missing:
            status = "CONNECTED"
        elif iom_ready or ioa_stream_ready:
            status = "DEGRADED"
        else:
            status = "ERROR"

        return {
            "status": status,
            "iom_ready": iom_ready,
            "ioa_stream_ready": ioa_stream_ready,
            "missing_permissions": missing,
        }
