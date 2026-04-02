from __future__ import annotations

import os
import time
from pathlib import Path
import subprocess
import sys

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("lograven.dev-worker")


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _runtime_dir() -> Path:
    return Path(settings.LOCAL_STORAGE_PATH) / "runtime"


def _pidfile() -> Path:
    return _runtime_dir() / "celery-worker.pid"


def _logfile() -> Path:
    return _runtime_dir() / "celery-worker.log"


def _write_pid(pid: int) -> None:
    _runtime_dir().mkdir(parents=True, exist_ok=True)
    _pidfile().write_text(str(pid), encoding="utf-8")


def _has_active_worker() -> bool:
    try:
        from app.tasks.celery_app import celery_app

        inspector = celery_app.control.inspect(timeout=1.0)
        return bool(inspector and inspector.ping())
    except Exception:
        return False


def ensure_dev_worker_running() -> bool:
    """
    In local development, start a detached Celery worker on demand so queued
    investigations begin processing without manual worker startup.
    """
    # Rely on AUTO_START_DEV_WORKER (not DEBUG): DEBUG defaults false and would
    # leave tasks stuck in Redis with no consumer for typical local .env setups.
    if settings.CELERY_TASK_ALWAYS_EAGER or not settings.AUTO_START_DEV_WORKER:
        return False

    if _has_active_worker():
        return False

    # Do not skip startup based on pidfile alone: Windows PID reuse or a non-Celery
    # process holding the same PID would leave the queue stuck with no consumer.

    _runtime_dir().mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "celery",
        "-A",
        "app.tasks.process_investigation",
        "worker",
        "--loglevel=info",
    ]
    if os.name == "nt":
        command.extend(["--pool=solo"])

    with _logfile().open("ab") as log_handle:
        kwargs: dict = {
            "cwd": str(_backend_root()),
            "stdin": subprocess.DEVNULL,
            "stdout": log_handle,
            "stderr": subprocess.STDOUT,
        }
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            kwargs["startupinfo"] = startupinfo
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        else:
            kwargs["start_new_session"] = True

        proc = subprocess.Popen(command, **kwargs)

    _write_pid(proc.pid)
    time.sleep(1.5)
    exit_code = proc.poll()
    if exit_code is not None:
        logger.error(
            "Celery worker process exited immediately (code=%s). Check %s",
            exit_code,
            _logfile(),
        )
        return False
    logger.info("Auto-started local Celery worker (pid=%s, log=%s)", proc.pid, _logfile())
    return True
