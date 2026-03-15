# LogRaven — Active Context

## Current Session Goal
Month 1 Week 2 — Implement JWT authentication system

## Status
Database layer complete. Server running. Starting auth endpoints next session.

## Environment (Windows, No Docker)
- OS: Windows 10, PowerShell
- Python: 3.14 at backend/venv/
- PostgreSQL: localhost:5432/lograven (password: root)
- Redis: localhost:6379 (not yet used)
- Start server: cd backend && uvicorn app.main:app --reload --port 8000
- Dev setup script: .\scripts\windows_setup.ps1
- DB utility: python scripts/db.py check|tables|migrations|drop

## What Was Completed (Month 1 Week 1)
- 159-file scaffold created across full LogRaven structure
- Virtual environment created at backend/venv/, all packages installed
- All 6 SQLAlchemy 2.0 models implemented with relationships:
  user, investigation, investigation_file, report, finding, audit_log
- All 6 Alembic migrations written and applied (alembic upgrade head)
- Tables confirmed in PostgreSQL: users, investigations,
  investigation_files, reports, findings, audit_log
- dependencies.py: async engine, get_db, get_storage,
  get_current_user, require_pro_tier
- main.py: lifespan startup, license check, CORS, StaticFiles,
  exception handlers, router registration
- config.py: absolute .env path resolution (Windows fix)
- license.py: Windows-compatible fingerprint (no os.uname())
- storage.py: LocalStorageBackend fully implemented
- utils/exceptions.py: all custom exception classes
- utils/logger.py: structured logging
- utils/security.py: hash_password, verify_password,
  create_access_token, create_refresh_token, decode_token
- health route: GET /health returns 200
- /docs Swagger UI confirmed working
- backend/scripts/db.py: Python psql replacement (no more.com)
- scripts/windows_setup.ps1: one-command dev session setup

## What Was NOT Done (still pending)
- auth_service.py: register, login, refresh business logic
- api/auth/routes.py: POST /auth/register, /auth/login, /auth/refresh
- api/router.py: auth router not yet registered
- Schemas: user.py schemas not yet validated against Pydantic v2

## All Decisions Locked
- Name: LogRaven / lograven.io / Docker: lograven:v1.0
- Docker delivery model, no hosted SaaS for v1
- Investigation model with multi-file correlation
- Local storage for dev (not S3)
- PyArmor + hardware-bound license for protection
- No admin panel in v1
- Cloud AI only (Claude claude-sonnet-4-6) for v1
- Project folder: lograven/

## Next Session — Start With This Prompt
Paste this exactly at the start of the next session:

```
@memory-bank/projectbrief.md
@memory-bank/techContext.md
@memory-bank/systemPatterns.md
@memory-bank/activeContext.md
@backend/app/schemas/user.py
@backend/app/models/user.py
@backend/app/utils/security.py
@backend/app/utils/exceptions.py
@backend/app/services/auth_service.py
@backend/app/dependencies.py
@backend/app/api/auth/routes.py
@backend/app/api/router.py
@backend/app/main.py

Implement the complete JWT authentication system for LogRaven.

TASK 1 — Fill in backend/app/schemas/user.py
  UserCreate: email (EmailStr), password (str, min 8 chars)
  UserResponse: id, email, tier, created_at
  UserLogin: email, password
  TokenResponse: access_token, refresh_token, token_type="bearer"

TASK 2 — Fill in backend/app/services/auth_service.py
  register(db, email, password) -> User
    Check email not already taken (raise 409 if exists)
    Hash password with hash_password()
    Insert User row, return it
  login(db, email, password) -> TokenResponse
    Fetch user by email (raise 401 if not found)
    Verify password (raise 401 if wrong)
    Write audit_log entry: action="login"
    Return TokenResponse with access + refresh tokens
  refresh(db, refresh_token) -> TokenResponse
    Decode refresh token (raise 401 if expired/invalid)
    Fetch user by id from token
    Return new TokenResponse

TASK 3 — Fill in backend/app/api/auth/routes.py
  POST /auth/register -> UserResponse (201)
  POST /auth/login    -> TokenResponse (200)
  POST /auth/refresh  -> TokenResponse (200)
  GET  /auth/me       -> UserResponse (200, requires auth)

TASK 4 — Register auth router in backend/app/api/router.py

RULES:
- Pydantic v2 everywhere
- async/await throughout
- Use get_db() dependency from dependencies.py
- audit_log entry on every login and failed_login
- Fill existing files only — do not create new files
```

## Open Questions
None. All decisions made.
