# LogRaven — Syslog AI Prompt

from app.ai.prompts.base_prompt import SYSTEM_PROMPT, build_prompt

SYSLOG_SYSTEM_PROMPT = SYSTEM_PROMPT + """

Linux Syslog specific guidance:
- PAM auth failures then success from same IP = brute force success (T1110.001)
- sudo from non-standard users = privilege escalation (T1548.003)
- useradd/usermod events = persistence (T1136.001)
- SSH from new IP with valid credentials = initial access (T1078)"""


def build_syslog_prompt(events: list) -> tuple[str, str]:
    """Returns (system_prompt, user_prompt) for Linux syslog analysis."""
    return SYSLOG_SYSTEM_PROMPT, build_prompt(events, "Linux Syslog")
