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
