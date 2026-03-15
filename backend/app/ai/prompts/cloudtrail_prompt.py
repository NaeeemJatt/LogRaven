# LogRaven — CloudTrail AI Prompt
# Log-type-specific additions for AWS CloudTrail analysis.
# TODO Month 3 Week 3: Implement.

CLOUDTRAIL_ADDITIONS = """
AWS CloudTrail specific instructions:
- AssumeRole to high-privilege roles = privilege escalation (T1078.004)
- CreateAccessKey for another user = persistence (T1098.001)
- Failed API calls from unusual IPs = reconnaissance or credential testing
- Security group modifications = defense evasion (T1562.007)
- S3 GetObject on sensitive buckets = data exfiltration (T1530)
"""
