# LogRaven — Celery Application Configuration

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
    # Run tasks synchronously without a broker — safe for development/testing on Windows.
    # Set to False in production with Redis.
    task_always_eager=True,
    task_eager_propagates=True,
)

# Tasks are registered by importing process_investigation from process_investigation.py.
# Do NOT import here — celery_app is imported by process_investigation, circular otherwise.
