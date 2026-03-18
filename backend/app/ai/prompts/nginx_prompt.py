# LogRaven — Nginx AI Prompt

from app.ai.prompts.base_prompt import SYSTEM_PROMPT, build_prompt

NGINX_SYSTEM_PROMPT = SYSTEM_PROMPT + """

Web access log specific guidance:
- High 4xx rate from single IP = scanning (T1595)
- SQL keywords in URL = injection attempt (T1190)
- Path traversal patterns = directory traversal (T1083)
- Large POST to unusual endpoints = webshell upload attempt"""


def build_nginx_prompt(events: list) -> tuple[str, str]:
    """Returns (system_prompt, user_prompt) for Nginx access log analysis."""
    return NGINX_SYSTEM_PROMPT, build_prompt(events, "Nginx Access Log")
