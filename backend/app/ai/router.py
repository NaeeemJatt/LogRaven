# LogRaven — AI Analysis Router

from app.utils.logger import get_logger

logger = get_logger(__name__)


async def route_analysis(
    events: list,
    log_type: str,
    chains: list,
    user_tier: str,
) -> tuple[list, list]:
    """
    Route events to the correct prompt builder and Gemini engine.
    Returns (single_source_findings, correlated_findings).
    """
    from app.ai.cloud import engine

    # Select prompt builder based on log_type
    system_prompt, user_prompt = _select_prompt(events, log_type)

    # Single-source analysis
    single_findings = await engine.analyze_events(events, log_type, system_prompt, user_prompt)

    # Correlated chain analysis
    correlated_findings: list = []
    if chains:
        correlated_findings = await engine.analyze_chains(chains)

    logger.info(
        "LogRaven AI router: %d single findings, %d correlated findings (log_type=%s)",
        len(single_findings),
        len(correlated_findings),
        log_type,
    )
    return single_findings, correlated_findings


def _select_prompt(events: list, log_type: str) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for the given log_type."""
    if log_type == "windows_event":
        from app.ai.prompts.windows_prompt import build_windows_prompt
        return build_windows_prompt(events)

    if log_type == "syslog":
        from app.ai.prompts.syslog_prompt import build_syslog_prompt
        return build_syslog_prompt(events)

    if log_type == "cloudtrail":
        from app.ai.prompts.cloudtrail_prompt import build_cloudtrail_prompt
        return build_cloudtrail_prompt(events)

    if log_type == "nginx":
        from app.ai.prompts.nginx_prompt import build_nginx_prompt
        return build_nginx_prompt(events)

    # Default / mixed — use base prompt directly
    from app.ai.prompts.base_prompt import SYSTEM_PROMPT, build_prompt
    return SYSTEM_PROMPT, build_prompt(events, log_type or "mixed")
