import uuid
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import settings
from app.models.finding import Finding
from app.models.investigation import Investigation
from app.models.investigation_file import InvestigationFile
from app.models.report import Report
from app.parsers.normalizer import NormalizedEvent
from app.rules.schema import RuleDefinition, SimpleCondition, SimpleMatch
from app.tasks.process_investigation import _run_pipeline


class _Result:
    def __init__(self, value=None, values=None):
        self._value = value
        self._values = values or []

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return self

    def all(self):
        return self._values


class _FakeSession:
    def __init__(self, investigation, user):
        self.investigation = investigation
        self.user = user
        self.added = []
        self.execute_count = 0

    async def execute(self, _statement):
        self.execute_count += 1
        if self.execute_count == 1:
            return _Result(value=self.investigation)
        if self.execute_count == 2:
            return _Result(value=self.user)
        return _Result(values=[item for item in self.added if isinstance(item, Finding)])

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        for value in self.added:
            if isinstance(value, Report) and value.id is None:
                value.id = uuid.uuid4()
                value.created_at = datetime.utcnow()

    async def commit(self):
        return None

    async def rollback(self):
        return None


class _SessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *_args):
        return None


async def _run_rules_pipeline(
    monkeypatch,
    tmp_path: Path,
    *,
    ai_configured: bool,
    ai_raises: bool,
    duplicate_filenames: bool = False,
    initial_status: str = "queued",
    include_yaml_rule: bool = True,
    events_per_file: int = 1,
):
    investigation = Investigation(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="Rules only",
        status=initial_status,
        correlation_enabled=duplicate_filenames,
        created_at=datetime(2026, 7, 10),
        queued_at=datetime.utcnow(),
    )
    investigation.files = [
        InvestigationFile(
            id=uuid.UUID("11111111-0000-0000-0000-000000000001"),
            investigation_id=investigation.id,
            filename="auth.log",
            source_type="linux_endpoint",
            ingestion_mode="parsers",
            storage_key="uploads/auth.log",
            status="pending",
        )
    ]
    if duplicate_filenames:
        investigation.files.append(
            InvestigationFile(
                id=uuid.UUID("22222222-0000-0000-0000-000000000002"),
                investigation_id=investigation.id,
                filename="auth.log",
                source_type="linux_endpoint",
                ingestion_mode="parsers",
                storage_key="uploads/auth-copy.log",
                status="pending",
            )
        )
    user = SimpleNamespace(id=investigation.user_id, tier="free", email="analyst@example.com")
    session = _FakeSession(investigation, user)
    storage = SimpleNamespace(get_file_path=AsyncMock(return_value=tmp_path / "auth.log"))
    rule = RuleDefinition(
        id="rules-only",
        title="Rules-only detection",
        severity="high",
        description="A deterministic rule fired.",
        mitre_technique_id="T1110",
        mitre_tactic="credential-access",
        flag="rules_only",
        match=SimpleMatch(
            type="simple",
            log_type="linux_endpoint",
            conditions=[SimpleCondition(field="event_type", op="eq", value="auth_failure")],
        ),
    )

    async def ingest(**kwargs):
        events = [
            NormalizedEvent(
                timestamp=datetime(2026, 7, 10, 12, 0, index),
                source_type="linux_endpoint",
                event_type="auth_failure",
                source_ip="203.0.113.10",
                raw_message=f"failed login {kwargs['inv_file'].id} {index}",
            )
            for index in range(events_per_file)
        ]
        return events, "syslog", {
            "detection_confidence": 1.0,
            "requested_ingestion_mode": "parsers",
            "actual_ingestion_path": "parsers",
        }

    route_analysis = AsyncMock(side_effect=RuntimeError("AI unavailable")) if ai_raises else AsyncMock(return_value=([], []))
    generate_pdf = MagicMock(return_value=str(tmp_path / "report.pdf"))
    correlate = MagicMock(return_value=[])

    monkeypatch.setattr("app.dependencies.AsyncSessionLocal", lambda: _SessionContext(session))
    monkeypatch.setattr("app.utils.storage.create_storage_backend", lambda: storage)
    monkeypatch.setattr("app.parsers.pipeline_ingest.ingest_log_file", ingest)
    monkeypatch.setattr("app.correlation.engine.correlate", correlate)
    monkeypatch.setattr(
        "app.rules.loader.get_rules",
        lambda: [rule] if include_yaml_rule else [],
    )
    monkeypatch.setattr("app.ai.router.route_analysis", route_analysis)
    monkeypatch.setattr("app.reports.pdf_generator.generate_pdf", generate_pdf)
    monkeypatch.setattr("app.reports.uploader.upload_report", AsyncMock(return_value="reports/report.pdf"))
    monkeypatch.setattr("app.services.notification_service.send_job_complete", lambda **_kwargs: None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "configured" if ai_configured else "")
    monkeypatch.setattr(settings, "LOCAL_STORAGE_PATH", str(tmp_path))
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
    monkeypatch.setattr(settings, "MAX_PARSED_EVENTS_PER_FILE", 100)
    monkeypatch.setattr(settings, "MAX_PARSED_EVENTS_PER_INVESTIGATION", 100)

    await _run_pipeline(str(investigation.id), cloud_ai_consent=ai_configured)
    return investigation, session, route_analysis, generate_pdf, correlate


@pytest.mark.asyncio
async def test_rules_only_mode_completes_without_calling_ai(monkeypatch, tmp_path):
    investigation, session, route_analysis, generate_pdf, _correlate = await _run_rules_pipeline(
        monkeypatch,
        tmp_path,
        ai_configured=False,
        ai_raises=False,
    )

    report = next(item for item in session.added if isinstance(item, Report))
    findings = [item for item in session.added if isinstance(item, Finding)]

    assert investigation.status == "complete"
    assert route_analysis.await_count == 0
    assert len(findings) == 1
    assert findings[0].title == "Rules-only detection"
    assert findings[0].source_files == ["auth.log"]
    assert report.severity_counts == {"high": 1}
    assert report.single_source_findings[0]["title"] == "Rules-only detection"
    assert "Found 1 individual finding" in report.summary
    assert generate_pdf.call_args.args[1][0].title == "Rules-only detection"


@pytest.mark.asyncio
async def test_ai_exception_still_persists_rules_and_completes(monkeypatch, tmp_path):
    investigation, session, route_analysis, _generate_pdf, _correlate = await _run_rules_pipeline(
        monkeypatch,
        tmp_path,
        ai_configured=True,
        ai_raises=True,
    )

    findings = [item for item in session.added if isinstance(item, Finding)]

    assert route_analysis.await_count == 1
    assert investigation.status == "complete"
    assert [finding.title for finding in findings] == ["Rules-only detection"]


@pytest.mark.asyncio
async def test_duplicate_filenames_stay_distinct_through_correlation_and_attribution(
    monkeypatch,
    tmp_path,
):
    investigation, session, _route_analysis, _generate_pdf, correlate = await _run_rules_pipeline(
        monkeypatch,
        tmp_path,
        ai_configured=False,
        ai_raises=False,
        duplicate_filenames=True,
    )

    events_by_file = correlate.call_args.args[1]
    findings = [item for item in session.added if isinstance(item, Finding)]

    assert set(events_by_file) == {
        "11111111-0000-0000-0000-000000000001",
        "22222222-0000-0000-0000-000000000002",
    }
    assert investigation.status == "complete"
    assert findings[0].source_files == [
        "auth.log [11111111]",
        "auth.log [22222222]",
    ]


@pytest.mark.asyncio
async def test_processing_redelivery_can_run_inner_pipeline(monkeypatch, tmp_path):
    investigation, _session, _route_analysis, _generate_pdf, _correlate = await _run_rules_pipeline(
        monkeypatch,
        tmp_path,
        ai_configured=False,
        ai_raises=False,
        initial_status="processing",
    )

    assert investigation.status == "complete"


@pytest.mark.asyncio
async def test_builtin_rule_persists_without_ai_or_yaml_rules(monkeypatch, tmp_path):
    investigation, session, route_analysis, _generate_pdf, _correlate = await _run_rules_pipeline(
        monkeypatch,
        tmp_path,
        ai_configured=False,
        ai_raises=False,
        include_yaml_rule=False,
        events_per_file=5,
    )
    findings = [item for item in session.added if isinstance(item, Finding)]

    assert investigation.status == "complete"
    assert route_analysis.await_count == 0
    assert [finding.title for finding in findings] == [
        "Authentication Brute Force"
    ]
    assert findings[0].confidence == 1.0
