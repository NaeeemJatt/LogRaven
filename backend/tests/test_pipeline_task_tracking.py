# LogRaven — Background pipeline task tracking
#
# asyncio.create_task keeps only a weak reference from the event loop, so a
# fire-and-forget task can be garbage-collected mid-run and silently cancel the
# investigation pipeline. _spawn_pipeline_task must hold a strong reference until
# the coroutine finishes, then release it.

import asyncio

import pytest

from app.api.investigations import routes


@pytest.mark.asyncio
async def test_spawn_pipeline_task_holds_reference_until_done():
    started = asyncio.Event()
    release = asyncio.Event()

    async def worker():
        started.set()
        await release.wait()

    routes._spawn_pipeline_task(worker(), name="test-pipeline")

    await started.wait()
    # While running, a strong reference must be held so GC cannot cancel it.
    assert len(routes._BACKGROUND_TASKS) == 1

    release.set()
    await asyncio.sleep(0)  # let the task finish and the done-callback fire
    await asyncio.sleep(0)

    # Reference is released once complete — no leak.
    assert len(routes._BACKGROUND_TASKS) == 0


@pytest.mark.asyncio
async def test_spawn_pipeline_task_releases_reference_on_error():
    async def boom():
        raise RuntimeError("pipeline blew up")

    routes._spawn_pipeline_task(boom(), name="test-pipeline-error")

    # Drain the loop so the task runs and its done-callback removes it.
    for _ in range(5):
        await asyncio.sleep(0)

    assert len(routes._BACKGROUND_TASKS) == 0
