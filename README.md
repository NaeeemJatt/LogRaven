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

When `DEBUG=true`, LogRaven will auto-start a local Celery worker on the first queued analysis if one is not already running.

For Docker-based local stacks, `docker-compose.yml` no longer exposes Postgres or Redis on host ports and requires `JWT_SECRET_KEY` to be set explicitly.

## Docs

See `MASTER_SPEC.md` and project specs under `specs/`.
