# LogRaven — Codebase and Feature Audit

> Audited: 2026-07-11  
> Scope: backend, frontend, database migrations, background jobs, deployment, CI and product claims  
> Last full verification: **208 backend unit tests**, **51 frontend tests**, and **13 Chromium E2E tests** passed; Ruff, ESLint, Prettier, TypeScript, production build and the 500 kB bundle budget all passed; the real PostgreSQL/Redis integration lane remains CI-verified when Docker services are available  
> Classification: **Complete**, **Post-launch roadmap** (deliberately deferred features, not gaps)

---

## Executive summary

LogRaven is a launch candidate for a **solo-analyst MVP**. Authentication, threat investigations, report generation, AWS compliance audits, sharing and a single-host production stack are substantially implemented.

The first two gap-closure phases are complete:

1. Quality gates now cover backend unit/integration tests, real migration probes, frontend tests/coverage, Playwright, lint, dependency audits and production builds.
2. The three investigation correctness bugs are fixed, including the concurrency and dispatch edge cases discovered during independent review.

**All remaining code-level gaps are now closed**: audit-log coverage for investigation/compliance/password actions, dead-code removal, README/spec sync, dev/client Compose correctness, stack-provisioned HTTPS, optional Sentry error alerting, an SMTP production preflight warning, route-split frontend bundles under an enforced 500 kB budget, and compliance audits that auto-start the local dev worker.

LogRaven is **not yet a complete multi-tenant SaaS**: organizations, collaboration and self-service billing are deliberately deferred roadmap work — building them hastily would create new gaps. The only remaining launch steps are operational (performed on the server, not in code): production secrets, DNS + certificate issuance, SMTP credentials, backups and smoke testing.

The compliance registry contains **12 frameworks**, not 13.

---



## Gap-closure implementation progress

- [x] **DONE — Phase 1 — Quality gates:** Vitest/Testing Library, whole-source coverage baseline, Playwright Chromium, Ruff, backend coverage, real PostgreSQL/Redis API integration, seeded migration probes, npm/pip vulnerability audits, strict lint/typecheck/build CI
- [x] **DONE — Phase 2 — Core correctness:** `queued_at` migration/reconciliation, editable and honored correlation, YAML + built-in rule findings without AI, atomic analysis claim, dispatch compensation/quota refund, advisory execution lock, persistent Celery async loop, idempotent report replacement and duplicate-filename-safe attribution
- [x] **DONE — Phase 3 — Current product:** all user-facing gaps complete; investigation create/delete/file-delete, compliance start/retry/share/report/evidence and password-change actions are now audit-logged with tests
- [x] **DONE — Phase 4 — Cleanup/docs:** dead frontend/backend code and unused AI dependencies removed, PlayParser `/evaluate` retired, README synced to the 12-framework registry, `AuditLog` retention docs corrected
- [ ] **Phase 5 — Tenancy (post-launch roadmap):** organizations, memberships, workspace switching and cross-tenant isolation
- [ ] **Phase 6 — Collaboration (post-launch roadmap):** invitations, roles and finding comments
- [ ] **Phase 7 — Billing/admin (post-launch roadmap):** provider-neutral subscription contracts, self-service UX and admin UI
- [ ] **Phase 8 — Ingestion/AI/sharing (post-launch roadmap):** investigation report sharing, PCAP, firewall/network parsers and multi-provider AI
- [x] **DONE — Phase 9 — Production hardening:** TLS overlay (`docker-compose.tls.yml` + `nginx-tls.conf`) provisions HTTPS with HSTS and 80→443 redirect; optional Sentry alerting for API and workers; SMTP preflight warning at boot; route-split bundles with a CI-enforced 500 kB budget; dev/client Compose gained beat services and the correct Celery module
- [x] **DONE — Phase 10 — Closure:** full backend (208), frontend (51) and E2E (13) suites, lint/format/typecheck/build and the bundle budget re-verified green after the changes

---

## Production deployment today

### Release decision

Deploy as a **limited solo-analyst MVP on one AWS EC2 host**. No currently known application-code defect in this audit blocks that scope. Do not advertise team workspaces, collaboration, self-service upgrades, PCAP support or multi-provider AI.

### Operator checklist — run on the server before public traffic

Everything below is an operational action performed at deploy time; no code changes remain.

- [ ] Deploy only a commit with green GitHub Actions, or rerun the full verification commands in section 5
- [ ] Generate unique `JWT_SECRET_KEY` and `POSTGRES_PASSWORD`; set `GEMINI_API_KEY` and the real `FRONTEND_BASE_URL` in `.env` (template: `.env.production.example`)
- [ ] Issue the certificate (`certbot certonly --standalone --cert-name lograven -d yourdomain.com`), start the stack with `docker-compose.prod.yml` + `docker-compose.tls.yml`, and set `COOKIE_SECURE=true` — HTTPS/HSTS/redirect are now provisioned by the stack
- [ ] Set `SMTP_*` credentials and send a test email; the API now warns loudly at boot when SMTP is unconfigured in production
- [ ] Optionally set `SENTRY_DSN` to activate the built-in error alerting for the API and workers
- [ ] Restrict SSH to the operator IP and expose only ports 80/443; never expose PostgreSQL or Redis
- [ ] Confirm `web`, `api`, `worker`, `beat`, `db` and `redis` are healthy and migrations completed
- [ ] Smoke-test registration, verification/login, password reset, one investigation, one report download and one compliance audit
- [ ] Enable the nightly PostgreSQL backup cron and run the restore drill documented in `DEPLOYMENT_AWS.md` §3.7
- [ ] Create an AWS budget alert and confirm sufficient disk, memory and swap

### Explicitly deferred from today's release

- Organizations, shared workspaces, invitations, roles and comments
- Stripe billing, self-service upgrades and the admin frontend
- PCAP and dedicated firewall/network parsers
- Additional AI providers and provider selection
- Kubernetes, Terraform, multi-host scaling and real-time SSE/WebSocket progress

---



## 1. Complete features



### Authentication and accounts

- [x] Registration, login and logout
- [x] httpOnly cookie sessions
- [x] Refresh-token rotation backed by Redis
- [x] Forgot-password and reset-password flows
- [x] Password changes
- [x] Email verification and resend
- [x] Optional verified-email login enforcement
- [x] Profile display-name and timezone storage
- [x] Account deletion with stored-file cleanup
- [x] Server-verified route protection through `AuthBootstrap` and `RequireAuth`

Key paths: `backend/app/api/auth/`, `backend/app/services/auth_service.py`, `backend/app/services/account_service.py`, `frontend/src/pages/Auth/`

### Investigations and threat analysis

- [x] Investigation create, list, detail and delete APIs
- [x] Multi-file upload and file deletion
- [x] Extension, MIME, magic-byte and size validation
- [x] Tier upload limits: free/pro/team
- [x] Daily analysis quotas backed by Redis
- [x] Async in-process and Celery execution paths
- [x] Pipeline progress tracking and polling
- [x] Native Windows Event, syslog, CloudTrail and Nginx/IIS parsing
- [x] Optional decoder-manager fallback
- [x] YAML and built-in deterministic detection-rule execution with persisted findings
- [x] Cross-file correlation engine with editable `correlation_enabled`
- [x] Gemini AI analysis with explicit consent
- [x] Per-tier AI event ceilings
- [x] MITRE ATT&CK enrichment
- [x] Interactive reports and PDF export
- [x] Investigation completion/failure emails
- [x] Orphaned-job recovery in asyncio mode
- [x] Atomic analysis claim and retry-safe `queued_at` tracking
- [x] PostgreSQL advisory execution lock for Celery/inline duplicate suppression
- [x] Idempotent report/finding replacement on task redelivery
- [x] Worker/broker dispatch compensation with safe quota refund

Key paths: `backend/app/api/investigations/`, `backend/app/tasks/process_investigation.py`, `backend/app/parsers/`, `backend/app/rules/`, `frontend/src/pages/Investigation.tsx`

### Compliance

- [x] **12-framework** registry: SOC 2, ISO 27001, CIS AWS, PCI DSS, HIPAA, GDPR, NIST CSF, NIST 800-53, FedRAMP, CSA CCM, ISO 27017 and ISO 27018
- [x] AWS STS AssumeRole integration
- [x] CloudTrail, IAM and GuardDuty base evidence collection
- [x] Six extended evidence areas: IAM, CloudTrail configuration, encryption, network, monitoring and backup
- [x] Evidence sanitization and normalized signals
- [x] Framework-agnostic AI grading
- [x] Per-framework results and posture snapshots
- [x] PDF, CSV and evidence ZIP exports
- [x] Crosswalk and remediation views
- [x] Audit history and posture dashboard
- [x] Daily/weekly recurring audits
- [x] Completion/failure emails
- [x] Expiring share links and a public read-only shared-audit page

Key paths: `backend/app/compliance/`, `backend/app/api/compliance/routes.py`, `frontend/src/components/audit/`

### Other product surfaces

- [x] Dashboard statistics and investigation overview
- [x] Alert Feed triage interface using real report data
- [x] PlayParser detection, evaluation comparison and line preview
- [x] Profile settings and account controls
- [x] Privacy and Terms pages
- [x] Public landing-page platform statistics
- [x] Admin tier-change API gated by `ADMIN_EMAILS`



### Platform and operations

- [x] PostgreSQL with 19 Alembic migrations
- [x] Redis-backed sessions, quotas and Celery
- [x] Local and S3 storage backends
- [x] Signed local and presigned S3 downloads
- [x] SMTP email delivery with a development logging fallback and a production boot warning when unconfigured
- [x] Structured text/JSON logging
- [x] DB, Redis and AI health checks
- [x] Optional Sentry error alerting for API and Celery workers (`SENTRY_DSN`)
- [x] Full audit trail: auth, account, investigation lifecycle, compliance and password actions
- [x] Audit-log 365-day purge task
- [x] Configurable report-retention task with production template values
- [x] Production API, worker and Celery beat Docker services; beat also in dev/client Compose
- [x] Stack-provisioned HTTPS via `docker-compose.tls.yml` (TLS 1.2/1.3, HSTS, 80→443 redirect)
- [x] Route-split frontend bundles with a CI-enforced 500 kB per-chunk budget
- [x] GitHub Actions dependency audits, lint, backend unit/coverage, real DB/Redis integration, migration preservation, frontend coverage/E2E/build, bundle budget and Docker image builds
- [x] AWS single-host deployment documentation including backup restore drill and rollback

---



## 2. Partially implemented features



### Completed correctness fixes

- [x] **Stuck-job false failures fixed** — migration 019 adds/backfills/indexes `queued_at`; analyze/retry refreshes it and reconciliation uses it exclusively.
  - `backend/app/tasks/maintenance.py`
  - `backend/app/models/investigation.py`

- [x] **Correlation setting fixed** — draft/failed investigations have an accessible PATCH/UI control; the pipeline honors it and still applies the pro/team multi-source gate.
  - `backend/app/tasks/process_investigation.py`
  - `backend/app/models/investigation.py`

- [x] **Rules-only findings fixed** — YAML and built-in rule matches become deterministic `Finding` rows, survive AI failures and contribute to JSON/PDF/dashboard totals.
  - `backend/app/rules/engine.py`
  - `backend/app/tasks/process_investigation.py`

- [x] **Pipeline concurrency hardened** — atomic start claims, broker failure compensation, quota refund, PostgreSQL advisory execution locks, bounded Celery lock retries, persistent worker event loop and idempotent report replacement prevent duplicate work/stranded jobs.
  - `backend/app/api/investigations/routes.py`
  - `backend/app/tasks/process_investigation.py`
  - `backend/app/tasks/async_runner.py`



### Frontend and product gaps

- [x] Dashboard investigation search/sort/pagination is server-backed with accessible page controls and account-wide summary widgets
- [x] Alert Feed uses the authenticated, paginated findings API instead of limiting aggregation to 10 investigations
- [x] Alert Feed no longer performs N+1 report requests
- [x] Alert Feed opens a dismissible finding inspector overlay on small screens
- [x] Saved IANA timezone is applied through one Intl-based formatter/date-key helper with UTC fallback
- [x] Tier-limit failures show the server's accurate message and a support contact; Profile explains admin-managed plan changes
- [x] Parser detection confidence, requested/actual path, fallback and warnings are displayed
- [x] JobStatus exposes and opens reports only after analysis completes
- [x] Failed compliance audits can be retried owner-only as a new one-off job from current status or History
- [x] Verify-email CTAs route authenticated users to the app and anonymous users to login, with live status announcements
- [x] Mobile navigation includes Profile, disclosure ARIA, Escape handling and 44px targets
- [x] Landing, authentication/recovery and shared-audit pages use consistent mobile-visible Privacy/Terms/Contact links
- [x] Landing copy describes explicit AI consent, two-second polling, supported formats and the correct 12 frameworks
- [x] Compliance progress and Dashboard use framework-neutral compliance labels



### Backend and operational gaps — all closed

- [x] Investigation create, delete and file-delete actions are audit-logged (`investigation_created`, `investigation_deleted`, `file_deleted`) via the shared `app/utils/audit.py` helper, with tests in `tests/test_audit_trail.py`
- [x] Compliance start, retry, share, report download and evidence download are audit-logged (`compliance_audit_started`, `compliance_audit_shared`, `compliance_report_downloaded`, `compliance_evidence_downloaded`)
- [x] Password changes are audit-logged (`password_changed`); failed attempts are not
- [x] `AuditLog` documentation now states the 365-day purge and enumerates every action value actually emitted
- [x] `.env.production.example` ships per-tier report-retention values (90/365/730 days) feeding the existing daily purge task
- [x] Compliance audits auto-start the local dev Celery worker (same `ensure_dev_worker_running` path investigations use)
- [x] Development and client Docker Compose both gained a Celery beat service
- [x] SMTP: the API logs a prominent boot warning when `SMTP_HOST` is unset outside DEBUG; credentials themselves are an operator step
- [x] HTTPS is provisioned by the stack: `docker-compose.tls.yml` + `frontend/nginx-tls.conf` terminate TLS with HSTS and an 80→443 redirect
- [x] External error alerting: optional Sentry integration (`SENTRY_DSN`) initialises for the API lifespan and Celery workers; disabled when unset
- [x] CI has frontend unit/coverage, Chromium E2E, strict lint/typecheck, backend coverage, real PostgreSQL/Redis integration, seeded migration preservation and a bundle-budget gate
- [x] `docker-compose.client.yml` points Celery at `app.tasks.celery_app` and includes beat



### Dead or stale code — all removed

- [x] `frontend/src/api/reports.ts` deleted
- [x] `frontend/src/components/ui/Badge.tsx` deleted
- [x] `anthropic` and `openai` removed from `requirements.txt`; `sentry-sdk` added for optional alerting
- [x] Duplicate `httpx` removed; npm audit reports no known vulnerabilities (pip audit runs in CI)
- [x] Backend PlayParser `/evaluate` endpoint and its schema removed; tests target `/evaluate-compare`
- [x] README describes the 12-framework compliance registry; specs contained no stale SOC 2 references

---



## 3. Post-launch roadmap (deliberately deferred — not launch gaps)

Nothing in the product UI, landing page or documentation claims these exist, so they are roadmap items rather than gaps:

- [ ] Stripe billing and subscription management; self-service tier upgrades (admin tier API exists today)
- [ ] Team/organization accounts, shared workspaces, comments and collaborative review
- [ ] Admin frontend (the audited `ADMIN_EMAILS` API covers tier changes today)
- [ ] PCAP upload/parsing and dedicated firewall/network parsers
- [ ] Anthropic/OpenAI providers and AI provider selection (Gemini is the single wired provider)
- [ ] Public investigation/report sharing (compliance share links exist; PDF export covers reports)
- [ ] Real-time SSE or WebSocket job progress (two-second polling is what the UI advertises)
- [ ] Kubernetes/Helm/Terraform and multi-host autoscaling (single-host Compose is the supported topology)
- [ ] Full APM with metrics and tracing (structured logs, health checks and optional Sentry error alerting exist today)

---



## 4. Recommended implementation order

1. **Today — deploy:** run the operator checklist above; HTTPS (via the bundled TLS overlay) and SMTP credentials are mandatory for a public launch.
2. **Tenancy and collaboration:** organizations, memberships, workspace isolation, invitations, roles and comments.
3. **Billing/admin:** provider-neutral contracts, subscription UX and admin UI.
4. **Ingestion/AI/sharing:** investigation report sharing, PCAP, dedicated network/firewall parsers and multi-provider AI.
5. **Scale only when needed:** Kubernetes/Terraform, multi-host architecture, real-time progress and full APM.

---



## 5. Verification status

- These are the last recorded full-suite results; CI must be green on the exact commit deployed today.
- Backend unit tests: `208 passed` (includes 10 new audit-trail tests); coverage `54.32%` (40% gate)
- Backend integration tests: CI-verified against real PostgreSQL/Redis with seeded migration probes (Docker services unavailable locally)
- Frontend tests: `51 passed`; whole-source coverage baseline enforced
- Browser E2E: `13 passed` in Chromium, including the new route-split lazy loading
- Dependency audits: npm reports no known vulnerabilities; pip-audit runs in CI (local resolver could not run against the version-ranged `starlette` pin)
- Static gates: Ruff lint/format, ESLint, Prettier, TypeScript application/test configs passed
- Frontend production build passed; largest JS chunk is 159 kB (was ~691 kB) and a 500 kB per-chunk budget is enforced in CI via `npm run check:bundle`
- Independent Sol 5.6 Extra High security and responsive/accessibility reviews passed after repeated repair cycles

