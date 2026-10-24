# LogRaven v2.5.0: Zero-Setup External Domain Scanner & DAST Importer Capability Plan

## 1. CAPABILITY SUMMARY

LogRaven v2.5.0 introduces **zero-setup external domain scanning** and **DAST (OWASP ZAP / Burp Suite) telemetry ingestion**. 

- **External Domain Teaser Scanner (Pipeline B - Compliance & Posture)**: Security teams and consultants (e.g., Obsidian SOC Group) can input any public domain or web URL (e.g., `https://client.com`) without requiring cloud API keys. Within 30 seconds, LogRaven executes 12 non-intrusive network/HTTP/TLS/DNS checks, maps findings to OWASP Web 2025 and compliance frameworks (SOC 2, ISO 27001), renders an Internet-to-Application Attack Path DAG, generates 1-click remediation scripts (Nginx, Cloudflare, AWS WAF), and produces a 1-page branded Executive Teaser PDF.
- **DAST Importer (Pipeline A - Ingestion & SIEM)**: Ingests automated web vulnerability scan exports from OWASP ZAP (JSON) and Burp Suite (XML), normalizes findings into standard `NormalizedEvent` entities, applies deterministic CWE/OWASP rules, correlates root causes via Gemini AI, and maps exposures to MITRE ATT&CK (`T1190`, `T1059`, etc.).

---

## 2. ARCHITECTURAL & SYSTEM INVARIANTS

### 2.1 Reusability & Zero Disconnection
Rather than building an isolated microservice, this capability reuses LogRaven's existing foundational pipelines:
- **Pipeline B Integration**: The external scanner is registered as a first-class `BaseCloudCollector` (`provider="external_domain"`) inside `app.compliance.collectors.factory.get_collector()`. Audit jobs, status polling, AI control grading, crosswalking, exception handling, and evidence storage work natively without modifying core Celery mechanics.
- **Pipeline A Integration**: The DAST importer is registered as a first-class `BaseParser` (`parser="dast"`) inside `PARSER_REGISTRY`. File uploads, format sniffing, quality detection, rules evaluation, AI investigation, and report generation follow the identical lifecycle as EVTX, Syslog, and CloudTrail logs.

### 2.2 Security & Safety Guardrails (Non-Negotiable)
1. **Strict SSRF Defense in `ExternalDomainCollector`**:
   - Hostname is validated via `urllib.parse.urlparse()`.
   - Rejects raw IP literals, `.local`, `.internal`, and non-HTTP/HTTPS protocols.
   - Performs DNS resolution via `socket.getaddrinfo()` and validates each resolved IP using `ipaddress.ip_address(ip).is_global`.
   - Explicitly rejects loopback (`127.0.0.0/8`), private networks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local (`169.254.0.0/16`), and AWS/GCP/Azure instance metadata endpoints (`169.254.169.254`, `metadata.google.internal`).
2. **Non-Intrusive Scanning Only**:
   - Outbound scans send only passive HTTP `GET` and `HEAD` probes with strict 10s timeouts.
   - Identifies itself with a transparent user-agent: `LogRaven-Surface-Auditor/2.5 (+https://lograven.io)`.
   - No SQL injection payloads, fuzzing strings, or exploitation attempts are ever dispatched.
3. **Database Constraints & Schema Backward Compatibility**:
   - Alembic migration `024` broadens `cloud_accounts.provider` check constraints to permit `'external_domain'`.
   - `role_arn` column on `soc2_audit_jobs` stores synthetic identifier `external_domain:<domain>` without violating existing NOT NULL constraints.
   - Adds `target_domain: VARCHAR(512)` and `scan_scope_metadata: JSONB` to `cloud_accounts` and `soc2_audit_jobs`.

---

## 3. IMPLEMENTATION CONTRACT & FILE-BY-FILE SPECIFICATION

### Phase 1: Backend Zero-Setup External Domain Collector (Pipeline B)

#### 1. Database Migration: `backend/alembic/versions/024_add_external_domain_and_dast.py`
- **Actions**:
  - Add `target_domain` column (`VARCHAR(512)`, nullable=True) to `cloud_accounts` and `soc2_audit_jobs`.
  - Add `scan_scope_metadata` column (`JSONB`, default=`{}`) to `cloud_accounts` and `soc2_audit_jobs`.
  - Update `cloud_accounts.provider` check constraint (if applicable) to accept `'external_domain'`.

#### 2. Collector Implementation: `backend/app/compliance/collectors/external_domain.py`
- **Class**: `ExternalDomainCollector(BaseCloudCollector)`
- **Methods**:
  - `verify_credentials(credentials: dict) -> dict`:
    - Validates target domain syntax and verifies DNS resolution.
    - Applies SSRF guardrail: rejects private and cloud metadata IPs.
    - Returns `{"healthy": bool, "error": str | None, "account_id": domain, "provider": "external_domain"}`.
  - `collect_evidence(credentials: dict, start_date, end_date) -> dict`:
    - Executes the 12 passive surface checks concurrently via `asyncio.gather()`:
      1. **TLS / SSL Handshake**: TLS version (1.2/1.3), cipher suite, certificate expiry date (`notAfter`), self-signed check.
      2. **HTTP-to-HTTPS Redirection**: Requests `http://<domain>`, confirms 301/308 redirect to HTTPS.
      3. **HSTS Header**: Checks `Strict-Transport-Security`, `max-age` (warns if < 31536000), `includeSubDomains`.
      4. **Content Security Policy (CSP)**: Checks for `Content-Security-Policy`, flags `unsafe-inline`, `unsafe-eval`, or `*`.
      5. **Clickjacking Defense**: Checks `X-Frame-Options` (`DENY` / `SAMEORIGIN`) and `frame-ancestors`.
      6. **MIME Sniffing**: Verifies `X-Content-Type-Options: nosniff`.
      7. **Referrer & Permissions Policy**: Inspects `Referrer-Policy` and `Permissions-Policy`.
      8. **CORS Configuration**: Dispatches test `Origin: https://evil.example`, detects wildcard reflection and credentials allowance.
      9. **Cookie Security Attributes**: Evaluates `Set-Cookie` for `Secure`, `HttpOnly`, and `SameSite`.
      10. **Information Disclosure / Server Banners**: Inspects `Server`, `X-Powered-By`, `X-AspNet-Version` for technology/version disclosure.
      11. **Exposed Sensitive Files (Passive Safe Probe)**: Sends `HEAD` or safe `GET` to 8 paths (`/.env`, `/.git/config`, `/swagger.json`, `/openapi.json`, `/v2/api-docs`, `/graphql`, `/phpinfo.php`, `/server-status`). Checks for HTTP 200 with sensitive signatures.
      12. **DNS Email & Disclosure Hygiene**: Queries DNS TXT for SPF (`v=spf1`), DMARC (`v=DMARC1`), and probes `/.well-known/security.txt`.
    - Returns normalized raw evidence dictionary:
      ```python
      {
          "provider": "external_domain",
          "target_domain": domain,
          "tls": {...},
          "headers": {...},
          "cors": {...},
          "cookies": {...},
          "sensitive_paths": {...},
          "dns": {...},
          "collected_at": "..."
      }
      ```

#### 3. Factory Integration: `backend/app/compliance/collectors/factory.py`
- Modify `get_collector(provider: str)`:
  - If `provider == "external_domain"`: return `ExternalDomainCollector()`.

#### 4. Framework Definition: `backend/app/compliance/frameworks/owasp_web.py`
- Registers framework `"owasp_web"`:
  - Framework Name: `OWASP Web & External Surface Security (v2025)`
  - 12 automatable controls:
    - `OWASP-01`: Cryptographic & Transport Layer Security (TLS 1.2+, valid cert)
    - `OWASP-02`: HTTPS Enforcement & Redirection
    - `OWASP-03`: Strict-Transport-Security (HSTS)
    - `OWASP-04`: Content-Security-Policy (XSS & Injection Mitigation)
    - `OWASP-05`: Clickjacking Defense (`X-Frame-Options` / `frame-ancestors`)
    - `OWASP-06`: MIME-Type Sniffing Protection (`nosniff`)
    - `OWASP-07`: Referrer & Permissions Privacy
    - `OWASP-08`: Cross-Origin Resource Sharing (CORS) Security
    - `OWASP-09`: Session & Cookie Security (`Secure`, `HttpOnly`, `SameSite`)
    - `OWASP-10`: Server & Stack Technology Masking
    - `OWASP-11`: Sensitive Configuration & API Exposure Defense
    - `OWASP-12`: DNS Email Security (SPF & DMARC) & Security.txt
  - Mapped Crosswalks:
    - Crosswalk to SOC 2: `CC6.1` (Logical Access), `CC6.6` (Perimeter), `CC6.7` (Data Transmission)
    - Crosswalk to ISO 27001: `A.8.20` (Network Security), `A.8.21` (Network Services), `A.8.26` (App Security)

#### 5. Framework Registration: `backend/app/compliance/frameworks/__init__.py`
- Import and register `owasp_web` in `FRAMEWORK_REGISTRY` so it is included in all audit framework listings and crosswalk calculations.

#### 6. Signals Engine: `backend/app/compliance/signals.py`
- Extend `build_evidence_signals()` to synthesize external domain telemetry into deterministic boolean/numeric signals:
  - `tls_1_2_plus_enforced`: bool
  - `cert_valid_and_not_expiring`: bool
  - `hsts_enabled`: bool
  - `csp_header_present`: bool
  - `clickjacking_protection`: bool
  - `nosniff_enabled`: bool
  - `cookie_secure_httponly`: bool
  - `cors_not_wildcard`: bool
  - `no_exposed_sensitive_paths`: bool
  - `server_banner_redacted`: bool
  - `spf_dmarc_enforced`: bool
  - `security_txt_present`: bool

#### 7. Attack Path Graph Engine: `backend/app/compliance/graph/builder.py`
- Extend `build_attack_path_graph()`:
  - When audit has `provider == "external_domain"`, constructs an **Internet-to-App Perimeter DAG**:
    - `Node 1 (External)`: "Public Internet / Adversary"
    - `Node 2 (Network Perimeter)`: "DNS & TLS Gateway"
    - `Node 3 (Web Server / API)`: "Target Domain Application"
    - `Node 4 (Application Secrets & Auth)`: "Session Storage & Admin Endpoints"
  - **Toxic Combinations Detected**:
    - Missing HSTS + Cleartext HTTP accessible ➡️ Insecure Transport Vector
    - Wildcard CORS (`*`) + Missing `HttpOnly` Cookies ➡️ Cross-Site Data Exfiltration Vector
    - Exposed API Schema (`/swagger.json` or `/.env`) + Server Version Leak ➡️ Attack Surface Discovery Vector
  - Computes blast radius and marks `critical_path`.

#### 8. Remediation Catalog: `backend/app/compliance/remediation/catalog.py`
- Add dedicated remediation blueprints for all 12 OWASP Web controls.
- Provides copy-pasteable fix code in 4 formats:
  - **Nginx Config**: (`add_header Content-Security-Policy ...`, `ssl_protocols TLSv1.2 TLSv1.3;`, etc.)
  - **Cloudflare / Terraform**: (`cloudflare_ruleset`, `cloudflare_page_rule`)
  - **AWS CloudFront & WAF**: (`AWS-AWSManagedRulesCommonRuleSet`, Response Headers Policy)
  - **Apache / IIS**: (`Header set X-Content-Type-Options "nosniff"`)

#### 9. Executive Teaser PDF: `backend/app/compliance/report_generator.py`
- Implement `generate_teaser_report(job: AuditJob, summary: dict) -> bytes`:
  - 1-page high-impact executive summary designed for pitch decks / LinkedIn / client discovery.
  - Branded layout with Obsidian SOC Group / LogRaven co-branding.
  - Features:
    - Overall Security & Compliance Grade (A/B/C/F)
    - Top 3 Critical External Exposures identified
    - Attack Path & Blast Radius summary diagram
    - Actionable 72-hour remediation checklist
    - Clear Call to Action (CTA): "Upgrade to Continuous Cloud & Internal Monitoring"

---

### Phase 2: Backend OWASP ZAP & Burp Suite DAST Parser (Pipeline A)

#### 1. DAST Parser: `backend/app/parsers/dast_scanner.py`
- **Class**: `DASTReportParser(BaseParser)`
- **Methods**:
  - `parse(file_path: str) -> list[NormalizedEvent]`:
    - Detects whether file is JSON (ZAP) or XML (Burp).
    - Routes to `_parse_zap_json()` or `_parse_burp_xml()`.
  - `_parse_zap_json(data: dict) -> list[NormalizedEvent]`:
    - Iterates over `site[].alerts[]`.
    - Normalizes each instance into a `NormalizedEvent`:
      - `timestamp`: current scan timestamp or parsed date.
      - `event_type`: `"dast_finding"`
      - `source_ip`: site host / IP
      - `identity`: vulnerable parameter or URI path
      - `action`: HTTP method + URL
      - `severity`: mapped from ZAP risk code (0: Informational, 1: Low, 2: Medium, 3: High, 4: Critical)
      - `extra`: `{"cwe_id": ..., "alert": ..., "description": ..., "solution": ..., "evidence": ..., "plugin_id": ...}`
  - `_parse_burp_xml(xml_content: str) -> list[NormalizedEvent]`:
    - Parses XML `<issues><issue>...</issues>`.
    - Extracts `<type>`, `<name>`, `<host>`, `<path>`, `<location>`, `<severity>`, `<confidence>`, `<issueBackground>`, `<remediationBackground>`.
    - Normalizes into unified `NormalizedEvent`.

#### 2. Sniffer & Detector: `backend/app/parsers/sniff.py` & `backend/app/parsers/detector.py`
- In `sniff_upload()`:
  - Add signature detection for:
    - OWASP ZAP JSON: checks for `"@programName": "ZAP"` or top-level `"site"` containing `"alerts"`.
    - Burp Suite XML: checks for `<issues burpVersion=` or `<issue><serialNumber>`.
    - Sets `suggested_log_format = "dast"`.
- In `detect_candidates()`:
  - If DAST signature matched: returns `LogTypeCandidate(log_type="dast", confidence=0.98)`.

#### 3. Registry & Validation: `backend/app/parsers/registry.py` & `validators.py`
- In `registry.py`:
  - Register `"dast": DASTReportParser` in `PARSER_REGISTRY`.
- In `validators.py`:
  - Update `_mime_matches_extension()` and `validate_file_upload()` to accept `.json` and `.xml` for DAST logs.

#### 4. Deterministic DAST Rules: `backend/app/data/rules/builtin/dast.yaml`
- Rule definitions matching CWEs and DAST finding titles:
  - `DAST-001`: SQL Injection (`CWE-89`) ➡️ Severity: Critical, MITRE: `T1190`
  - `DAST-002`: Cross-Site Scripting (XSS, `CWE-79`) ➡️ Severity: High, MITRE: `T1059.007`
  - `DAST-003`: Server-Side Request Forgery (SSRF, `CWE-918`) ➡️ Severity: Critical, MITRE: `T1190`
  - `DAST-004`: Path / Directory Traversal (`CWE-22`) ➡️ Severity: High, MITRE: `T1083`
  - `DAST-005`: Broken Access Control & IDOR (`CWE-284`, `CWE-639`) ➡️ Severity: High, MITRE: `T1552`
  - `DAST-006`: Sensitive Data Exposure & Information Leakage (`CWE-200`) ➡️ Severity: Medium, MITRE: `T1592`
  - `DAST-007`: Missing / Insecure Headers & Cookies ➡️ Severity: Low/Medium, MITRE: `T1539`

#### 5. AI Prompt & Router: `backend/app/ai/prompts/dast_prompt.py` & `router.py`
- `build_dast_prompt(events: list[dict], findings: list[dict]) -> str`:
  - Groups isolated DAST alerts by underlying architecture root cause (e.g., ORM bypass, unvalidated input, legacy middleware).
  - Evaluates real-world exploitability vs false positive indicators.
  - Produces executive summary, attack scenario, and exact developer remediation code.
- In `backend/app/ai/router.py`:
  - Route `log_type == "dast"` to `build_dast_prompt()`.

---

### Phase 3: Frontend UI & Executive Teaser Workflow

#### 1. TypeScript Types: `frontend/src/types/audit.ts`
- Update `CloudProvider` type union:
  ```typescript
  export type CloudProvider = 'aws' | 'gcp' | 'azure' | 'external_domain';
  ```
- Add `target_domain?: string` to `AuditStartBody` and `CreateCloudAccountBody`.

#### 2. Audit Initiation Form: `frontend/src/components/audit/AuditForm.tsx`
- Add fourth provider tab: **"Zero-Setup Web & Domain Scan"** (Globe icon 🌐).
- Form inputs:
  - `Company / Client Name` (text)
  - `Target Domain or URL` (e.g., `https://kkfoodproducts.com`)
  - `Authorization & Scope Checkbox` ("I confirm authorization to perform non-intrusive external posture checks on this domain")
  - Framework selector pre-selects `OWASP Web 2025` + `SOC 2` + `ISO 27001`.
- Triggers standard `startAudit({ provider: "external_domain", target_domain, ... })`.

#### 3. Continuous Monitoring: `frontend/src/components/audit/CloudAccountsManager.tsx`
- Adds "Add Web Domain Asset" option in the Connect Modal.
- Allows saving a client domain for autonomous weekly surface drift monitoring.

#### 4. SIEM & Parser UIs: `NewInvestigation.tsx` & `PlayParser.tsx`
- Add format badge: `"OWASP ZAP & Burp Suite (DAST JSON/XML)"`.
- Allows drag-and-drop ingestion of `.json` and `.xml` scan exports.
- PlayParser live preview shows parsed DAST alerts, CWE IDs, and remediation guidance.

#### 5. Teaser Download: `frontend/src/components/audit/AuditResults.tsx`
- When an audit has `provider === 'external_domain'`, display a prominent **"Download 1-Page Executive Teaser PDF"** button alongside the full audit report.

---

## 4. NON-GOALS (BOUNDARIES)

1. **No Active Exploitation or Fuzzing**: LogRaven will **not** execute automated SQL injection testing, buffer overflows, active password brute forcing, or destructive exploitation. It performs strictly passive, non-intrusive metadata and configuration audits.
2. **No Intrusive Web Crawling**: LogRaven will not crawl 10,000 subpages or submit forms. Deep scanning is delegated to dedicated DAST tools (OWASP ZAP / Burp), which LogRaven then ingests, analyzes, and contextualizes.
3. **No Private IP / Intranet Scanning**: Will not scan internal RFC1918 subnets from cloud workers.

---

## 5. TESTING & VERIFICATION PLAN (ZERO-REGRESSION)

### 5.1 Backend Unit & Integration Tests (Pytest)
1. **`backend/tests/test_external_domain_collector.py`**:
   - `test_ssrf_rejects_localhost_and_private_ips()`: Verifies loopback (`127.0.0.1`), metadata (`169.254.169.254`), and RFC1918 addresses raise validation errors.
   - `test_external_collector_parses_tls_and_headers()`: Mocked HTTP/SSL responses test all 12 checks.
   - `test_owasp_web_framework_registration()`: Confirms framework controls, scoring denominator, and crosswalk linkages.
   - `test_attack_path_graph_external_domain()`: Asserts Internet ➡️ App ➡️ Secrets DAG structure and toxic combination flags.
2. **`backend/tests/test_dast_parser.py`**:
   - `test_sniff_detects_zap_json_and_burp_xml()`: Verifies detector returns `dast` with > 0.95 confidence.
   - `test_dast_parser_extracts_cwe_and_solution()`: Verifies normalized events contain all metadata.
   - `test_dast_rules_emit_mitre_t1190()`: Runs rules engine against sample DAST findings, verifying deterministic findings generation.

### 5.2 End-to-End System Verification (Chrome / Playwright)
- Execute `temp/run_chrome_demo.mjs` extended with Step 11:
  - Submit `https://example.com` in AuditForm "Zero-Setup Web & Domain Scan".
  - Verify audit status transitions `pending` ➡️ `running` ➡️ `complete`.
  - Validate Attack Path graph shows internet-to-app nodes.
  - Validate 1-Click Remediation shows Nginx/Cloudflare code.
  - Verify 1-Page Executive Teaser PDF generation.

---

## 6. EXECUTION HANDOFF

- **Readiness**: Specifications, models, and interfaces are fully resolved and aligned with LogRaven v2.4.0.
- **Recommended Execution Order**:
  1. **Phase 1 Backend**: Alembic migration 024, `external_domain.py`, `owasp_web.py`, signals, graph, remediation, and report generator.
  2. **Phase 2 Backend**: DAST parser, sniff/detector registration, `dast.yaml`, and `dast_prompt.py`.
  3. **Phase 3 Frontend**: Types, `AuditForm.tsx` provider tab, `CloudAccountsManager.tsx`, and `AuditResults.tsx`.
  4. **Phase 4 QA**: Pytest test suite execution and Playwright E2E browser verification.
