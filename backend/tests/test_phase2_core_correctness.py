import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, text

from app.api.investigations import routes
from app.models.investigation import Investigation
from app.models.investigation_file import InvestigationFile
from app.schemas.investigation import InvestigationAnalyzeRequest, InvestigationUpdate
from app.tasks.maintenance import _stuck_investigations_update
from app.tasks.process_investigation import _build_source_labels, _should_run_correlation


def _investigation(*, status: str = "draft", correlation_enabled: bool = True) -> Investigation:
    return Investigation(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="Phase 2",
        status=status,
        correlation_enabled=correlation_enabled,
        created_at=datetime(2025, 1, 1),
        queued_at=None,
        completed_at=None,
        error_message=None,
    )


def test_queued_at_model_and_schemas_are_nullable_and_strict():
    assert Investigation.__table__.c.queued_at.nullable is True
    assert "queued_at" in routes.InvestigationResponse.model_fields
    assert InvestigationUpdate(correlation_enabled=True).correlation_enabled is True

    with pytest.raises(ValidationError):
        InvestigationUpdate(correlation_enabled="true")


def test_stuck_reconciliation_uses_queue_time_and_ignores_non_active_rows():
    now = datetime(2026, 7, 10, 12, 0, 0)
    cutoff = now - timedelta(hours=1)
    old = now - timedelta(days=30)
    recent = now - timedelta(minutes=5)

    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE investigations (
                id INTEGER PRIMARY KEY,
                status VARCHAR(20) NOT NULL,
                created_at DATETIME NOT NULL,
                queued_at DATETIME,
                error_message TEXT
            )
            """
        )
        connection.execute(
            text(
                """
                INSERT INTO investigations (id, status, created_at, queued_at)
                VALUES
                    (1, 'queued', :old, :recent),
                    (2, 'processing', :old, :old),
                    (3, 'complete', :old, :old),
                    (4, 'queued', :old, NULL)
                """
            ),
            {"old": old, "recent": recent},
        )

        result = connection.execute(_stuck_investigations_update(cutoff))
        rows = dict(connection.execute(text("SELECT id, status FROM investigations")).all())

    assert result.rowcount == 1
    assert rows == {1: "queued", 2: "failed", 3: "complete", 4: "queued"}


def test_concurrent_analyze_requests_have_one_database_claim_winner():
    investigation_id = uuid.uuid4()
    user_id = uuid.uuid4()
    queued_at = datetime(2026, 7, 10, 12, 0, 0)
    engine = create_engine("sqlite://")

    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE investigations (
                id VARCHAR(32) PRIMARY KEY,
                user_id VARCHAR(32) NOT NULL,
                status VARCHAR(20) NOT NULL,
                progress_stage VARCHAR(64),
                queued_at DATETIME,
                completed_at DATETIME,
                error_message TEXT
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO investigations (
                id, user_id, status, completed_at, error_message
            ) VALUES (?, ?, 'failed', '2026-07-01 00:00:00', 'old failure')
            """,
            (investigation_id.hex, user_id.hex),
        )

        first = connection.execute(
            routes._analyze_claim_statement(investigation_id, user_id, queued_at)
        )
        second = connection.execute(
            routes._analyze_claim_statement(investigation_id, user_id, queued_at)
        )
        row = connection.execute(
            text(
                """
                SELECT status, progress_stage, completed_at, error_message
                FROM investigations
                """
            )
        ).one()

    assert (first.rowcount, second.rowcount) == (1, 0)
    assert row == ("queued", "queued", None, None)


def test_duplicate_filenames_receive_distinct_stable_source_labels():
    first_id = uuid.UUID("11111111-0000-0000-0000-000000000001")
    second_id = uuid.UUID("22222222-0000-0000-0000-000000000002")
    files = [
        SimpleNamespace(id=first_id, filename="auth.log"),
        SimpleNamespace(id=second_id, filename="auth.log"),
        SimpleNamespace(id=uuid.uuid4(), filename="cloud.json"),
    ]

    labels = _build_source_labels(files)

    assert labels[str(first_id)] == "auth.log [11111111]"
    assert labels[str(second_id)] == "auth.log [22222222]"
    assert labels[str(files[2].id)] == "cloud.json"
    assert len({labels[str(first_id)], labels[str(second_id)]}) == 2


@pytest.mark.asyncio
async def test_retry_refreshes_queued_at_and_clears_stale_terminal_fields(monkeypatch):
    inv = _investigation(status="failed")
    inv.files = [
        InvestigationFile(
            investigation_id=inv.id,
            filename="auth.log",
            source_type="linux_endpoint",
            ingestion_mode="parsers",
            storage_key="uploads/auth.log",
            status="pending",
        )
    ]
    inv.completed_at = datetime(2026, 7, 1)
    inv.error_message = "old failure"
    user = SimpleNamespace(id=inv.user_id, tier="free")
    db = SimpleNamespace(
        add=MagicMock(),
        execute=AsyncMock(return_value=SimpleNamespace(rowcount=1)),
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )
    request = SimpleNamespace(client=None, headers={})

    async def get_inv(*args, **kwargs):
        return inv

    async def allow_analysis(*args, **kwargs):
        return True, 4

    def discard_pipeline(coro, **kwargs):
        coro.close()

    monkeypatch.setattr(routes, "_get_investigation_or_404", get_inv)
    monkeypatch.setattr("app.utils.rate_limiter.check_and_count_analysis", allow_analysis)
    monkeypatch.setattr(routes, "_spawn_pipeline_task", discard_pipeline)
    monkeypatch.setattr(routes.settings, "USE_ASYNCIO_INVESTIGATION_PIPELINE", True)
    monkeypatch.setattr(routes.settings, "GEMINI_API_KEY", "")

    before = datetime.utcnow()
    response = await routes.analyze_investigation.__wrapped__(
        request=request,
        investigation_id=inv.id,
        body=InvestigationAnalyzeRequest(),
        current_user=user,
        db=db,
    )
    after = datetime.utcnow()

    assert response["status"] == "queued"
    assert before <= inv.queued_at <= after
    assert inv.completed_at is None
    assert inv.error_message is None
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_losing_analyze_claim_does_not_consume_quota_or_dispatch(monkeypatch):
    inv = _investigation(status="draft")
    inv.files = [
        InvestigationFile(
            investigation_id=inv.id,
            filename="auth.log",
            source_type="linux_endpoint",
            ingestion_mode="parsers",
            storage_key="uploads/auth.log",
            status="pending",
        )
    ]
    user = SimpleNamespace(id=inv.user_id, tier="free")
    db = SimpleNamespace(
        execute=AsyncMock(return_value=SimpleNamespace(rowcount=0)),
        rollback=AsyncMock(),
    )
    quota = AsyncMock(return_value=(True, 4))
    spawn = MagicMock()

    async def get_inv(*args, **kwargs):
        return inv

    monkeypatch.setattr(routes, "_get_investigation_or_404", get_inv)
    monkeypatch.setattr("app.utils.rate_limiter.check_and_count_analysis", quota)
    monkeypatch.setattr(routes, "_spawn_pipeline_task", spawn)
    monkeypatch.setattr(routes.settings, "GEMINI_API_KEY", "")

    with pytest.raises(routes.HTTPException) as exc_info:
        await routes.analyze_investigation.__wrapped__(
            request=SimpleNamespace(client=None, headers={}),
            investigation_id=inv.id,
            body=InvestigationAnalyzeRequest(),
            current_user=user,
            db=db,
        )

    assert exc_info.value.status_code == 400
    db.rollback.assert_awaited_once()
    quota.assert_not_awaited()
    spawn.assert_not_called()


@pytest.mark.asyncio
async def test_correlation_setting_patch_is_limited_to_editable_investigations(monkeypatch):
    inv = _investigation(status="draft", correlation_enabled=True)
    inv.files = []
    inv.report = None
    db = SimpleNamespace(commit=AsyncMock())

    async def get_inv(*args, **kwargs):
        return inv

    monkeypatch.setattr(routes, "_get_investigation_or_404", get_inv)
    monkeypatch.setattr(routes.settings, "GEMINI_API_KEY", "")

    response = await routes.update_investigation(
        investigation_id=inv.id,
        body=InvestigationUpdate(correlation_enabled=False),
        current_user=SimpleNamespace(id=inv.user_id),
        db=db,
    )

    assert response.correlation_enabled is False
    assert inv.correlation_enabled is False

    inv.status = "processing"
    with pytest.raises(routes.HTTPException) as exc_info:
        await routes.update_investigation(
            investigation_id=inv.id,
            body=InvestigationUpdate(correlation_enabled=True),
            current_user=SimpleNamespace(id=inv.user_id),
            db=db,
        )
    assert exc_info.value.status_code == 400


def test_correlation_runs_only_when_enabled_with_two_successfully_parsed_files():
    parsed = {"one.log": [object()], "two.log": [object()]}

    assert _should_run_correlation(True, parsed) is True
    assert _should_run_correlation(False, parsed) is False
    assert _should_run_correlation(True, {"one.log": [object()]}) is False


def test_pro_gate_applies_only_to_enabled_cross_source_correlation(monkeypatch):
    ensure = MagicMock()
    monkeypatch.setattr(routes, "ensure_pro_or_team_tier", ensure)
    user = SimpleNamespace(tier="free")
    files = [
        SimpleNamespace(source_type="linux_endpoint"),
        SimpleNamespace(source_type="cloudtrail"),
    ]

    routes._ensure_pro_for_multi_source_correlation(
        SimpleNamespace(correlation_enabled=False, files=files),
        user,
    )
    routes._ensure_pro_for_multi_source_correlation(
        SimpleNamespace(correlation_enabled=True, files=[files[0], files[0]]),
        user,
    )
    assert ensure.call_count == 0

    routes._ensure_pro_for_multi_source_correlation(
        SimpleNamespace(correlation_enabled=True, files=files),
        user,
    )
    ensure.assert_called_once()
