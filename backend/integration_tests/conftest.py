import os
from collections.abc import Generator

import psycopg2
import pytest
import redis


def _service_url(name: str) -> str:
    url = os.getenv(f"INTEGRATION_{name}_URL") or os.getenv(f"{name}_URL")
    if not url:
        pytest.fail(f"INTEGRATION_{name}_URL is required when LOGRAVEN_RUN_INTEGRATION=1")
    return url


@pytest.fixture
def postgres_connection() -> Generator:
    url = _service_url("DATABASE").replace("postgresql+asyncpg://", "postgresql://", 1)
    connection = psycopg2.connect(url)
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def redis_client() -> Generator:
    client = redis.Redis.from_url(_service_url("REDIS"), decode_responses=True)
    client.ping()
    try:
        yield client
    finally:
        client.close()
