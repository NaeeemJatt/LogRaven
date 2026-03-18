# LogRaven — CloudTrail AI Prompt

from app.ai.prompts.base_prompt import SYSTEM_PROMPT, build_prompt

CLOUDTRAIL_SYSTEM_PROMPT = SYSTEM_PROMPT + """

AWS CloudTrail specific guidance:
- AssumeRole to privileged roles = privilege escalation (T1078.004)
- CreateAccessKey for other users = persistence (T1098.001)
- Failed API calls from new IPs = credential testing (T1110)
- Security group modifications = defense evasion (T1562.007)
- S3 GetObject on sensitive buckets = exfiltration (T1530)"""


def build_cloudtrail_prompt(events: list) -> tuple[str, str]:
    """Returns (system_prompt, user_prompt) for AWS CloudTrail analysis."""
    return CLOUDTRAIL_SYSTEM_PROMPT, build_prompt(events, "AWS CloudTrail")
