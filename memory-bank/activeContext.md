# LogRaven — Active Context

## Current Session Goal
Month 1 Week 3 — File upload pipeline (investigations + file upload)

## Status
Auth system complete. Server running with all auth endpoints verified.

## Environment (Windows, No Docker)
- OS: Windows 10, PowerShell
- Python: 3.14 at backend/venv/
- PostgreSQL: localhost:5432/lograven (password: root)
- Redis: localhost:6379 (not yet used)
- Start server: cd backend && uvicorn app.main:app --reload --port 8000
- Dev setup script: .\scripts\windows_setup.ps1
- DB utility: python scripts/db.py check|tables|migrations|drop
- NOTE: bcrypt pinned to 4.2.1 (passlib incompatible with bcrypt 5.x)

## What Was Completed (Month 1 Week 2 — Auth)
- utils/security.py: hash_password, verify_password (bcrypt 4.2.1),
  create_access_token, create_refresh_token, decode_token (raises HTTP 401)
- services/auth_service.py: register_user, login_user, refresh_token
  All write audit_log entries. Failed logins write failed_login audit.
- api/auth/routes.py: POST /auth/register (201), POST /auth/login (200),
  POST /auth/refresh (200), GET /auth/me (200)
- api/auth/helpers.py: create_token_pair, verify_token_or_raise
- api/router.py: auth router registered at /auth prefix
- email-validator installed (required for Pydantic EmailStr)
- bcrypt downgraded to 4.2.1 (passlib 1.7.4 incompatible with 5.x)

## All Auth Endpoints Verified Live
- POST /auth/register  -> 201 TokenResponse (access + refresh tokens)
- POST /auth/login     -> 200 TokenResponse
- POST /auth/refresh   -> 200 {access_token, token_type}
- GET  /auth/me        -> 200 UserResponse {id, email, tier, created_at}
- Wrong password       -> 401 {"detail": "Invalid credentials"}
- Duplicate email      -> 400 {"detail": "Email already registered"}

## All Decisions Locked
- Name: LogRaven / lograven.io / Docker: lograven:v1.0
- Docker delivery model, no hosted SaaS for v1
- Investigation model with multi-file correlation
- Local storage for dev (not S3)
- PyArmor + hardware-bound license for protection
- No admin panel in v1
- Cloud AI only (Claude claude-sonnet-4-6) for v1
- bcrypt pinned to 4.2.1 — do not upgrade until passlib is replaced
- Project folder: lograven/

## Next Session — Start With This Prompt
Paste this exactly at the start of the next session:

```
@memory-bank/projectbrief.md
@memory-bank/techContext.md
@memory-bank/systemPatterns.md
@memory-bank/activeContext.md
@backend/app/schemas/investigation.py
@backend/app/models/investigation.py
@backend/app/models/investigation_file.py
@backend/app/services/investigation_service.py
@backend/app/api/investigations/routes.py
@backend/app/api/investigations/validators.py
@backend/app/api/router.py
@backend/app/dependencies.py

Implement the complete investigation + file upload system.

TASK 1 — backend/app/schemas/investigation.py
  InvestigationCreate: name (str, 1-200 chars)
  InvestigationResponse: id, name, status, correlation_enabled,
    files (list[InvestigationFileResponse]), created_at
  InvestigationFileResponse: id, filename, source_type, log_type,
    status, event_count, uploaded_at
  InvestigationStatusResponse: id, status, files (list with statuses)

TASK 2 — backend/app/services/investigation_service.py
  create_investigation(name, user_id, db) -> Investigation
  list_investigations(user_id, db) -> list[Investigation]
  get_investigation(inv_id, user_id, db) -> Investigation
    Raise 404 if not found or not owned by user
  delete_investigation(inv_id, user_id, db) -> None
    Raise 404 if not found, raise 403 if not owned
  upload_file(inv_id, user_id, file, source_type, db, storage)
    -> InvestigationFile
    Enforce file size limits: free=5MB, pro=50MB, team=200MB
    Detect source_type from parameter
    Save via storage.save_file()
    Create InvestigationFile row
    key format: uploads/{inv_id}/{uuid}_{filename}

TASK 3 — backend/app/api/investigations/routes.py
  POST   /api/v1/investigations          -> InvestigationResponse (201)
  GET    /api/v1/investigations          -> list[InvestigationResponse]
  GET    /api/v1/investigations/{id}     -> InvestigationResponse
  DELETE /api/v1/investigations/{id}     -> 204
  POST   /api/v1/investigations/{id}/files -> InvestigationFileResponse
    Accept: multipart/form-data
    Fields: file (UploadFile), source_type (str)

TASK 4 — Register investigations router in api/router.py

RULES:
- All routes require authentication (Depends(get_current_user))
- SQLAlchemy 2.0 select() only
- File size limit enforced before saving
- Fill existing files only
```

## Open Questions
None. All decisions made.
