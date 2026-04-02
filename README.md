# LogRaven

**Watch your logs. Find the threat.**

LogRaven is a security investigation platform. Upload log files, correlate events across sources, and get a MITRE ATT&CK–mapped PDF report. Production deployments are intended for **AWS** (API, workers, RDS, Redis, S3).

## Quick start (development)

```bash
cp .env.example .env
# Set DATABASE_URL, REDIS_URL, a strong 32+ char JWT_SECRET_KEY, and at least one AI API key in .env
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
# Worker: celery -A app.tasks.process_investigation worker --loglevel=info --pool=solo
# Frontend: cd frontend && npm install && npm run dev
```

By default, investigations run **in-process** (`USE_ASYNCIO_INVESTIGATION_PIPELINE=true` in `.env.example`) so analysis progresses without a Celery worker—useful on Windows. For a separate worker, set `USE_ASYNCIO_INVESTIGATION_PIPELINE=false` and run `celery -A app.tasks.process_investigation worker --loglevel=info --pool=solo`, or use Docker Compose (which disables in-process mode and uses `lograven-worker`).

For Docker-based local stacks, `docker-compose.yml` no longer exposes Postgres or Redis on host ports and requires `JWT_SECRET_KEY` to be set explicitly.

## Docs

See `MASTER_SPEC.md` and project specs under `specs/`.
