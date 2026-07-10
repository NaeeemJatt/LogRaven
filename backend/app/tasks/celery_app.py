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
        "app.tasks.maintenance",
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
    # Hard ceilings so a hung task can never occupy a worker forever.
    # Soft limit raises SoftTimeLimitExceeded inside the task first.
    "task_soft_time_limit": 1500,   # 25 min
    "task_time_limit": 1800,        # 30 min hard kill
    # Keep task results from accumulating in Redis indefinitely.
    "result_expires": 86400,        # 24 h
    "beat_schedule": {
        # Continuous monitoring: check hourly for recurring audits that are due.
        # Run a beat worker with: celery -A app.tasks.celery_app beat
        "compliance-rescan-due-audits": {
            "task": "compliance.rescan_due_audits",
            "schedule": 3600.0,
        },
        # Reliability: fail jobs stuck in a running state past their TTL
        # (e.g. a worker crashed mid-pipeline) so users can retry.
        "reconcile-stuck-jobs": {
            "task": "maintenance.reconcile_stuck_jobs",
            "schedule": 900.0,  # every 15 min
        },
    },
}
# Prefork-only; solo/threads pools on Windows ignore or warn on this.
if os.name != "nt":
    _conf["worker_max_tasks_per_child"] = 100
celery_app.conf.update(_conf)
