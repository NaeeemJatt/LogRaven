"""Unit tests for zombie state reapers and sweeper tasks."""

from datetime import datetime, timedelta
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.models.investigation import Investigation
from app.models.soc2_audit import AuditJob, ComplianceException
from app.schemas.enums import InvestigationStatus, AuditJobStatus, ExceptionStatus
from app.tasks.reaper import (
    sweep_stale_investigations,
    sweep_stale_audit_jobs,
    sweep_expired_compliance_exceptions,
)


@pytest.mark.asyncio
async def test_sweep_stale_investigations_reaps_zombies():
    """Verifies investigations stuck in processing past 15m timeout are marked failed."""
    now = datetime.utcnow()
    stale_inv = Investigation(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="Zombie Investigation",
        status=InvestigationStatus.PROCESSING,
        queued_at=now - timedelta(minutes=30),
        heartbeat_at=now - timedelta(minutes=20),
    )
    active_inv = Investigation(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="Active Investigation",
        status=InvestigationStatus.PROCESSING,
        queued_at=now - timedelta(minutes=5),
        heartbeat_at=now - timedelta(minutes=1),
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    # Mock query returns only the stale investigation
    mock_result.scalars.return_value.all.return_value = [stale_inv]
    mock_db.execute.return_value = mock_result

    reaped = await sweep_stale_investigations(mock_db, timeout_minutes=15)

    assert len(reaped) == 1
    assert reaped[0] == str(stale_inv.id)
    assert stale_inv.status == InvestigationStatus.FAILED
    assert "Worker timeout" in stale_inv.error_message
    assert stale_inv.completed_at is not None
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_sweep_stale_audit_jobs_reaps_zombies():
    """Verifies audit jobs stuck in running past 30m timeout are marked failed."""
    now = datetime.utcnow()
    stale_job = AuditJob(
        id=uuid.uuid4(),
        company_name="Zombie Corp",
        role_arn="arn:aws:iam::123456789012:role/AuditRole",
        audit_start_date=now.date(),
        audit_end_date=now.date(),
        status=AuditJobStatus.RUNNING,
        heartbeat_at=now - timedelta(minutes=45),
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [stale_job]
    mock_db.execute.return_value = mock_result

    reaped = await sweep_stale_audit_jobs(mock_db, timeout_minutes=30)

    assert len(reaped) == 1
    assert reaped[0] == str(stale_job.id)
    assert stale_job.status == AuditJobStatus.FAILED
    assert "Worker timeout" in stale_job.error_message
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_sweep_expired_compliance_exceptions():
    """Verifies active exceptions with past expires_at are transitioned to expired."""
    now = datetime.utcnow()
    expired_exc = ComplianceException(
        id=uuid.uuid4(),
        company_name="Acme",
        framework="soc2",
        control_id="CC6.1",
        business_justification="Legacy firewall deprecation",
        suppressed_by="admin@acme.com",
        status=ExceptionStatus.ACTIVE,
        expires_at=now - timedelta(days=2),
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [expired_exc]
    mock_db.execute.return_value = mock_result

    swept = await sweep_expired_compliance_exceptions(mock_db)

    assert len(swept) == 1
    assert swept[0] == str(expired_exc.id)
    assert expired_exc.status == ExceptionStatus.EXPIRED
    mock_db.commit.assert_awaited_once()
