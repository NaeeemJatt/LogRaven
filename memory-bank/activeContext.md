# LogRaven — Active Context

## Current Session Goal
Month 4 + Frontend COMPLETE

## Status
Full backend pipeline + PDF generation + React frontend operational.

## Environment (Windows, No Docker)
- OS: Windows 10, PowerShell
- Python: 3.14 at backend/venv/
- PostgreSQL: localhost:5432/lograven (password: root)
- Redis: localhost:6379 (NOT needed — Celery task_always_eager=True)
- Start backend: cd backend && uvicorn app.main:app --reload --port 8000
- Start frontend: cd frontend && npm run dev  (runs on http://localhost:5173)
- Dev setup script: .\scripts\windows_setup.ps1
- DB utility: python scripts/db.py check|tables|migrations|drop
- NOTE: bcrypt pinned to 4.2.1 (passlib incompatible with bcrypt 5.x)
- GEMINI_API_KEY set in .env and working
- enterprise-attack.json downloaded to backend/app/data/ (35.7 MB)
- WeasyPrint 68.x installed (pure Python, no GTK needed on Windows)
- Jinja2 3.1.6 installed

## All Completed (Months 1–4 + Frontend)

### Foundation + Auth (Month 1)
- All 6 DB tables, Alembic migrations applied
- JWT auth: register, login, refresh, /auth/me
- dependencies.py, main.py, config.py, license.py all working

### Investigation CRUD + File Upload (Month 1 Week 3)
- Full CRUD: POST/GET/DELETE /api/v1/investigations
- File upload: POST /api/v1/investigations/{id}/files
- File delete: DELETE /api/v1/investigations/{id}/files/{file_id}
- Analyze trigger: POST /api/v1/investigations/{id}/analyze
- Status polling: GET /api/v1/investigations/{id}/status
- Report endpoint: GET /api/v1/investigations/{id}/report
- PDF download: GET /api/v1/investigations/{id}/report/download

### Parsers (Month 2)
- windows_event (evtx + CSV), syslog, cloudtrail, nginx
- detector.py: two-phase log type detection
- NormalizedEvent dataclass + normalize_entity()
- Celery pipeline scaffold with task_always_eager=True

### Rule Engine + Correlation + AI (Month 3)
- rules/engine.py: 4 rules
- correlation: entity_extractor, chain_builder, engine
- ai/cost_limiter.py: enforce_ceiling() free/pro/team tiers
- ai/prompts/: base, windows, syslog, cloudtrail, nginx, correlation
- ai/chunker.py: split_events() + merge_findings()
- ai/cloud/engine.py: Gemini 2.5 Flash via google-genai
- ai/router.py: route_analysis() dispatch
- reports/mitre_mapper.py: enrich_all(), get_coverage_matrix()
- process_investigation.py: fully wired end-to-end pipeline
- Report + Finding rows saved to DB after AI analysis

### PDF Reports (Month 4)
- reports/builder.py: build_report_context() for Jinja2
- reports/templates/lograven_report.html: full WeasyPrint PDF template
- reports/templates/lograven_report.css: complete brand styling
- reports/pdf_generator.py: generate_pdf() WeasyPrint + Jinja2
- reports/uploader.py: upload_report() with temp file cleanup
- storage.py: save_file_from_bytes() added to LocalStorageBackend
- process_investigation.py: Step 5j PDF generation wired in (non-critical failure)
- GET /api/v1/investigations/{id}/report/download returns download URL

### Frontend (Month 4 — React/TypeScript/Tailwind)
- api/client.ts: Axios with JWT request interceptor + 401 auto-refresh
- store/authStore.ts: Zustand store (setTokens, setUser, logout)
- api/auth.ts: register, login, refresh, me
- api/investigations.ts: full CRUD + upload + analyze + report endpoints
- hooks/useAuth.ts: login/register/logout with navigate
- hooks/useJobStatus.ts: React Query polling (3s interval, stops on terminal state)
- App.tsx: React Router with ProtectedRoute, all 7 routes
- pages/Auth/Login.tsx: centered card, error handling, loading state
- pages/Auth/Register.tsx: password match validation, error handling
- pages/Dashboard.tsx: investigation table, status badges, delete, report link
- pages/NewInvestigation.tsx: name form → navigate to investigation detail
- pages/Investigation.tsx: drag-drop upload, source type selector, analyze button
- pages/JobStatus.tsx: stepped progress bar, 3s polling, auto-navigate on complete
- pages/Report.tsx: full findings display, correlated section, IOCs, PDF download
- components/reports/FindingCard.tsx: severity badges, IOCs, remediation, MITRE detail
- components/ui/Badge.tsx: soft + solid severity badge variants
- All files TypeScript clean (tsc --noEmit exits 0)

## All Decisions Locked
- Name: LogRaven / lograven.io / Docker: lograven:v1.0
- Docker delivery model, no hosted SaaS for v1
- AI: google-genai (gemini-2.5-flash) — NOT anthropic, NOT google-generativeai
- bcrypt pinned to 4.2.1 — do not upgrade until passlib is replaced
- Celery task_always_eager=True for dev (no Redis needed)
- Local storage for dev, S3 backend stubs ready for production
- PyArmor + hardware-bound license for Docker protection
- No admin panel in v1
- Frontend: Vite + React 18 + TypeScript + Tailwind + Zustand + React Query

## What Is NOT Done Yet (Remaining)
- license.py: full HMAC validation (currently bypass_dev=True)
- Rate limiting on auth endpoints
- Full structured JSON logging (currently basic stream logger)
- Audit log retention cleanup job
- Docker image build (docker-compose + Dockerfile)
- PyArmor obfuscation pipeline
- Frontend: npm deps must be installed (npm install in frontend/)
- vite-env.d.ts missing — worked around via /// <reference in main.tsx

## Open Questions
None. All decisions made.


## Status
Full backend pipeline operational end-to-end:
parse → run_rules → correlate → enforce_ceiling → Gemini AI → MITRE enrich → save Report + Findings → complete

## Environment (Windows, No Docker)
- OS: Windows 10, PowerShell
- Python: 3.14 at backend/venv/
- PostgreSQL: localhost:5432/lograven (password: root)
- Redis: localhost:6379 (NOT needed — Celery task_always_eager=True)
- Start server: cd backend && uvicorn app.main:app --reload --port 8000
- Dev setup script: .\scripts\windows_setup.ps1
- DB utility: python scripts/db.py check|tables|migrations|drop
- NOTE: bcrypt pinned to 4.2.1 (passlib incompatible with bcrypt 5.x)
- GEMINI_API_KEY set in .env and working
- enterprise-attack.json downloaded to backend/app/data/ (35.7 MB)

## All Completed (Months 1–3)

### Foundation + Auth (Month 1)
- All 6 DB tables, Alembic migrations applied
- JWT auth: register, login, refresh, /auth/me
- dependencies.py, main.py, config.py, license.py all working

### Investigation CRUD + File Upload (Month 1 Week 3)
- Full CRUD: POST/GET/DELETE /api/v1/investigations
- File upload: POST /api/v1/investigations/{id}/files
- File delete: DELETE /api/v1/investigations/{id}/files/{file_id}
- Analyze trigger: POST /api/v1/investigations/{id}/analyze
- Status polling: GET /api/v1/investigations/{id}/status
- Report endpoint: GET /api/v1/investigations/{id}/report

### Parsers (Month 2)
- windows_event (evtx + CSV), syslog, cloudtrail, nginx
- detector.py: two-phase log type detection
- NormalizedEvent dataclass + normalize_entity()
- Celery pipeline scaffold with task_always_eager=True

### Rule Engine + Correlation + AI (Month 3)
- rules/engine.py: 4 rules (critical brute force, high lateral movement,
  high sensitive action, 5s deduplication window)
- correlation/entity_extractor.py: extract_entities()
- correlation/chain_builder.py: build_chains() 5-min sliding window
- correlation/engine.py: correlate() orchestration
- ai/cost_limiter.py: enforce_ceiling() free/pro/team tiers
- ai/prompts/: base, windows, syslog, cloudtrail, nginx, correlation
- ai/chunker.py: split_events() with overlap, merge_findings() dedup
- ai/cloud/engine.py: Gemini 2.5 Flash via google-genai
  3-attempt backoff, graceful skip if API key missing
- ai/router.py: route_analysis() dispatch by log_type
- reports/mitre_mapper.py: enrich_all(), get_coverage_matrix()
  Lazy load enterprise-attack.json, graceful skip if missing
- process_investigation.py: fully wired end-to-end pipeline
- Report + Finding rows saved to DB after AI analysis
- GET /api/v1/investigations/{id}/report returns full report + findings

## All Decisions Locked
- Name: LogRaven / lograven.io / Docker: lograven:v1.0
- Docker delivery model, no hosted SaaS for v1
- AI: google-genai (gemini-2.5-flash) — NOT anthropic, NOT google-generativeai
- bcrypt pinned to 4.2.1 — do not upgrade until passlib is replaced
- Celery task_always_eager=True for dev (no Redis needed)
- Local storage for dev, S3 backend stubs ready for production
- PyArmor + hardware-bound license for Docker protection
- No admin panel in v1

## What Is NOT Done Yet
- PDF report generation (Month 4)
- schemas/report.py: Pydantic response models for report/findings
- api/reports/routes.py: dedicated reports router (GET report, download PDF)
- reports/pdf_generator.py: WeasyPrint + Jinja2 HTML template
- reports/builder.py: compile findings into PDF context
- license.py: full HMAC validation (currently bypass_dev=True)
- Frontend (not started)
- Rate limiting on auth endpoints
- Docker image build

## Next Session — Month 4 (PDF Reports)

```
@memory-bank/projectbrief.md
@memory-bank/techContext.md
@memory-bank/systemPatterns.md
@memory-bank/activeContext.md
@backend/app/models/report.py
@backend/app/models/finding.py
@backend/app/api/investigations/routes.py
@backend/app/reports/mitre_mapper.py
@backend/app/schemas/investigation.py

Read all memory bank files first.

WHAT IS ALREADY DONE — DO NOT REIMPLEMENT:
- All 6 DB tables, JWT auth, investigation CRUD, file upload
- All 4 parsers, rule engine, correlation engine, cost limiter
- Full Gemini AI pipeline: analyze_events, analyze_chains
- MITRE enrichment: enrich_all() with enterprise-attack.json
- Report and Finding rows saved to DB after every analysis
- GET /api/v1/investigations/{id}/report — returns report + findings JSON
- enterprise-attack.json at backend/app/data/ (35.7 MB, downloaded)
- google-genai installed, GEMINI_API_KEY in .env

TODAY: Implement PDF report generation.

TASK 1 — backend/app/schemas/report.py
  FindingResponse: all Finding model fields as Pydantic model
  ReportResponse: all Report fields + findings: list[FindingResponse]
  Both use from_attributes = True

TASK 2 — backend/app/reports/builder.py
  build_report_context(report, findings) -> dict
  Assembles template context dict for Jinja2:
    investigation_name, created_at, summary,
    severity_counts, mitre_techniques (enriched list),
    correlated_findings (list), single_findings (list),
    findings_by_severity (grouped dict),
    mitre_coverage_matrix (from mitre_mapper.get_coverage_matrix)

TASK 3 — backend/app/reports/pdf_generator.py
  generate_pdf(report, findings, output_path: str) -> str
  Use WeasyPrint + Jinja2.
  Template: backend/app/templates/lograven_report.html
  Style: professional dark-header security report aesthetic
  Sections:
    Cover: LogRaven logo text, investigation name, date, severity summary
    Executive Summary: AI-generated summary text
    Findings table: severity badge, title, MITRE ID, description, remediation
    Correlated findings section (if any)
    MITRE ATT&CK coverage matrix
    IOC appendix
  Return output_path on success.
  On WeasyPrint error: log and re-raise.

TASK 4 — Wire PDF into process_investigation.py
  After saving Report + Findings (existing Step 5i):
  Step 5k — Generate PDF:
    from app.reports.pdf_generator import generate_pdf
    from app.reports.builder import build_report_context
    pdf_key = f"reports/lograven-report-{report.id}.pdf"
    pdf_path = os.path.join(settings.LOCAL_STORAGE_PATH, pdf_key)
    generate_pdf(report, all_findings, pdf_path)
    report.pdf_storage_key = pdf_key
    await db.commit()
    Log: f"LogRaven: PDF report generated at {pdf_path}"

TASK 5 — Add PDF download endpoint to investigations/routes.py
  GET /api/v1/investigations/{id}/report/download
  Fetch report, verify ownership
  Raise 404 if no pdf_storage_key yet
  Stream PDF file using FastAPI FileResponse
  Content-Disposition: attachment; filename=lograven-report-{id}.pdf

RULES:
- Fill existing files only — do not create new files
  EXCEPTION: create backend/app/templates/lograven_report.html
  (this is a template file, not a Python module)
- WeasyPrint for PDF generation (already in requirements.txt)
- Jinja2 for HTML templating (already in requirements.txt)
- All DB operations async, SQLAlchemy 2.0 select() only
```

## Open Questions
None. All decisions made.
