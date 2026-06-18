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
#
# TODO Month 1 Week 1: Implement this file.

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
    COOKIE_SECURE: bool = False
    # When False, login/register/refresh JSON omits tokens (cookies only). Set True for non-browser API clients.
    INCLUDE_TOKENS_IN_AUTH_JSON: bool = False
    # When True, rate limits use first X-Forwarded-For hop (enable only behind a trusted reverse proxy)
    TRUST_FORWARDED_FOR: bool = False

    # Storage
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    LOCAL_STORAGE_PATH: str = "./local"
    # Base URL for LocalStorageBackend download links (reverse-proxy / public API URL)
    PUBLIC_API_BASE_URL: str = "http://localhost:8000"
    # Optional S3-compatible endpoint (MinIO, etc.)
    S3_ENDPOINT_URL: str = ""

    # AI
    GEMINI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

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

    model_config = ConfigDict(env_file=str(_ENV_FILE), case_sensitive=True)

    def model_post_init(self, __context) -> None:
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
