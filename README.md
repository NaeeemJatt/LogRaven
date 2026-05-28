# LogRaven

**Watch your logs. Find the threat.**

LogRaven is a cybersecurity platform with two modes:

- **Threat Detection** — upload log files (EVTX, syslog, CloudTrail, Nginx), AI maps events to MITRE ATT&CK, generates a PDF incident report
- **SOC 2 Compliance Audit** — connect an AWS account via STS AssumeRole, collect CloudTrail / IAM / GuardDuty evidence, AI maps to SOC 2 CC6/CC7 controls, generates a PDF evidence package

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI 0.111 + Python 3.11 |
| ORM | SQLAlchemy 2.0 (async) + Alembic |
| Queue | Celery 5 + Redis 7 |
| Database | PostgreSQL 15 |
| AI | Google Gemini 2.5 Flash (`google-genai`) |
| PDF | reportlab (compliance) + WeasyPrint (threat reports) |
| Storage | Local (dev) / S3 (prod) via `storage.py` abstraction |
| Frontend | React 18 + Vite + TypeScript + Tailwind CSS |

## Quick Start (development)

```bash
cp .env.example .env
# Fill in: DATABASE_URL, JWT_SECRET_KEY (32+ chars), GEMINI_API_KEY
```

**Backend (PowerShell):**
```powershell
cd backend
pip install -r requirements.txt
.\run-api.ps1
```

**Worker** (required for compliance audits; optional for threat detection which runs in-process by default):
```powershell
cd backend
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Database migrations:**
```powershell
cd backend
alembic upgrade head
```

## Docker Compose

```bash
cp .env.example .env
# Fill in: JWT_SECRET_KEY, GEMINI_API_KEY
docker compose up -d
```

Services started: `lograven` (API on :8000), `lograven-worker` (Celery), `lograven-db` (Postgres on :5432), `lograven-redis`.

> **Note:** `JWT_SECRET_KEY` is required — Docker Compose will refuse to start without it.

## SOC 2 Compliance Audit — AWS Setup

1. In the **customer's** AWS account, create an IAM role with the policy in the `/compliance` helper UI.
2. Set the trust principal to LogRaven's AWS account ID (`VITE_AWS_ACCOUNT_ID` in `.env`).
3. Paste the role ARN into the audit form at `/compliance`.

LogRaven assumes the role via STS (`AssumeRole`) — no long-lived credentials are stored.

## Environment Variables

See `.env.example` for the full list. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `JWT_SECRET_KEY` | Yes | 32+ random characters |
| `GEMINI_API_KEY` | Yes | Google AI Studio key — used for both threat detection and SOC 2 |
| `REDIS_URL` | Yes | Redis connection string |
| `STORAGE_BACKEND` | No | `local` (default) or `s3` |
| `VITE_AWS_ACCOUNT_ID` | No | Your AWS account ID shown in the IAM role trust-policy helper |

## Development Notes

- By default, threat-detection investigations run **in-process** (`USE_ASYNCIO_INVESTIGATION_PIPELINE=true`) so analysis works without a Celery worker — useful on Windows.
- Compliance audits **always** require a live Celery worker connected to Redis.
- Set `USE_ASYNCIO_INVESTIGATION_PIPELINE=false` when running the Docker Compose stack (already set in `docker-compose.yml`).
