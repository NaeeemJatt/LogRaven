# LogRaven — Optional external error alerting (Sentry)
#
# init_error_alerting() is a no-op unless SENTRY_DSN is configured, so
# development, tests and DSN-less deployments are unaffected. Called from the
# API lifespan and the Celery worker/beat entrypoints.

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def init_error_alerting(component: str) -> bool:
    """Initialize Sentry for `component` ('api' | 'worker'). Returns True when active."""
    dsn = settings.SENTRY_DSN.strip()
    if not dsn:
        return False

    try:
        import sentry_sdk
    except ImportError:
        logger.warning("SENTRY_DSN is set but sentry-sdk is not installed; alerting disabled")
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment="production" if not settings.DEBUG else "development",
        release=settings.APP_VERSION,
        # Errors only — no performance tracing to keep overhead near zero.
        traces_sample_rate=0.0,
        send_default_pii=False,
    )
    sentry_sdk.set_tag("component", component)
    logger.info("Sentry error alerting active (component=%s)", component)
    return True
