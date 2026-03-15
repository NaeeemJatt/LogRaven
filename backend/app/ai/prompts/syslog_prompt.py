# LogRaven — Syslog AI Prompt
# Log-type-specific additions for Linux syslog and auth.log analysis.
# TODO Month 3 Week 3: Implement.

SYSLOG_ADDITIONS = """
Linux syslog specific instructions:
- PAM authentication failures followed by success = brute force success (T1110.001)
- Sudo chains from non-standard users = privilege escalation (T1548.003)
- New user creation (useradd) = persistence (T1136.001)
- SSH from new country/IP = initial access (T1078)
"""
