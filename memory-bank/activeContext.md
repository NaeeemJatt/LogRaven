# LogRaven — Active Context

## Current Session Goal
Month 1 Week 3 + Month 2 — Investigation CRUD, File Upload, Parser Pipeline, Celery scaffold

## Status
Parser pipeline complete. Investigation routes complete. All files compile clean.

## Environment (Windows, No Docker)
- OS: Windows 10, PowerShell
- Python: 3.14 at backend/venv/
- PostgreSQL: localhost:5432/lograven (password: root)
- Redis: localhost:6379 (not needed — Celery runs TASK_ALWAYS_EAGER=True for dev)
- Start server: cd backend && uvicorn app.main:app --reload --port 8000
- Dev setup script: .\scripts\windows_setup.ps1
- DB utility: python scripts/db.py check|tables|migrations|drop
- NOTE: bcrypt pinned to 4.2.1 (passlib incompatible with bcrypt 5.x)

## What Was Completed This Session

### Month 1 Week 3 — Investigation CRUD + File Upload
- api/investigations/routes.py: ALL endpoints implemented
  POST /api/v1/investigations (create)
  GET  /api/v1/investigations (list, paginated)
  GET  /api/v1/investigations/{id}
  DELETE /api/v1/investigations/{id}
  POST /api/v1/investigations/{id}/files (multipart upload)
  DELETE /api/v1/investigations/{id}/files/{file_id}
  POST /api/v1/investigations/{id}/analyze (queues pipeline)
  GET  /api/v1/investigations/{id}/status (polling)
- api/router.py: investigations router registered at /api/v1/investigations

### Month 2 — Parsers + Celery Pipeline Scaffold
- parsers/base.py: BaseParser ABC with _stream_lines (UTF-8/latin-1 fallback),
  _safe_parse_timestamp (4 format attempts), _log_skip
- parsers/normalizer.py: NormalizedEvent dataclass + normalize_entity() utility
- parsers/detector.py: two-phase detection (extension + content scan)
  returns: windows_event | syslog | cloudtrail | nginx
  raises: UnknownLogTypeError if nothing matches
- parsers/windows_event.py: WindowsEventParser
  evtx via PyEvtxParser (try/except if not installed), CSV fallback
  EVENT_TYPE_MAP for 8 Windows event IDs
  _detect_patterns: brute_force_candidate, lateral_movement_candidate
- parsers/syslog.py: SyslogParser
  5 pattern auto-selection from first 200 lines (best match wins)
  username/IP extraction from message, event_type classification
  _detect_patterns: brute_force_candidate, privilege_escalation_candidate, account_modification
- parsers/cloudtrail.py: CloudTrailParser
  Handles {"Records":[...]} and single-event JSON
  11 sensitive actions flagged, errorCode -> failed_api_call flag
- parsers/nginx.py: NginxParser
  Combined log regex, injection_attempt detection
  _detect_patterns: scanning (50+ req/60s), 4xx_spike (20+ 4xx)
- tasks/celery_app.py: Celery configured with task_always_eager=True (dev)
- tasks/process_investigation.py: full async pipeline
  status: processing -> per-file: detect+parse -> complete/failed
  asyncio.run(_run_pipeline()) wraps async SQLAlchemy in sync Celery task

## All Decisions Locked
- Name: LogRaven / lograven.io / Docker: lograven:v1.0
- Docker delivery model, no hosted SaaS for v1
- Investigation model with multi-file correlation
- Local storage for dev (not S3)
- PyArmor + hardware-bound license for protection
- No admin panel in v1
- Cloud AI only (Claude claude-sonnet-4-6) for v1
- bcrypt pinned to 4.2.1 — do not upgrade until passlib is replaced
- Celery task_always_eager=True for dev (no Redis needed to test pipeline)
- Project folder: lograven/

## Next Session — Month 3 (Correlation + AI)

```
@memory-bank/projectbrief.md
@memory-bank/techContext.md
@memory-bank/systemPatterns.md
@memory-bank/activeContext.md
@backend/app/parsers/normalizer.py
@backend/app/models/investigation.py
@backend/app/models/investigation_file.py
@backend/app/models/report.py
@backend/app/models/finding.py
@backend/app/tasks/process_investigation.py

Read all memory bank files first.

WHAT IS ALREADY DONE — DO NOT REIMPLEMENT:
- All 6 DB tables exist and all migrations applied
- Full JWT auth: register, login, refresh, /auth/me
- Investigation CRUD: create, list, get, delete
- File upload: POST /api/v1/investigations/{id}/files
- Pipeline scaffold: POST /api/v1/investigations/{id}/analyze triggers
  process_investigation Celery task (TASK_ALWAYS_EAGER=True)
- All 4 parsers working: windows_event, syslog, cloudtrail, nginx
- NormalizedEvent dataclass and normalize_entity() utility

TODAY: Implement the rule engine and correlation engine scaffolds,
then wire them into the pipeline.

TASK 1 — backend/app/rules/engine.py
  run_rules(events: list[NormalizedEvent]) -> list[NormalizedEvent]
  Apply deterministic rules before AI (reduces AI token cost 60-80%):
  - Mark severity_hint="critical" if brute_force_candidate + >20 events
  - Mark severity_hint="high" if lateral_movement_candidate
  - Mark severity_hint="high" if sensitive_action (CloudTrail)
  - Deduplicate identical raw_messages within 5s windows
  Return enriched event list.

TASK 2 — backend/app/correlation/entity_extractor.py
  extract_entities(events: list[NormalizedEvent]) -> dict
  Returns: {"ips": set, "users": set, "hosts": set}
  Normalize with normalize_entity() from parsers/normalizer.py

TASK 3 — backend/app/correlation/chain_builder.py
  build_chains(events: list[NormalizedEvent]) -> list[dict]
  Group related events into attack chains:
  - 5-minute sliding window
  - Same IP or same username across different source_types
  - Returns list of chain dicts: {entity, events, span_seconds, source_types}

TASK 4 — backend/app/correlation/engine.py
  correlate(events: list[NormalizedEvent]) -> dict
  Calls entity_extractor + chain_builder
  Returns correlation_summary dict for the AI prompt

TASK 5 — Wire into tasks/process_investigation.py
  After parsing all files, call:
    from app.rules.engine import run_rules
    from app.correlation.engine import correlate
    all_events = run_rules(all_events)
    correlation_summary = correlate(all_events) if len(investigation.files) > 1 else {}
  Log summary stats. Store correlation_summary for AI step (next month).

TASK 6 — backend/app/ai/cost_limiter.py
  enforce_ceiling(events, tier) -> list[NormalizedEvent]
  Tier ceilings from config: AI_CEILING_FREE/PRO/TEAM
  Prioritize: critical > high > medium > informational
  Return top N events by severity.

RULES:
- Fill existing files only — do not create new files
- SQLAlchemy 2.0 select() only
- All DB operations async
```

## Open Questions
None. All decisions made.
