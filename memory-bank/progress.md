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
Status: COMPLETE
Completed: 2026-03-18

### Done
- [x] utils/security.py: hash_password (bcrypt 4.2.1), verify_password,
      create_access_token (15min), create_refresh_token (7d), decode_token
- [x] services/auth_service.py: register_user, login_user, refresh_token
      All write audit_log. Failed logins write failed_login audit entry.
- [x] api/auth/routes.py: POST /auth/register (201), POST /auth/login (200),
      POST /auth/refresh (200), GET /auth/me (200)
- [x] api/auth/helpers.py: create_token_pair, verify_token_or_raise
- [x] api/router.py: auth router registered at /auth prefix
- [x] email-validator installed (pydantic[email])
- [x] bcrypt pinned to 4.2.1 (passlib 1.7.4 incompatible with bcrypt 5.x)
- [x] All 6 auth scenarios verified live against running server

---

## Month 1 Week 3 — File Upload Pipeline + Investigation CRUD
Status: COMPLETE
Completed: 2026-03-18

### Done
- [x] schemas/investigation.py: InvestigationCreate, InvestigationResponse,
      InvestigationFileResponse, InvestigationStatusResponse
- [x] api/investigations/routes.py: ALL endpoints implemented inline
      POST /api/v1/investigations (create, 201)
      GET  /api/v1/investigations (list, paginated)
      GET  /api/v1/investigations/{id}
      DELETE /api/v1/investigations/{id} (204)
      POST /api/v1/investigations/{id}/files (multipart upload, 201)
      DELETE /api/v1/investigations/{id}/files/{file_id} (204)
      POST /api/v1/investigations/{id}/analyze (queue pipeline)
      GET  /api/v1/investigations/{id}/status (polling endpoint)
- [x] api/investigations/validators.py: ALLOWED_EXTENSIONS, TIER_SIZE_LIMITS,
      VALID_SOURCE_TYPES constants used by routes
- [x] api/router.py: investigations router registered at /api/v1/investigations
- [x] Upload stored via LocalStorageBackend (key: uploads/{inv_id}/{uuid}_{name})
- [x] InvestigationFile row created per upload with source_type

---

## Month 2 — Log Parsers + Celery Pipeline Scaffold
Status: COMPLETE
Completed: 2026-03-18

### Done
- [x] parsers/base.py: BaseParser ABC
      _stream_lines: UTF-8 with latin-1 fallback, true streaming
      _safe_parse_timestamp: 4 format attempts, returns None on failure
      _log_skip: DEBUG level via structured logger
- [x] parsers/normalizer.py: NormalizedEvent dataclass
      + normalize_entity() utility for correlation
- [x] parsers/detector.py: two-phase detection
      Phase 1: extension hint (.evtx/.json/.csv)
      Phase 2: content scan first 50 lines (always overrides Phase 1)
      Raises UnknownLogTypeError if nothing matches
- [x] parsers/windows_event.py: WindowsEventParser
      evtx via PyEvtxParser (graceful ImportError fallback to CSV)
      CSV DictReader fallback for CSV exports
      EVENT_TYPE_MAP: 8 Windows Security event IDs
      _detect_patterns: brute_force_candidate (5+ failures/60s same IP),
      lateral_movement_candidate (auth_success/explicit_cred to 3+ hosts)
- [x] parsers/syslog.py: SyslogParser
      5 pattern candidates, best match selected from first 200 lines
      Username extraction: 3 regex patterns
      Source IP extraction from message body
      _detect_patterns: brute_force, privilege_escalation, account_modification
- [x] parsers/cloudtrail.py: CloudTrailParser
      Handles {"Records":[...]} and single-event JSON
      11 SENSITIVE_ACTIONS flagged, errorCode -> failed_api_call + auth_failure
- [x] parsers/nginx.py: NginxParser
      Combined log regex parsing
      injection_attempt: SQL keywords, path traversal in URL
      _detect_patterns: scanning (50+/60s), 4xx_spike (20+ 4xx per IP)
- [x] tasks/celery_app.py: Celery with task_always_eager=True (dev, no Redis needed)
- [x] tasks/process_investigation.py: async pipeline via asyncio.run()
      Status flow: queued -> processing -> per-file detect+parse -> complete/failed
      Per-file: detector.detect() -> parser selection -> parse() -> DB update

---

## Month 3 — Correlation + AI
Status: IN PROGRESS — Week 1–2 complete, AI integration pending

### Done
- [x] rules/engine.py: run_rules()
      Rule 1: critical severity if brute_force_candidate + >20 auth_failure events
      Rule 2: high severity if lateral_movement_candidate
      Rule 3: high severity if sensitive_action (CloudTrail)
      Rule 4: deduplication within 5-second window (flag + severity="deduplicated")
- [x] correlation/entity_extractor.py: extract_entities()
      Returns {ips, users, hosts} sets, normalized via normalize_entity()
- [x] correlation/chain_builder.py: build_chains()
      5-minute sliding window, same IP or username across different source_types
      Cross-source only (2+ source_types required), sorted by event_count desc
- [x] correlation/engine.py: correlate()
      Orchestrates entity_extractor + chain_builder
      Returns {entities, chains, chain_count, top_entity}
- [x] ai/cost_limiter.py: enforce_ceiling(events, tier) -> (list, bool)
      free=2000, pro=10000, team=50000 events
      Priority: critical > high > medium > informational > deduplicated
- [x] tasks/process_investigation.py: pipeline extended
      queued -> processing -> parse -> run_rules -> correlate -> enforce_ceiling -> complete

### Not Done Yet
- [ ] ai/prompts/base_prompt.py: SYSTEM_PROMPT + build_prompt()
- [ ] ai/prompts/windows_prompt.py, syslog_prompt.py,
      cloudtrail_prompt.py, nginx_prompt.py, correlation_prompt.py
- [ ] ai/chunker.py: split_events(), merge_findings()
- [ ] ai/cloud/engine.py: Gemini API calls (google-genai, NOT anthropic)
- [ ] ai/router.py: route_analysis() dispatcher
- [ ] reports/mitre_mapper.py: enrich_finding(), enrich_all()
- [ ] Save Report and Finding rows to DB after AI analysis
- [ ] GET /api/v1/investigations/{id}/report endpoint

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
