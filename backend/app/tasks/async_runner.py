"""Process-local persistent event loop for synchronous Celery task wrappers."""

import asyncio
import os
import threading

from celery.signals import worker_process_shutdown, worker_shutdown


_lock = threading.RLock()
_loop: asyncio.AbstractEventLoop | None = None
_pid: int | None = None


def _reset_after_fork() -> None:
    global _lock, _loop, _pid
    _lock = threading.RLock()
    _loop = None
    _pid = None


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_reset_after_fork)


def _get_loop() -> asyncio.AbstractEventLoop:
    global _loop, _pid
    current_pid = os.getpid()
    if _loop is None or _loop.is_closed() or _pid != current_pid:
        _loop = asyncio.new_event_loop()
        _pid = current_pid
    return _loop


def run_async(awaitable):
    """Run one awaitable on the worker process's serialized persistent loop."""
    with _lock:
        loop = _get_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(awaitable)
        finally:
            asyncio.set_event_loop(None)


def close_async_runner(**_kwargs) -> None:
    """Cancel pending work and reset the process-local loop at worker shutdown."""
    global _loop, _pid
    with _lock:
        loop = _loop
        _loop = None
        _pid = None
        if loop is None or loop.is_closed():
            return

        asyncio.set_event_loop(loop)
        try:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.run_until_complete(loop.shutdown_default_executor())
        finally:
            loop.close()
            asyncio.set_event_loop(None)


worker_process_shutdown.connect(close_async_runner, weak=False)
worker_shutdown.connect(close_async_runner, weak=False)
