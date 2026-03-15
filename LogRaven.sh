#!/usr/bin/env bash
# =============================================================================
# LogRaven — Project Scaffold Script
# Run this script once to create the complete project structure.
# Usage: chmod +x scaffold.sh && ./scaffold.sh
# =============================================================================

set -e

PROJECT="lograven"
echo ""
echo "=============================================="
echo "  LogRaven — Creating Project Structure"
echo "=============================================="
echo ""

# =============================================================================
# ROOT
# =============================================================================
mkdir -p "$PROJECT"
cd "$PROJECT"

# Root files
cat > .cursorrules << 'EOF'
# LogRaven — Cursor AI Rules
# Read memory-bank/ files at the start of every session.

PROJECT=LogRaven
STACK=FastAPI + Python 3.11 + SQLAlchemy 2.0 + Celery + Redis + PostgreSQL + React 18 + TypeScript

RULES:
- SQLAlchemy 2.0 select() ONLY — never session.query()
- Pydantic v2 syntax everywhere
- Always async/await in FastAPI routes
- Never load full log file into memory — stream always
- Rule engine FIRST, AI SECOND — AI writes narrative, not detections
- Storage: always use app/utils/storage.py abstraction — never direct file ops
- License validated at main.py startup BEFORE anything else initializes
- pyevtx-rs (pip install evtx) — NOT python-evtx (440x slower)
- mitreattack-python loaded ONCE at module startup — not per request
- Never put business logic in route handlers — use services layer
- JWT access tokens: 15 min expiry. Refresh tokens: 7 days
EOF

cat > .env.example << 'EOF'
# ── LogRaven Environment Variables ──────────────────────────────────────────

# Storage backend: "local" for development, "s3" for production
STORAGE_BACKEND=local
LOCAL_STORAGE_PATH=./local

# Database
DATABASE_URL=postgresql://postgres:lgrpass@lograven-db:5432/lograven

# Redis
REDIS_URL=redis://lograven-redis:6379

# AI — Claude API (client provides their own key)
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Auth
JWT_SECRET_KEY=change-this-to-a-random-secret-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# License (set by client)
LICENSE_KEY=provided-by-lograven-vendor

# S3 (only needed when STORAGE_BACKEND=s3)
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
# AWS_REGION=eu-west-1
# S3_BUCKET_NAME=lograven-prod

# OpenAI fallback (optional)
# OPENAI_API_KEY=
EOF

cat > .gitignore << 'EOF'
# LogRaven .gitignore

# Local storage — never commit uploads or reports
local/uploads/
local/reports/
local/temp/
local/

# Environment
.env
*.env

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
.venv/
env/
*.egg-info/
dist/
build/
.pytest_cache/
.coverage
htmlcov/

# Node
node_modules/
dist/
.next/
.nuxt/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Secrets
*.pem
*.key
EOF

cat > docker-compose.yml << 'EOF'
# LogRaven — Development Docker Compose
# Uses local storage — no AWS required

version: '3.9'

services:
  lograven:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    container_name: lograven-app
    ports:
      - "8000:8000"
    environment:
      - LICENSE_KEY=${LICENSE_KEY:-dev-license-bypass}
      - DATABASE_URL=postgresql://postgres:lgrpass@lograven-db:5432/lograven
      - REDIS_URL=redis://lograven-redis:6379
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - STORAGE_BACKEND=local
      - JWT_SECRET_KEY=${JWT_SECRET_KEY:-dev-secret-change-in-prod}
    volumes:
      - ./backend:/app
      - ./local:/app/local
    depends_on:
      - lograven-db
      - lograven-redis
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  lograven-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    container_name: lograven-worker
    environment:
      - LICENSE_KEY=${LICENSE_KEY:-dev-license-bypass}
      - DATABASE_URL=postgresql://postgres:lgrpass@lograven-db:5432/lograven
      - REDIS_URL=redis://lograven-redis:6379
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - STORAGE_BACKEND=local
    volumes:
      - ./backend:/app
      - ./local:/app/local
    depends_on:
      - lograven-db
      - lograven-redis
    command: celery -A app.tasks.celery_app worker --loglevel=info

  lograven-db:
    image: postgres:15-alpine
    container_name: lograven-db
    environment:
      - POSTGRES_PASSWORD=lgrpass
      - POSTGRES_DB=lograven
      - POSTGRES_USER=postgres
    volumes:
      - lograven_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  lograven-redis:
    image: redis:7-alpine
    container_name: lograven-redis
    ports:
      - "6379:6379"

volumes:
  lograven_data:
EOF

cat > docker-compose.client.yml << 'EOF'
# LogRaven — Client Delivery Docker Compose
# This is the file you send to clients alongside .env template

version: '3.9'

services:
  lograven:
    image: lograven:v1.0
    container_name: lograven-app
    ports:
      - "8000:8000"
    environment:
      - LICENSE_KEY=${LICENSE_KEY}
      - DATABASE_URL=postgresql://postgres:lgrpass@lograven-db:5432/lograven
      - REDIS_URL=redis://lograven-redis:6379
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - STORAGE_BACKEND=local
    volumes:
      - ./data/uploads:/app/local/uploads
      - ./data/reports:/app/local/reports
    depends_on:
      - lograven-db
      - lograven-redis

  lograven-worker:
    image: lograven:v1.0
    container_name: lograven-worker
    command: celery -A app.tasks.celery_app worker --loglevel=info
    environment:
      - LICENSE_KEY=${LICENSE_KEY}
      - DATABASE_URL=postgresql://postgres:lgrpass@lograven-db:5432/lograven
      - REDIS_URL=redis://lograven-redis:6379
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - STORAGE_BACKEND=local
    volumes:
      - ./data/uploads:/app/local/uploads
      - ./data/reports:/app/local/reports
    depends_on:
      - lograven-db
      - lograven-redis

  lograven-db:
    image: postgres:15-alpine
    container_name: lograven-db
    environment:
      - POSTGRES_PASSWORD=lgrpass
      - POSTGRES_DB=lograven
    volumes:
      - lograven_data:/var/lib/postgresql/data

  lograven-redis:
    image: redis:7-alpine
    container_name: lograven-redis

volumes:
  lograven_data:
EOF

cat > lograven-license-generator.py << 'EOF'
#!/usr/bin/env python3
"""
LogRaven License Generator
--------------------------
Run this script on YOUR machine only.
NEVER include this file in the Docker image.

Usage:
    1. Ask client to run the fingerprint command below and send you the output.
    2. Run: python lograven-license-generator.py <client_id> <fingerprint> <expiry>
    3. Send the generated LICENSE_KEY to the client.

Client fingerprint command (client runs this):
    python -c "import hashlib,uuid,os; m=hex(uuid.getnode()); h=os.uname().nodename; print(hashlib.sha256(f'{m}:{h}'.encode()).hexdigest()[:32])"
"""

import hmac
import hashlib
import base64
import sys
from datetime import date, timedelta

# CRITICAL: Must match the SECRET_SALT in app/license.py inside the Docker image
SECRET_SALT = "lograven-salt-embedded-in-binary-2026"


def generate_license(client_id: str, fingerprint: str, expiry: str) -> str:
    """Generate a hardware-bound LogRaven license key."""
    msg = f"{client_id}:{fingerprint}:{expiry}"
    sig = hmac.new(SECRET_SALT.encode(), msg.encode(), hashlib.sha256).hexdigest()
    payload = base64.b64encode(f"{client_id}:{expiry}".encode()).decode()
    return f"{payload}.{sig}"


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python lograven-license-generator.py <client_id> <fingerprint> <expiry YYYY-MM-DD>")
        print("Example: python lograven-license-generator.py acme-corp abc123def456 2027-03-15")
        sys.exit(1)

    client_id   = sys.argv[1]
    fingerprint = sys.argv[2]
    expiry      = sys.argv[3]

    key = generate_license(client_id, fingerprint, expiry)
    print(f"\nLogRaven License Key for {client_id}:")
    print(f"  {key}")
    print(f"\nExpiry: {expiry}")
    print(f"Client: {client_id}")
    print(f"\nSend this LICENSE_KEY value to the client for their .env file.")
EOF

cat > MASTER_SPEC.md << 'EOF'
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
EOF

cat > PROGRESS.md << 'EOF'
# LogRaven — Build Progress

## Status
Phase: Project scaffold created. Month 1 Week 1 starting.

## What Is Done
- [x] Complete project planning and architecture
- [x] Master document (v3.0)
- [x] Project scaffold script run
- [x] Folder structure created

## What Is NOT Done
- [ ] Database models
- [ ] Alembic migrations
- [ ] JWT auth endpoints
- [ ] LocalStorageBackend
- [ ] Investigation API
- [ ] Parsers
- [ ] Correlation engine
- [ ] AI integration
- [ ] Report builder + PDF
- [ ] License system
- [ ] Frontend

## Current Session Goal
[Fill in before each Cursor session]

## Last Session
[Date and what was completed]

## Next Action
Start Month 1 Week 1: Database models — run Cursor Prompt 1 from master doc.
EOF

cat > README.md << 'EOF'
# LogRaven

**Watch your logs. Find the threat.**

LogRaven is a security investigation platform delivered as a licensed Docker image.
Upload log files, correlate events across sources, get a MITRE ATT&CK mapped PDF report.

## Quick Start (Development)

```bash
cp .env.example .env
# Fill in ANTHROPIC_API_KEY in .env
docker compose up -d
# Open http://localhost:8000
```

## For Clients
See docker-compose.client.yml and .env.example

## Docs
See MASTER_SPEC.md and lograven_master_v3.docx
EOF

# =============================================================================
# LOCAL STORAGE (gitignored)
# =============================================================================
mkdir -p local/uploads
mkdir -p local/reports
mkdir -p local/temp
touch local/.gitkeep

# =============================================================================
# TEST DATA PLACEHOLDER
# =============================================================================
mkdir -p test-data
cat > test-data/README.md << 'EOF'
# LogRaven Test Data

Clone real Windows attack EVTX samples here for parser testing:

```bash
git clone https://github.com/sbousseaden/EVTX-ATTACK-SAMPLES .
```

These files map Windows Event Log samples to MITRE ATT&CK techniques.
Use them to validate parsers before touching any client logs.
EOF

# =============================================================================
# MEMORY BANK
# =============================================================================
mkdir -p memory-bank

cat > memory-bank/projectbrief.md << 'EOF'
# LogRaven — Project Brief

## What It Is
LogRaven is a security investigation platform delivered as a
licensed Docker image. Users upload 1+ log files into a named
investigation. LogRaven parses them, correlates events across
sources, runs AI analysis using Claude, maps findings to MITRE
ATT&CK, and generates a PDF report named lograven-report-{uuid}.pdf.
Under 3 minutes per investigation.

## Brand
Name:     LogRaven
Domain:   lograven.io
Tagline:  Watch your logs. Find the threat.
Docker:   lograven:v1.0
Project:  lograven/

## Delivery Model
Docker image. Client runs on their own machine.
Logs never leave client premises.
Client provides their own ANTHROPIC_API_KEY.
Revenue: per-deployment license fees.

## Target Customer
Freelance pentesters, SOC analysts, DFIR consultants, MSSPs.
NOT SMB IT admins.

## Core Feature
Multi-file correlation: upload endpoint + firewall + CloudTrail together.
Same entity (IP/user/host) across sources in same 5-minute window = correlated finding.
Single file always works. More files = better correlation.

## Phase 1 Log Types
Windows Endpoint (EVTX via pyevtx-rs)
Linux Syslog / auth.log
AWS CloudTrail JSON
Nginx / Apache access logs
EOF

cat > memory-bank/techContext.md << 'EOF'
# LogRaven — Technical Context

## Stack
Backend:    FastAPI 0.111, Python 3.11, SQLAlchemy 2.0, Alembic 1.13
Queue:      Celery 5.3, Redis 7.2
Database:   PostgreSQL 15
Parsers:    pyevtx-rs (pip install evtx), mitreattack-python
AI:         Claude claude-sonnet-4-6 via anthropic SDK — cloud only v1
PDF:        WeasyPrint 62 + Jinja2 template: lograven_report.html
Storage:    LocalStorageBackend (dev) / S3StorageBackend (prod)
Frontend:   React 18, TypeScript 5.4, Vite 5.2, Tailwind 3.4, React Query 5
Protection: PyArmor obfuscation + hardware-bound license keys

## Critical Rules — Never Violate
- SQLAlchemy 2.0 select() ONLY — never session.query()
- Pydantic v2 syntax everywhere
- Always async/await in FastAPI routes
- Never load full log file into memory — stream always
- Rule engine FIRST, AI SECOND — AI writes narrative, not detections
- Storage: always use app/utils/storage.py abstraction
- License validated at main.py startup BEFORE anything else
- pyevtx-rs (pip install evtx) — NOT python-evtx (440x slower)
- mitreattack-python loaded ONCE at module startup — not per request

## Key GitHub Resources
- pyevtx-rs:          github.com/omerbenamram/pyevtx-rs (440x faster)
- mitreattack-python: github.com/mitre-attack/mitreattack-python
- Test data:          github.com/sbousseaden/EVTX-ATTACK-SAMPLES
- Scaffold:           vstorm-co/full-stack-fastapi-nextjs-llm-template
EOF

cat > memory-bank/systemPatterns.md << 'EOF'
# LogRaven — System Patterns

## All Decisions Final
1. Investigation model — named container for 1+ log files
2. Multi-file correlation engine — entity extraction + 5-min window chain building
3. Storage abstraction — LocalStorageBackend dev, S3StorageBackend prod
4. Docker delivery — no hosted SaaS for v1
5. Hardware-bound license keys + PyArmor obfuscation
6. Cloud AI only for v1 — local AI is Phase 2 Enterprise feature
7. Rule engine pre-filter reduces AI event count 60-80%
8. Hard AI cost ceiling per tier: free 2k, pro 10k, team 50k events
9. No admin panel in v1

## LogRaven Data Flow
Create investigation -> upload files with source type tags
-> click Run Analysis -> FastAPI enqueues Celery task
-> Worker: parse all files (pyevtx-rs / multi-pattern / JSON / regex)
-> Rule engine flags events
-> Correlation engine: entity extraction + cross-source chain building
-> Claude AI analysis (cost ceiling enforced)
-> mitreattack-python enriches technique IDs
-> WeasyPrint renders lograven_report.html to PDF
-> lograven-report-{uuid}.pdf saved to local/reports/
-> frontend polling detects complete -> Report page

## Layer Rules
Routes:      HTTP only — validate, call service, return response
Services:    Business logic — no raw DB in routes
Models:      Tables only — no business methods
Parsers:     File parsing only — no DB, no AI calls
Correlation: Event analysis only — no DB writes
AI:          Analysis only — input events, output JSON findings
Storage:     File I/O only — always via StorageBackend abstraction
Tasks:       Pipeline orchestration only — calls other layers
EOF

cat > memory-bank/activeContext.md << 'EOF'
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
EOF

cat > memory-bank/productContext.md << 'EOF'
# LogRaven — Product Context

## Why LogRaven Exists
Security consultants, pentesters, and SOC analysts spend hours manually
analyzing log files after an incident or engagement. There is no simple tool
that takes raw log files, correlates them across sources, and produces a
professional PDF report without requiring SIEM infrastructure.

LogRaven solves this with a Docker image that runs locally, processes logs
privately, and produces a consultant-quality deliverable in under 3 minutes.

## The Name
Raven from Norse mythology: Odin's all-seeing observers Huginn (Thought) and
Muninn (Memory), who flew across the world and returned with intelligence.
LogRaven watches your logs and returns with findings.

## Positioning
Say: "LogRaven turns your log files into a security incident report in 3 minutes"
Not: "AI-powered log analysis platform"
Not: "Affordable SIEM alternative"
People buy deliverables. The PDF report is the product.

## Monetization
Solo Analyst: $299 one-time
Team (5):     $799 one-time
Renewal:      $149/year
Per-Engagement: $75/month
Freelance delivery: $30-75/report (you run it, deliver PDF to client)
EOF

cat > memory-bank/progress.md << 'EOF'
# LogRaven — Detailed Progress Log

## Month 1 Week 1 — Foundation
Status: NOT STARTED

Goals:
- [ ] SQLAlchemy 2.0 models: user, investigation, investigation_file, report, finding, audit
- [ ] Alembic migration files for all 6 models
- [ ] dependencies.py: get_db, get_current_user, require_pro_tier
- [ ] utils/storage.py: StorageBackend ABC + LocalStorageBackend
- [ ] license.py: validate_license + get_machine_fingerprint
- [ ] utils/security.py: JWT + bcrypt functions
- [ ] utils/exceptions.py: custom exception classes
- [ ] auth routes: register, login, refresh
- [ ] main.py: app setup, StaticFiles mount, startup license check

## Month 1 Week 2 — File Pipeline
Status: NOT STARTED

## Month 2 — Parsers
Status: NOT STARTED

## Month 3 — Correlation + AI
Status: NOT STARTED

## Month 4 — Reports + License
Status: NOT STARTED

## Month 5 — Polish
Status: NOT STARTED

## Month 6 — First Sales
Status: NOT STARTED
EOF

# =============================================================================
# SPECS
# =============================================================================
mkdir -p specs

cat > specs/models_schemas.md << 'EOF'
# LogRaven — Models & Schemas Specification

## SQLAlchemy Models (backend/app/models/)

### users
- id: UUID (primary key, default uuid4)
- email: str (unique, indexed, not null)
- password_hash: str (bcrypt, not null, never plain text)
- tier: str (enum: free/pro/team, default "free")
- created_at: datetime (default utcnow)
- updated_at: datetime (onupdate utcnow)
- Relationships: investigations (one-to-many), audit_log (one-to-many)

### investigations
- id: UUID (primary key)
- user_id: UUID (FK to users.id, not null, indexed)
- name: str (not null, e.g. "Acme Corp March 2026 Intrusion")
- status: str (enum: draft/queued/processing/complete/failed, default "draft")
- correlation_enabled: bool (default True)
- time_window_start: datetime (nullable — auto-detected from files)
- time_window_end: datetime (nullable — auto-detected from files)
- created_at: datetime (default utcnow)
- completed_at: datetime (nullable — set when status=complete/failed)
- Relationships: files (one-to-many InvestigationFile), report (one-to-one)

### investigation_files
- id: UUID (primary key)
- investigation_id: UUID (FK to investigations.id, not null, indexed)
- filename: str (original filename, not null)
- source_type: str (enum: windows_endpoint/linux_endpoint/firewall/network/web_server/cloudtrail, not null)
- log_type: str (detected: evtx/syslog/cloudtrail/nginx, nullable — set after detection)
- storage_key: str (path in local storage e.g. uploads/{inv_id}/{uuid}_file.evtx)
- status: str (enum: pending/parsing/parsed/failed, default "pending")
- event_count: int (nullable — set after parsing)
- error_message: str (nullable — set if status=failed)
- uploaded_at: datetime (default utcnow)
- parsed_at: datetime (nullable)

### reports
- id: UUID (primary key)
- investigation_id: UUID (FK to investigations.id, unique, not null)
- user_id: UUID (FK to users.id, not null, indexed)
- summary: text (executive summary paragraph, nullable)
- severity_counts: JSON (e.g. {"critical": 2, "high": 5, "medium": 10, "low": 3, "info": 8})
- correlated_findings: JSON (array of correlated chain finding objects)
- single_source_findings: JSON (array of individual file finding objects)
- mitre_techniques: JSON (array of triggered technique IDs)
- pdf_storage_key: str (path to lograven-report-{uuid}.pdf, nullable)
- created_at: datetime (default utcnow)

### findings
- id: UUID (primary key)
- report_id: UUID (FK to reports.id, not null, indexed)
- severity: str (enum: critical/high/medium/low/informational, not null)
- title: str (short description, not null)
- description: text (plain English explanation, not null)
- mitre_technique_id: str (e.g. T1110.001, nullable)
- mitre_technique_name: str (full name, nullable)
- mitre_tactic: str (tactic name, nullable)
- iocs: JSON (array of IOC strings, default [])
- remediation: str (suggested action, nullable)
- source_files: JSON (array of investigation_file IDs, default [])
- finding_type: str (enum: correlated/single, not null)
- confidence: float (0.0-1.0, default 0.8)
- created_at: datetime (default utcnow)

### audit_log
- id: UUID (primary key)
- user_id: UUID (FK to users.id, nullable — some events are pre-auth)
- action: str (enum: login/register/upload/report_view/download/failed_login, not null)
- ip_address: str (nullable)
- user_agent: str (nullable)
- metadata: JSON (extra context, default {})
- created_at: datetime (default utcnow)
- NOTE: insert-only, never updated or deleted, 1-year retention

## Pydantic Schemas (backend/app/schemas/)

### user.py
- UserCreate: email (EmailStr), password (str min 8 chars)
- UserResponse: id, email, tier, created_at
- UserLogin: email, password
- TokenResponse: access_token, refresh_token, token_type="bearer"

### investigation.py
- InvestigationCreate: name (str, 1-200 chars)
- InvestigationFileResponse: id, filename, source_type, log_type, status, event_count
- InvestigationResponse: id, name, status, correlation_enabled, files (list), created_at
- InvestigationStatusResponse: id, status, progress_stage, files (list with status)

### report.py
- FindingSchema: severity, title, description, mitre_technique_id, iocs, remediation, finding_type, source_files
- ReportResponse: id, investigation_id, summary, severity_counts, correlated_findings, single_source_findings, mitre_techniques, created_at
- DownloadResponse: download_url (str), expires_in (int seconds)

### common.py
- ErrorResponse: error (str), code (str), detail (str)
- HealthResponse: status (str), db (str), redis (str), claude_api (str)
EOF

cat > specs/api_routes.md << 'EOF'
# LogRaven — API Routes Specification

## Auth Routes (prefix: /auth)
POST /auth/register
  Request:  UserCreate {email, password}
  Response: TokenResponse {access_token, refresh_token, token_type}
  Errors:   400 email already registered

POST /auth/login
  Request:  UserLogin {email, password}
  Response: TokenResponse
  Errors:   401 invalid credentials

POST /auth/refresh
  Request:  {refresh_token: str}
  Response: {access_token: str, token_type: "bearer"}
  Errors:   401 invalid or expired refresh token

## User Routes (prefix: /user, requires JWT)
GET /user/me
  Response: UserResponse {id, email, tier, created_at}

## Investigation Routes (prefix: /api/v1/investigations, requires JWT)
POST /api/v1/investigations
  Request:  InvestigationCreate {name}
  Response: InvestigationResponse (status=draft, files=[])

GET /api/v1/investigations
  Query:    page (int default 1), limit (int default 20)
  Response: {items: List[InvestigationResponse], total: int}

GET /api/v1/investigations/{investigation_id}
  Response: InvestigationResponse with file list

POST /api/v1/investigations/{investigation_id}/files
  Request:  multipart/form-data — file (UploadFile), source_type (str)
  Response: InvestigationFileResponse
  Validates: file extension in whitelist, MIME type, size limit by tier
  source_type must be: windows_endpoint/linux_endpoint/firewall/network/web_server/cloudtrail

DELETE /api/v1/investigations/{investigation_id}/files/{file_id}
  Response: 204 No Content
  Constraint: only allowed when investigation status=draft

POST /api/v1/investigations/{investigation_id}/analyze
  Validates: at least 1 file uploaded, status=draft
  Side effect: sets status=queued, enqueues Celery task
  Response: {job_id: str, status: "queued"}

GET /api/v1/investigations/{investigation_id}/status
  Response: InvestigationStatusResponse {id, status, progress_stage, files}
  progress_stage: one of: queued/parsing/rule_engine/correlation/ai_analysis/building_report/generating_pdf/complete/failed

## Report Routes (prefix: /api/v1/reports, requires JWT)
GET /api/v1/reports/{report_id}
  Response: ReportResponse (full findings)

GET /api/v1/reports/{report_id}/download
  Response: DownloadResponse {download_url, expires_in: 86400}
  URL format (dev): http://localhost:8000/files/reports/{investigation_id}/lograven-report-{uuid}.pdf

## Health Route
GET /health
  Response: HealthResponse {status, db, redis, claude_api}
  No auth required
EOF

cat > specs/parsers.md << 'EOF'
# LogRaven — Parsers Specification

## NormalizedEvent (normalizer.py)
All parsers output this standard schema regardless of source format.

Fields:
- timestamp: datetime (UTC ISO 8601, not null)
- source_type: str (which parser produced it)
- hostname: str | None
- username: str | None (normalized: lowercase, strip whitespace)
- source_ip: str | None (normalized: strip whitespace)
- destination_ip: str | None
- event_type: str (auth_success/auth_failure/sudo/process_exec/network/api_call/other)
- event_id: str | None (Windows EventID, CloudTrail eventName, etc.)
- raw_message: str (original log line, truncated to 500 chars)
- flags: List[str] (brute_force_candidate/privilege_escalation_candidate/etc.)
- severity_hint: str (informational/low/medium/high/critical)

## BaseParser (base.py)
Abstract class. All parsers inherit from this.
Required method: parse(file_path: str) -> List[NormalizedEvent]
Shared utility: _stream_lines(file_path) — UTF-8 with latin-1 fallback, yields lines
Shared utility: _safe_parse_timestamp(raw) — tries multiple formats, returns datetime or None
Shared utility: _log_skip(line, reason) — logs skipped lines as DEBUG, never raises

## windows_event.py
Library: from evtx import PyEvtxParser (pip install evtx — pyevtx-rs bindings)
Input: .evtx binary files or Windows Event CSV exports
EventID map:
  4625 -> auth_failure    4624 -> auth_success    4648 -> explicit_credential
  4720 -> account_created 4688 -> process_exec     4698 -> scheduled_task_create
  4702 -> scheduled_task_modify                     4732 -> group_member_add
Brute force flag: 5+ EventID 4625 from same IP within 60 seconds
Lateral movement flag: EventID 4648 targeting multiple different hostnames

## syslog.py
Multi-pattern approach: test 5 regex patterns against first 200 lines, use best match
Pattern 1: RFC3164  — "MMM DD HH:MM:SS hostname process[pid]: message"
Pattern 2: ISO8601  — "YYYY-MM-DDTHH:MM:SS hostname process[pid]: message"
Pattern 3: Custom1  — timestamp with timezone
Pattern 4: Custom2  — systemd journal format
Pattern 5: Minimal  — any line with sshd/sudo/PAM keyword
AI fallback: if no pattern matches >80%, send 50 sample lines to Claude for format detection
Extract: username from PAM/sshd message patterns, source_ip from "from X.X.X.X" patterns
Flags: brute_force (5+ auth_failure same IP/60s), privilege_escalation (sudo), account_modification

## cloudtrail.py
Input: CloudTrail JSON files (Records array or single event JSON)
Load entire JSON (CloudTrail files typically <20MB)
Iterate Records array, normalize each event
Extract: eventTime, eventSource, eventName, sourceIPAddress, userIdentity
Flag sensitive actions: IAM policy changes, security group mods, root usage, access key creation
Flag failed API calls: any event with errorCode field populated

## nginx.py
Combined log format: 'IP - - [datetime] "METHOD /path HTTP/1.1" status bytes "referer" "ua"'
Also handles Apache combined log format (identical structure)
Rate calculation: count requests per IP per 60-second window
Flags: scanning (50+ requests/IP/60s), 4xx_spike (20+ errors/IP), injection_attempt (SQL/path traversal in URL)
EOF

cat > specs/ai_layer.md << 'EOF'
# LogRaven — AI Layer Specification

## ai/router.py
Route all AI analysis. Cloud only for v1.
analyze(events_by_source, correlated_chains, user_tier) -> AnalysisResult
  1. Apply cost ceiling via cost_limiter.py
  2. Build separate prompts for correlated chains and single-source events
  3. Call cloud/engine.py
  4. On failure: try openai_engine.py fallback
  5. Return AnalysisResult

## ai/chunker.py
split_events(events, chunk_size=2000, overlap=50) -> List[List[NormalizedEvent]]
  Overlap of 50 events prevents missing cross-chunk patterns.
merge_results(results) -> List[Finding]
  Deduplicate using hash(event_type + source_ip + mitre_technique_id)
  On collision: keep finding with higher confidence score

## ai/cost_limiter.py
enforce_ceiling(events, user_tier) -> List[NormalizedEvent]
  Limits: free=2000, pro=10000, team=50000
  Selection priority: flagged before unflagged, critical before low
  If ceiling hit: log warning, note in report that X events were rule-only

## ai/cloud/engine.py (Claude claude-sonnet-4-6)
Before sending: strip PII from raw_message (replace internal hostnames with [HOST])
Prompt structure: system prompt (SOC analyst persona) + structured events JSON
Output: strict JSON array of finding objects
Retry: 3 attempts with exponential backoff (2s, 4s, 8s)
Log token count per request to cost_tracking table

## ai/cloud/consent.py
verify_consent(user) -> bool
  Cloud AI requires explicit opt-in. Check user settings/tier.
  Raise ConsentNotGrantedError if not granted.

## ai/prompts/base_prompt.py
System prompt defines:
  - Persona: senior SOC analyst, 15 years experience
  - Output format: STRICT JSON array only, no markdown, no commentary
  - Finding schema: {severity, title, description, mitre_technique_id, iocs, remediation}
  - Severity scale: critical/high/medium/low/informational
  - MITRE rule: never hallucinate technique IDs — omit field if unsure
  - Focus: actionable findings, not comprehensive coverage

## ai/prompts/correlation_prompt.py
build_correlation_prompt(chains) -> str
  Each chain includes: entity, entity_type, source_files, events (sorted by timestamp)
  Instruction: "These events share a common entity across multiple log sources.
  Identify the ATT&CK technique explaining ALL of them together.
  Describe the attack timeline in plain English.
  Assign severity based on combined evidence, not individual events."
EOF

cat > specs/frontend_pages.md << 'EOF'
# LogRaven — Frontend Pages Specification

## pages/Landing.tsx
Public page. No auth required.
Sections: Hero (tagline + CTA), How It Works (3 steps), Features, Pricing.
CTA: "Get LogRaven" -> links to Register page.

## pages/Auth/Login.tsx + Register.tsx
Login: email + password form. On success: store tokens, redirect to Dashboard.
Register: email + password + confirm. On success: auto-login, redirect to Dashboard.
Error handling: show API error messages inline.

## pages/Dashboard.tsx
Shows list of all user investigations sorted by created_at desc.
Table columns: name, status badge, file count, severity badge (highest found), date, Actions.
Actions: View, Delete.
Empty state: illustration + "Create your first investigation" button.
Top section: usage stats (uploads used vs plan limit).

## pages/NewInvestigation.tsx
Form: investigation name input.
On submit: POST /api/v1/investigations, redirect to Investigation detail page.

## pages/Investigation.tsx
Shows investigation detail with file upload zone.
FileUploadZone: drag-and-drop or click-to-browse.
Each uploaded file shows: filename, SourceTypeSelector dropdown, size, remove button.
SourceTypeSelector: auto-suggests type from file extension.
Run Analysis button: disabled until at least 1 file uploaded.
On Run Analysis: POST /api/v1/investigations/{id}/analyze, redirect to JobStatus page.

## pages/JobStatus.tsx
Receives investigation_id from navigation state.
Uses useJobStatus hook — polls GET /api/v1/investigations/{id}/status every 3 seconds.
Shows stepped progress bar: Queued -> Parsing -> Rule Engine -> Correlation -> AI Analysis -> Building Report -> Done.
Each step highlights as backend progresses (stored in Redis, returned in status response).
On complete: auto-navigate to /report/{report_id} after 1.5 second delay.
On failed: show error state with retry option.

## pages/Report.tsx
Fetches report with useReport(report_id).
Sections in order:
  1. Header: LogRaven branding, investigation name, date, top severity badge.
  2. Executive summary paragraph.
  3. Severity distribution: SeverityChart pie chart.
  4. Correlated findings (shown first — highest priority): each as CorrelationCard.
  5. Individual file findings: each as FindingCard sorted by severity.
  6. MITRE ATT&CK matrix: MitreMatrix component.
  7. IOC table: IOCTable component.
  8. DownloadButton: calls reports.getDownloadUrl(), opens PDF URL.
EOF

# =============================================================================
# BACKEND
# =============================================================================
mkdir -p backend

cat > backend/Dockerfile.dev << 'EOF'
# LogRaven — Development Dockerfile (no PyArmor obfuscation)
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libfontconfig1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
EOF

cat > backend/Dockerfile << 'EOF'
# LogRaven — Production Dockerfile (with PyArmor obfuscation)
# Stage 1: Obfuscate source with PyArmor
FROM python:3.11-slim as builder

WORKDIR /src
RUN pip install pyarmor
COPY app/ /src/app/
RUN pyarmor gen --recursive -O /dist /src/app

# Stage 2: Runtime image with obfuscated code only
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libfontconfig1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy obfuscated app (no .py source files)
COPY --from=builder /dist /app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

cat > backend/requirements.txt << 'EOF'
# LogRaven — Backend Dependencies (Development)
# NOTE: boto3 is NOT included — add to requirements.prod.txt for S3

# Web framework
fastapi==0.111.0
uvicorn[standard]==0.30.1

# Database
sqlalchemy==2.0.31
alembic==1.13.2
asyncpg==0.29.0
psycopg2-binary==2.9.9

# Validation
pydantic==2.8.2
pydantic-settings==2.3.4
email-validator==2.2.0

# Auth
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
bcrypt==4.1.3
python-multipart==0.0.9

# Task queue
celery==5.3.6
redis==5.0.7
kombu==5.3.4

# EVTX parsing (pyevtx-rs bindings — 440x faster than python-evtx)
evtx==0.8.9

# MITRE ATT&CK
mitreattack-python==5.4.0

# AI
anthropic==0.28.0
openai==1.35.0

# PDF generation
weasyprint==62.3
jinja2==3.1.4

# File I/O
aiofiles==23.2.1

# HTTP client (for health checks)
httpx==0.27.0

# Testing
pytest==8.2.2
pytest-asyncio==0.23.7
httpx==0.27.0

# Logging
structlog==24.2.0
EOF

cat > backend/requirements.prod.txt << 'EOF'
# LogRaven — Production Additional Dependencies
# Include everything from requirements.txt PLUS these:

# AWS S3 (production storage)
boto3==1.34.131

# Code obfuscation (build only)
pyarmor==8.5.9
EOF

cat > backend/alembic.ini << 'EOF'
# LogRaven — Alembic Configuration
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = driver://user:pass@localhost/dbname

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
EOF

# Alembic folder
mkdir -p backend/alembic/versions

cat > backend/alembic/env.py << 'EOF'
# LogRaven — Alembic Environment Configuration
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so Alembic can detect them
from app.models import Base  # noqa: F401

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
EOF

# Alembic migration stubs
for i in "001_create_users" "002_create_investigations" "003_create_investigation_files" "004_create_reports" "005_create_findings" "006_create_audit_log"; do
    cat > "backend/alembic/versions/${i}.py" << MIGEOF
# LogRaven — Migration: ${i}
# Implement this migration in Month 1 Week 1
"""${i//_/ }

Revision ID: ${i:0:3}
Revises:
Create Date: 2026-01-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '${i:0:3}'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # TODO: Implement in Month 1 Week 1
    pass


def downgrade() -> None:
    # TODO: Implement in Month 1 Week 1
    pass
MIGEOF
done

# App package
mkdir -p backend/app

cat > backend/app/__init__.py << 'EOF'
# LogRaven — Application Package
EOF

cat > backend/app/main.py << 'EOF'
# LogRaven — FastAPI Application Entry Point
#
# PURPOSE:
#   Creates and configures the FastAPI application.
#   Registers all API routers with their URL prefixes.
#   Mounts local file storage at /files for development PDF serving.
#   Startup event: validates license before any other initialization.
#   Configures CORS, exception handlers, and middleware.
#
# CRITICAL: validate_license() must be called FIRST in startup event.
#           If license is invalid, SystemExit is raised and app does not start.
#
# TODO Month 1 Week 1: Implement this file.

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(
    title="LogRaven API",
    description="Watch your logs. Find the threat.",
    version="1.0.0",
)

# TODO: Add CORS middleware
# TODO: Add global exception handlers
# TODO: Mount StaticFiles at /files for local/reports/
# TODO: Add startup event that calls validate_license()
# TODO: Register all routers from api/router.py
EOF

cat > backend/app/config.py << 'EOF'
# LogRaven — Application Configuration
#
# PURPOSE:
#   Reads ALL environment variables using Pydantic BaseSettings.
#   Validates types and required values at startup.
#   If any required variable is missing, app refuses to start.
#   Single source of truth for all config — imported everywhere as `settings`.
#
# USAGE:
#   from app.config import settings
#   url = settings.DATABASE_URL
#
# TODO Month 1 Week 1: Implement this file.

from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    # App
    APP_NAME: str = "LogRaven"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Auth
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Storage
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    LOCAL_STORAGE_PATH: str = "./local"

    # AI
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # License
    LICENSE_KEY: str = ""
    LICENSE_BYPASS_DEV: bool = False  # Set True only in development

    # S3 (production only)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "eu-west-1"
    S3_BUCKET_NAME: str = "lograven-prod"

    # AI Cost Ceilings (max events sent to AI per investigation)
    AI_CEILING_FREE: int = 2000
    AI_CEILING_PRO: int = 10000
    AI_CEILING_TEAM: int = 50000

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
EOF

cat > backend/app/dependencies.py << 'EOF'
# LogRaven — FastAPI Dependency Injectors
#
# PURPOSE:
#   Reusable async functions injected into route handlers by FastAPI.
#
# KEY INJECTORS:
#   get_db()           — yields async SQLAlchemy session, always closes after request
#   get_storage()      — returns correct StorageBackend based on config
#   get_current_user() — validates JWT, returns authenticated User object
#   require_pro_tier() — calls get_current_user + checks tier is pro/team
#
# USAGE in routes:
#   async def my_route(db = Depends(get_db), user = Depends(get_current_user)):
#
# TODO Month 1 Week 1: Implement this file.

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# TODO: Implement get_db()
# TODO: Implement get_storage()
# TODO: Implement get_current_user()
# TODO: Implement require_pro_tier()
EOF

cat > backend/app/license.py << 'EOF'
# LogRaven — License Validation
#
# PURPOSE:
#   Called at FastAPI startup event BEFORE anything else initializes.
#   Validates the LICENSE_KEY environment variable against machine fingerprint.
#   Raises SystemExit with clear message if license is invalid or expired.
#   The SECRET_SALT is hardcoded here — it is embedded in the obfuscated Docker
#   image and cannot be read by the client from the running container.
#
# MACHINE FINGERPRINT:
#   SHA256 hash of (MAC address + hostname) — unique per machine.
#   Client runs this to get their fingerprint:
#   python -c "import hashlib,uuid,os; m=hex(uuid.getnode()); h=os.uname().nodename; print(hashlib.sha256(f'{m}:{h}'.encode()).hexdigest()[:32])"
#
# LICENSE KEY FORMAT:
#   base64(client_id:expiry) + "." + HMAC(client_id:fingerprint:expiry)
#
# TODO Month 4 Week 3: Implement this file.

import hashlib
import uuid
import hmac
import base64
import os
from datetime import date

# CRITICAL: Must match lograven-license-generator.py SECRET_SALT
# Never change this value after deployment — existing licenses will break
SECRET_SALT = "lograven-salt-embedded-in-binary-2026"


def get_machine_fingerprint() -> str:
    """Generate a unique fingerprint for the current machine."""
    mac = hex(uuid.getnode())
    hostname = os.uname().nodename
    return hashlib.sha256(f"{mac}:{hostname}".encode()).hexdigest()[:32]


def validate_license(license_key: str, bypass_dev: bool = False) -> bool:
    """
    Validate the LogRaven license key.
    Called at startup — raises SystemExit if invalid.
    """
    if bypass_dev and os.getenv("DEBUG") == "True":
        return True  # Allow dev bypass only when DEBUG=True

    # TODO Month 4 Week 3: Implement full HMAC validation
    # For now in development: accept any non-empty key
    if not license_key:
        raise SystemExit("[LogRaven] No LICENSE_KEY set. Contact vendor.")
    return True
EOF

# API layer
mkdir -p backend/app/api

cat > backend/app/api/__init__.py << 'EOF'
# LogRaven — API Package
EOF

cat > backend/app/api/router.py << 'EOF'
# LogRaven — Master API Router
#
# PURPOSE:
#   Registers all sub-routers with their URL prefixes.
#   This file is imported by main.py once.
#   All route handlers live in their own sub-packages.
#
# TODO Month 1 Week 1: Import and register auth router.
# TODO Month 1 Week 3: Register investigations router.
# TODO Month 4 Week 1: Register reports router.

from fastapi import APIRouter

router = APIRouter()

# TODO: from app.api.auth.routes import router as auth_router
# TODO: router.include_router(auth_router, prefix="/auth", tags=["auth"])
# TODO: from app.api.investigations.routes import router as inv_router
# TODO: router.include_router(inv_router, prefix="/api/v1/investigations", tags=["investigations"])
# TODO: from app.api.reports.routes import router as rep_router
# TODO: router.include_router(rep_router, prefix="/api/v1/reports", tags=["reports"])
# TODO: from app.api.health.routes import router as health_router
# TODO: router.include_router(health_router, tags=["health"])
EOF

# Auth routes
mkdir -p backend/app/api/auth

cat > backend/app/api/auth/__init__.py << 'EOF'
# LogRaven — Auth API Package
EOF

cat > backend/app/api/auth/routes.py << 'EOF'
# LogRaven — Auth Routes
#
# PURPOSE:
#   HTTP route handlers for authentication.
#   All business logic lives in services/auth_service.py.
#   These handlers only: validate input, call service, return response.
#
# ENDPOINTS:
#   POST /auth/register — create account, return JWT token pair
#   POST /auth/login    — authenticate, return JWT token pair
#   POST /auth/refresh  — exchange refresh token for new access token
#
# TODO Month 1 Week 1: Implement this file.

from fastapi import APIRouter

router = APIRouter()

# TODO: Implement register endpoint
# TODO: Implement login endpoint
# TODO: Implement refresh endpoint
EOF

cat > backend/app/api/auth/helpers.py << 'EOF'
# LogRaven — Auth Helper Functions
#
# PURPOSE:
#   JWT creation and validation helpers used by auth routes and dependencies.
#   These wrap the functions in utils/security.py with auth-specific logic.
#
# FUNCTIONS:
#   create_token_pair(user_id, tier) -> TokenResponse
#   verify_token_or_raise(token: str) -> dict (decoded claims)
#
# TODO Month 1 Week 1: Implement this file.
EOF

# Investigations routes
mkdir -p backend/app/api/investigations

cat > backend/app/api/investigations/__init__.py << 'EOF'
# LogRaven — Investigations API Package
EOF

cat > backend/app/api/investigations/routes.py << 'EOF'
# LogRaven — Investigation Routes
#
# PURPOSE:
#   HTTP route handlers for investigation CRUD and file upload.
#   All business logic lives in services/investigation_service.py.
#
# ENDPOINTS:
#   POST   /api/v1/investigations                        — create investigation
#   GET    /api/v1/investigations                        — list user investigations
#   GET    /api/v1/investigations/{id}                   — get investigation detail
#   POST   /api/v1/investigations/{id}/files             — upload file with source_type
#   DELETE /api/v1/investigations/{id}/files/{file_id}   — remove file
#   POST   /api/v1/investigations/{id}/analyze           — start LogRaven analysis
#   GET    /api/v1/investigations/{id}/status            — poll job progress
#
# FILE UPLOAD NOTE:
#   Files must stream to LocalStorageBackend — never load into memory.
#   Storage key format: uploads/{investigation_id}/{uuid}_{filename}
#
# TODO Month 1 Week 3: Implement this file.

from fastapi import APIRouter

router = APIRouter()

# TODO: Implement all investigation endpoints
EOF

cat > backend/app/api/investigations/validators.py << 'EOF'
# LogRaven — File Upload Validators
#
# PURPOSE:
#   Server-side validation for uploaded log files.
#   Client-side validation is UX only — server-side is the security boundary.
#
# VALIDATES:
#   - File extension must be in whitelist: [evtx, csv, log, txt, json]
#   - MIME type must match extension (prevents extension spoofing)
#   - File size must be under tier limit: free=5MB, pro=50MB, team=200MB
#   - source_type must be a valid enum value
#
# RAISES:
#   InvalidFileTypeError (400) if type check fails
#   FileTooLargeError (400) if size exceeds tier limit
#
# TODO Month 1 Week 3: Implement this file.

ALLOWED_EXTENSIONS = {"evtx", "csv", "log", "txt", "json"}

TIER_SIZE_LIMITS = {
    "free": 5 * 1024 * 1024,    # 5MB
    "pro":  50 * 1024 * 1024,   # 50MB
    "team": 200 * 1024 * 1024,  # 200MB
}

VALID_SOURCE_TYPES = {
    "windows_endpoint", "linux_endpoint", "firewall",
    "network", "web_server", "cloudtrail"
}

# TODO: Implement validate_file_upload(file, user) -> None
EOF

# Reports routes
mkdir -p backend/app/api/reports

cat > backend/app/api/reports/__init__.py << 'EOF'
# LogRaven — Reports API Package
EOF

cat > backend/app/api/reports/routes.py << 'EOF'
# LogRaven — Report Routes
#
# PURPOSE:
#   HTTP route handlers for fetching and downloading reports.
#
# ENDPOINTS:
#   GET /api/v1/reports/{report_id}          — full report JSON with all findings
#   GET /api/v1/reports/{report_id}/download — returns URL for PDF download
#
# PDF DOWNLOAD NOTE:
#   In development: returns http://localhost:8000/files/reports/{inv_id}/lograven-report-{uuid}.pdf
#   In production: returns a signed S3 URL valid for 24 hours
#
# TODO Month 4 Week 1: Implement this file.

from fastapi import APIRouter

router = APIRouter()
EOF

cat > backend/app/api/reports/helpers.py << 'EOF'
# LogRaven — Report Response Helpers
#
# PURPOSE:
#   Build API response shapes for reports.
#   Generate download URLs (local static URL or signed S3 URL).
#
# TODO Month 4 Week 1: Implement this file.
EOF

# Health routes
mkdir -p backend/app/api/health

cat > backend/app/api/health/__init__.py << 'EOF'
# LogRaven — Health API Package
EOF

cat > backend/app/api/health/routes.py << 'EOF'
# LogRaven — Health Check Route
#
# PURPOSE:
#   GET /health — no auth required
#   Checks: database connectivity, Redis connectivity, Claude API reachability
#   Returns: {"status": "ok", "db": "ok", "redis": "ok", "claude_api": "ok"}
#   Used by monitoring tools and the client to verify installation.
#
# TODO Month 1 Week 1: Implement basic health check.

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    # TODO: Add real checks for DB, Redis, and Claude API
    return {"status": "ok", "db": "pending", "redis": "pending", "claude_api": "pending"}
EOF

# Models
mkdir -p backend/app/models

cat > backend/app/models/__init__.py << 'EOF'
# LogRaven — Models Package
# Exports Base and all models so Alembic can detect them.
# Import all models here so they are registered with SQLAlchemy metadata.

from app.models.base import Base
from app.models.user import User
from app.models.investigation import Investigation
from app.models.investigation_file import InvestigationFile
from app.models.report import Report
from app.models.finding import Finding
from app.models.audit import AuditLog

__all__ = ["Base", "User", "Investigation", "InvestigationFile", "Report", "Finding", "AuditLog"]
EOF

cat > backend/app/models/base.py << 'EOF'
# LogRaven — SQLAlchemy Declarative Base
# All models inherit from Base.

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
EOF

cat > backend/app/models/user.py << 'EOF'
# LogRaven — User Model
#
# PURPOSE:
#   Represents a LogRaven user account.
#   The `tier` field drives all business logic:
#     - Upload file size limits (free=5MB, pro=50MB, team=200MB)
#     - AI cost ceiling (free=2k, pro=10k, team=50k events)
#     - Report retention period
#
# RELATIONSHIPS:
#   investigations — one-to-many
#   audit_log      — one-to-many
#
# TODO Month 1 Week 1: Implement this model.

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id:            Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email:         Mapped[str]        = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str]        = mapped_column(String(255), nullable=False)
    tier:          Mapped[str]        = mapped_column(String(20), nullable=False, default="free")
    created_at:    Mapped[datetime]   = mapped_column(DateTime, default=datetime.utcnow)
    updated_at:    Mapped[datetime]   = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    # TODO: Add investigations relationship
    # TODO: Add audit_log relationship
EOF

cat > backend/app/models/investigation.py << 'EOF'
# LogRaven — Investigation Model
#
# PURPOSE:
#   An investigation is a named container for one or more log files.
#   This is the core LogRaven unit of work.
#
# STATUS FLOW:
#   draft -> queued -> processing -> complete / failed
#
# CORRELATION:
#   correlation_enabled=True means the correlation engine will run
#   when 2+ files with different source_types are uploaded.
#   Single file investigations always work regardless of this flag.
#
# TODO Month 1 Week 1: Implement this model.

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class Investigation(Base):
    __tablename__ = "investigations"

    id:                  Mapped[uuid.UUID]         = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id:             Mapped[uuid.UUID]         = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name:                Mapped[str]               = mapped_column(String(200), nullable=False)
    status:              Mapped[str]               = mapped_column(String(20), nullable=False, default="draft")
    correlation_enabled: Mapped[bool]              = mapped_column(Boolean, default=True)
    time_window_start:   Mapped[datetime | None]   = mapped_column(DateTime, nullable=True)
    time_window_end:     Mapped[datetime | None]   = mapped_column(DateTime, nullable=True)
    created_at:          Mapped[datetime]          = mapped_column(DateTime, default=datetime.utcnow)
    completed_at:        Mapped[datetime | None]   = mapped_column(DateTime, nullable=True)

    # TODO: Add files relationship (one-to-many InvestigationFile)
    # TODO: Add report relationship (one-to-one)
EOF

cat > backend/app/models/investigation_file.py << 'EOF'
# LogRaven — InvestigationFile Model
#
# PURPOSE:
#   One row per uploaded file in an investigation.
#   Files parse independently — one failure does not block others.
#   The source_type field drives correlation entity extraction.
#
# SOURCE_TYPE VALUES:
#   windows_endpoint | linux_endpoint | firewall | network | web_server | cloudtrail
#
# LOG_TYPE VALUES (auto-detected by detector.py):
#   evtx | syslog | cloudtrail | nginx
#
# STORAGE KEY FORMAT:
#   uploads/{investigation_id}/{uuid}_{original_filename}
#
# TODO Month 1 Week 1: Implement this model.

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class InvestigationFile(Base):
    __tablename__ = "investigation_files"

    id:               Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("investigations.id"), nullable=False, index=True)
    filename:         Mapped[str]             = mapped_column(String(255), nullable=False)
    source_type:      Mapped[str]             = mapped_column(String(50), nullable=False)
    log_type:         Mapped[str | None]      = mapped_column(String(20), nullable=True)
    storage_key:      Mapped[str]             = mapped_column(String(500), nullable=False)
    status:           Mapped[str]             = mapped_column(String(20), nullable=False, default="pending")
    event_count:      Mapped[int | None]      = mapped_column(Integer, nullable=True)
    error_message:    Mapped[str | None]      = mapped_column(Text, nullable=True)
    uploaded_at:      Mapped[datetime]        = mapped_column(DateTime, default=datetime.utcnow)
    parsed_at:        Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
EOF

cat > backend/app/models/report.py << 'EOF'
# LogRaven — Report Model
#
# PURPOSE:
#   Stores the complete output of a LogRaven analysis.
#   JSONB columns allow efficient querying of nested finding data.
#
# TWO FINDING COLUMNS:
#   correlated_findings    — cross-source chains (highest priority findings)
#   single_source_findings — individual file findings (lower priority)
#
# PDF:
#   pdf_storage_key points to lograven-report-{uuid}.pdf in local/reports/
#
# TODO Month 4 Week 1: Implement this model.

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import Base


class Report(Base):
    __tablename__ = "reports"

    id:                      Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id:        Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("investigations.id"), unique=True, nullable=False)
    user_id:                 Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    summary:                 Mapped[str | None]   = mapped_column(Text, nullable=True)
    severity_counts:         Mapped[dict]         = mapped_column(JSONB, default=dict)
    correlated_findings:     Mapped[list]         = mapped_column(JSONB, default=list)
    single_source_findings:  Mapped[list]         = mapped_column(JSONB, default=list)
    mitre_techniques:        Mapped[list]         = mapped_column(JSONB, default=list)
    pdf_storage_key:         Mapped[str | None]   = mapped_column(String(500), nullable=True)
    created_at:              Mapped[datetime]     = mapped_column(DateTime, default=datetime.utcnow)
EOF

cat > backend/app/models/finding.py << 'EOF'
# LogRaven — Finding Model
#
# PURPOSE:
#   One row per individual finding in a report.
#   Storing findings separately enables cross-report analytics.
#
# FINDING_TYPE VALUES:
#   correlated — found by correlation engine (spans multiple source files)
#   single     — found in a single log file
#
# SOURCE_FILES:
#   JSON array of investigation_file IDs that contributed to this finding.
#   For correlated findings: 2+ file IDs.
#   For single findings: 1 file ID.
#
# TODO Month 4 Week 1: Implement this model.

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import Base


class Finding(Base):
    __tablename__ = "findings"

    id:                   Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id:            Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), ForeignKey("reports.id"), nullable=False, index=True)
    severity:             Mapped[str]         = mapped_column(String(20), nullable=False)
    title:                Mapped[str]         = mapped_column(String(300), nullable=False)
    description:          Mapped[str]         = mapped_column(Text, nullable=False)
    mitre_technique_id:   Mapped[str | None]  = mapped_column(String(20), nullable=True)
    mitre_technique_name: Mapped[str | None]  = mapped_column(String(200), nullable=True)
    mitre_tactic:         Mapped[str | None]  = mapped_column(String(100), nullable=True)
    iocs:                 Mapped[list]        = mapped_column(JSONB, default=list)
    remediation:          Mapped[str | None]  = mapped_column(Text, nullable=True)
    source_files:         Mapped[list]        = mapped_column(JSONB, default=list)
    finding_type:         Mapped[str]         = mapped_column(String(20), nullable=False, default="single")
    confidence:           Mapped[float]       = mapped_column(Float, default=0.8)
    created_at:           Mapped[datetime]    = mapped_column(DateTime, default=datetime.utcnow)
EOF

cat > backend/app/models/audit.py << 'EOF'
# LogRaven — AuditLog Model
#
# PURPOSE:
#   Security audit trail for the LogRaven platform.
#   Records every meaningful user action with IP and metadata.
#
# IMPORTANT: Insert-only table.
#   Records are NEVER updated or deleted.
#   1-year retention policy.
#   Used for security investigations and compliance documentation.
#
# ACTION VALUES:
#   login | register | upload | analyze | report_view | download | failed_login
#
# TODO Month 1 Week 1: Implement this model.

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id:         Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id:    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action:     Mapped[str]             = mapped_column(String(50), nullable=False)
    ip_address: Mapped[str | None]      = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None]      = mapped_column(String(500), nullable=True)
    metadata_:  Mapped[dict]            = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime]        = mapped_column(DateTime, default=datetime.utcnow)
EOF

# Schemas
mkdir -p backend/app/schemas

cat > backend/app/schemas/__init__.py << 'EOF'
# LogRaven — Schemas Package
EOF

cat > backend/app/schemas/user.py << 'EOF'
# LogRaven — User Pydantic Schemas
#
# PURPOSE:
#   Defines the shapes of data coming IN (requests) and going OUT (responses).
#   Completely separate from SQLAlchemy models — never expose ORM objects directly.
#
# SCHEMAS:
#   UserCreate      — POST /auth/register request body
#   UserLogin       — POST /auth/login request body
#   UserResponse    — GET /user/me response (never includes password_hash)
#   TokenResponse   — response after register/login/refresh
#
# TODO Month 1 Week 1: Implement this file.

from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str  # min 8 chars — validate in service


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    tier: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
EOF

cat > backend/app/schemas/investigation.py << 'EOF'
# LogRaven — Investigation Pydantic Schemas
#
# PURPOSE:
#   Request/response shapes for investigation and file upload endpoints.
#
# SCHEMAS:
#   InvestigationCreate         — POST /api/v1/investigations
#   InvestigationFileResponse   — file detail in investigation responses
#   InvestigationResponse       — GET /api/v1/investigations/{id}
#   InvestigationStatusResponse — GET /api/v1/investigations/{id}/status
#
# TODO Month 1 Week 3: Implement this file.

from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, List


class InvestigationCreate(BaseModel):
    name: str  # 1-200 chars


class InvestigationFileResponse(BaseModel):
    id: UUID
    filename: str
    source_type: str
    log_type: Optional[str]
    status: str
    event_count: Optional[int]

    class Config:
        from_attributes = True


class InvestigationResponse(BaseModel):
    id: UUID
    name: str
    status: str
    correlation_enabled: bool
    files: List[InvestigationFileResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


class InvestigationStatusResponse(BaseModel):
    id: UUID
    status: str
    progress_stage: Optional[str]  # queued/parsing/rule_engine/correlation/ai_analysis/building_report/complete/failed
    files: List[InvestigationFileResponse] = []
EOF

cat > backend/app/schemas/report.py << 'EOF'
# LogRaven — Report Pydantic Schemas
#
# PURPOSE:
#   Response shapes for report endpoints.
#
# TODO Month 4 Week 1: Implement this file.

from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Any


class FindingSchema(BaseModel):
    severity: str
    title: str
    description: str
    mitre_technique_id: Optional[str]
    mitre_technique_name: Optional[str]
    mitre_tactic: Optional[str]
    iocs: List[str] = []
    remediation: Optional[str]
    finding_type: str  # correlated or single
    source_files: List[str] = []


class ReportResponse(BaseModel):
    id: UUID
    investigation_id: UUID
    summary: Optional[str]
    severity_counts: dict
    correlated_findings: List[Any] = []
    single_source_findings: List[Any] = []
    mitre_techniques: List[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


class DownloadResponse(BaseModel):
    download_url: str
    expires_in: int = 86400  # 24 hours
EOF

cat > backend/app/schemas/common.py << 'EOF'
# LogRaven — Common Pydantic Schemas
#
# PURPOSE:
#   Shared response shapes used across multiple endpoints.

from pydantic import BaseModel
from typing import Optional


class ErrorResponse(BaseModel):
    error: str
    code: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    db: str
    redis: str
    claude_api: str
EOF

# Services
mkdir -p backend/app/services

cat > backend/app/services/__init__.py << 'EOF'
# LogRaven — Services Package
EOF

cat > backend/app/services/auth_service.py << 'EOF'
# LogRaven — Auth Service
#
# PURPOSE:
#   Business logic for user authentication.
#   Route handlers call these functions — no DB access in routes.
#
# FUNCTIONS:
#   register_user(email, password, db) -> TokenResponse
#     - Validate email format (EmailStr handles this)
#     - Check email not already registered (raise 400 if taken)
#     - Hash password with bcrypt (cost factor 12)
#     - Create User record
#     - Generate JWT token pair
#     - Log registration to audit_log
#     - Return TokenResponse
#
#   login_user(email, password, db) -> TokenResponse
#     - Fetch user by email (raise 401 if not found)
#     - Verify password hash (raise 401 if wrong)
#     - Generate JWT token pair
#     - Log login to audit_log
#     - Return TokenResponse
#
#   refresh_token(refresh_token: str, db) -> dict
#     - Decode refresh token (raise 401 if invalid/expired)
#     - Fetch user (raise 401 if not found)
#     - Generate new access token
#     - Return {"access_token": ..., "token_type": "bearer"}
#
# TODO Month 1 Week 1: Implement this file.
EOF

cat > backend/app/services/investigation_service.py << 'EOF'
# LogRaven — Investigation Service
#
# PURPOSE:
#   Business logic for investigation management and file upload.
#
# FUNCTIONS:
#   create_investigation(name, user, db) -> Investigation
#   get_investigation(id, user, db) -> Investigation (raise 404 if not found, 403 if not owner)
#   list_investigations(user, db, page, limit) -> (List[Investigation], total)
#   add_file(investigation_id, file, source_type, user, db, storage) -> InvestigationFile
#     - Stream file to storage (never load into memory)
#     - Storage key: uploads/{investigation_id}/{uuid}_{filename}
#     - Create InvestigationFile record with status=pending
#   remove_file(investigation_id, file_id, user, db) -> None
#     - Only allowed when investigation status=draft
#   start_analysis(investigation_id, user, db) -> str (job_id)
#     - Validate at least 1 file uploaded
#     - Set investigation status=queued
#     - Enqueue Celery task: process_investigation.delay(investigation_id)
#     - Return investigation_id as job_id
#
# TODO Month 1 Week 3: Implement this file.
EOF

cat > backend/app/services/report_service.py << 'EOF'
# LogRaven — Report Service
#
# PURPOSE:
#   Business logic for fetching reports and generating download URLs.
#
# FUNCTIONS:
#   get_report(report_id, user, db) -> Report
#     - Fetch report (raise 404 if not found)
#     - Verify user owns the associated investigation (raise 403 if not)
#
#   get_download_url(report_id, user, db, storage) -> DownloadResponse
#     - Get report's pdf_storage_key
#     - Return storage.get_download_url(pdf_storage_key)
#     - Local dev: http://localhost:8000/files/reports/{inv_id}/lograven-report-{uuid}.pdf
#     - Production: signed S3 URL valid for 24 hours
#
# TODO Month 4 Week 1: Implement this file.
EOF

cat > backend/app/services/notification_service.py << 'EOF'
# LogRaven — Notification Service
#
# PURPOSE:
#   Send email notifications for job completion and failure.
#   Uses AWS SES in production (same dependency as S3).
#   In development: just logs the notification content.
#
# FUNCTIONS:
#   send_job_complete(user, investigation, report) -> None
#     - Send email with summary and download link if job took > 30 seconds
#
#   send_job_failed(user, investigation, error_msg) -> None
#     - Send failure notification with generic user-facing message
#
# TODO Month 5: Implement this file.
EOF

# Parsers
mkdir -p backend/app/parsers

cat > backend/app/parsers/__init__.py << 'EOF'
# LogRaven — Parsers Package
EOF

cat > backend/app/parsers/base.py << 'EOF'
# LogRaven — Abstract Base Parser
#
# PURPOSE:
#   Defines the interface all LogRaven parsers must implement.
#   Provides shared utility methods inherited by all parsers.
#
# REQUIRED METHOD:
#   parse(file_path: str) -> List[NormalizedEvent]
#     Must be implemented by every parser subclass.
#     Must stream the file — never load entirely into memory.
#     Must never raise on malformed individual lines — skip and log warning.
#
# SHARED UTILITIES (inherited by all parsers):
#   _stream_lines(file_path) -> Iterator[str]
#     Streams file line by line. UTF-8 with latin-1 fallback.
#   _safe_parse_timestamp(raw: str) -> datetime | None
#     Tries multiple timestamp formats. Returns None if all fail.
#   _log_skip(line: str, reason: str) -> None
#     Logs skipped lines as DEBUG. Never raises.
#
# TODO Month 2 Week 1: Implement this file.

from abc import ABC, abstractmethod
from typing import Iterator
from app.parsers.normalizer import NormalizedEvent


class BaseParser(ABC):

    @abstractmethod
    def parse(self, file_path: str) -> list[NormalizedEvent]:
        """Parse a log file and return normalized events."""
        pass

    def _stream_lines(self, file_path: str) -> Iterator[str]:
        """Stream file line by line with encoding fallback. Never loads full file."""
        # TODO: Implement UTF-8 with latin-1 fallback
        pass

    def _safe_parse_timestamp(self, raw: str):
        """Try multiple timestamp formats. Return datetime or None."""
        # TODO: Implement multi-format timestamp parsing
        pass

    def _log_skip(self, line: str, reason: str) -> None:
        """Log a skipped line as DEBUG."""
        # TODO: Use structured logger
        pass
EOF

cat > backend/app/parsers/normalizer.py << 'EOF'
# LogRaven — NormalizedEvent Schema
#
# PURPOSE:
#   Defines the single output format all LogRaven parsers produce.
#   This abstraction means the AI layer never sees raw log format differences.
#   All 4 parsers output NormalizedEvent objects regardless of input format.
#
# FIELDS:
#   timestamp     — datetime UTC (required)
#   source_type   — which parser/source produced this event
#   hostname      — machine name (nullable)
#   username      — account name (nullable, normalized: lowercase, stripped)
#   source_ip     — source IP address (nullable, normalized: stripped)
#   destination_ip — destination IP (nullable)
#   event_type    — category: auth_success/auth_failure/sudo/process_exec/network/api_call/other
#   event_id      — format-specific ID (Windows EventID, CloudTrail eventName, etc.)
#   raw_message   — original log line truncated to 500 chars
#   flags         — list of detection flags: brute_force_candidate/privilege_escalation_candidate/etc.
#   severity_hint — preliminary severity from rule engine
#
# TODO Month 2 Week 1: Implement this file.

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class NormalizedEvent:
    timestamp:      datetime
    source_type:    str
    hostname:       Optional[str]   = None
    username:       Optional[str]   = None
    source_ip:      Optional[str]   = None
    destination_ip: Optional[str]   = None
    event_type:     str             = "other"
    event_id:       Optional[str]   = None
    raw_message:    str             = ""
    flags:          list            = field(default_factory=list)
    severity_hint:  str             = "informational"
EOF

cat > backend/app/parsers/detector.py << 'EOF'
# LogRaven — Log Type Detector
#
# PURPOSE:
#   Auto-detects the log format of an uploaded file.
#   Two-phase detection: file extension first, then content analysis.
#   Phase 2 always overrides Phase 1 (content is more reliable).
#
# DETECTION LOGIC:
#   Phase 1 (extension):
#     .evtx -> windows_event (tentative)
#     .json -> cloudtrail (tentative)
#     .log, .txt, .csv -> inconclusive
#
#   Phase 2 (content — reads first 50 lines):
#     EventID field present -> windows_event (overrides Phase 1)
#     RFC3164 syslog pattern -> syslog
#     JSON with eventSource + eventName keys -> cloudtrail
#     Combined log format IP pattern -> nginx
#
# RETURNS: one of "windows_event" | "syslog" | "cloudtrail" | "nginx"
# RAISES:  UnknownLogTypeError if neither phase identifies the format
#
# TODO Month 2 Week 1: Implement this file.

from app.utils.exceptions import UnknownLogTypeError


def detect(file_path: str) -> str:
    """
    Detect the log type of a file.
    Returns: windows_event | syslog | cloudtrail | nginx
    Raises: UnknownLogTypeError
    """
    # TODO: Implement two-phase detection
    raise UnknownLogTypeError(f"Could not detect log type for: {file_path}")
EOF

cat > backend/app/parsers/windows_event.py << 'EOF'
# LogRaven — Windows Event Log Parser
#
# PURPOSE:
#   Parses Windows Event Log files (.evtx binary or CSV export).
#   Uses pyevtx-rs (pip install evtx) — 440x faster than python-evtx.
#
# LIBRARY:
#   from evtx import PyEvtxParser
#   parser = PyEvtxParser(file_path)
#   for record in parser.records_json(): ...
#
# EVENTID CLASSIFICATION MAP:
#   4625 -> auth_failure       (failed login)
#   4624 -> auth_success       (successful login)
#   4648 -> explicit_credential (RunAs / network logon with explicit creds)
#   4720 -> account_created
#   4688 -> process_exec
#   4698 -> scheduled_task_create
#   4702 -> scheduled_task_modify
#   4732 -> group_member_add
#
# DETECTION FLAGS:
#   brute_force: 5+ EventID 4625 from same IP within 60 seconds
#   lateral_movement: EventID 4648 targeting 3+ different hostnames
#
# TEST WITH: lograven/test-data/Credential_Access/*.evtx
#
# TODO Month 2 Week 3: Implement this file.

from app.parsers.base import BaseParser
from app.parsers.normalizer import NormalizedEvent


class WindowsEventParser(BaseParser):

    # EventID -> event_type mapping
    EVENT_TYPE_MAP = {
        "4625": "auth_failure",
        "4624": "auth_success",
        "4648": "explicit_credential",
        "4720": "account_created",
        "4688": "process_exec",
        "4698": "scheduled_task",
        "4702": "scheduled_task",
        "4732": "group_modification",
    }

    def parse(self, file_path: str) -> list[NormalizedEvent]:
        # TODO: Implement using from evtx import PyEvtxParser
        # Stream records via parser.records_json()
        # Apply EVENT_TYPE_MAP for classification
        # Call _detect_patterns() after parsing all events
        return []

    def _detect_patterns(self, events: list) -> list:
        # TODO: Brute force and lateral movement detection
        return events
EOF

cat > backend/app/parsers/syslog.py << 'EOF'
# LogRaven — Linux Syslog / auth.log Parser
#
# PURPOSE:
#   Parses Linux auth.log, /var/log/secure, and general syslog files.
#   Handles the major syslog format variations across Linux distributions.
#
# MULTI-PATTERN APPROACH:
#   Reads first 200 lines. Tests 5 regex patterns. Uses the one matching
#   the highest percentage of lines. This handles Ubuntu/CentOS/Debian
#   differences without breaking on custom formats.
#
# PATTERNS TESTED:
#   1. RFC3164:  "MMM DD HH:MM:SS hostname process[pid]: message"
#   2. ISO8601:  "YYYY-MM-DDTHH:MM:SS+tz hostname process[pid]: message"
#   3. Custom1:  RFC3164 with year
#   4. Custom2:  systemd journal format
#   5. Minimal:  any line containing sshd|sudo|PAM keyword
#
# AI FALLBACK:
#   If no pattern matches >80% of sample lines, send 50 sample lines
#   to Claude with a format detection prompt. AI identifies the format
#   and returns a working regex. This handles truly custom syslog formats.
#
# DETECTION FLAGS:
#   brute_force: 5+ auth_failure from same IP within 60 seconds
#   privilege_escalation: any sudo event
#   account_modification: useradd/passwd/usermod in message
#
# TODO Month 2 Week 1: Implement this file.

from app.parsers.base import BaseParser
from app.parsers.normalizer import NormalizedEvent


class SyslogParser(BaseParser):

    def parse(self, file_path: str) -> list[NormalizedEvent]:
        # TODO: Multi-pattern detection then parse
        # TODO: AI-assisted fallback for unknown formats
        return []
EOF

cat > backend/app/parsers/cloudtrail.py << 'EOF'
# LogRaven — AWS CloudTrail Parser
#
# PURPOSE:
#   Parses AWS CloudTrail JSON log files.
#   Handles both the standard Records array format and single-event files.
#
# FORMAT:
#   Standard: {"Records": [{event1}, {event2}, ...]}
#   Single:   {eventTime, eventSource, eventName, ...}
#
# KEY FIELDS EXTRACTED:
#   eventTime, eventSource, eventName, sourceIPAddress,
#   userIdentity (type, arn, accountId), errorCode
#
# DETECTION FLAGS:
#   sensitive_action: IAM policy changes, security group modifications,
#                     root account usage, access key creation
#   failed_api_call: any event with errorCode field populated
#   cross_account: events where userIdentity.accountId differs from normal
#
# NOTE: CloudTrail files are typically <20MB. Load full JSON is acceptable.
#       No line-by-line streaming needed for this format.
#
# TODO Month 2 Week 3: Implement this file.

from app.parsers.base import BaseParser
from app.parsers.normalizer import NormalizedEvent


class CloudTrailParser(BaseParser):

    def parse(self, file_path: str) -> list[NormalizedEvent]:
        # TODO: Load JSON, handle Records array or single event
        # TODO: Extract all key fields per event
        # TODO: Apply detection flags
        return []
EOF

cat > backend/app/parsers/nginx.py << 'EOF'
# LogRaven — Nginx / Apache Access Log Parser
#
# PURPOSE:
#   Parses Nginx combined log format and Apache combined log format.
#   Both formats are structurally identical — one parser handles both.
#
# FORMAT:
#   IP - - [DD/Mon/YYYY:HH:MM:SS +tz] "METHOD /path HTTP/1.1" status bytes "referer" "ua"
#
# KEY FIELDS EXTRACTED:
#   remote_addr, time_local, method, request_path, protocol,
#   status_code, body_bytes, referer, user_agent
#
# DETECTION FLAGS:
#   scanning: 50+ requests from same IP within 60 seconds
#   4xx_spike: 20+ 4xx responses from same IP
#   injection_attempt: SQL keywords or path traversal sequences in URL
#   scanner_ua: matches known scanner User-Agent signatures
#
# TODO Month 2 Week 1: Implement this file.

from app.parsers.base import BaseParser
from app.parsers.normalizer import NormalizedEvent


class NginxParser(BaseParser):

    def parse(self, file_path: str) -> list[NormalizedEvent]:
        # TODO: Stream lines, parse with combined log regex
        # TODO: Calculate request rates per IP per 60-second window
        # TODO: Apply detection flags
        return []
EOF

# Correlation engine
mkdir -p backend/app/correlation

cat > backend/app/correlation/__init__.py << 'EOF'
# LogRaven — Correlation Engine Package
EOF

cat > backend/app/correlation/engine.py << 'EOF'
# LogRaven — Correlation Engine
#
# PURPOSE:
#   The core LogRaven feature. Finds connections between events
#   across multiple log source files by matching shared entities
#   within time windows.
#
# MAIN FUNCTION:
#   analyze(investigation_id, events_by_file) -> List[CorrelatedChain]
#
#   events_by_file: dict of {source_type: List[NormalizedEvent]}
#
#   ALGORITHM:
#     1. entity_extractor.extract_all(events_by_file)
#        -> {entity_value: List[EntityOccurrence]}
#     2. Filter: keep entities appearing in 2+ different source_type files
#     3. For each qualifying entity:
#        chain_builder.build_chain(entity, occurrences, time_window=300)
#        -> List[CorrelatedChain]
#     4. Score each chain:
#        - 2 source types: High
#        - 3+ source types: Critical (regardless of individual event severity)
#     5. Return sorted List[CorrelatedChain] by score descending
#
# SINGLE FILE BEHAVIOR:
#   If events_by_file has only one key, return [] immediately.
#   Single file investigations run without correlation — no error.
#
# TODO Month 3 Week 1: Implement this file.

from app.parsers.normalizer import NormalizedEvent


def analyze(investigation_id: str, events_by_file: dict) -> list:
    """
    Run LogRaven correlation analysis across multiple log source files.
    Returns list of CorrelatedChain objects. Empty list if only one file.
    """
    if len(events_by_file) < 2:
        return []

    # TODO: Implement correlation algorithm
    return []
EOF

cat > backend/app/correlation/entity_extractor.py << 'EOF'
# LogRaven — Entity Extractor
#
# PURPOSE:
#   Extracts and normalizes shared entities across all log source files.
#   Entity normalization is CRITICAL for accurate correlation.
#   Without normalization, "10.1.1.5" and "10.1.1.5 " are different entities.
#
# ENTITIES EXTRACTED:
#   - IP addresses: from source_ip and destination_ip fields
#   - Usernames: from username field
#   - Hostnames: from hostname field
#
# NORMALIZATION RULES (applied before grouping):
#   - Lowercase all values
#   - Strip leading/trailing whitespace
#   - Strip trailing dots from hostnames (DNS artifact)
#   - Remove port numbers from IPs if present (e.g. "10.1.1.5:443" -> "10.1.1.5")
#
# MAIN FUNCTION:
#   extract_all(events_by_file) -> dict[entity_value, List[EntityOccurrence]]
#
# TODO Month 3 Week 1: Implement this file.

from app.parsers.normalizer import NormalizedEvent
from dataclasses import dataclass


@dataclass
class EntityOccurrence:
    entity_value: str
    entity_type: str    # ip | username | hostname
    source_type: str    # which log source file
    timestamp: object   # datetime
    event: NormalizedEvent


def extract_all(events_by_file: dict) -> dict:
    """
    Extract all entities from all source files.
    Returns {normalized_entity_value: [EntityOccurrence, ...]}
    """
    # TODO: Implement entity extraction with normalization
    return {}
EOF

cat > backend/app/correlation/chain_builder.py << 'EOF'
# LogRaven — Chain Builder
#
# PURPOSE:
#   Groups entity occurrences into time-windowed event chains.
#   A chain = same entity appearing across multiple source types
#   within a configurable time window (default: 5 minutes = 300 seconds).
#
# MAIN FUNCTION:
#   build_chain(entity_value, occurrences, time_window=300) -> List[CorrelatedChain]
#
# CHAIN SCORING:
#   Chains spanning more source types are more significant:
#   2 source types -> severity_elevation = "high"
#   3+ source types -> severity_elevation = "critical"
#
# EXAMPLE CHAIN:
#   Entity: IP 185.220.101.42
#   Occurrences:
#     - windows_endpoint: powershell.exe spawn at 14:02:08
#     - firewall: blocked outbound 443 at 14:02:11
#     - cloudtrail: AssumeRole API at 14:02:15
#   All within 300-second window -> CorrelatedChain with Critical elevation
#
# TODO Month 3 Week 1: Implement this file.

from dataclasses import dataclass, field
from typing import List


@dataclass
class CorrelatedChain:
    entity_value: str
    entity_type: str
    source_types: List[str]
    events: List[object]        # List[EntityOccurrence]
    time_span_seconds: float
    severity_elevation: str     # high | critical
    score: float


def build_chain(entity_value: str, occurrences: list, time_window: int = 300) -> List[CorrelatedChain]:
    """
    Build correlated chains from entity occurrences within a time window.
    Returns list of CorrelatedChain objects.
    """
    # TODO: Implement chain building with time window grouping
    return []
EOF

# AI layer
mkdir -p backend/app/ai
mkdir -p backend/app/ai/cloud
mkdir -p backend/app/ai/prompts

cat > backend/app/ai/__init__.py << 'EOF'
# LogRaven — AI Package
EOF

cat > backend/app/ai/router.py << 'EOF'
# LogRaven — AI Analysis Router
#
# PURPOSE:
#   Single decision point for all AI analysis in LogRaven.
#   Routes to cloud AI (Claude) for v1.
#   Local AI (Ollama + LLaMA) is Phase 2 Enterprise feature.
#
# MAIN FUNCTION:
#   analyze(events_by_source, correlated_chains, user_tier) -> AnalysisResult
#     1. Apply cost ceiling via cost_limiter.enforce_ceiling()
#     2. Build prompts: one for correlated chains, one per source type
#     3. Call cloud/engine.py (Claude claude-sonnet-4-6)
#     4. On Claude failure: try cloud/openai_engine.py (GPT-4o)
#     5. Return merged AnalysisResult
#
# TODO Month 3 Week 3: Implement this file.
EOF

cat > backend/app/ai/chunker.py << 'EOF'
# LogRaven — Event Chunker
#
# PURPOSE:
#   Splits large event lists into overlapping chunks for AI processing.
#   The 50-event overlap prevents missing patterns at chunk boundaries.
#
# FUNCTIONS:
#   split_events(events, chunk_size=2000, overlap=50) -> List[List[NormalizedEvent]]
#     Splits event list into overlapping chunks.
#     Example: 5000 events -> 3 chunks: [0-2049], [2000-4049], [4000-4999]
#
#   merge_results(results) -> List[Finding]
#     Merges findings from all chunks.
#     Deduplicates using hash(severity + source_ip + mitre_technique_id).
#     On collision: keep finding with higher confidence score.
#
# TODO Month 3 Week 3: Implement this file.

def split_events(events: list, chunk_size: int = 2000, overlap: int = 50) -> list:
    """Split events into overlapping chunks for AI processing."""
    # TODO: Implement chunking with overlap
    return [events]  # Stub: return single chunk


def merge_results(results: list) -> list:
    """Merge and deduplicate findings from multiple chunks."""
    # TODO: Implement deduplication
    return results
EOF

cat > backend/app/ai/cost_limiter.py << 'EOF'
# LogRaven — AI Cost Limiter
#
# PURPOSE:
#   Enforces hard per-investigation event ceiling before sending to Claude.
#   Prevents unbounded API costs regardless of file size.
#   Makes AI cost predictable: maximum $0.10-0.15 per investigation.
#
# TIER LIMITS:
#   free:  2,000 events max sent to AI
#   pro:   10,000 events max
#   team:  50,000 events max
#
# SELECTION PRIORITY (when ceiling is hit):
#   1. Flagged events (any flag in flags list) over unflagged
#   2. Higher severity_hint over lower
#   3. Events from correlated chains over single-source
#
# When ceiling is hit: the report notes which events were rule-only
# vs AI-analyzed, so the user understands coverage.
#
# TODO Month 3 Week 1: Implement this file.

TIER_CEILINGS = {
    "free":  2_000,
    "pro":  10_000,
    "team": 50_000,
}


def enforce_ceiling(events: list, user_tier: str) -> tuple[list, bool]:
    """
    Select events within the tier ceiling.
    Returns (selected_events, was_truncated)
    """
    ceiling = TIER_CEILINGS.get(user_tier, 2_000)
    if len(events) <= ceiling:
        return events, False

    # TODO: Implement priority-based selection
    return events[:ceiling], True
EOF

cat > backend/app/ai/cloud/__init__.py << 'EOF'
# LogRaven — Cloud AI Package
EOF

cat > backend/app/ai/cloud/engine.py << 'EOF'
# LogRaven — Claude API Engine (Primary)
#
# PURPOSE:
#   Sends analysis requests to Claude claude-sonnet-4-6 via the official
#   Anthropic Python SDK. Primary AI engine for LogRaven v1.
#
# PRIVACY NOTE:
#   Before sending events, strip PII from raw_message fields:
#   - Replace internal hostnames with [HOST]
#   - Replace internal usernames with [USER] in raw_message only
#   (structured fields like username are kept for correlation)
#
# PROMPT CONSTRUCTION:
#   System prompt: SOC analyst persona from prompts/base_prompt.py
#   User message: structured JSON of events or correlated chains
#   Output format: STRICT JSON array only — no markdown, no commentary
#
# RETRY LOGIC:
#   3 attempts with exponential backoff: 2s, 4s, 8s delays
#   Retries on: rate limits (429), transient errors (500/503)
#   Does NOT retry on: auth errors (401), bad requests (400)
#
# COST TRACKING:
#   Log input_tokens + output_tokens per request to a simple log entry
#
# TODO Month 3 Week 3: Implement this file.

from anthropic import Anthropic

client = Anthropic()  # Reads ANTHROPIC_API_KEY from environment


async def analyze(events: list, log_type: str, user_tier: str) -> list:
    """
    Analyze events using Claude claude-sonnet-4-6.
    Returns list of finding dicts.
    """
    # TODO: Implement Claude API call with retry logic
    # TODO: Strip PII from raw_message before sending
    # TODO: Build prompt from prompts/ templates
    # TODO: Parse strict JSON response
    return []
EOF

cat > backend/app/ai/cloud/openai_engine.py << 'EOF'
# LogRaven — OpenAI GPT-4o Engine (Fallback)
#
# PURPOSE:
#   Fallback AI engine used when Claude API is unavailable.
#   Same interface as claude engine.py — drop-in replacement.
#   Only called by ai/router.py when Claude fails after retries.
#
# TODO Month 3 Week 3: Implement this file. (Lower priority than Claude engine)
EOF

cat > backend/app/ai/cloud/consent.py << 'EOF'
# LogRaven — Cloud AI Consent Check
#
# PURPOSE:
#   Verifies the user has explicitly opted in to cloud AI analysis.
#   Cloud AI sends event data to Anthropic servers.
#   This must be explicitly opted in — never automatic.
#
# CONSENT CHECK:
#   In LogRaven v1 (Docker delivery), consent is controlled by:
#   - The client's own API key usage (they know their key goes to Anthropic)
#   - An opt-in toggle in the UI per investigation
#
# TODO Month 3 Week 3: Implement this file.
EOF

# Prompts
cat > backend/app/ai/prompts/__init__.py << 'EOF'
# LogRaven — AI Prompts Package
EOF

cat > backend/app/ai/prompts/base_prompt.py << 'EOF'
# LogRaven — Base AI Prompt Template
#
# PURPOSE:
#   Defines the system prompt and output schema used by ALL LogRaven
#   AI analysis requests. This is the most important file in the AI layer.
#   Finding quality depends entirely on this prompt.
#
# SYSTEM PROMPT DEFINES:
#   - Persona: senior SOC analyst, 15 years experience, DFIR specialist
#   - Output: STRICT JSON array only — no markdown, no preamble, no commentary
#   - Finding schema:
#       {"severity": "critical|high|medium|low|informational",
#        "title": "short description max 80 chars",
#        "description": "plain English 2-3 sentences",
#        "mitre_technique_id": "T####.### or null if unsure",
#        "iocs": ["ip", "hash", "domain", ...],
#        "remediation": "one concrete action",
#        "confidence": 0.0-1.0}
#   - MITRE rule: NEVER hallucinate technique IDs — use null if unsure
#   - Severity guidance: based on actual impact, not just presence of indicator
#   - Focus: actionable findings only, not comprehensive coverage
#
# TODO Month 3 Week 3: Implement this file.


SYSTEM_PROMPT = """You are a senior SOC analyst and DFIR specialist with 15 years of experience.

Analyze the provided security log events and return ONLY a JSON array of findings.
No markdown. No commentary. No preamble. Only the JSON array.

Each finding must follow this exact schema:
{
  "severity": "critical|high|medium|low|informational",
  "title": "short description (max 80 chars)",
  "description": "plain English explanation of what happened (2-3 sentences)",
  "mitre_technique_id": "T####.### or null if you are not certain",
  "iocs": ["list of extracted IPs, hashes, domains, usernames"],
  "remediation": "one specific, actionable remediation step",
  "confidence": 0.9
}

CRITICAL RULES:
- Return only the JSON array. Nothing else.
- NEVER hallucinate MITRE technique IDs. Use null if unsure.
- Severity must reflect actual impact, not just indicator presence.
- Focus on actionable findings. Ignore noise.
"""


def build_prompt(events_json: str, log_type: str) -> str:
    """Build the full user message prompt for a standard log analysis."""
    # TODO: Add log-type-specific instructions
    return f"Analyze these {log_type} log events:\n\n{events_json}"
EOF

cat > backend/app/ai/prompts/windows_prompt.py << 'EOF'
# LogRaven — Windows Event Log AI Prompt
#
# PURPOSE:
#   Log-type-specific additions to the base prompt for Windows Event Logs.
#   Imported by base_prompt.py build_prompt() when log_type="windows_event"
#
# WINDOWS-SPECIFIC INSTRUCTIONS:
#   - Pay special attention to EventID 4625/4624 authentication chains
#   - Flag any EventID 4688 (process creation) with suspicious parent/child relationships
#   - EventID 4648 across multiple hostnames indicates lateral movement
#   - Scheduled task creation (4698/4702) is a common persistence technique
#
# TODO Month 3 Week 3: Implement this file.

WINDOWS_ADDITIONS = """
Windows Event Log specific instructions:
- Authentication chains (4625->4624) indicate successful brute force
- 4648 with multiple target hostnames = lateral movement (T1021)
- 4688 with unusual parent processes = process injection or LOLBin abuse
- 4698/4702 = scheduled task persistence (T1053.005)
"""
EOF

cat > backend/app/ai/prompts/syslog_prompt.py << 'EOF'
# LogRaven — Syslog AI Prompt
# Log-type-specific additions for Linux syslog and auth.log analysis.
# TODO Month 3 Week 3: Implement.

SYSLOG_ADDITIONS = """
Linux syslog specific instructions:
- PAM authentication failures followed by success = brute force success (T1110.001)
- Sudo chains from non-standard users = privilege escalation (T1548.003)
- New user creation (useradd) = persistence (T1136.001)
- SSH from new country/IP = initial access (T1078)
"""
EOF

cat > backend/app/ai/prompts/cloudtrail_prompt.py << 'EOF'
# LogRaven — CloudTrail AI Prompt
# Log-type-specific additions for AWS CloudTrail analysis.
# TODO Month 3 Week 3: Implement.

CLOUDTRAIL_ADDITIONS = """
AWS CloudTrail specific instructions:
- AssumeRole to high-privilege roles = privilege escalation (T1078.004)
- CreateAccessKey for another user = persistence (T1098.001)
- Failed API calls from unusual IPs = reconnaissance or credential testing
- Security group modifications = defense evasion (T1562.007)
- S3 GetObject on sensitive buckets = data exfiltration (T1530)
"""
EOF

cat > backend/app/ai/prompts/nginx_prompt.py << 'EOF'
# LogRaven — Nginx/Apache AI Prompt
# Log-type-specific additions for web access log analysis.
# TODO Month 3 Week 3: Implement.

NGINX_ADDITIONS = """
Web access log specific instructions:
- High 4xx rate from single IP = scanning or brute force (T1595)
- SQL keywords in URL paths = SQL injection attempt (T1190)
- Path traversal patterns (../../../) = directory traversal
- POST to unusual endpoints with large bodies = webshell upload attempt
"""
EOF

cat > backend/app/ai/prompts/correlation_prompt.py << 'EOF'
# LogRaven — Correlation AI Prompt
#
# PURPOSE:
#   The most important LogRaven prompt file.
#   Used when Claude analyzes correlated event chains (multi-source findings).
#   Produces qualitatively richer findings than single-source analysis.
#
# KEY DIFFERENCE FROM STANDARD PROMPTS:
#   Standard prompts: analyze individual events in isolation
#   Correlation prompt: analyze connected chains spanning multiple sources
#
# PROMPT INSTRUCTION:
#   "These events share a common entity (IP/username/hostname) across
#    multiple log sources. They are not isolated events.
#    Identify the SINGLE ATT&CK technique that explains ALL of them together.
#    Describe the attack timeline in plain English from first to last event.
#    Assign severity based on combined evidence, not individual event severity."
#
# EXAMPLE OUTPUT:
#   A chain of powershell.exe spawn + firewall block + CloudTrail AssumeRole
#   gets a precise lateral movement technique ID (T1021.006 or T1078.004)
#   and a narrative: "Attacker spawned PowerShell on endpoint at 14:02:08,
#   attempted outbound connection blocked by firewall at 14:02:11, then
#   successfully assumed an IAM role via CloudTrail at 14:02:15,
#   suggesting credential theft and cloud pivot."
#
# TODO Month 3 Week 1: Implement this file.


def build_correlation_prompt(chains: list) -> str:
    """
    Build a prompt for analyzing correlated event chains.
    chains: List[CorrelatedChain] from correlation/chain_builder.py
    """
    # TODO: Serialize chains to JSON and build structured prompt
    return ""
EOF

# Reports
mkdir -p backend/app/reports
mkdir -p backend/app/reports/templates

cat > backend/app/reports/__init__.py << 'EOF'
# LogRaven — Reports Package
EOF

cat > backend/app/reports/builder.py << 'EOF'
# LogRaven — Report Builder
#
# PURPOSE:
#   Assembles the final LogRaven report from all analysis outputs.
#   This is the last step before PDF generation.
#
# MAIN FUNCTION:
#   build_report(investigation, correlated_findings, single_source_findings, db) -> Report
#
# ALGORITHM:
#   1. Merge correlated and single-source findings into one list
#   2. Deduplicate: same (severity + source_ip + mitre_id) = same finding
#      On collision: keep finding with higher confidence score
#   3. Call mitre_mapper.enrich(findings) to add full technique names
#   4. Sort by severity (critical first), then confidence
#   5. Generate executive summary (plain English, 2-3 sentences)
#   6. Count severity distribution for SeverityChart
#   7. Create Report and Finding records in database
#   8. Return Report object
#
# TODO Month 4 Week 1: Implement this file.
EOF

cat > backend/app/reports/mitre_mapper.py << 'EOF'
# LogRaven — MITRE ATT&CK Mapper
#
# PURPOSE:
#   Enriches LogRaven findings with full MITRE ATT&CK technique data.
#   Uses the official mitreattack-python library (pip install mitreattack-python)
#   maintained by MITRE themselves — always accurate, always current.
#
# LIBRARY USAGE:
#   from mitreattack.stix20 import MitreAttackData
#   _atk = MitreAttackData('enterprise-attack.json')  # loaded ONCE at startup
#
# KEY FUNCTIONS:
#   enrich(findings) -> List[Finding]
#     For each finding with mitre_technique_id:
#     calls _atk.get_object_by_attack_id(technique_id, 'attack-pattern')
#     Adds: technique_name, tactic_name, description (first 300 chars)
#
#   get_coverage_matrix(technique_ids) -> dict
#     Returns all 14 ATT&CK tactics showing which were triggered.
#     Used for the MITRE coverage visualization in the PDF report.
#
# NOTE: MitreAttackData is loaded ONCE at module import, not per request.
#       enterprise-attack.json must be bundled in the Docker image.
#       Download from: https://github.com/mitre-attack/attack-stix-data
#
# TODO Month 4 Week 1: Implement this file.

# Load ONCE at module startup — never reload per request
_atk = None  # Will be MitreAttackData('enterprise-attack.json')


def enrich(findings: list) -> list:
    """Add full ATT&CK technique data to each finding."""
    # TODO: Implement using mitreattack-python
    return findings


def get_coverage_matrix(technique_ids: list) -> dict:
    """Build ATT&CK tactic coverage matrix showing triggered techniques."""
    # TODO: Return dict of {tactic: {name, techniques: [{id, name, triggered}]}}
    return {}
EOF

cat > backend/app/reports/pdf_generator.py << 'EOF'
# LogRaven — PDF Report Generator
#
# PURPOSE:
#   Renders the LogRaven security investigation report to a PDF file.
#   Uses WeasyPrint to convert a Jinja2 HTML template to PDF.
#
# MAIN FUNCTION:
#   generate_pdf(report, findings, investigation) -> str (path to PDF file)
#
# PROCESS:
#   1. Load lograven_report.html template via Jinja2
#   2. Build template context:
#      - report (summary, severity_counts)
#      - correlated_findings (shown first in report)
#      - single_source_findings
#      - mitre_matrix (from mitre_mapper.get_coverage_matrix())
#      - investigation (name, date, file list)
#   3. Render template to HTML string
#   4. Call WeasyPrint HTML(string=html).write_pdf()
#   5. Write PDF to local/temp/{job_id}/lograven-report-{uuid}.pdf
#   6. Return file path
#
# PDF BRANDING:
#   Every page has LogRaven header.
#   Footer contains client license ID (watermark).
#   PDF metadata: Creator="LogRaven v1.0", Producer=client_license_id
#
# TODO Month 4 Week 1: Implement this file.
EOF

cat > backend/app/reports/uploader.py << 'EOF'
# LogRaven — Report Uploader
#
# PURPOSE:
#   Moves the generated PDF from temp storage to permanent report storage.
#   Uses the StorageBackend abstraction — same code works local and S3.
#
# MAIN FUNCTION:
#   upload_report(temp_path, investigation_id) -> str (storage_key)
#
# STORAGE KEY FORMAT:
#   reports/{investigation_id}/lograven-report-{uuid}.pdf
#
# After upload: temp file is deleted.
# The storage_key is saved to the Report.pdf_storage_key column.
#
# TODO Month 4 Week 1: Implement this file.
EOF

cat > backend/app/reports/templates/lograven_report.html << 'EOF'
<!DOCTYPE html>
<!--
LogRaven — PDF Report Template
Rendered by WeasyPrint via pdf_generator.py

TEMPLATE CONTEXT VARIABLES:
  report.summary          — executive summary paragraph
  report.severity_counts  — {critical, high, medium, low, informational}
  correlated_findings     — list of cross-source chain findings (shown first)
  single_source_findings  — list of individual file findings
  mitre_matrix            — {tactic: {name, techniques: [{id, name, triggered}]}}
  investigation.name      — investigation name
  investigation.created_at — date of analysis
  client_license_id       — embedded in footer for watermarking

TODO Month 4 Week 1: Design and implement this template.
-->
<html>
<head>
    <meta charset="UTF-8">
    <title>LogRaven Security Report</title>
    <link rel="stylesheet" href="lograven_report.css">
</head>
<body>
    <header>
        <h1>LogRaven</h1>
        <p>Watch your logs. Find the threat.</p>
    </header>

    <!-- TODO: Cover page -->
    <!-- TODO: Executive summary section -->
    <!-- TODO: Correlated findings section (shown first) -->
    <!-- TODO: Individual findings table -->
    <!-- TODO: MITRE ATT&CK coverage matrix -->
    <!-- TODO: IOC reference table -->
    <!-- TODO: Recommended actions -->

    <footer>
        <!-- Client license ID watermark -->
    </footer>
</body>
</html>
EOF

cat > backend/app/reports/templates/lograven_report.css << 'EOF'
/*
LogRaven — PDF Report Stylesheet
Used by WeasyPrint via pdf_generator.py

SECTIONS TO STYLE:
  @page rules — margins, headers, footers
  .cover-page — LogRaven branding, investigation name, severity badge
  .executive-summary — highlighted summary box
  .correlated-finding — cross-source finding card (prominent styling)
  .finding-table — individual findings table
  .severity-badge — color-coded: critical=red, high=orange, medium=yellow, low=blue
  .mitre-matrix — tactic coverage grid
  .ioc-table — extracted IOCs reference

BRAND COLORS:
  Primary:   #3B82F6 (electric blue)
  Dark:      #0D0F14 (raven black)
  Accent:    #7C3AED (raven purple)

TODO Month 4 Week 1: Design and implement this stylesheet.
*/

body {
    font-family: Arial, sans-serif;
    color: #0F172A;
}

/* TODO: Implement full LogRaven report styling */
EOF

# Celery Tasks
mkdir -p backend/app/tasks

cat > backend/app/tasks/__init__.py << 'EOF'
# LogRaven — Tasks Package
EOF

cat > backend/app/tasks/celery_app.py << 'EOF'
# LogRaven — Celery Application Configuration
#
# PURPOSE:
#   Creates and configures the Celery application instance.
#   Redis is used as both broker and result backend.
#
# KEY CONFIGURATION:
#   task_serializer = "json"          — human-readable task payloads
#   worker_max_tasks_per_child = 100  — prevent memory leaks in long-running workers
#   task_acks_late = True             — tasks acknowledged AFTER completion, not before
#   task_reject_on_worker_lost = True — re-queue tasks if worker crashes mid-processing
#
# QUEUES:
#   default  — standard investigations
#   priority — team tier investigations (processed first)
#
# TODO Month 1 Week 3: Implement this file.

from celery import Celery
import os

celery_app = Celery(
    "lograven",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379"),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_max_tasks_per_child=100,
)

# TODO: Import and register process_investigation task
EOF

cat > backend/app/tasks/process_investigation.py << 'EOF'
# LogRaven — Main Investigation Processing Task
#
# PURPOSE:
#   The core Celery task that orchestrates the complete LogRaven pipeline.
#   This is the most important file in the backend.
#
# CALLED BY:
#   investigation_service.start_analysis() via process_investigation.delay(investigation_id)
#
# PIPELINE (in order):
#   1.  Update investigation status to "processing"
#   2.  For each InvestigationFile in investigation:
#       a. Download file from local storage to temp path
#       b. Run detector.detect(temp_path) to identify log type
#       c. Update file log_type in DB
#       d. Run appropriate parser (pyevtx-rs / syslog / cloudtrail / nginx)
#       e. Update file status=parsed, event_count in DB
#       f. Update investigation progress_stage in Redis for frontend polling
#   3.  Run rule engine across all normalized events
#   4.  Run correlation engine with events grouped by source_type
#   5.  Apply cost_limiter.enforce_ceiling() per user tier
#   6.  Run AI analysis via ai/router.py
#   7.  Run report builder to create Report and Finding records
#   8.  Generate PDF via pdf_generator.generate_pdf()
#   9.  Upload PDF to storage via uploader.upload_report()
#   10. Update investigation status to "complete", set completed_at
#   11. Send notification if job took > 30 seconds
#
# ERROR HANDLING:
#   Any exception at any step:
#   - Sets investigation status to "failed"
#   - Sets error_message on the failed InvestigationFile (if file-specific)
#   - Logs full traceback
#   - Temp files always deleted in finally block
#
# PROGRESS TRACKING:
#   After each major step, store current stage in Redis:
#   redis.set(f"lograven:progress:{investigation_id}", stage_name, ex=3600)
#   Frontend polls /api/v1/investigations/{id}/status which reads from Redis.
#
# TODO Month 2 Week 1: Implement scaffold. Month 3+: Full implementation.

from app.tasks.celery_app import celery_app


@celery_app.task(name="process_investigation", bind=True, max_retries=0)
def process_investigation(self, investigation_id: str):
    """
    LogRaven main processing pipeline.
    Orchestrates parsing -> rule engine -> correlation -> AI -> report -> PDF.
    """
    # TODO: Implement full pipeline
    print(f"[LogRaven] Processing investigation {investigation_id}")
    # Stub implementation — will be expanded in later months
EOF

# Utils
mkdir -p backend/app/utils

cat > backend/app/utils/__init__.py << 'EOF'
# LogRaven — Utils Package
EOF

cat > backend/app/utils/storage.py << 'EOF'
# LogRaven — Storage Backend Abstraction
#
# PURPOSE:
#   Provides a unified file storage interface with two implementations:
#   - LocalStorageBackend: saves files to ./local/ folder (development)
#   - S3StorageBackend: saves files to AWS S3 (production)
#
# SWITCHING BETWEEN BACKENDS:
#   Set STORAGE_BACKEND="local" for development (default)
#   Set STORAGE_BACKEND="s3" for production
#   Nothing else changes — all file operations go through this abstraction.
#
# CRITICAL RULE: Never use direct file operations anywhere in the codebase.
#   Always use storage.save_file(), storage.get_download_url(), etc.
#
# LOCAL STORAGE SERVING:
#   In development, FastAPI serves local/ at /files/ via StaticFiles mount.
#   get_download_url() returns http://localhost:8000/files/{key}
#
# S3 PRODUCTION:
#   S3StorageBackend stub is here for reference.
#   Full implementation added in requirements.prod.txt with boto3.
#
# TODO Month 1 Week 1: Implement LocalStorageBackend.

from abc import ABC, abstractmethod
from pathlib import Path
import aiofiles


class StorageBackend(ABC):

    @abstractmethod
    async def save_file(self, file_obj, key: str) -> str:
        """Save a file. Returns the storage key."""
        pass

    @abstractmethod
    async def get_file_path(self, key: str) -> Path:
        """Get local file path (for workers to read files)."""
        pass

    @abstractmethod
    def get_download_url(self, key: str) -> str:
        """Get URL for file download."""
        pass

    @abstractmethod
    async def delete_file(self, key: str) -> None:
        """Delete a file."""
        pass


class LocalStorageBackend(StorageBackend):
    """
    Development storage backend. Saves files to local filesystem.
    Files served by FastAPI StaticFiles mount at /files/
    """

    def __init__(self, base_path: str = "./local"):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)

    async def save_file(self, file_obj, key: str) -> str:
        dest = self.base / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(dest, "wb") as f:
            while chunk := await file_obj.read(1024 * 1024):  # 1MB chunks
                await f.write(chunk)
        return key

    async def get_file_path(self, key: str) -> Path:
        return self.base / key

    def get_download_url(self, key: str) -> str:
        return f"http://localhost:8000/files/{key}"

    async def delete_file(self, key: str) -> None:
        path = self.base / key
        if path.exists():
            path.unlink()


class S3StorageBackend(StorageBackend):
    """
    Production storage backend. Saves files to AWS S3.
    Requires boto3 (in requirements.prod.txt only).
    Full implementation added when STORAGE_BACKEND=s3.
    """

    def __init__(self, bucket: str, region: str = "eu-west-1"):
        self.bucket = bucket
        self.region = region
        # boto3 imported here to avoid ImportError in dev (not in requirements.txt)
        # import boto3
        # self.client = boto3.client("s3", region_name=region)

    async def save_file(self, file_obj, key: str) -> str:
        # TODO: Implement S3 multipart upload for large files
        raise NotImplementedError("S3StorageBackend not yet implemented for production")

    async def get_file_path(self, key: str) -> Path:
        # TODO: Download from S3 to temp path
        raise NotImplementedError

    def get_download_url(self, key: str) -> str:
        # TODO: Generate pre-signed URL valid for 24 hours
        raise NotImplementedError

    async def delete_file(self, key: str) -> None:
        # TODO: Delete object from S3
        raise NotImplementedError
EOF

cat > backend/app/utils/security.py << 'EOF'
# LogRaven — Security Utilities
#
# PURPOSE:
#   JWT token creation/validation and bcrypt password hashing.
#   Used by auth_service.py and dependencies.py.
#
# FUNCTIONS:
#   hash_password(plain: str) -> str
#     bcrypt hash with cost factor 12 (~250ms per hash)
#
#   verify_password(plain: str, hashed: str) -> bool
#     Compare plain text to bcrypt hash
#
#   create_access_token(user_id: str, tier: str) -> str
#     JWT with 15-minute expiry, contains user_id and tier claims
#
#   create_refresh_token(user_id: str) -> str
#     JWT with 7-day expiry, contains only user_id
#
#   decode_token(token: str) -> dict
#     Validates signature and expiry, returns claims dict
#     Raises TokenExpiredError or InvalidTokenError on failure
#
# TODO Month 1 Week 1: Implement this file.

from passlib.context import CryptContext
from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime, timedelta
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-prod")
ALGORITHM  = os.getenv("JWT_ALGORITHM", "HS256")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str, tier: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15)))
    payload = {"sub": user_id, "tier": tier, "exp": expire, "type": "access"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7)))
    payload = {"sub": user_id, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    # TODO: Add proper error handling with custom exceptions
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
EOF

cat > backend/app/utils/rate_limiter.py << 'EOF'
# LogRaven — Redis-Backed Rate Limiter
#
# PURPOSE:
#   Prevents abuse of the LogRaven API.
#   Uses Redis INCR + EXPIRE for atomic sliding window counters.
#
# LIMITS:
#   Per-user daily upload limit:
#     free: 1 investigation/day
#     pro:  50 investigations/day
#     team: 200 investigations/day
#
#   Per-IP request rate (prevents API scraping):
#     100 requests/minute per IP address
#
# FUNCTIONS:
#   check_upload_rate(user_id, tier) -> (allowed: bool, remaining: int)
#   check_api_rate(ip_address) -> (allowed: bool, remaining: int)
#
# TODO Month 1 Week 3: Implement this file.

TIER_DAILY_LIMITS = {
    "free": 1,
    "pro":  50,
    "team": 200,
}
EOF

cat > backend/app/utils/logger.py << 'EOF'
# LogRaven — Structured Logger
#
# PURPOSE:
#   Configures structured JSON logging for production.
#   Human-readable format for development.
#   Every log entry includes: timestamp, level, logger name, message.
#   Request middleware adds request_id to all log entries within a request.
#
# USAGE:
#   from app.utils.logger import get_logger
#   logger = get_logger(__name__)
#   logger.info("Processing investigation", investigation_id=str(inv_id))
#
# TODO Month 1 Week 1: Implement basic logger. Full structured logging Month 5.

import logging
import os


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if os.getenv("DEBUG") == "True" else logging.INFO)
    return logger
EOF

cat > backend/app/utils/exceptions.py << 'EOF'
# LogRaven — Custom Exception Classes
#
# PURPOSE:
#   Custom exceptions that map to HTTP status codes.
#   The global exception handler in main.py catches these and converts
#   them to consistent JSON error responses.
#
# RESPONSE SHAPE:
#   {"error": "Human readable message", "code": "MACHINE_CODE", "detail": "optional"}
#
# TODO Month 1 Week 1: Implement this file.

from fastapi import HTTPException


class LogRavenError(Exception):
    """Base exception for all LogRaven errors."""
    def __init__(self, message: str, code: str = "LOGRAVEN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(LogRavenError):
    status_code = 404
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, "NOT_FOUND")


class ForbiddenError(LogRavenError):
    status_code = 403
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, "FORBIDDEN")


class RateLimitError(LogRavenError):
    status_code = 429
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, "RATE_LIMIT")


class InvalidFileTypeError(LogRavenError):
    status_code = 400
    def __init__(self, message: str = "Invalid file type"):
        super().__init__(message, "INVALID_FILE_TYPE")


class FileTooLargeError(LogRavenError):
    status_code = 400
    def __init__(self, message: str = "File exceeds tier size limit"):
        super().__init__(message, "FILE_TOO_LARGE")


class LicenseError(LogRavenError):
    status_code = 403
    def __init__(self, message: str = "Invalid or expired license"):
        super().__init__(message, "LICENSE_ERROR")


class UnknownLogTypeError(LogRavenError):
    status_code = 400
    def __init__(self, message: str = "Cannot detect log file format"):
        super().__init__(message, "UNKNOWN_LOG_TYPE")


class AIEngineError(LogRavenError):
    status_code = 503
    def __init__(self, message: str = "AI analysis engine unavailable"):
        super().__init__(message, "AI_ENGINE_ERROR")
EOF

# =============================================================================
# FRONTEND
# =============================================================================
mkdir -p frontend/src/pages/Auth
mkdir -p frontend/src/components/investigation
mkdir -p frontend/src/components/reports
mkdir -p frontend/src/components/layout
mkdir -p frontend/src/components/ui
mkdir -p frontend/src/hooks
mkdir -p frontend/src/api
mkdir -p frontend/src/store
mkdir -p frontend/src/types

cat > frontend/Dockerfile.dev << 'EOF'
# LogRaven — Frontend Development Dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]
EOF

cat > frontend/package.json << 'EOF'
{
  "name": "lograven-frontend",
  "version": "1.0.0",
  "description": "LogRaven — Security Investigation Platform",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint src --ext ts,tsx"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.24.0",
    "@tanstack/react-query": "^5.50.0",
    "axios": "^1.7.2",
    "zustand": "^4.5.4",
    "recharts": "^2.12.7"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.39",
    "tailwindcss": "^3.4.6",
    "typescript": "^5.5.3",
    "vite": "^5.3.4"
  }
}
EOF

cat > frontend/vite.config.ts << 'EOF'
// LogRaven — Vite Configuration
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/auth': { target: 'http://localhost:8000', changeOrigin: true },
      '/files': { target: 'http://localhost:8000', changeOrigin: true },
      '/health': { target: 'http://localhost:8000', changeOrigin: true },
    }
  }
})
EOF

cat > frontend/tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}
EOF

cat > frontend/tailwind.config.ts << 'EOF'
// LogRaven — Tailwind CSS Configuration
import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // LogRaven brand colors
        raven: {
          50:  '#f0f4ff',
          100: '#e0e9ff',
          500: '#3B82F6',  // electric blue
          600: '#2563EB',
          700: '#1d4ed8',
          900: '#0D0F14',  // raven black
        },
        violet: {
          500: '#7C3AED',  // raven purple
          600: '#6d28d9',
        }
      }
    }
  },
  plugins: []
} satisfies Config
EOF

cat > frontend/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>LogRaven — Watch your logs. Find the threat.</title>
    <meta name="description" content="LogRaven: Security investigation platform. Upload logs, correlate evidence, get MITRE ATT&CK mapped PDF reports." />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
EOF

cat > frontend/src/main.tsx << 'EOF'
// LogRaven — React Application Entry Point
import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    }
  }
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
)
EOF

cat > frontend/src/index.css << 'EOF'
/* LogRaven — Global Styles */
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --lograven-blue: #3B82F6;
  --lograven-black: #0D0F14;
  --lograven-purple: #7C3AED;
}

body {
  font-family: 'Arial', sans-serif;
  background-color: #F8FAFC;
  color: #0F172A;
}
EOF

cat > frontend/src/App.tsx << 'EOF'
// LogRaven — Root Application Component
// Sets up React Router with all LogRaven routes.
// Protected routes require authentication (JWT in authStore).
//
// ROUTES:
//   /              — Landing page (public)
//   /login         — Login page (public)
//   /register      — Register page (public)
//   /dashboard     — Investigation list (protected)
//   /new           — Create investigation (protected)
//   /investigation/:id  — Investigation detail + file upload (protected)
//   /status/:id    — Job status polling page (protected)
//   /report/:id    — Full LogRaven report view (protected)
//
// TODO Month 1 Week 3: Implement this file.

import React from 'react'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <h1 className="text-3xl font-bold text-center pt-20 text-blue-600">
        LogRaven
      </h1>
      <p className="text-center text-gray-500 mt-2">
        Watch your logs. Find the threat.
      </p>
      <p className="text-center text-gray-400 mt-4 text-sm">
        Frontend scaffold ready. Implement App.tsx in Month 1 Week 3.
      </p>
    </div>
  )
}
EOF

# Pages
cat > frontend/src/pages/Landing.tsx << 'EOF'
// LogRaven — Landing Page
//
// PURPOSE:
//   Public marketing page. No auth required.
//   Converts visitors into LogRaven users.
//
// SECTIONS:
//   Hero: "Watch your logs. Find the threat." + Get LogRaven CTA
//   How It Works: 3 steps (Upload -> Correlate -> Report)
//   Features: Multi-file correlation, Privacy-first, MITRE ATT&CK, PDF Report
//   Pricing: Solo $299 | Team $799 | Per-Engagement $75/month
//   Footer: lograven.io
//
// TODO Month 5: Implement this page.

export default function Landing() {
  return <div>LogRaven Landing Page — TODO Month 5</div>
}
EOF

cat > frontend/src/pages/Dashboard.tsx << 'EOF'
// LogRaven — Dashboard Page
//
// PURPOSE:
//   Shows all user investigations. The main LogRaven workspace.
//
// LAYOUT:
//   Top: "LogRaven" header with New Investigation button
//   Usage bar: investigations used vs plan limit
//   Table: name | status | files | highest severity | date | Actions
//   Empty state: "Create your first investigation" with illustration
//
// DATA:
//   useInvestigations() hook — paginated list from GET /api/v1/investigations
//
// TODO Month 1 Week 3: Implement this page.

export default function Dashboard() {
  return <div>LogRaven Dashboard — TODO Month 1 Week 3</div>
}
EOF

cat > frontend/src/pages/NewInvestigation.tsx << 'EOF'
// LogRaven — New Investigation Page
//
// PURPOSE:
//   Simple form to create a new investigation.
//   Just asks for a name, then redirects to Investigation detail page
//   where files can be uploaded.
//
// FORM:
//   Investigation name (required, 1-200 chars)
//   Submit -> POST /api/v1/investigations -> redirect to /investigation/{id}
//
// TODO Month 1 Week 3: Implement this page.

export default function NewInvestigation() {
  return <div>New LogRaven Investigation — TODO Month 1 Week 3</div>
}
EOF

cat > frontend/src/pages/Investigation.tsx << 'EOF'
// LogRaven — Investigation Detail Page
//
// PURPOSE:
//   Shows the investigation with its file list.
//   Allows uploading additional files and starting analysis.
//
// SECTIONS:
//   Header: investigation name + status badge
//   FileUploadZone: drag-and-drop area (only shown when status=draft)
//   FileList: uploaded files with source type badges and status
//   Run Analysis button: disabled until status=draft and >= 1 file
//
// KEY COMPONENT:
//   SourceTypeSelector per file — auto-suggests type from extension,
//   user can override. Type is sent with file to POST .../files
//
// TODO Month 1 Week 3: Implement this page.

export default function Investigation() {
  return <div>LogRaven Investigation Detail — TODO Month 1 Week 3</div>
}
EOF

cat > frontend/src/pages/JobStatus.tsx << 'EOF'
// LogRaven — Job Status Polling Page
//
// PURPOSE:
//   Shows live progress of a running LogRaven analysis.
//   Polls backend every 3 seconds until complete or failed.
//
// PROGRESS STAGES (shown as stepped progress bar):
//   Queued -> Parsing Files -> Rule Engine -> Correlation -> AI Analysis -> Building Report -> Done
//
// POLLING:
//   useJobStatus(investigation_id) hook
//   React Query refetchInterval: 3000ms when not terminal, false when complete/failed
//
// ON COMPLETE: auto-navigate to /report/{report_id} after 1.5s delay
// ON FAILED: show error with retry option and support contact
//
// TODO Month 1 Week 3: Implement this page.

export default function JobStatus() {
  return <div>LogRaven Analysis In Progress — TODO Month 1 Week 3</div>
}
EOF

cat > frontend/src/pages/Report.tsx << 'EOF'
// LogRaven — Report Page
//
// PURPOSE:
//   Displays the complete LogRaven security investigation report.
//   This is the main deliverable the client receives.
//
// SECTIONS (in order):
//   1. Header: LogRaven brand, investigation name, date, severity badge
//   2. Executive summary paragraph
//   3. Severity chart: SeverityChart pie/donut chart
//   4. Correlated findings (shown FIRST — highest priority):
//      Each CorrelationCard shows all contributing files
//   5. Individual findings sorted by severity: FindingCard per finding
//   6. MITRE ATT&CK coverage: MitreMatrix component
//   7. IOC reference table: IOCTable component
//   8. Download button: DownloadButton -> opens PDF URL
//
// TODO Month 4 Week 1: Implement this page.

export default function Report() {
  return <div>LogRaven Report — TODO Month 4 Week 1</div>
}
EOF

cat > frontend/src/pages/Auth/Login.tsx << 'EOF'
// LogRaven — Login Page
// Email + password form. On success: store JWT tokens in authStore, redirect to /dashboard.
// TODO Month 1 Week 1: Implement.

export default function Login() {
  return <div>LogRaven Login — TODO Month 1 Week 1</div>
}
EOF

cat > frontend/src/pages/Auth/Register.tsx << 'EOF'
// LogRaven — Register Page
// Email + password + confirm form. On success: auto-login, redirect to /dashboard.
// TODO Month 1 Week 1: Implement.

export default function Register() {
  return <div>LogRaven Register — TODO Month 1 Week 1</div>
}
EOF

# Components
cat > frontend/src/components/investigation/FileUploadZone.tsx << 'EOF'
// LogRaven — File Upload Drop Zone
//
// PURPOSE:
//   Drag-and-drop file upload area for adding log files to an investigation.
//   Supports multiple files dropped at once.
//   Client-side validation: file type and size before uploading.
//
// BEHAVIOR:
//   - Drag over: highlight zone with blue border
//   - Drop: validate each file, show SourceTypeSelector for each
//   - Click: open file browser (accepts same extension whitelist)
//   - Each accepted file shows preview: filename, size, SourceTypeSelector, remove button
//
// PROPS:
//   investigationId: string
//   onFileAdded: (file: InvestigationFile) => void
//   disabled: boolean (true when investigation is not in draft state)
//
// TODO Month 1 Week 3: Implement this component.

export default function FileUploadZone({ disabled = false }: { disabled?: boolean }) {
  return (
    <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
      <p className="text-gray-500">Drop log files here</p>
      <p className="text-sm text-gray-400 mt-1">EVTX, CSV, LOG, TXT, JSON — TODO</p>
    </div>
  )
}
EOF

cat > frontend/src/components/investigation/SourceTypeSelector.tsx << 'EOF'
// LogRaven — Source Type Selector
//
// PURPOSE:
//   Dropdown to tag each uploaded file with its log source type.
//   Auto-suggests type based on file extension.
//   User can override the auto-detected type.
//
// SOURCE TYPE OPTIONS:
//   windows_endpoint  — Windows Event Log (EVTX)
//   linux_endpoint    — Linux auth.log / syslog
//   firewall          — Palo Alto, Fortinet, Cisco ASA
//   network           — NetFlow, IDS/IPS
//   web_server        — Nginx / Apache
//   cloudtrail        — AWS CloudTrail
//
// AUTO-SUGGEST LOGIC:
//   .evtx -> windows_endpoint
//   .json -> cloudtrail
//   .log / .txt -> linux_endpoint (with manual override encouraged)
//
// PROPS:
//   filename: string (for auto-suggest)
//   value: string
//   onChange: (sourceType: string) => void
//
// TODO Month 1 Week 3: Implement this component.

export default function SourceTypeSelector({ onChange }: { onChange: (t: string) => void }) {
  return (
    <select onChange={e => onChange(e.target.value)} className="border rounded px-2 py-1 text-sm">
      <option value="">Select source type...</option>
      <option value="windows_endpoint">Windows Endpoint</option>
      <option value="linux_endpoint">Linux Endpoint</option>
      <option value="firewall">Firewall</option>
      <option value="network">Network</option>
      <option value="web_server">Web Server</option>
      <option value="cloudtrail">AWS CloudTrail</option>
    </select>
  )
}
EOF

cat > frontend/src/components/investigation/FileList.tsx << 'EOF'
// LogRaven — File List Component
// Shows uploaded files with source type badge and parse status.
// TODO Month 1 Week 3: Implement.

export default function FileList() {
  return <div>File List — TODO</div>
}
EOF

cat > frontend/src/components/reports/FindingCard.tsx << 'EOF'
// LogRaven — Finding Card Component
//
// PURPOSE:
//   Displays a single LogRaven security finding.
//
// LAYOUT:
//   Top row: severity badge | MITRE technique ID (clickable link to ATT&CK) | finding_type badge
//   Title: bold, 1-2 lines
//   Description: plain English, 2-3 sentences
//   IOCs: inline tags (IP addresses, hashes, domains)
//   Remediation: italic, action-oriented
//   Source files: small badges showing which log files contributed
//
// PROPS:
//   finding: FindingSchema
//
// TODO Month 4 Week 1: Implement this component.

export default function FindingCard() {
  return <div className="border rounded p-4">Finding Card — TODO Month 4 Week 1</div>
}
EOF

cat > frontend/src/components/reports/CorrelationCard.tsx << 'EOF'
// LogRaven — Correlation Card Component
//
// PURPOSE:
//   Displays a correlated finding that spans multiple log source files.
//   This is the most important LogRaven finding type.
//   Shown BEFORE individual findings in the report.
//
// LAYOUT:
//   Header: "CORRELATED FINDING" badge | Critical/High severity | source file count
//   Entity: "Entity: 185.220.101.42 (IP)" — the linking entity
//   Timeline: chronological list of events from each source file
//   ATT&CK: technique ID + name
//   Description: narrative explanation of the attack chain
//   Contributing files: badges showing each source type that contributed
//
// PROPS:
//   finding: CorrelatedFinding (includes source_files array)
//
// TODO Month 4 Week 1: Implement this component.

export default function CorrelationCard() {
  return (
    <div className="border-2 border-purple-500 rounded p-4 bg-purple-50">
      Correlation Card — Correlated Finding — TODO Month 4 Week 1
    </div>
  )
}
EOF

cat > frontend/src/components/reports/SeverityChart.tsx << 'EOF'
// LogRaven — Severity Distribution Chart
// Pie/donut chart showing finding counts per severity level.
// Uses recharts. Colors: critical=red, high=orange, medium=yellow, low=blue, info=gray
// TODO Month 4 Week 1: Implement.

export default function SeverityChart() {
  return <div>Severity Chart — TODO</div>
}
EOF

cat > frontend/src/components/reports/MitreMatrix.tsx << 'EOF'
// LogRaven — MITRE ATT&CK Coverage Matrix
// Shows all 14 ATT&CK tactics with triggered techniques highlighted.
// Triggered techniques shown in blue/red. Untriggered in gray.
// TODO Month 4 Week 1: Implement.

export default function MitreMatrix() {
  return <div>MITRE ATT&CK Matrix — TODO</div>
}
EOF

cat > frontend/src/components/reports/IOCTable.tsx << 'EOF'
// LogRaven — IOC Reference Table
// Table of all extracted IOCs: IP addresses, hashes, domains, usernames.
// Columns: Type | Value | Found In (source files)
// TODO Month 4 Week 1: Implement.

export default function IOCTable() {
  return <div>IOC Table — TODO</div>
}
EOF

cat > frontend/src/components/reports/DownloadButton.tsx << 'EOF'
// LogRaven — PDF Download Button
//
// PURPOSE:
//   Triggers download of the lograven-report-{uuid}.pdf
//
// BEHAVIOR:
//   1. Call reports.getDownloadUrl(report_id) -> GET /api/v1/reports/{id}/download
//   2. Response: {download_url: "http://localhost:8000/files/reports/..."}
//   3. Open download_url in new tab (browser handles PDF download)
//
// TODO Month 4 Week 1: Implement.

export default function DownloadButton({ reportId }: { reportId: string }) {
  return (
    <button className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
      Download PDF Report
    </button>
  )
}
EOF

cat > frontend/src/components/layout/Navbar.tsx << 'EOF'
// LogRaven — Navigation Bar
// Shows LogRaven logo, main nav links, user menu.
// Unauthenticated: Login + Get LogRaven buttons
// Authenticated: Dashboard | New Investigation | user menu (logout)
// TODO Month 1 Week 3: Implement.

export default function Navbar() {
  return (
    <nav className="bg-gray-900 text-white px-6 py-4 flex justify-between items-center">
      <span className="text-blue-400 font-bold text-xl">LogRaven</span>
      <span className="text-gray-400 text-sm">Watch your logs. Find the threat.</span>
    </nav>
  )
}
EOF

cat > frontend/src/components/layout/PageWrapper.tsx << 'EOF'
// LogRaven — Page Wrapper
// Wraps page content with consistent padding and max-width.
// TODO Month 1 Week 3: Implement.

export default function PageWrapper({ children }: { children: React.ReactNode }) {
  return <main className="max-w-6xl mx-auto px-4 py-8">{children}</main>
}
EOF

cat > frontend/src/components/ui/Badge.tsx << 'EOF'
// LogRaven — Severity Badge Component
// Color-coded severity indicator.
// critical=red, high=orange, medium=yellow, low=blue, informational=gray
// TODO Month 1 Week 3: Implement.

export default function Badge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    critical: 'bg-red-100 text-red-800',
    high:     'bg-orange-100 text-orange-800',
    medium:   'bg-yellow-100 text-yellow-800',
    low:      'bg-blue-100 text-blue-800',
    informational: 'bg-gray-100 text-gray-800',
  }
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[severity] || colors.informational}`}>
      {severity.toUpperCase()}
    </span>
  )
}
EOF

cat > frontend/src/components/ui/StatusPill.tsx << 'EOF'
// LogRaven — Job Status Pill
// Shows investigation/file status as a colored pill.
// draft=gray, queued=yellow, processing=blue (animated), complete=green, failed=red
// TODO Month 1 Week 3: Implement.

export default function StatusPill({ status }: { status: string }) {
  return <span className="px-2 py-1 rounded-full text-xs bg-gray-100">{status}</span>
}
EOF

cat > frontend/src/components/ui/ProgressBar.tsx << 'EOF'
// LogRaven — Analysis Progress Bar
// Stepped progress bar for JobStatus page.
// Steps: Queued -> Parsing -> Rule Engine -> Correlation -> AI Analysis -> Report -> Done
// TODO Month 1 Week 3: Implement.

export default function ProgressBar({ stage }: { stage: string }) {
  return (
    <div className="w-full bg-gray-200 rounded-full h-2">
      <div className="bg-blue-600 h-2 rounded-full w-1/4 transition-all" />
    </div>
  )
}
EOF

cat > frontend/src/components/ui/EmptyState.tsx << 'EOF'
// LogRaven — Empty State Component
// Shown when a list has no items (no investigations, no reports, etc.)
// TODO Month 1 Week 3: Implement.

export default function EmptyState({ message, actionLabel, onAction }: {
  message: string, actionLabel?: string, onAction?: () => void
}) {
  return (
    <div className="text-center py-16">
      <p className="text-gray-500">{message}</p>
      {actionLabel && (
        <button onClick={onAction} className="mt-4 text-blue-600 hover:underline">{actionLabel}</button>
      )}
    </div>
  )
}
EOF

# Hooks
cat > frontend/src/hooks/useInvestigation.ts << 'EOF'
// LogRaven — useInvestigation Hook
// Fetches a single investigation with file list.
// GET /api/v1/investigations/{id}
// TODO Month 1 Week 3: Implement.

export function useInvestigation(id: string) {
  // TODO: implement with React Query
  return { investigation: null, isLoading: true, error: null }
}
EOF

cat > frontend/src/hooks/useFileUpload.ts << 'EOF'
// LogRaven — useFileUpload Hook
// Handles file upload mutation.
// POST /api/v1/investigations/{id}/files (multipart + source_type)
// Returns: { upload, isUploading, error }
// TODO Month 1 Week 3: Implement.

export function useFileUpload(investigationId: string) {
  // TODO: implement with React Query useMutation
  return { upload: async () => {}, isUploading: false, error: null }
}
EOF

cat > frontend/src/hooks/useJobStatus.ts << 'EOF'
// LogRaven — useJobStatus Polling Hook
//
// PURPOSE:
//   Polls investigation status every 3 seconds until analysis is complete.
//   The most technically critical frontend hook.
//
// POLLING LOGIC:
//   React Query refetchInterval: 3000ms when status is NOT terminal
//   Terminal states: complete | failed -> refetchInterval becomes false (stops polling)
//
// RETURNS:
//   status: string (queued/parsing/rule_engine/correlation/ai_analysis/complete/failed)
//   progress_stage: string (for progress bar display)
//   report_id: string | null (available when complete)
//   files: InvestigationFile[] (with per-file status)
//   isLoading: boolean
//   error: Error | null
//
// TODO Month 1 Week 3: Implement.

export function useJobStatus(investigationId: string) {
  // TODO: implement with React Query, refetchInterval for polling
  return { status: 'queued', progress_stage: null, report_id: null, isLoading: true }
}
EOF

cat > frontend/src/hooks/useReport.ts << 'EOF'
// LogRaven — useReport Hook
// Fetches full report with all findings from GET /api/v1/reports/{id}
// TODO Month 4 Week 1: Implement.

export function useReport(reportId: string) {
  return { report: null, isLoading: true, error: null }
}
EOF

cat > frontend/src/hooks/useAuth.ts << 'EOF'
// LogRaven — useAuth Hook
// Provides login, logout, and current user from authStore.
// Handles token refresh transparently via Axios interceptor in api/client.ts
// TODO Month 1 Week 1: Implement.

export function useAuth() {
  return { user: null, login: async () => {}, logout: () => {}, isAuthenticated: false }
}
EOF

# API
cat > frontend/src/api/client.ts << 'EOF'
// LogRaven — Axios HTTP Client
//
// PURPOSE:
//   Single Axios instance used by ALL LogRaven API call files.
//   Never create another Axios instance elsewhere.
//
// CONFIGURATION:
//   baseURL: from VITE_API_URL env var (default: http://localhost:8000)
//
// REQUEST INTERCEPTOR:
//   Reads JWT access token from Zustand authStore.
//   Adds: Authorization: Bearer {access_token} to every request.
//
// RESPONSE INTERCEPTOR:
//   On 401 response:
//     1. Attempt silent token refresh via POST /auth/refresh
//     2. If refresh succeeds: retry original request with new token
//     3. If refresh fails: clear authStore, redirect to /login
//   Users are never unexpectedly logged out during an active session.
//
// TODO Month 1 Week 1: Implement this file.

import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

// TODO: Add request interceptor (JWT injection)
// TODO: Add response interceptor (token refresh on 401)

export default client
EOF

cat > frontend/src/api/auth.ts << 'EOF'
// LogRaven — Auth API Functions
// register(email, password) -> TokenResponse
// login(email, password) -> TokenResponse
// refresh(refresh_token) -> {access_token}
// TODO Month 1 Week 1: Implement.

import client from './client'

export const authApi = {
  register: (email: string, password: string) =>
    client.post('/auth/register', { email, password }),
  login: (email: string, password: string) =>
    client.post('/auth/login', { email, password }),
  refresh: (refreshToken: string) =>
    client.post('/auth/refresh', { refresh_token: refreshToken }),
}
EOF

cat > frontend/src/api/investigations.ts << 'EOF'
// LogRaven — Investigations API Functions
// All investigation and file upload API calls.
// TODO Month 1 Week 3: Implement.

import client from './client'

export const investigationsApi = {
  create: (name: string) =>
    client.post('/api/v1/investigations', { name }),
  list: (page = 1, limit = 20) =>
    client.get('/api/v1/investigations', { params: { page, limit } }),
  get: (id: string) =>
    client.get(`/api/v1/investigations/${id}`),
  uploadFile: (id: string, file: File, sourceType: string) => {
    const form = new FormData()
    form.append('file', file)
    form.append('source_type', sourceType)
    return client.post(`/api/v1/investigations/${id}/files`, form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  removeFile: (id: string, fileId: string) =>
    client.delete(`/api/v1/investigations/${id}/files/${fileId}`),
  analyze: (id: string) =>
    client.post(`/api/v1/investigations/${id}/analyze`),
  getStatus: (id: string) =>
    client.get(`/api/v1/investigations/${id}/status`),
}
EOF

cat > frontend/src/api/reports.ts << 'EOF'
// LogRaven — Reports API Functions
// TODO Month 4 Week 1: Implement.

import client from './client'

export const reportsApi = {
  get: (id: string) =>
    client.get(`/api/v1/reports/${id}`),
  getDownloadUrl: (id: string) =>
    client.get(`/api/v1/reports/${id}/download`),
}
EOF

# Store
cat > frontend/src/store/authStore.ts << 'EOF'
// LogRaven — Auth State Store (Zustand)
//
// PURPOSE:
//   Global authentication state for LogRaven frontend.
//   Stores JWT tokens and current user info.
//
// STATE:
//   user: { id, email, tier } | null
//   accessToken: string | null
//   refreshToken: string | null
//   isAuthenticated: boolean
//
// ACTIONS:
//   setTokens(access, refresh) — called after login/register/refresh
//   setUser(user) — called after fetching /user/me
//   logout() — clears all auth state, redirects to /login
//
// NOTE: Tokens stored in memory (Zustand state), NOT localStorage.
//       localStorage is insecure for tokens (XSS risk).
//       Tokens are lost on page refresh — handled by refresh token flow.
//
// TODO Month 1 Week 1: Implement this file.

import { create } from 'zustand'

interface AuthState {
  user: { id: string; email: string; tier: string } | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  setTokens: (access: string, refresh: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  setTokens: (access, refresh) =>
    set({ accessToken: access, refreshToken: refresh, isAuthenticated: true }),
  logout: () =>
    set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false }),
}))
EOF

# Types
cat > frontend/src/types/investigation.ts << 'EOF'
// LogRaven — Investigation TypeScript Types

export interface InvestigationFile {
  id: string
  filename: string
  source_type: string
  log_type: string | null
  status: 'pending' | 'parsing' | 'parsed' | 'failed'
  event_count: number | null
}

export interface Investigation {
  id: string
  name: string
  status: 'draft' | 'queued' | 'processing' | 'complete' | 'failed'
  correlation_enabled: boolean
  files: InvestigationFile[]
  created_at: string
}

export interface InvestigationStatus {
  id: string
  status: string
  progress_stage: string | null
  files: InvestigationFile[]
}
EOF

cat > frontend/src/types/report.ts << 'EOF'
// LogRaven — Report TypeScript Types

export interface Finding {
  id: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'informational'
  title: string
  description: string
  mitre_technique_id: string | null
  mitre_technique_name: string | null
  mitre_tactic: string | null
  iocs: string[]
  remediation: string | null
  finding_type: 'correlated' | 'single'
  source_files: string[]
  confidence: number
}

export interface Report {
  id: string
  investigation_id: string
  summary: string | null
  severity_counts: Record<string, number>
  correlated_findings: Finding[]
  single_source_findings: Finding[]
  mitre_techniques: string[]
  created_at: string
}
EOF

cat > frontend/src/types/user.ts << 'EOF'
// LogRaven — User TypeScript Types

export interface User {
  id: string
  email: string
  tier: 'free' | 'pro' | 'team'
  created_at: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}
EOF

cat > frontend/src/types/api.ts << 'EOF'
// LogRaven — API Response TypeScript Types

export interface ErrorResponse {
  error: string
  code: string
  detail?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  limit: number
}

export interface DownloadResponse {
  download_url: string
  expires_in: number
}
EOF

# =============================================================================
# DONE
# =============================================================================
cd ..

echo ""
echo "=============================================="
echo "  LogRaven scaffold created successfully!"
echo "=============================================="
echo ""
echo "  Project: ./${PROJECT}/"
echo ""
echo "  NEXT STEPS:"
echo "  1. cd ${PROJECT}"
echo "  2. cp .env.example .env"
echo "  3. Add your ANTHROPIC_API_KEY to .env"
echo "  4. git init && git add . && git commit -m 'LogRaven scaffold'"
echo "  5. Create private GitHub repo named lograven and push"
echo "  6. Clone EVTX test data:"
echo "     git clone https://github.com/sbousseaden/EVTX-ATTACK-SAMPLES test-data"
echo "  7. Open Cursor in lograven/"
echo "  8. Tag memory-bank files and run Cursor Prompt 1 from master doc"
echo ""
echo "  STRUCTURE:"
find ${PROJECT} -type f | sort | head -80
echo ""
echo "  Total files created: $(find ${PROJECT} -type f | wc -l)"
echo ""