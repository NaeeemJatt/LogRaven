import asyncio
import inspect

import pytest

from app.compliance import tasks as compliance_tasks
from app.tasks import async_runner
from app.tasks import maintenance
from app.tasks import process_investigation as investigation_tasks


@pytest.fixture(autouse=True)
def reset_runner():
    async_runner.close_async_runner()
    yield
    async_runner.close_async_runner()


async def _loop_id():
    return id(asyncio.get_running_loop())


def test_sequential_invocations_reuse_one_event_loop():
    first = async_runner.run_async(_loop_id())
    second = async_runner.run_async(_loop_id())

    assert first == second


def test_exception_does_not_poison_next_invocation():
    async def fail():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        async_runner.run_async(fail())

    assert isinstance(async_runner.run_async(_loop_id()), int)


def test_all_sync_celery_wrappers_use_shared_runner(monkeypatch):
    calls = []

    def fake_run(awaitable):
        calls.append(awaitable)
        awaitable.close()
        return True

    monkeypatch.setattr(investigation_tasks, "run_async", fake_run)
    monkeypatch.setattr(compliance_tasks, "run_async", fake_run)
    monkeypatch.setattr(maintenance, "run_async", fake_run)

    investigation_tasks.process_investigation.run("00000000-0000-0000-0000-000000000001")
    compliance_tasks.run_soc2_audit.run("00000000-0000-0000-0000-000000000002")
    compliance_tasks.rescan_due_audits.run()
    maintenance.reconcile_stuck_jobs.run()
    maintenance.purge_expired_reports.run()
    maintenance.purge_expired_audit_logs.run()

    assert len(calls) == 6


def test_no_celery_wrapper_uses_asyncio_run():
    wrappers = [
        investigation_tasks.process_investigation.run,
        compliance_tasks.run_soc2_audit.run,
        compliance_tasks.rescan_due_audits.run,
        maintenance.reconcile_stuck_jobs.run,
        maintenance.purge_expired_reports.run,
        maintenance.purge_expired_audit_logs.run,
    ]

    assert all("asyncio.run" not in inspect.getsource(wrapper) for wrapper in wrappers)
