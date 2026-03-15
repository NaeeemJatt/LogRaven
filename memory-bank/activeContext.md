# LogRaven — Active Context

## Current Session Goal
Month 1 Week 1 — Implement database models and auth foundation

## Status
Scaffold created. Memory bank written. Ready to start Month 1 Week 1.

## All Decisions Locked
- Name: LogRaven / lograven.io / Docker: lograven:v1.0
- Docker delivery model, no hosted SaaS for v1
- Investigation model with multi-file correlation
- Local storage for dev (not S3)
- PyArmor + hardware-bound license for protection
- No admin panel in v1
- Cloud AI only (Claude claude-sonnet-4-6) for v1
- vstorm-co template used as reference scaffold
- Project folder: lograven/

## What Comes Next
1. Implement 6 SQLAlchemy models in backend/app/models/
2. Alembic migration files
3. JWT auth endpoints
4. LocalStorageBackend + license.py

## Open Questions
None. All decisions made.
