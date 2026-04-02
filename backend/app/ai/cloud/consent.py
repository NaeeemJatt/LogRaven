from fastapi import HTTPException, status

from app.config import settings


def cloud_ai_enabled() -> bool:
    """Return True when any external AI provider is configured."""
    return any([settings.GEMINI_API_KEY, settings.ANTHROPIC_API_KEY, settings.OPENAI_API_KEY])


def require_cloud_ai_consent(consent_given: bool) -> None:
    """
    Enforce explicit opt-in before analysis is allowed to send log-derived
    data to an external AI provider.
    """
    if cloud_ai_enabled() and not consent_given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cloud AI analysis requires explicit consent.",
        )
