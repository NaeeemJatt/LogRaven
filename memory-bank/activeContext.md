# LogRaven — Active Context

## Current Session Goal
Month 3 Week 1–2 — Rule engine, correlation engine, cost limiter

## Status
Rule engine, correlation engine, and cost limiter complete and wired into pipeline.
AI integration (Gemini) is the next step.

## Environment (Windows, No Docker)
- OS: Windows 10, PowerShell
- Python: 3.14 at backend/venv/
- PostgreSQL: localhost:5432/lograven (password: root)
- Redis: localhost:6379 (NOT needed — Celery runs TASK_ALWAYS_EAGER=True)
- Start server: cd backend && uvicorn app.main:app --reload --port 8000
- Dev setup script: .\scripts\windows_setup.ps1
- DB utility: python scripts/db.py check|tables|migrations|drop
- NOTE: bcrypt pinned to 4.2.1 (passlib incompatible with bcrypt 5.x)

## What Was Completed This Session

### Rule Engine
- rules/engine.py: run_rules(events) -> list[NormalizedEvent]
  Rule 1: severity_hint="critical" if brute_force_candidate + >20 auth_failure events
  Rule 2: severity_hint="high" if lateral_movement_candidate flag
  Rule 3: severity_hint="high" if sensitive_action flag (CloudTrail)
  Rule 4: deduplication — identical raw_message within 5s window gets
          flag "deduplicated" and severity_hint="deduplicated"

### Correlation Engine
- correlation/entity_extractor.py: extract_entities()
  Returns {ips, users, hosts} sets, all normalized via normalize_entity()
- correlation/chain_builder.py: build_chains()
  5-minute sliding window, same IP or username across different source_types
  Returns chains sorted by event_count desc, only cross-source chains kept
- correlation/engine.py: correlate()
  Calls entity_extractor + chain_builder
  Returns {entities, chains, chain_count, top_entity}

### AI Cost Limiter
- ai/cost_limiter.py: enforce_ceiling(events, tier) -> (list, bool)
  free=2000, pro=10000, team=50000 events max
  Priority order: critical > high > medium > informational > deduplicated

### Pipeline Wired (process_investigation.py)
  queued -> processing -> parse all files ->
  run_rules -> correlate -> enforce_ceiling -> status=complete
  (AI step comes next session)

## All Decisions Locked
- Name: LogRaven / lograven.io / Docker: lograven:v1.0
- Docker delivery model, no hosted SaaS for v1
- Investigation model with multi-file correlation
- Local storage for dev (not S3)
- PyArmor + hardware-bound license for protection
- No admin panel in v1
- AI: google-genai (Gemini 2.5 Flash) — NOT anthropic, NOT google-generativeai
- bcrypt pinned to 4.2.1 — do not upgrade until passlib is replaced
- Celery task_always_eager=True for dev (no Redis needed to test pipeline)
- Project folder: lograven/

## What Is NOT Done Yet
- AI integration (Gemini API calls) — next session
- Report and Finding DB records not saved yet
- PDF generation not started
- Frontend not started

## Next Session — AI Integration

Paste this prompt exactly:

```
@memory-bank/projectbrief.md
@memory-bank/techContext.md
@memory-bank/systemPatterns.md
@memory-bank/activeContext.md
@backend/app/parsers/normalizer.py
@backend/app/ai/cost_limiter.py
@backend/app/ai/router.py
@backend/app/ai/chunker.py
@backend/app/ai/cloud/engine.py
@backend/app/ai/prompts/base_prompt.py
@backend/app/ai/prompts/windows_prompt.py
@backend/app/ai/prompts/syslog_prompt.py
@backend/app/ai/prompts/cloudtrail_prompt.py
@backend/app/ai/prompts/nginx_prompt.py
@backend/app/ai/prompts/correlation_prompt.py
@backend/app/reports/mitre_mapper.py
@backend/app/models/report.py
@backend/app/models/finding.py
@backend/app/tasks/process_investigation.py

Read all memory bank files first.

WHAT IS ALREADY DONE — DO NOT REIMPLEMENT:
- All 6 database tables, JWT auth, investigation CRUD, file upload
- All 4 parsers: windows_event, syslog, cloudtrail, nginx
- Rule engine: run_rules() in app/rules/engine.py
- Correlation engine: correlate() in app/correlation/engine.py
- Cost limiter: enforce_ceiling() in app/ai/cost_limiter.py
- Pipeline in process_investigation.py runs through:
  queued -> processing -> parse all files -> run_rules ->
  correlate -> enforce_ceiling -> status=complete
- Celery task_always_eager=True (no Redis needed in dev)

ENVIRONMENT:
- Windows, no Docker
- PostgreSQL localhost:5432/lograven
- Virtual environment: backend/venv/
- Start server: cd backend && uvicorn app.main:app --reload --port 8000

AI PROVIDER — CRITICAL — READ THIS BEFORE WRITING ANY CODE:
Do NOT use anthropic SDK.
Do NOT use google-generativeai (old deprecated package).
Use ONLY: google-genai (pip install google-genai)

Correct import:
  from google import genai
  from google.genai import types

Client initialization (reads GEMINI_API_KEY from .env automatically):
  client = genai.Client()

Async call pattern:
  response = await client.aio.models.generate_content(
      model="gemini-2.5-flash",
      contents=prompt_text,
      config=types.GenerateContentConfig(
          system_instruction=system_prompt,
          response_mime_type="application/json",
          temperature=0.1,
          max_output_tokens=8192,
      )
  )
  findings = json.loads(response.text)

Add to requirements.txt: google-genai>=1.0.0
Add to .env: GEMINI_API_KEY=your-key-from-aistudio.google.com

TODAY: Implement the complete AI analysis layer and wire it
into the pipeline. Fill in existing files only.
Do not create new files.
[... full AI task prompt follows ...]
```

## Open Questions
None. All decisions made.
