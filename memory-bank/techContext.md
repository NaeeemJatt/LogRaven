# LogRaven — Technical Context

## Stack
Backend:    FastAPI 0.111, Python 3.14, SQLAlchemy 2.0, Alembic 1.13
Queue:      Celery 5.3, Redis 7.2 (task_always_eager=True in dev — no Redis needed)
Database:   PostgreSQL 15
Parsers:    pyevtx-rs (pip install evtx), mitreattack-python
AI:         Gemini 2.5 Flash via google-genai package — cloud only v1
            API key: GEMINI_API_KEY (set in .env, read via settings.GEMINI_API_KEY)
            Client init: genai.Client(api_key=api_key) — NOT genai.Client()
            NOT anthropic SDK — not installed or used
Rule Engine: YAML rules loaded from app/data/rules/ (2,212 total at startup)
            Evaluator uses event_id index for ~100× faster per-event lookup
            Pre-compiled regex via SimpleCondition._compiled_re (PrivateAttr)
PDF:        WeasyPrint primary (Linux/Docker, needs GTK3)
            xhtml2pdf fallback (Windows dev, pure Python, no system deps)
            Both use same Jinja2 template: lograven_report.html
Storage:    LocalStorageBackend (dev) / S3StorageBackend (prod)
Frontend:   React 18, TypeScript 5.4, Vite 5.2, Tailwind 3.4, React Query 5
Protection: PyArmor obfuscation + hardware-bound license keys

## Critical Rules — Never Violate
- SQLAlchemy 2.0 `select()` ONLY — never `session.query()`
- Pydantic v2 syntax everywhere
- Always async/await in FastAPI routes
- Never load full log file into memory — stream always
- Rule engine FIRST, AI SECOND — AI writes narrative, not detections
- Storage: always use `app/utils/storage.py` abstraction
- License validated at `main.py` startup BEFORE anything else
- pyevtx-rs (`pip install evtx`) — NOT python-evtx (440× slower)
- mitreattack-python loaded ONCE at module startup — not per request
- GEMINI_API_KEY read via `settings.GEMINI_API_KEY` — NOT `os.environ.get()`
- bcrypt pinned to 4.2.1 — do not upgrade until passlib is replaced

## Key File Locations
- Rule YAML files:    `backend/app/data/rules/builtin/` and `backend/app/data/rules/sigma/`
- Rule schema:        `backend/app/rules/schema.py`
- Rule loader:        `backend/app/rules/loader.py`
- Rule evaluator:     `backend/app/rules/evaluator.py`
- Rule engine:        `backend/app/rules/engine.py`
- Sigma converter:    `scripts/sigma_to_lograven.py`
- Pipeline:           `backend/app/tasks/process_investigation.py`
- AI client:          `backend/app/ai/cloud/engine.py`
- PDF generator:      `backend/app/reports/pdf_generator.py`
- Config (settings):  `backend/app/config.py`

## Key GitHub Resources
- pyevtx-rs:          github.com/omerbenamram/pyevtx-rs (440× faster)
- mitreattack-python: github.com/mitre-attack/mitreattack-python
- Test data:          github.com/sbousseaden/EVTX-ATTACK-SAMPLES
- SigmaHQ rules:      github.com/SigmaHQ/sigma (converter at scripts/sigma_to_lograven.py)
- Scaffold:           vstorm-co/full-stack-fastapi-nextjs-llm-template

## Alembic Migrations Applied
- 001: create users table
- 002: create investigations table
- 003: create investigation_files table
- 004: create reports table
- 005: create findings table
- 006: create audit_log table
- 007: add investigation.error_message column (Text, nullable)
