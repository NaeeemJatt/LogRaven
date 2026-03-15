# LogRaven — Celery Application Configuration
#
# PURPOSE:
#   Creates and configures the Celery application instance.
#   Redis is used as both broker and result backend.
#
# KEY CONFIGURATION:
#   task_serializer = "json"          — human-readable task payloads
#   worker_max_tasks_per_child = 100  — prevent memory leaks in long-running workers
#   task_acks_late = True             — tasks acknowledged AFTER completion, not before
#   task_reject_on_worker_lost = True — re-queue tasks if worker crashes mid-processing
#
# QUEUES:
#   default  — standard investigations
#   priority — team tier investigations (processed first)
#
# TODO Month 1 Week 3: Implement this file.

from celery import Celery
import os

celery_app = Celery(
    "lograven",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379"),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_max_tasks_per_child=100,
)

# TODO: Import and register process_investigation task
