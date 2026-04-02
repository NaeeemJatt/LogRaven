from pathlib import Path

from app.tasks import dev_worker


class DummyProcess:
    def __init__(self, pid: int):
        self.pid = pid

    def poll(self):
        return None  # still "running" after ensure_dev_worker_running's sleep + poll check


def test_dev_worker_skips_when_auto_start_disabled(monkeypatch):
    monkeypatch.setattr(dev_worker.settings, "CELERY_TASK_ALWAYS_EAGER", False, raising=False)
    monkeypatch.setattr(dev_worker.settings, "AUTO_START_DEV_WORKER", False, raising=False)

    started = {"called": False}

    def fake_popen(*args, **kwargs):
        started["called"] = True
        return DummyProcess(123)

    monkeypatch.setattr(dev_worker.subprocess, "Popen", fake_popen)

    assert dev_worker.ensure_dev_worker_running() is False
    assert started["called"] is False


def test_dev_worker_skips_when_worker_already_active(monkeypatch):
    monkeypatch.setattr(dev_worker.settings, "CELERY_TASK_ALWAYS_EAGER", False, raising=False)
    monkeypatch.setattr(dev_worker.settings, "AUTO_START_DEV_WORKER", True, raising=False)
    monkeypatch.setattr(dev_worker, "_has_active_worker", lambda: True)

    started = {"called": False}

    def fake_popen(*args, **kwargs):
        started["called"] = True
        return DummyProcess(123)

    monkeypatch.setattr(dev_worker.subprocess, "Popen", fake_popen)

    assert dev_worker.ensure_dev_worker_running() is False
    assert started["called"] is False


def test_dev_worker_starts_detached_process(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(dev_worker.settings, "CELERY_TASK_ALWAYS_EAGER", False, raising=False)
    monkeypatch.setattr(dev_worker.settings, "AUTO_START_DEV_WORKER", True, raising=False)
    monkeypatch.setattr(dev_worker, "_has_active_worker", lambda: False)
    monkeypatch.setattr(dev_worker, "_backend_root", lambda: tmp_path)
    monkeypatch.setattr(dev_worker, "_runtime_dir", lambda: tmp_path / "runtime")
    monkeypatch.setattr(dev_worker, "_pidfile", lambda: tmp_path / "runtime" / "celery-worker.pid")
    monkeypatch.setattr(dev_worker, "_logfile", lambda: tmp_path / "runtime" / "celery-worker.log")

    captured: dict = {}

    def fake_popen(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return DummyProcess(456)

    monkeypatch.setattr(dev_worker.subprocess, "Popen", fake_popen)

    assert dev_worker.ensure_dev_worker_running() is True
    assert captured["command"][:5] == [
        dev_worker.sys.executable,
        "-m",
        "celery",
        "-A",
        "app.tasks.process_investigation",
    ]
    assert (tmp_path / "runtime" / "celery-worker.pid").read_text(encoding="utf-8") == "456"
