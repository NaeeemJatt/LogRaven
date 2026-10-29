# LogRaven — Application Configuration
#
# PURPOSE:
#   Reads ALL environment variables using Pydantic BaseSettings.
#   Validates types and required values at startup.
#   If any required variable is missing, app refuses to start.
#   Single source of truth for all config — imported everywhere as `settings`.
#
# USAGE:
#   from app.config import settings
#   url = settings.DATABASE_URL

from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Literal
from pathlib import Path

# .env lives at project root: LogRaven/.env (two levels above backend/app/config.py)
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    # App
    APP_NAME: str = "LogRaven"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    # Extra CORS origins (comma-separated) appended to the built-in localhost
    # list. Set this in production, e.g. "https://app.lograven.com".
    CORS_ALLOWED_ORIGINS: str = ""

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Auth
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "lograven"
    JWT_AUDIENCE: str = "lograven-api"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    # httpOnly cookies: set True behind HTTPS in production
    COOKIE_SECURE: bool | None = None
    # Comma-separated emails allowed to call admin endpoints (tier changes).
    # Empty = admin endpoints disabled entirely.
    ADMIN_EMAILS: str = ""
    # When True, users must verify their email before they can log in.
    REQUIRE_VERIFIED_EMAIL_FOR_LOGIN: bool = False
    # When False, login/register/refresh JSON omits tokens (cookies only). Set True for non-browser API clients.
    INCLUDE_TOKENS_IN_AUTH_JSON: bool = False
    # When True, rate limits use first X-Forwarded-For hop (enable only behind a trusted reverse proxy)
    TRUST_FORWARDED_FOR: bool = False

    # Email (SMTP — works with Amazon SES SMTP, Gmail, Mailgun, etc.)
    # When SMTP_HOST is empty, emails are logged instead of sent (dev-safe).
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "no-reply@lograven.local"
    SMTP_USE_TLS: bool = True
    # Public URL of the frontend — used to build links in emails (verify/reset).
    FRONTEND_BASE_URL: str = "http://localhost:5173"

    # Rate limiting: set to the Redis URL in production so limits are shared
    # across API replicas. Empty = in-memory (single process only).
    RATE_LIMIT_STORAGE_URL: str = ""

    # Logging: "text" (colored, dev) or "json" (production log aggregation).
    LOG_FORMAT: Literal["text", "json"] = "text"

    # Error alerting: Sentry DSN for the API and Celery workers. Empty = disabled.
    SENTRY_DSN: str = ""

    # Storage
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    LOCAL_STORAGE_PATH: str = "./local"
    # Base URL for LocalStorageBackend download links (reverse-proxy / public API URL)
    PUBLIC_API_BASE_URL: str = "http://localhost:8000"
    # Optional S3-compatible endpoint (MinIO, etc.)
    S3_ENDPOINT_URL: str = ""

    # AI — single wired provider; other provider keys were removed because
    # nothing consumed them and they made health/consent claim AI was enabled.
    GEMINI_API_KEY: str = ""

    # S3 (production only)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "eu-west-1"
    S3_BUCKET_NAME: str = "lograven-prod"
    S3_DOWNLOAD_URL_EXPIRE_SECONDS: int = 900
    # Optional STS AssumeRole ExternalId for SOC 2 collection (confused-deputy
    # defense). When set, customers must add a matching sts:ExternalId condition
    # to their role trust policy. Empty = not enforced (backward compatible).
    AWS_ASSUME_ROLE_EXTERNAL_ID: str = ""

    # AI Cost Ceilings (max events sent to AI per investigation)
    AI_CEILING_FREE: int = 2000
    AI_CEILING_PRO: int = 10000
    AI_CEILING_TEAM: int = 50000
    # Per-tier daily analysis quota (investigations analyzed per UTC day).
    # 0 disables the quota for that tier.
    DAILY_ANALYSES_FREE: int = 5
    DAILY_ANALYSES_PRO: int = 50
    DAILY_ANALYSES_TEAM: int = 200
    # Per-tier report retention in days; 0 = keep forever (default). When set,
    # a daily maintenance task deletes reports (and their PDFs) older than this.
    REPORT_RETENTION_DAYS_FREE: int = 0
    REPORT_RETENTION_DAYS_PRO: int = 0
    REPORT_RETENTION_DAYS_TEAM: int = 0
    # Hard cap before analysis/report generation to avoid memory blowups on pathological logs.
    MAX_PARSED_EVENTS_PER_FILE: int = 50000
    MAX_PARSED_EVENTS_PER_INVESTIGATION: int = 100000
    # Testing-only escape hatch. Keep False in normal runs so analysis stays worker-isolated.
    CELERY_TASK_ALWAYS_EAGER: bool = False
    # Local development convenience: start a worker automatically when jobs are queued.
    AUTO_START_DEV_WORKER: bool = True
    # When True, run the investigation pipeline with asyncio in the API process (no Celery consumer).
    # Reliable for local uvicorn on Windows; set False when using a dedicated Celery worker (Docker/K8s).
    USE_ASYNCIO_INVESTIGATION_PIPELINE: bool = True

    # Decoder manager (Logtest-compatible API, e.g. Wazuh Manager 4.7+). Optional — only required when using decoders.
    DECODER_MANAGER_API_URL: str = ""
    DECODER_MANAGER_USER: str = ""
    DECODER_MANAGER_PASSWORD: str = ""
    DECODER_MANAGER_VERIFY_TLS: bool = True
    DECODER_MANAGER_HTTP_TIMEOUT_SEC: float = 60.0
    DECODER_MAX_LINES_PER_FILE: int = 2000
    DECODER_PLAY_MAX_LINES: int = 200

    # PlayParser: raw-vs-parsed line preview (POST /play-parser/preview)
    PLAY_PARSER_PREVIEW_MAX_LINES: int = 100
    PLAY_PARSER_PREVIEW_RAW_MAX_CHARS: int = 2000

    model_config = ConfigDict(env_file=str(_ENV_FILE), case_sensitive=True, extra="ignore")

    def model_post_init(self, __context) -> None:
        if self.COOKIE_SECURE is None:
            self.COOKIE_SECURE = not self.DEBUG
        weak = {
            "",
            "change-this-to-a-random-secret-in-production",
            "dev-secret-change-in-prod",
            "replace-with-a-strong-random-secret-at-least-32-chars",
        }
        if self.JWT_SECRET_KEY in weak or "replace-with" in self.JWT_SECRET_KEY.lower() or len(self.JWT_SECRET_KEY) < 32:
            raise ValueError("JWT_SECRET_KEY must be a strong random string at least 32 characters long.")

        if self.S3_DOWNLOAD_URL_EXPIRE_SECONDS <= 0 or self.S3_DOWNLOAD_URL_EXPIRE_SECONDS > 86400:
            raise ValueError("S3_DOWNLOAD_URL_EXPIRE_SECONDS must be between 1 and 86400.")

        if self.MAX_PARSED_EVENTS_PER_FILE <= 0 or self.MAX_PARSED_EVENTS_PER_INVESTIGATION <= 0:
            raise ValueError("Parsed event caps must be positive integers.")

        if self.DECODER_MAX_LINES_PER_FILE <= 0 or self.DECODER_PLAY_MAX_LINES <= 0:
            raise ValueError("Decoder line caps must be positive integers.")

        if self.PLAY_PARSER_PREVIEW_MAX_LINES <= 0 or self.PLAY_PARSER_PREVIEW_RAW_MAX_CHARS <= 0:
            raise ValueError("PlayParser preview caps must be positive integers.")


settings = Settings()
