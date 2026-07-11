import os
import uuid

import pytest


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("LOGRAVEN_RUN_INTEGRATION") != "1",
        reason="set LOGRAVEN_RUN_INTEGRATION=1 to use real PostgreSQL and Redis",
    ),
]


def test_postgresql_round_trip(postgres_connection):
    with postgres_connection.cursor() as cursor:
        cursor.execute("CREATE TEMP TABLE lograven_integration_probe (value text NOT NULL)")
        cursor.execute("INSERT INTO lograven_integration_probe (value) VALUES (%s)", ("connected",))
        cursor.execute("SELECT value FROM lograven_integration_probe")
        assert cursor.fetchone() == ("connected",)


def test_redis_round_trip(redis_client):
    key = f"lograven:integration:{uuid.uuid4()}"
    try:
        assert redis_client.set(key, "connected", ex=30)
        assert redis_client.get(key) == "connected"
    finally:
        redis_client.delete(key)
