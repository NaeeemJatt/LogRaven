import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from celery.exceptions import Retry

from app.tasks import process_investigation as pipeline


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value


class _ConnectionContext:
    def __init__(self, *, acquired: bool, events: list[str]):
        self.acquired = acquired
        self.events = events

    async def __aenter__(self):
        self.events.append("open")
        return self

    async def __aexit__(self, *_args):
        self.events.append("close")

    async def execute(self, statement, _params):
        sql = str(statement)
        if "pg_try_advisory_lock" in sql:
            self.events.append("lock")
            return _ScalarResult(self.acquired)
        if "pg_advisory_unlock" in sql:
            self.events.append("unlock")
            return _ScalarResult(True)
        raise AssertionError(f"unexpected SQL: {sql}")

    async def commit(self):
        self.events.append("commit")


def _connection_factory(*, acquired: bool, events: list[str]):
    return lambda: _ConnectionContext(acquired=acquired, events=events)


def _guard_factory(*, acquired: bool, events: list[str]):
    return lambda investigation_id: pipeline._pipeline_execution_guard(
        investigation_id,
        connection_factory=_connection_factory(acquired=acquired, events=events),
    )


def test_advisory_lock_key_is_stable_signed_64_bit():
    investigation_id = "12345678-1234-5678-9abc-def012345678"

    first = pipeline._advisory_lock_key(investigation_id)
    second = pipeline._advisory_lock_key(str(uuid.UUID(investigation_id)))

    assert first == second
    assert -(2**63) <= first < 2**63
    assert first != pipeline._advisory_lock_key(str(uuid.uuid4()))


@pytest.mark.asyncio
async def test_guard_unlocks_before_connection_close_after_success():
    events: list[str] = []

    async with pipeline._pipeline_execution_guard(
        str(uuid.uuid4()),
        connection_factory=_connection_factory(acquired=True, events=events),
    ) as acquired:
        assert acquired is True
        events.append("inner")

    assert events == [
        "open",
        "lock",
        "commit",
        "inner",
        "unlock",
        "commit",
        "close",
    ]


@pytest.mark.asyncio
async def test_guard_unlocks_before_connection_close_after_exception():
    events: list[str] = []

    with pytest.raises(RuntimeError, match="pipeline failed"):
        async with pipeline._pipeline_execution_guard(
            str(uuid.uuid4()),
            connection_factory=_connection_factory(acquired=True, events=events),
        ) as acquired:
            assert acquired is True
            events.append("inner")
            raise RuntimeError("pipeline failed")

    assert events == [
        "open",
        "lock",
        "commit",
        "inner",
        "unlock",
        "commit",
        "close",
    ]


@pytest.mark.asyncio
async def test_concurrent_lock_miss_skips_inner_pipeline():
    events: list[str] = []
    runner = AsyncMock()

    ran = await pipeline._run_pipeline_guarded(
        str(uuid.uuid4()),
        guard_factory=_guard_factory(acquired=False, events=events),
        pipeline_runner=runner,
    )

    assert ran is False
    runner.assert_not_awaited()
    assert events == ["open", "lock", "commit", "close"]


@pytest.mark.asyncio
async def test_processing_redelivery_runs_when_lock_is_available():
    events: list[str] = []
    runner = AsyncMock()
    investigation_id = str(uuid.uuid4())

    ran = await pipeline._run_pipeline_guarded(
        investigation_id,
        cloud_ai_consent=True,
        guard_factory=_guard_factory(acquired=True, events=events),
        pipeline_runner=runner,
    )

    assert ran is True
    runner.assert_awaited_once_with(
        investigation_id,
        cloud_ai_consent=True,
    )
    assert events == ["open", "lock", "commit", "unlock", "commit", "close"]


def test_celery_entry_uses_guarded_pipeline(monkeypatch):
    guarded = AsyncMock(return_value=True)
    retry = MagicMock()
    investigation_id = str(uuid.uuid4())
    monkeypatch.setattr(pipeline, "_run_pipeline_guarded", guarded)
    monkeypatch.setattr(pipeline.process_investigation, "retry", retry)

    pipeline.process_investigation.run(investigation_id, True)

    guarded.assert_awaited_once_with(
        investigation_id,
        cloud_ai_consent=True,
    )
    retry.assert_not_called()


def test_celery_lock_miss_retries_with_bounded_backoff(monkeypatch):
    guarded = AsyncMock(return_value=False)
    retry = MagicMock(side_effect=Retry())
    investigation_id = str(uuid.uuid4())
    monkeypatch.setattr(pipeline, "_run_pipeline_guarded", guarded)
    monkeypatch.setattr(pipeline.process_investigation, "retry", retry)

    with pytest.raises(Retry):
        pipeline.process_investigation.run(investigation_id, False)

    assert pipeline.process_investigation.max_retries == 6
    assert retry.call_args.kwargs["countdown"] <= 8
    guarded.assert_awaited_once_with(
        investigation_id,
        cloud_ai_consent=False,
    )


@pytest.mark.asyncio
async def test_inline_entry_uses_guarded_pipeline(monkeypatch):
    guarded = AsyncMock()
    investigation_id = str(uuid.uuid4())
    monkeypatch.setattr(pipeline, "_run_pipeline_guarded", guarded)

    await pipeline.run_investigation_pipeline_inline(
        investigation_id,
        cloud_ai_consent=True,
    )

    guarded.assert_awaited_once_with(
        investigation_id,
        cloud_ai_consent=True,
    )
