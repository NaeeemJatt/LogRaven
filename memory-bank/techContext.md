# LogRaven — Technical Context

## Stack
Backend:    FastAPI 0.111, Python 3.11, SQLAlchemy 2.0, Alembic 1.13
Queue:      Celery 5.3, Redis 7.2
Database:   PostgreSQL 15
Parsers:    pyevtx-rs (pip install evtx), mitreattack-python
AI:         Claude claude-sonnet-4-6 via anthropic SDK — cloud only v1
PDF:        WeasyPrint 62 + Jinja2 template: lograven_report.html
Storage:    LocalStorageBackend (dev) / S3StorageBackend (prod)
Frontend:   React 18, TypeScript 5.4, Vite 5.2, Tailwind 3.4, React Query 5
Protection: PyArmor obfuscation + hardware-bound license keys

## Critical Rules — Never Violate
- SQLAlchemy 2.0 select() ONLY — never session.query()
- Pydantic v2 syntax everywhere
- Always async/await in FastAPI routes
- Never load full log file into memory — stream always
- Rule engine FIRST, AI SECOND — AI writes narrative, not detections
- Storage: always use app/utils/storage.py abstraction
- License validated at main.py startup BEFORE anything else
- pyevtx-rs (pip install evtx) — NOT python-evtx (440x slower)
- mitreattack-python loaded ONCE at module startup — not per request

## Key GitHub Resources
- pyevtx-rs:          github.com/omerbenamram/pyevtx-rs (440x faster)
- mitreattack-python: github.com/mitre-attack/mitreattack-python
- Test data:          github.com/sbousseaden/EVTX-ATTACK-SAMPLES
- Scaffold:           vstorm-co/full-stack-fastapi-nextjs-llm-template
