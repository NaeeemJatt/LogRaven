import sys
import os
import types
from unittest.mock import MagicMock, patch

# Add backend root to path so `from app.xxx` works
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# Stub out settings before app.config is imported (patch target must exist).
# ---------------------------------------------------------------------------
_mock_settings = MagicMock()
_mock_settings.DATABASE_URL         = "postgresql://test:test@localhost/test"
_mock_settings.REDIS_URL            = "redis://localhost:6379"
_mock_settings.JWT_SECRET_KEY       = "test-secret-key-with-32-characters!"
_mock_settings.JWT_ALGORITHM        = "HS256"
_mock_settings.JWT_ISSUER           = "lograven"
_mock_settings.JWT_AUDIENCE         = "lograven-api"
_mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES  = 15
_mock_settings.REFRESH_TOKEN_EXPIRE_DAYS    = 7
_mock_settings.STORAGE_BACKEND     = "local"
_mock_settings.LOCAL_STORAGE_PATH  = "./local"
_mock_settings.GEMINI_API_KEY      = "test-gemini-key"
_mock_settings.ANTHROPIC_API_KEY   = ""
_mock_settings.OPENAI_API_KEY      = ""
_mock_settings.DEBUG               = False
_mock_settings.APP_NAME            = "LogRaven"
_mock_settings.APP_VERSION         = "1.0.0"
_mock_settings.AWS_ACCESS_KEY_ID   = ""
_mock_settings.AWS_SECRET_ACCESS_KEY = ""
_mock_settings.AWS_REGION          = "eu-west-1"
_mock_settings.S3_BUCKET_NAME      = "test-bucket"
_mock_settings.S3_DOWNLOAD_URL_EXPIRE_SECONDS = 900
_mock_settings.AI_CEILING_FREE     = 2000
_mock_settings.AI_CEILING_PRO      = 10000
_mock_settings.AI_CEILING_TEAM     = 50000
_mock_settings.MAX_PARSED_EVENTS_PER_FILE = 50000
_mock_settings.MAX_PARSED_EVENTS_PER_INVESTIGATION = 100000
_mock_settings.CELERY_TASK_ALWAYS_EAGER = True
_mock_settings.AUTO_START_DEV_WORKER = True
_mock_settings.COOKIE_SECURE       = False
_mock_settings.PUBLIC_API_BASE_URL = "http://localhost:8000"
_mock_settings.INCLUDE_TOKENS_IN_AUTH_JSON = False
_mock_settings.TRUST_FORWARDED_FOR = False

_cfg_stub = types.ModuleType("app.config")
_cfg_stub.settings = _mock_settings
sys.modules["app.config"] = _cfg_stub

# Avoid real DB engine during import (patch target must exist on sqlalchemy, not app.dependencies)
import importlib
import unittest.mock as _mock

_fake_engine = _mock.MagicMock()
_fake_session_maker = _mock.MagicMock()
patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=_fake_engine).start()
_dep_mod = importlib.import_module("app.dependencies")
_dep_mod.AsyncSessionLocal = _fake_session_maker
