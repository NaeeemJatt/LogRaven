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
