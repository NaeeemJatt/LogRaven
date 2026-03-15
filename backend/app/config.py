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
from typing import Literal
from pathlib import Path

# .env lives at project root: LogRaven/.env (two levels above backend/app/config.py)
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    # App
    APP_NAME: str = "LogRaven"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Auth
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Storage
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    LOCAL_STORAGE_PATH: str = "./local"

    # AI
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # License
    LICENSE_KEY: str = ""
    LICENSE_BYPASS_DEV: bool = False  # Set True only in development

    # S3 (production only)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "eu-west-1"
    S3_BUCKET_NAME: str = "lograven-prod"

    # AI Cost Ceilings (max events sent to AI per investigation)
    AI_CEILING_FREE: int = 2000
    AI_CEILING_PRO: int = 10000
    AI_CEILING_TEAM: int = 50000

    class Config:
        env_file = str(_ENV_FILE)
        case_sensitive = True


settings = Settings()
