from __future__ import annotations

import os
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


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _read_pid() -> int | None:
    try:
        return int(_pidfile().read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


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
    if not settings.DEBUG or settings.CELERY_TASK_ALWAYS_EAGER or not settings.AUTO_START_DEV_WORKER:
        return False

    if _has_active_worker():
        return False

    pid = _read_pid()
    if pid and _pid_is_running(pid):
        return False

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
    logger.info("Auto-started local Celery worker (pid=%s, log=%s)", proc.pid, _logfile())
    return True
