# LogRaven — Master Specification
See lograven_master_v3.docx for the full detailed specification.

## Project
Name: LogRaven
Domain: lograven.io
Tagline: Watch your logs. Find the threat.
Docker: lograven:v1.0

## Quick Reference
- Tech stack: FastAPI + React + Celery + Redis + PostgreSQL + Claude API + WeasyPrint
- Delivery: Docker image (on-premise, client runs locally)
- AI: Claude claude-sonnet-4-6 (cloud) — local AI is Phase 2
- Storage: LocalStorageBackend (dev) / S3StorageBackend (prod)

## Critical Rules
1. SQLAlchemy 2.0 select() style only
2. Pydantic v2 everywhere
3. Async/await in all FastAPI routes
4. Never load log files fully into memory — stream
5. Rule engine first, AI second
6. Always use storage.py abstraction
7. License validated at startup first
