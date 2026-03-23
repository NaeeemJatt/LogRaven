# LogRaven — Active Context

## Current Status
**All Months 1–4 complete. Production bug fixes + rule engine expansion complete.**
Pipeline verified end-to-end: parse → rules → correlate → Gemini AI → MITRE → PDF → complete.

---

## Environment (Windows, No Docker)
- OS: Windows 10, PowerShell
- Python: 3.14 at `backend/venv/`
- PostgreSQL: localhost:5432/lograven (password: root)
- Redis: localhost:6379 (NOT needed — Celery `task_always_eager=True`)
- Start backend: `cd backend && uvicorn app.main:app --reload --port 8000`
- Start frontend: `cd frontend && npm run dev` (runs on http://localhost:5173)
- Dev setup script: `.\scripts\windows_setup.ps1`
- DB utility: `python scripts/db.py check|tables|migrations|drop`
- `GEMINI_API_KEY` set in `.env` and confirmed working
- `enterprise-attack.json` at `backend/app/data/` (35.7 MB)
- `bcrypt` pinned to 4.2.1 — do not upgrade until passlib is replaced

---

## All Decisions Locked
- Name: LogRaven / lograven.io / Docker: lograven:v1.0
- Docker delivery model, no hosted SaaS for v1
- AI: `google-genai` (gemini-2.5-flash) — NOT anthropic, NOT ANTHROPIC_API_KEY
- `bcrypt` pinned to 4.2.1 — do not upgrade until passlib is replaced
- Celery `task_always_eager=True` for dev (no Redis needed)
- Local storage for dev, S3 backend stubs ready for production
- PyArmor + hardware-bound license for Docker protection
- No admin panel in v1
- Frontend: Vite + React 18 + TypeScript + Tailwind + Zustand + React Query
- Rule engine: YAML-first with event_id index; hardcoded rules remain as fallback
- PDF: WeasyPrint (primary, Linux/Docker) + xhtml2pdf (fallback, Windows dev)

---

## Completed Work

### Foundation + Auth (Month 1)
- All 6 DB tables, Alembic migrations 001–007 applied
- JWT auth: register, login, refresh, /auth/me
- `dependencies.py`, `main.py`, `config.py`, `license.py` all working

### Investigation CRUD + File Upload (Month 1 Week 3)
- Full CRUD + file upload + analyze trigger + status polling + report endpoint
- PDF download: `GET /api/v1/investigations/{id}/report/download`

### Parsers (Month 2)
- `windows_event` (evtx + CSV), `syslog`, `cloudtrail`, `nginx`
- `NormalizedEvent` dataclass now includes `extra_fields: dict` for rule matching
- All 4 parsers populate `extra_fields` with source-specific metadata

### Rule Engine + Correlation + AI (Month 3)
- `rules/engine.py`: 4 hardcoded rules + YAML rule evaluation
- `rules/schema.py`: Pydantic models for YAML rule format (SimpleMatch, ThresholdMatch)
- `rules/loader.py`: YAML loader with file-level caching
- `rules/evaluator.py`: evaluator with **event_id index** (~100× faster) + pre-compiled regex
- Correlation engine: entity extraction + 5-min sliding window chain building
- AI cost limiter: priority-based event selection (critical > high > medium > info)
- Gemini 2.5 Flash: `analyze_events()` + `analyze_chains()` with 3-attempt backoff

### YAML Rule Library (Rule Engine Expansion)
- **2,212 total rules** loaded at startup (2,202 simple + 10 threshold)
- Built-in rules: 48 rules across `windows.yaml`, `linux.yaml`, `cloudtrail.yaml`, `nginx.yaml`
- Sigma-derived rules: 89 Windows + 13 Linux + 16 CloudTrail + 6 Nginx = **124 Sigma rules** in YAML
- Converter script: `scripts/sigma_to_lograven.py` (converts SigmaHQ repos to LogRaven format)
- Rule directories: `backend/app/data/rules/builtin/` and `backend/app/data/rules/sigma/`

### PDF Reports (Month 4)
- `reports/builder.py`, `reports/templates/lograven_report.html/.css`
- `reports/pdf_generator.py`: WeasyPrint primary → **xhtml2pdf fallback** (works on Windows)
- `reports/uploader.py`: stores PDF via storage abstraction

### Production Bug Fixes (Pre-Launch)
- `rules/engine.py` created (was missing — CRITICAL)
- Correlation `correlate = analyze` alias added (function name mismatch — CRITICAL)
- File size validation by tier added to upload endpoint
- PDF download uses DI storage (not hardcoded `LocalStorageBackend()`)
- `LogRavenError.status_code = 500` added to base exception class
- HTTP 500 responses hide raw exception detail (only generic message returned)
- `investigation.error_message` column added (migration 007) — pipeline failure reason surfaced
- AI client bug fixed: now reads `settings.GEMINI_API_KEY` (not `os.environ`) and passes `api_key=` to `genai.Client()`
- Rule engine performance: event_id index + pre-compiled regex (39s → ~0.3s for 2k events)
- PDF fallback: `xhtml2pdf` installed and wired as WeasyPrint fallback

### Frontend (Month 4 — React/TypeScript/Tailwind)
- All 16 components complete; TypeScript clean (`tsc --noEmit` exits 0)
- `api/client.ts`, `store/authStore.ts`, all hooks, all pages, FindingCard, Badge

---

## What Is NOT Done Yet
- `license.py`: full HMAC validation (currently `bypass_dev=True`)
- Rate limiting on auth endpoints
- Full structured JSON logging
- Audit log retention cleanup job
- Docker image build (`docker-compose` + `Dockerfile`)
- PyArmor obfuscation pipeline
- `mitreattack-python` not installed in venv (`pip install mitreattack-python` needed)
- EQL-style sequence rules (would unlock ~800 more Sigma rules currently skipped)
- `vite-env.d.ts` missing — worked around via `/// <reference` in `main.tsx`

---

## Open Questions
None. All decisions made.
