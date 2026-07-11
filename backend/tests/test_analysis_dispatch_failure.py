import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import create_engine, text

from app.api.investigations import routes
from app.models.investigation import Investigation
from app.models.investigation_file import InvestigationFile
from app.schemas.investigation import InvestigationAnalyzeRequest
from app.tasks.process_investigation import process_investigation


def _investigation() -> Investigation:
    investigation = Investigation(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="Dispatch failure",
        status="draft",
        correlation_enabled=False,
        created_at=datetime(2026, 7, 10),
    )
    investigation.files = [
        InvestigationFile(
            investigation_id=investigation.id,
            filename="auth.log",
            source_type="linux_endpoint",
            ingestion_mode="parsers",
            storage_key="uploads/auth.log",
            status="pending",
        )
    ]
    return investigation


def _request():
    return SimpleNamespace(client=None, headers={})


def _db(*rowcounts: int):
    return SimpleNamespace(
        add=MagicMock(),
        execute=AsyncMock(
            side_effect=[
                SimpleNamespace(rowcount=rowcount)
                for rowcount in rowcounts
            ]
        ),
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )


def _setup(monkeypatch, investigation, quota, refund, ensure_worker, delay):
    async def get_inv(*_args, **_kwargs):
        return investigation

    monkeypatch.setattr(routes, "_get_investigation_or_404", get_inv)
    monkeypatch.setattr(routes.settings, "USE_ASYNCIO_INVESTIGATION_PIPELINE", False)
    monkeypatch.setattr(routes.settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr("app.utils.rate_limiter.check_and_count_analysis", quota)
    monkeypatch.setattr("app.utils.rate_limiter.refund_analysis_quota", refund)
    monkeypatch.setattr(
        "app.tasks.dev_worker.ensure_dev_worker_running",
        ensure_worker,
    )
    monkeypatch.setattr(process_investigation, "delay", delay)


async def _analyze(investigation, db):
    return await routes.analyze_investigation.__wrapped__(
        request=_request(),
        investigation_id=investigation.id,
        body=InvestigationAnalyzeRequest(),
        current_user=SimpleNamespace(id=investigation.user_id, tier="free"),
        db=db,
    )


@pytest.mark.asyncio
async def test_worker_start_failure_compensates_refunds_and_allows_retry(monkeypatch):
    investigation = _investigation()
    db = _db(1, 1, 1)
    quota = AsyncMock(return_value=(True, 4))
    refund = AsyncMock(return_value=True)
    ensure_worker = MagicMock(side_effect=[RuntimeError("worker start failed"), True])
    delay = MagicMock()
    _setup(monkeypatch, investigation, quota, refund, ensure_worker, delay)

    with pytest.raises(routes.HTTPException) as exc_info:
        await _analyze(investigation, db)

    assert exc_info.value.status_code == 503
    assert investigation.status == "failed"
    assert investigation.error_message == routes._DISPATCH_FAILURE_MESSAGE
    refund.assert_awaited_once_with(str(investigation.user_id), "free")
    delay.assert_not_called()

    response = await _analyze(investigation, db)

    assert response["status"] == "queued"
    assert investigation.status == "queued"
    assert delay.call_count == 1
    assert refund.await_count == 1


@pytest.mark.asyncio
async def test_worker_start_false_compensates_without_calling_delay(monkeypatch):
    investigation = _investigation()
    db = _db(1, 1)
    quota = AsyncMock(return_value=(True, 4))
    refund = AsyncMock(return_value=True)
    ensure_worker = MagicMock(return_value=False)
    delay = MagicMock()
    _setup(monkeypatch, investigation, quota, refund, ensure_worker, delay)

    with pytest.raises(routes.HTTPException) as exc_info:
        await _analyze(investigation, db)

    assert exc_info.value.status_code == 503
    assert investigation.status == "failed"
    delay.assert_not_called()
    refund.assert_awaited_once()


@pytest.mark.asyncio
async def test_broker_failure_compensates_and_refunds(monkeypatch):
    investigation = _investigation()
    db = _db(1, 1)
    quota = AsyncMock(return_value=(True, 4))
    refund = AsyncMock(return_value=True)
    ensure_worker = MagicMock()
    delay = MagicMock(side_effect=RuntimeError("broker unavailable"))
    _setup(monkeypatch, investigation, quota, refund, ensure_worker, delay)

    with pytest.raises(routes.HTTPException) as exc_info:
        await _analyze(investigation, db)

    assert exc_info.value.status_code == 503
    ensure_worker.assert_called_once()
    delay.assert_called_once()
    assert investigation.status == "failed"
    refund.assert_awaited_once()
    assert db.commit.await_count == 2


@pytest.mark.asyncio
async def test_ambiguous_dispatch_does_not_overwrite_advanced_worker_or_refund(monkeypatch):
    investigation = _investigation()
    db = _db(1, 0)
    quota = AsyncMock(return_value=(True, 4))
    refund = AsyncMock(return_value=True)
    ensure_worker = MagicMock()
    delay = MagicMock(side_effect=RuntimeError("ambiguous broker result"))
    _setup(monkeypatch, investigation, quota, refund, ensure_worker, delay)

    with pytest.raises(routes.HTTPException) as exc_info:
        await _analyze(investigation, db)

    assert exc_info.value.status_code == 503
    assert investigation.status == "queued"
    refund.assert_not_awaited()


@pytest.mark.asyncio
async def test_successful_celery_dispatch_does_not_refund(monkeypatch):
    investigation = _investigation()
    db = _db(1)
    quota = AsyncMock(return_value=(True, 4))
    refund = AsyncMock(return_value=True)
    ensure_worker = MagicMock()
    delay = MagicMock()
    _setup(monkeypatch, investigation, quota, refund, ensure_worker, delay)

    response = await _analyze(investigation, db)

    assert response["status"] == "queued"
    delay.assert_called_once()
    refund.assert_not_awaited()
    assert db.execute.await_count == 1
    assert db.commit.await_count == 1


@pytest.mark.asyncio
async def test_dispatch_failure_does_not_refund_when_quota_failed_open(monkeypatch):
    investigation = _investigation()
    db = _db(1, 1)
    quota = AsyncMock(return_value=(True, -1))
    refund = AsyncMock(return_value=True)
    ensure_worker = MagicMock()
    delay = MagicMock(side_effect=RuntimeError("broker unavailable"))
    _setup(monkeypatch, investigation, quota, refund, ensure_worker, delay)

    with pytest.raises(routes.HTTPException):
        await _analyze(investigation, db)

    assert investigation.status == "failed"
    refund.assert_not_awaited()


def test_dispatch_compensation_requires_matching_id_user_and_queued_status():
    investigation_id = uuid.uuid4()
    user_id = uuid.uuid4()
    engine = create_engine("sqlite://")

    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE investigations (
                id VARCHAR(32) PRIMARY KEY,
                user_id VARCHAR(32) NOT NULL,
                status VARCHAR(20) NOT NULL,
                progress_stage VARCHAR(64),
                completed_at DATETIME,
                error_message TEXT
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO investigations (
                id, user_id, status, progress_stage, completed_at, error_message
            ) VALUES (?, ?, 'processing', 'parsing', NULL, NULL)
            """,
            (investigation_id.hex, user_id.hex),
        )
        processing = connection.execute(
            routes._dispatch_failure_compensation_statement(
                investigation_id,
                user_id,
            )
        )
        connection.execute(
            text("UPDATE investigations SET status = 'queued'")
        )
        wrong_user = connection.execute(
            routes._dispatch_failure_compensation_statement(
                investigation_id,
                uuid.uuid4(),
            )
        )
        compensated = connection.execute(
            routes._dispatch_failure_compensation_statement(
                investigation_id,
                user_id,
            )
        )
        row = connection.execute(
            text("SELECT status, error_message FROM investigations")
        ).one()

    assert (processing.rowcount, wrong_user.rowcount, compensated.rowcount) == (0, 0, 1)
    assert row == ("failed", routes._DISPATCH_FAILURE_MESSAGE)
