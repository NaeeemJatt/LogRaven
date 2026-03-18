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
Status: COMPLETE
Completed: 2026-03-18

### Done
- [x] rules/engine.py: run_rules()
      Rule 1: severity_hint="critical" if brute_force_candidate + >20 auth_failure events
      Rule 2: severity_hint="high" if lateral_movement_candidate
      Rule 3: severity_hint="high" if sensitive_action (CloudTrail)
      Rule 4: deduplication within 5-second window (flag + severity_hint="deduplicated")
- [x] correlation/entity_extractor.py: extract_entities()
      Returns {ips, users, hosts} normalized via normalize_entity()
- [x] correlation/chain_builder.py: build_chains()
      5-minute sliding window, same IP or username across different source_types
      Cross-source only chains, sorted by event_count desc
- [x] correlation/engine.py: correlate()
      Returns {entities, chains, chain_count, top_entity}
- [x] ai/cost_limiter.py: enforce_ceiling(events, tier) -> (list, bool)
      free=2000, pro=10000, team=50000 events
      Priority: critical > high > medium > informational > deduplicated
- [x] ai/prompts/base_prompt.py: SYSTEM_PROMPT, _serialize_events(), build_prompt()
- [x] ai/prompts/windows_prompt.py: build_windows_prompt() -> (system, user)
- [x] ai/prompts/syslog_prompt.py: build_syslog_prompt()
- [x] ai/prompts/cloudtrail_prompt.py: build_cloudtrail_prompt()
- [x] ai/prompts/nginx_prompt.py: build_nginx_prompt()
- [x] ai/prompts/correlation_prompt.py: build_correlation_prompt()
      Serializes NormalizedEvent dataclasses to JSON-safe dicts
- [x] ai/chunker.py: split_events() with 50-event overlap, merge_findings() dedup by title
- [x] ai/cloud/engine.py: Gemini 2.5 Flash via google-genai (NOT anthropic)
      analyze_events(): chunked with 3-attempt exponential backoff
      analyze_chains(): single call for correlation chains
      Graceful skip if GEMINI_API_KEY missing or google-genai not installed
- [x] ai/router.py: route_analysis() — dispatches to correct prompt builder by log_type
- [x] reports/mitre_mapper.py: enrich_finding(), enrich_all(), get_coverage_matrix()
      Lazy-loads enterprise-attack.json (35.7 MB, downloaded to backend/app/data/)
      Graceful skip if file missing or mitreattack-python not installed
- [x] tasks/process_investigation.py: full end-to-end pipeline wired
      parse → run_rules → correlate → enforce_ceiling →
      route_analysis (Gemini) → enrich_all (MITRE) →
      save Report + Finding rows → investigation.status = "complete"
- [x] api/investigations/routes.py: GET /{id}/report endpoint
      Returns {report fields, findings: [all Finding rows]}
- [x] config.py: GEMINI_API_KEY field added
- [x] requirements.txt: google-genai>=1.0.0 added and installed

---

## Month 4 — Reports + PDF + Frontend
Status: COMPLETE
Completed: 2026-03-18

### Done
- [x] reports/builder.py: build_report_context(report, findings) -> dict
      Splits correlated/single, sorts by severity, deduplicates IOCs
- [x] reports/templates/lograven_report.html: full Jinja2/WeasyPrint PDF template
      Cover page, executive summary, correlated findings, individual findings,
      MITRE ATT&CK table, IOC reference table, @page footers
- [x] reports/templates/lograven_report.css: complete brand styling
      LogRaven colors (#3B82F6, #0D0F14, #7C3AED), severity badges,
      finding cards with left-border severity color, @page footer rules
- [x] reports/pdf_generator.py: generate_pdf(report, findings, output_dir) -> str
      Jinja2 renders HTML, WeasyPrint converts to PDF bytes
      Raises ImportError with clear message if WeasyPrint/Jinja2 missing
- [x] reports/uploader.py: upload_report(pdf_path, investigation_id, storage) -> str
      Reads bytes, stores via save_file_from_bytes(), deletes temp file
- [x] utils/storage.py: save_file_from_bytes(key, data) added to LocalStorageBackend
- [x] tasks/process_investigation.py: Step 5j PDF generation wired
      Non-critical: PDF failure logged but investigation still marked complete
- [x] api/investigations/routes.py: GET /{id}/report/download
      Returns {download_url, filename, expires_in}
- [x] WeasyPrint 68.x + Jinja2 3.1.6 installed and working

### Frontend (all 16 tasks complete)
- [x] api/client.ts: Axios with JWT interceptor + 401 auto-refresh flow
- [x] store/authStore.ts: Zustand (setTokens, setUser, logout)
- [x] api/auth.ts: register, login, refresh, me
- [x] api/investigations.ts: full API surface (CRUD + upload + analyze + report)
- [x] hooks/useAuth.ts: login/register/logout with useNavigate
- [x] hooks/useJobStatus.ts: React Query 3s polling, stops on complete/failed
- [x] App.tsx: BrowserRouter, ProtectedRoute, all 7 routes
- [x] pages/Auth/Login.tsx: form, loading state, error display
- [x] pages/Auth/Register.tsx: passwords-match validation, error display
- [x] pages/Dashboard.tsx: investigation table, status badges, delete, report link
- [x] pages/NewInvestigation.tsx: name form → navigate to investigation
- [x] pages/Investigation.tsx: drag-drop upload, source type selector, analyze
- [x] pages/JobStatus.tsx: stepped progress bar, auto-navigate on complete
- [x] pages/Report.tsx: findings display, correlated section, IOCs, PDF download
- [x] components/reports/FindingCard.tsx: severity badges, IOCs, remediation, MITRE
- [x] components/ui/Badge.tsx: soft + solid severity badge variants
- [x] TypeScript: tsc --noEmit exits 0, zero errors

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
