#!/bin/sh
# LogRaven — container entrypoint (api | worker | beat)
set -e

ROLE="${1:-api}"

case "$ROLE" in
  api)
    echo "[entrypoint] running database migrations..."
    alembic upgrade head
    echo "[entrypoint] starting API (workers=${UVICORN_WORKERS:-2})"
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${UVICORN_WORKERS:-2}"
    ;;
  worker)
    echo "[entrypoint] starting Celery worker (concurrency=${CELERY_CONCURRENCY:-1})"
    exec celery -A app.tasks.celery_app worker --loglevel=info --concurrency "${CELERY_CONCURRENCY:-1}"
    ;;
  beat)
    echo "[entrypoint] starting Celery beat"
    exec celery -A app.tasks.celery_app beat --loglevel=info
    ;;
  *)
    exec "$@"
    ;;
esac
