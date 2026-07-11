import uuid
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, Response

from app.api.compliance import routes as compliance_routes
from app.api.dashboard import routes as dashboard_routes
from app.api.investigations import routes as investigation_routes
from app.models.soc2_audit import AuditJob


def _added_audit_job(add_mock) -> AuditJob:
    """The retry route now also queues an AuditLog row; pick the AuditJob."""
    return next(
        call.args[0] for call in add_mock.call_args_list
        if isinstance(call.args[0], AuditJob)
    )


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value

    def scalar_one_or_none(self):
        return self.value


class _ScalarsResult:
    def __init__(self, values):
        self.values = values

    def scalars(self):
        return SimpleNamespace(all=lambda: self.values)


@pytest.mark.asyncio
async def test_investigation_list_preserves_array_and_exposes_pagination_metadata(monkeypatch):
    user = SimpleNamespace(id=uuid.uuid4())
    investigation = SimpleNamespace(id=uuid.uuid4())
    db = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[
                _ScalarResult(41),
                _ScalarsResult([investigation]),
            ]
        )
    )
    response = Response()
    serialized = SimpleNamespace(id=investigation.id)
    monkeypatch.setattr(
        investigation_routes,
        "_serialize_investigation_response",
        lambda _: serialized,
    )

    result = await investigation_routes.list_investigations(
        response=response,
        page=2,
        limit=20,
        search=" auth ",
        sort="name",
        direction="asc",
        current_user=user,
        db=db,
    )

    assert result == [serialized]
    assert response.headers["X-Total-Count"] == "41"
    assert response.headers["X-Total-Pages"] == "3"
    statements = [str(call.args[0]) for call in db.execute.await_args_list]
    assert all("investigations.user_id" in statement for statement in statements)
    assert "lower(investigations.name) LIKE lower" in statements[0]
    assert "investigations.name ASC" in statements[1]
    assert "investigations.id ASC" in statements[1]


@pytest.mark.asyncio
async def test_findings_are_user_scoped_filtered_paginated_and_never_include_raw_logs():
    user = SimpleNamespace(id=uuid.uuid4())
    finding_id = uuid.uuid4()
    investigation_id = uuid.uuid4()
    report_id = uuid.uuid4()
    finding = SimpleNamespace(
        id=finding_id,
        severity="high",
        title="Suspicious login",
        description="Repeated failed authentication",
        finding_type="single",
        mitre_technique_id="T1110",
        mitre_technique_name="Brute Force",
        mitre_tactic="Credential Access",
        remediation="Reset credentials",
        source_files=["auth.log"],
        confidence=0.9,
        created_at=None,
    )
    row = (finding, report_id, investigation_id, "Auth review", None)
    db = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[
                _ScalarResult(1),
                SimpleNamespace(all=lambda: [("critical", 2), ("high", 1)]),
                SimpleNamespace(all=lambda: [row]),
            ]
        )
    )

    result = await investigation_routes.list_findings(
        page=1,
        limit=20,
        severity="high",
        search="login",
        current_user=user,
        db=db,
    )

    assert result["total"] == 1
    assert result["severity_counts"] == {"critical": 2, "high": 1}
    assert result["items"][0]["investigation"] == {
        "id": str(investigation_id),
        "name": "Auth review",
        "created_at": None,
    }
    assert "raw_logs" not in str(result).lower()
    statements = [str(call.args[0]) for call in db.execute.await_args_list]
    assert all("reports.user_id" in statement for statement in statements)
    assert all("investigations.user_id" in statement for statement in statements)


@pytest.mark.asyncio
async def test_dashboard_stats_are_account_wide_instead_of_page_derived():
    user = SimpleNamespace(id=uuid.uuid4(), timezone="Asia/Karachi")
    created_at = datetime(2026, 7, 10, 12)
    db = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[
                _ScalarResult(41),
                SimpleNamespace(all=lambda: [("complete", 30), ("processing", 2), ("failed", 9)]),
                _ScalarResult(50),
                _ScalarResult(120),
                _ScalarsResult([{"critical": 3, "high": 5}, {"critical": 2}]),
                _ScalarsResult([created_at]),
            ]
        )
    )

    result = await dashboard_routes.get_dashboard_stats(current_user=user, db=db)

    assert result.total_investigations == 41
    assert result.active_investigations == 2
    assert result.status_counts == {"complete": 30, "processing": 2, "failed": 9}
    assert result.severity_counts == {"critical": 5, "high": 5}
    assert result.recent_investigation_dates == [created_at.isoformat()]
    assert result.recent_daily_counts == {"2026-07-10": 1}
    statements = [str(call.args[0]) for call in db.execute.await_args_list]
    assert "investigation_files.status" in statements[2]
    assert "investigations.queued_at" in statements[3]


@pytest.mark.asyncio
async def test_compliance_retry_is_owner_only_failed_only_and_enqueues_new_one_off_job(monkeypatch):
    user = SimpleNamespace(id=uuid.uuid4())
    old = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user.id,
        status="failed",
        company_name="Example",
        role_arn="arn:aws:iam::123456789012:role/LogRaven",
        audit_start_date=date(2026, 1, 1),
        audit_end_date=date(2026, 1, 31),
        frameworks=["soc2", "iso27001"],
    )
    db = SimpleNamespace(
        execute=AsyncMock(return_value=_ScalarResult(old)),
        add=MagicMock(),
        commit=AsyncMock(),
        refresh=AsyncMock(),
    )
    enqueue = MagicMock(return_value=SimpleNamespace(id="task"))
    monkeypatch.setattr(compliance_routes.run_soc2_audit, "apply_async", enqueue)
    request = SimpleNamespace(client=None, headers={})

    response = await compliance_routes.retry_audit.__wrapped__(
        request=request,
        audit_id=str(old.id),
        current_user=user,
        db=db,
    )

    new_job = _added_audit_job(db.add)
    assert new_job.id != old.id
    assert new_job.user_id == user.id
    assert new_job.recurrence == "none"
    assert new_job.status == "pending"
    assert old.status == "retried"
    assert response.audit_id == str(new_job.id)
    assert "role_arn" not in response.model_dump()
    enqueue.assert_called_once_with(args=[str(new_job.id)], task_id=str(new_job.id))

    old.status = "complete"
    with pytest.raises(HTTPException) as exc_info:
        await compliance_routes.retry_audit.__wrapped__(
            request=request,
            audit_id=str(old.id),
            current_user=user,
            db=db,
        )
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_compliance_retry_marks_new_job_failed_when_dispatch_fails(monkeypatch):
    user = SimpleNamespace(id=uuid.uuid4())
    old = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user.id,
        status="failed",
        company_name="Example",
        role_arn="arn:aws:iam::123456789012:role/LogRaven",
        audit_start_date=date(2026, 1, 1),
        audit_end_date=date(2026, 1, 31),
        frameworks=["soc2"],
    )
    db = SimpleNamespace(
        execute=AsyncMock(return_value=_ScalarResult(old)),
        add=MagicMock(),
        commit=AsyncMock(),
        refresh=AsyncMock(),
    )
    monkeypatch.setattr(
        compliance_routes.run_soc2_audit,
        "apply_async",
        MagicMock(side_effect=RuntimeError("broker down")),
    )

    with pytest.raises(HTTPException) as exc_info:
        await compliance_routes.retry_audit.__wrapped__(
            request=SimpleNamespace(client=None, headers={}),
            audit_id=str(old.id),
            current_user=user,
            db=db,
        )

    assert exc_info.value.status_code == 503
    new_job = _added_audit_job(db.add)
    assert new_job.status == "failed"
    assert "retry" in new_job.error_message.lower()


@pytest.mark.asyncio
async def test_audit_history_batches_snapshot_scores_and_is_paginated():
    user = SimpleNamespace(id=uuid.uuid4())
    jobs = [
        SimpleNamespace(
            id=uuid.uuid4(),
            company_name=f"Company {index}",
            frameworks=["soc2"],
            status="complete",
            created_at=datetime(2026, 7, 10, 12, index),
            recurrence="none",
        )
        for index in range(2)
    ]
    snapshot_scores = [(job.id, 80 + index) for index, job in enumerate(jobs)]
    db = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[
                _ScalarResult(22),
                _ScalarsResult(jobs),
                SimpleNamespace(all=lambda: snapshot_scores),
            ]
        )
    )
    response = Response()

    result = await compliance_routes.list_audits(
        response=response,
        page=2,
        limit=20,
        current_user=user,
        db=db,
    )

    assert len(result) == 2
    assert [item.score_percent for item in result] == [80, 81]
    assert response.headers["X-Total-Count"] == "22"
    assert response.headers["X-Total-Pages"] == "2"
    assert db.execute.await_count == 3
