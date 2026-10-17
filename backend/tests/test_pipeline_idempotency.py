import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.dml import Delete

from app.models.finding import Finding
from app.models.report import Report
from app.tasks.process_investigation import _run_pipeline, _upsert_report_and_findings


class _Result:
    def __init__(self, value=None):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _ReportSession:
    def __init__(self, existing_report):
        self.existing_report = existing_report
        self.execute_count = 0
        self.statements = []
        self.added = []
        self.flush = AsyncMock()
        self.commit = AsyncMock()

    async def execute(self, statement):
        self.execute_count += 1
        self.statements.append(statement)
        if self.execute_count == 2:
            return _Result(self.existing_report)
        return _Result()

    def add(self, value):
        self.added.append(value)


class _SessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *_args):
        return None


def _finding(title: str, source_files: list[str]) -> dict:
    return {
        "severity": "high",
        "title": title,
        "description": "Detected by a deterministic rule.",
        "mitre_technique_id": "T1110",
        "mitre_technique_name": "Brute Force",
        "mitre_tactic": "credential-access",
        "iocs": [],
        "remediation": None,
        "finding_type": "single",
        "confidence": 1.0,
        "source_files": source_files,
    }


@pytest.mark.asyncio
async def test_redelivered_pipeline_replaces_existing_partial_report_and_findings():
    investigation = SimpleNamespace(id=uuid.uuid4(), user_id=uuid.uuid4())
    report = Report(
        id=uuid.uuid4(),
        investigation_id=investigation.id,
        user_id=investigation.user_id,
        summary="partial",
        severity_counts={"critical": 99},
        correlated_findings=[],
        single_source_findings=[],
        mitre_techniques=[],
        pdf_storage_key="reports/partial.pdf",
    )

    first_session = _ReportSession(report)
    first_result = await _upsert_report_and_findings(
        first_session,
        investigation=investigation,
        single_findings=[_finding("First result", ["auth.log"])],
        correlated_findings=[],
        severity_counts={"high": 1},
        mitre_techniques=["T1110"],
        parsed_source_files=["auth.log"],
        correlated_source_files=["auth.log"],
    )

    assert first_result is report
    assert not any(isinstance(value, Report) for value in first_session.added)
    assert [value.title for value in first_session.added if isinstance(value, Finding)] == [
        "First result"
    ]
    assert any(isinstance(statement, Delete) for statement in first_session.statements)
    assert "FOR UPDATE" in str(first_session.statements[0])
    assert report.severity_counts == {"high": 1}
    assert report.pdf_storage_key is None

    redelivery_session = _ReportSession(report)
    redelivery_result = await _upsert_report_and_findings(
        redelivery_session,
        investigation=investigation,
        single_findings=[_finding("Replacement result", ["auth.log"])],
        correlated_findings=[],
        severity_counts={"high": 1},
        mitre_techniques=["T1110"],
        parsed_source_files=["auth.log"],
        correlated_source_files=["auth.log"],
    )

    assert redelivery_result.id == report.id
    assert not any(isinstance(value, Report) for value in redelivery_session.added)
    assert [value.title for value in redelivery_session.added if isinstance(value, Finding)] == [
        "Replacement result"
    ]
    assert report.single_source_findings[0]["title"] == "Replacement result"


@pytest.mark.asyncio
async def test_pipeline_rolls_back_integrity_error_before_failure_query(monkeypatch):
    operations = []

    class FailingSession:
        async def execute(self, _statement):
            operations.append("execute")
            if operations == ["execute"]:
                raise IntegrityError("INSERT reports", {}, RuntimeError("duplicate"))
            return _Result()

        async def rollback(self):
            operations.append("rollback")

        async def commit(self):
            operations.append("commit")

    session = FailingSession()
    monkeypatch.setattr(
        "app.dependencies.AsyncSessionLocal",
        lambda: _SessionContext(session),
    )
    monkeypatch.setattr(
        "app.utils.storage.create_storage_backend",
        lambda: SimpleNamespace(),
    )

    with pytest.raises(IntegrityError):
        await _run_pipeline(str(uuid.uuid4()))

    assert operations[:3] == ["execute", "rollback", "execute"]


@pytest.mark.asyncio
async def test_completed_pipeline_redelivery_is_a_noop(monkeypatch):
    investigation = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="Already complete",
        status="complete",
        files=[],
    )

    class CompleteSession:
        execute_count = 0

        async def execute(self, _statement):
            self.execute_count += 1
            return _Result(investigation)

    session = CompleteSession()
    storage = SimpleNamespace(get_file_path=AsyncMock())
    monkeypatch.setattr(
        "app.dependencies.AsyncSessionLocal",
        lambda: _SessionContext(session),
    )
    monkeypatch.setattr(
        "app.utils.storage.create_storage_backend",
        lambda: storage,
    )

    await _run_pipeline(str(investigation.id))

    assert session.execute_count == 1
    storage.get_file_path.assert_not_awaited()
