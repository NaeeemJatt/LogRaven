# LogRaven — Windows Event Log AI Prompt

from app.ai.prompts.base_prompt import SYSTEM_PROMPT, build_prompt

WINDOWS_SYSTEM_PROMPT = SYSTEM_PROMPT + """

Windows Event Log specific guidance:
- EventID 4625 chains to 4624 from same IP = successful brute force
- EventID 4648 across multiple hostnames = lateral movement (T1021)
- EventID 4688 with cmd.exe/powershell.exe parent = suspicious execution
- EventID 4698/4702 = scheduled task persistence (T1053.005)
- EventID 4720 = new account creation (T1136.001)"""


def build_windows_prompt(events: list) -> tuple[str, str]:
    """Returns (system_prompt, user_prompt) for Windows Event Log analysis."""
    return WINDOWS_SYSTEM_PROMPT, build_prompt(events, "Windows Event Log")
