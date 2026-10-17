import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.tasks.process_investigation import _pipeline_execution_guard


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("LOGRAVEN_RUN_INTEGRATION") != "1",
        reason="set LOGRAVEN_RUN_INTEGRATION=1 to use real PostgreSQL",
    ),
]


@pytest.mark.asyncio
async def test_postgres_session_lock_blocks_concurrent_run_and_allows_redelivery():
    investigation_id = str(uuid.uuid4())
    url = (os.getenv("INTEGRATION_DATABASE_URL") or os.environ["DATABASE_URL"]).replace(
        "postgresql://", "postgresql+asyncpg://", 1
    )
    engine = create_async_engine(url, poolclass=NullPool)

    try:
        async with _pipeline_execution_guard(
            investigation_id,
            connection_factory=engine.connect,
        ) as first:
            assert first is True
            async with _pipeline_execution_guard(
                investigation_id,
                connection_factory=engine.connect,
            ) as concurrent:
                assert concurrent is False

        async with _pipeline_execution_guard(
            investigation_id,
            connection_factory=engine.connect,
        ) as redelivery:
            assert redelivery is True
    finally:
        await engine.dispose()
