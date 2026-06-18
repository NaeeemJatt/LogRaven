# LogRaven — Celery Application Configuration

import os

from celery import Celery

from app.config import settings

celery_app = Celery(
    "lograven",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.process_investigation",
        "app.compliance.tasks",
    ],
)

_conf = {
    "task_serializer": "json",
    "accept_content": ["json"],
    "result_serializer": "json",
    "task_acks_late": True,
    "task_reject_on_worker_lost": True,
    "task_always_eager": settings.CELERY_TASK_ALWAYS_EAGER,
    "task_eager_propagates": True,
    # Continuous monitoring: check hourly for recurring audits that are due.
    # Run a beat worker with: celery -A app.tasks.celery_app beat
    "beat_schedule": {
        "compliance-rescan-due-audits": {
            "task": "compliance.rescan_due_audits",
            "schedule": 3600.0,
        },
    },
}
# Prefork-only; solo/threads pools on Windows ignore or warn on this.
if os.name != "nt":
    _conf["worker_max_tasks_per_child"] = 100
celery_app.conf.update(_conf)
