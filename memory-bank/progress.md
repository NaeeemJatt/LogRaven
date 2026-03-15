# LogRaven — Detailed Progress Log

## Month 1 Week 1 — Foundation
Status: COMPLETE
Completed: 2026-03-15

### Done
- [x] SQLAlchemy 2.0 models with mapped_column() syntax:
      user, investigation, investigation_file, report, finding, audit_log
- [x] Full bidirectional ORM relationships wired across all models
- [x] Alembic migration files 001-006 written and applied
- [x] All 6 tables confirmed in PostgreSQL (alembic upgrade head)
- [x] dependencies.py: async engine, get_db, get_storage,
      get_current_user, require_pro_tier
- [x] main.py: lifespan startup, license check, CORS, StaticFiles
      mount, exception handlers, router registration
- [x] config.py: absolute .env path resolution (Windows fix)
- [x] license.py: Windows-compatible machine fingerprint
- [x] storage.py: LocalStorageBackend fully implemented
- [x] utils/exceptions.py: LogRavenError + all subclasses
- [x] utils/logger.py: get_logger() structured logging
- [x] utils/security.py: hash_password, verify_password,
      create_access_token, create_refresh_token, decode_token
- [x] api/health/routes.py: GET /health returns 200
- [x] FastAPI server starts: uvicorn app.main:app --reload --port 8000
- [x] /docs Swagger UI confirmed loading
- [x] backend/scripts/db.py: Python psql replacement for Windows
      (check, tables, migrations, drop commands)
- [x] scripts/windows_setup.ps1: one-command dev session setup

### Not Done (moved to Week 2)
- [ ] auth_service.py: register, login, refresh
- [ ] api/auth/routes.py: POST /auth/register, /login, /refresh, GET /me
- [ ] api/router.py: auth router registration
- [ ] schemas/user.py: Pydantic v2 validated

---

## Month 1 Week 2 — Authentication
Status: NOT STARTED

### Goals
- [ ] schemas/user.py: UserCreate, UserResponse, UserLogin, TokenResponse
- [ ] auth_service.py: register, login (with audit log), refresh
- [ ] api/auth/routes.py: register, login, refresh, me
- [ ] api/router.py: register auth router
- [ ] Write auth integration test

---

## Month 1 Week 3 — File Upload Pipeline
Status: NOT STARTED

### Goals
- [ ] schemas/investigation.py: all schemas
- [ ] services/investigation_service.py: create, list, get, delete
- [ ] api/investigations/routes.py: CRUD + file upload
- [ ] api/investigations/validators.py: file type + size checks
- [ ] File size limits: free=5MB, pro=50MB, team=200MB
- [ ] Upload stored via LocalStorageBackend
- [ ] InvestigationFile row created per upload

---

## Month 2 — Log Parsers
Status: NOT STARTED

### Goals
- [ ] parsers/detector.py: auto-detect evtx/syslog/cloudtrail/nginx
- [ ] parsers/windows_event.py: pyevtx-rs parsing
- [ ] parsers/syslog.py: Linux auth.log / syslog
- [ ] parsers/cloudtrail.py: AWS CloudTrail JSON
- [ ] parsers/nginx.py: access log regex parsing
- [ ] parsers/normalizer.py: unified NormalizedEvent format
- [ ] parsers/base.py: BaseParser ABC

---

## Month 3 — Correlation + AI
Status: NOT STARTED

### Goals
- [ ] correlation/entity_extractor.py: IP, user, host extraction
- [ ] correlation/chain_builder.py: 5-min window cross-source chains
- [ ] correlation/engine.py: orchestration
- [ ] ai/cost_limiter.py: enforce free/pro/team event ceilings
- [ ] ai/cloud/engine.py: Claude claude-sonnet-4-6 integration
- [ ] ai/prompts/: per-log-type prompt templates
- [ ] Rule engine: pre-filter events before AI (60-80% reduction)
- [ ] Celery task: tasks/process_investigation.py pipeline

---

## Month 4 — Reports + License
Status: NOT STARTED

### Goals
- [ ] reports/builder.py: compile findings into Report row
- [ ] reports/mitre_mapper.py: mitreattack-python enrichment
- [ ] reports/pdf_generator.py: WeasyPrint lograven_report.html
- [ ] schemas/report.py: all report schemas
- [ ] api/reports/routes.py: get report, download PDF
- [ ] license.py: full HMAC validation with machine fingerprint
- [ ] lograven-license-generator.py: complete implementation

---

## Month 5 — Polish
Status: NOT STARTED

### Goals
- [ ] Rate limiting on auth endpoints
- [ ] Full structured JSON logging
- [ ] utils/rate_limiter.py: Redis-backed rate limiter
- [ ] Audit log retention cleanup job
- [ ] Error handling hardening

---

## Month 6 — First Sales
Status: NOT STARTED

### Goals
- [ ] PyArmor obfuscation pipeline
- [ ] Docker image build: lograven:v1.0
- [ ] docker-compose.client.yml tested end-to-end
- [ ] First customer deployment
