---
phase: "01-password-reset"
plan: 1
type: feature
wave: 1
depends_on: []
files_modified:
  - backend/app/utils/crypto_envelope.py
  - backend/app/utils/password_policy.py
  - backend/app/utils/security.py
  - backend/app/services/account_service.py
  - backend/app/services/auth_service.py
  - backend/app/services/email_service.py
  - backend/app/api/auth/routes.py
  - backend/app/schemas/user.py
  - backend/app/models/user.py
  - backend/tests/test_password_reset_security.py
  - frontend/src/utils/crypto.ts
  - frontend/src/types/auth.ts
  - frontend/src/api/auth.ts
  - frontend/src/components/auth/PasswordStrengthMeter.tsx
  - frontend/src/pages/Auth/ForgotPassword.tsx
  - frontend/src/pages/Auth/ResetPassword.tsx
  - frontend/src/pages/Auth/ForgotPassword.test.tsx
  - frontend/src/pages/Auth/ResetPassword.test.tsx
  - docs/security/password-reset-policy.md
autonomous: true
requirements:
  - PWD-SEC-01: Zero-Knowledge User Enumeration Defense with Identical Neutral Messaging & Constant-Time Response (CWE-204)
  - PWD-SEC-02: HTTP Parameter Pollution & Multi-Recipient Burp Suite Injection Defense with Zero-Email Fallback (CWE-233, CWE-88)
  - PWD-SEC-03: Zero-Plaintext Wire Interception Defense via Web Crypto RSA-OAEP + AES-256-GCM Envelope (CWE-319, CWE-311)
  - PWD-SEC-04: Host Header Poisoning & Password Reset Link Hijacking Defense (CWE-644)
  - PWD-SEC-05: Referer Header & Browser History Token Leakage Mitigation (CWE-200, CWE-525)
  - PWD-SEC-06: Cryptographic Single-Use JTI & Password Hash Fingerprint Invalidation (CWE-613, CWE-294)
  - PWD-SEC-07: Concurrency & Race Condition Defense via Atomic Row & Redis Locking (CWE-362)
  - PWD-SEC-08: Token Ephemerality (15-Minute Expiry) & Dedicated Pre-Flight Verification (NIST SP 800-63B)
  - PWD-SEC-09: Global Session Revocation Across All Devices & Cookies on Password Reset (ASVS V3.3.1)
  - PWD-SEC-10: Denial of Service & Mailbox Bombing Defense via IP & Email Throttling (CWE-770)
  - PWD-SEC-11: Enterprise Password Complexity & Breached Password Blacklist Enforcement (CWE-521, NIST SP 800-63B)
  - PWD-SEC-12: Immediate Post-Reset Security Alert Notification & SIEM Audit Logging (CWE-778, SOC 2 CC6.8)
  - PWD-SEC-13: Replay Attack & Tampering Rejection via Millisecond Timestamps and Cryptographic Nonces
  - PWD-SEC-14: Clickjacking & UI Redressing Defense via Frame-Ancestors Restrictions (CWE-1021)
---

<objective>
Deliver a battle-hardened, zero-knowledge, intercept-proof end-to-end Password Forgot and Reset system for LogRaven.
The architecture defends against local proxy inspection (Burp Suite, OWASP ZAP) via client-side Web Crypto hybrid envelope encryption, completely eliminates user enumeration via timing equalization and neutral messaging, permanently blocks HTTP parameter pollution / multi-email injections with a zero-email abort policy, revokes all active global sessions upon reset, protects against Host header and Referer leakage, prevents race conditions via atomic database locking, enforces NIST SP 800-63B password complexity, and alerts the user immediately upon password changes.
</objective>

<security_threat_model_and_guarantees>
### Comprehensive Threat Model (14 Vectors)

1. **Information Disclosure & User Enumeration (CWE-204, OWASP WSTG-IDNT-04)**:
   - *Attack*: Discerning registered emails by comparing HTTP status codes (200 vs 404), error messages ("User not found"), or response times (bcrypt hash vs immediate return).
   - *Defense*:
     - Server returns identical HTTP 202 Accepted for both registered and unregistered emails.
     - Identical neutral message: *"If an account exists for the provided email, a password reset link has been dispatched."*
     - Constant-time equalization: when an email is not found, the backend executes `DUMMY_PASSWORD_HASH` computation and a simulated dispatch delay to match the latency profile of existing users.

2. **Proxy Interception & Zero-Plaintext Transmission (CWE-319, CWE-311, ASVS V9)**:
   - *Attack*: Burp Suite / OWASP ZAP inspecting local network traffic can capture cleartext emails, passwords, and tokens.
   - *Defense*:
     - Client-side hybrid envelope encryption using Web Crypto API (`window.crypto.subtle`).
     - Backend serves public key at `GET /api/v1/auth/crypto/public-key` (RSA-OAEP 2048-bit with SHA-256).
     - Browser creates ephemeral AES-256-GCM key, encrypts payload (`email` or `new_password` + `token` + millisecond timestamp + UUID nonce) with AES-GCM.
     - Browser encrypts AES key with server's RSA-OAEP public key.
     - Payload on the wire: `{ "key_id": "...", "encrypted_key": "...", "iv": "...", "ciphertext": "...", "tag": "..." }`.
     - Burp Suite request body is 100% opaque ciphertext. If any byte is modified in Burp Suite, the 128-bit GCM authentication tag verification fails and the request is rejected with HTTP 400.

3. **HTTP Parameter Pollution (HPP) & Multi-Recipient Burp Suite Injection (CWE-233, CWE-88, WSTG-INPV-04)**:
   - *Attack*: Attacker injects duplicate email keys, JSON arrays (`{"email": ["victim@domain.com", "evil@attacker.com"]}`), delimiter lists (`victim@domain.com, evil@attacker.com`), or CRLF injection (`\r\nBcc: evil@attacker.com`).
   - *Defense*:
     - Pydantic schema with `model_config = ConfigDict(extra="forbid", strict=True)`.
     - Custom validator `StrictSingleEmail`: rejects arrays, objects, any whitespace, commas, semicolons, quotes, `< >`, `\r`, `\n`, and enforces exactly one `@`.
     - **CRITICAL INVARIANT**: If any parameter pollution, delimiter, or anomaly is detected, the request is aborted with HTTP 400, logged in `AuditLog`, and **ZERO emails are dispatched** (never to both, never to either).

4. **Host Header Poisoning / Password Reset Poisoning (CWE-644, WSTG-CONF-07)**:
   - *Attack*: Attacker sends `Host: evil.com` or `X-Forwarded-Host: evil.com` in forgot-password request. If server builds link from `request.base_url`, the victim receives an email with `https://evil.com/reset-password?token=...`.
   - *Defense*: The reset URL is strictly built from immutable server configuration `settings.FRONTEND_BASE_URL`. Never inspect or trust the incoming `Host` or `X-Forwarded-*` headers.

5. **Token Leakage via HTTP Referer Headers (CWE-200, WSTG-SESS-04)**:
   - *Attack*: Victim opens reset link `https://app.com/reset-password?token=secret123`. External links or assets on the page leak the token via the `Referer` header.
   - *Defense*:
     - Serve `Referrer-Policy: strict-origin-when-cross-origin` and meta tag `no-referrer`.
     - On page load in `ResetPassword.tsx`, store token in memory and scrub URL using `window.history.replaceState({}, document.title, window.location.pathname)`.

6. **Token Leakage via Browser Cache & Shared Terminal History (CWE-525)**:
   - *Attack*: Reset tokens or account data remain in disk cache or browser history on public terminals.
   - *Defense*:
     - HTTP response headers: `Cache-Control: no-store, no-cache, must-revalidate, max-age=0` and `Pragma: no-cache`.
     - `replaceState` eliminates token from browser navigation history.

7. **Cryptographic Single-Use JTI & Password Hash Fingerprint Invalidation (CWE-613, CWE-294)**:
   - *Attack*: Replay of used reset tokens.
   - *Defense*:
     - Dual-layer invalidation:
       1. Token embeds short hash fingerprint of current password (`pwf = sha256(password_hash)[:16]`). Once the password is reset, `user.password_hash` changes, rendering the old token instantly mathematically invalid.
       2. Token embeds unique `jti = str(uuid4())`. Once redeemed, `jti` is blacklisted in Redis with 15-minute TTL.

8. **Concurrency & Race Condition Exploitation (CWE-362, TOCTOU)**:
   - *Attack*: Attacker sends concurrent parallel requests with the same token to bypass single-use check or cause multiple resets.
   - *Defense*:
     - Redis atomic lock: `lock:reset_token:{jti}` via `SET ... NX EX 30`.
     - Database row lock: `select(User).where(User.id == user_id).with_for_update()` in SQLAlchemy ensures serial processing inside an atomic transaction.

9. **Token Ephemerality & Pre-Flight Verification (NIST SP 800-63B)**:
   - *Attack*: Long-lived tokens (60 mins+) widen attack window.
   - *Defense*:
     - Token lifetime shortened from 60 minutes to **15 minutes**.
     - Dedicated idempotent pre-flight endpoint `GET /api/v1/auth/password/reset/verify?token=...` checks validity without consuming token, returning `{ "valid": true, "email_masked": "u***@domain.com" }`.

10. **Global Session Revocation (ASVS V3.3.1)**:
    - *Attack*: Attacker possesses active stolen session cookie or refresh token. Victim resets password, but attacker session stays alive.
    - *Defense*:
      - Password reset immediately calls `auth_service.revoke_all_user_tokens(user.id)`.
      - Increments `token_version` on `User` model, immediately invalidating all pre-reset JWT access tokens.
      - Purges all active refresh tokens from DB and Redis.
      - Clears current auth cookies, forcing complete re-authentication.

11. **Denial of Service & Mailbox Bombing (CWE-770, CWE-400)**:
    - *Attack*: Automated scripts trigger thousands of forgot-password calls for a victim's email, spamming their inbox and depleting SMTP quota.
    - *Defense*:
      - Dual throttling:
        1. IP rate limiting: 5 requests per 15 minutes.
        2. Per-Email Redis cooldown lock: `lock:pwd_reset_cooldown:{sha256(email)}` with 60-second TTL.
        - If an email was sent within 60s, silently suppress email delivery while returning the exact same 202 Success message.

12. **Enterprise Password Complexity & Breached Password Blacklist (CWE-521, NIST SP 800-63B)**:
    - *Attack*: User sets predictable or breached passwords (`Password123!`).
    - *Defense*:
      - Engine in `backend/app/utils/password_policy.py`:
        - Minimum length: 12 characters.
        - Complexity: uppercase, lowercase, digit, special character.
        - Dictionary check against top 10,000 breached passwords.
        - Rejection of email prefix / username inside password.
      - Frontend live interactive `PasswordStrengthMeter` checklist.

13. **Immediate Post-Reset Security Alert Notification & SIEM Audit Trail (CWE-778, SOC 2 CC6.8)**:
    - *Defense*:
      - Upon successful reset, immediately dispatch security alert email:
        *"Security Notice: Your LogRaven password was updated on [datetime] UTC from IP [ip] ([user_agent]). If this was not you, lock your account immediately."*
      - Record structured `AuditLog` entry with action `password_reset_success`, IP, user agent, timestamp.

14. **Clickjacking & UI Redressing (CWE-1021)**:
    - *Defense*: Strict security headers `X-Frame-Options: DENY` and `Content-Security-Policy: frame-ancestors 'none'`.
</security_threat_model_and_guarantees>

<tasks>

### Wave 1: Cryptographic Envelope, Policy Engine & Backend Core Defense

#### Task 1.1: Hybrid Envelope Cryptography Engine
- **File**: `backend/app/utils/crypto_envelope.py`
- **Action**:
  - Implement RSA-OAEP 2048-bit key management (server private/public key pair).
  - Expose `get_public_key_pem()` and `get_public_key_id()`.
  - Implement `decrypt_payload(envelope: EncryptedPayload) -> dict`:
    - Decrypts AES key via RSA-OAEP with SHA-256.
    - Decrypts payload ciphertext via AES-256-GCM, verifying 128-bit authentication tag.
    - Validates embedded `timestamp` (rejects if clock drift > 60 seconds).
    - Validates and records `nonce` in Redis (rejects replay attacks).
- **Verify**: Unit tests verifying encryption/decryption round-trip, ciphertext tampering rejection, expired timestamp rejection, and nonce replay rejection.

#### Task 1.2: Cryptographic Public Key Distribution Endpoint
- **File**: `backend/app/api/auth/routes.py`
- **Action**:
  - Implement `GET /api/v1/auth/crypto/public-key`.
  - Returns `{ "key_id": "lograven-key-v1", "algorithm": "RSA-OAEP-256", "public_key": "...PEM..." }`.
  - Set `Cache-Control: public, max-age=3600`.
- **Verify**: `curl -s http://127.0.0.1:8000/api/v1/auth/crypto/public-key` returns valid PEM.

#### Task 1.3: NIST SP 800-63B Password Policy Engine
- **File**: `backend/app/utils/password_policy.py`
- **Action**:
  - Implement `validate_password_strength(password: str, user_context: dict | None = None) -> None`:
    - Minimum length: 12 characters.
    - Character diversity: uppercase, lowercase, number, symbol.
    - Blacklist check: top breached passwords (embedded set of common passwords).
    - Context check: rejects if user's email username is contained in password.
    - Raises `HTTPException(status_code=400, detail="...")` with specific feedback.
- **Verify**: Unit tests passing valid passwords, weak passwords (<12 chars, no symbols), and common breached passwords.

#### Task 1.4: Strict Anti-Pollution Schema & Single-Email Validator
- **File**: `backend/app/schemas/user.py`
- **Action**:
  - Implement `StrictSingleEmail` custom type with Pydantic validator:
    - Banned: commas, semicolons, whitespace, quotes, `< >`, `\r`, `\n`.
    - Exactly one `@` symbol.
    - Strict RFC 5322 validation.
  - Define `EncryptedEnvelopeRequest` model with `model_config = ConfigDict(extra="forbid", strict=True)`.
  - Update `ForgotPasswordRequest` and `ResetPasswordRequest` models.
- **Verify**: Unit test feeding duplicate parameters, JSON arrays, and CRLF injections to ensure 100% rejection.

#### Task 1.5: Zero-Knowledge Handler with Constant-Time Equalization & Cooldown Lock
- **File**: `backend/app/services/account_service.py`
- **Action**:
  - Update `request_password_reset(email: str, db: AsyncSession, ip_address: str | None)`:
    - Check Redis 60s cooldown lock: `lock:pwd_reset_cooldown:{sha256(email)}`.
    - Query DB for `User` by email.
    - If user exists and not on cooldown: generate 15-min token with `pwf` fingerprint, dispatch email via `email_service`, set Redis cooldown.
    - If user does NOT exist: run `DUMMY_PASSWORD_HASH` computation + simulated delay to match execution latency.
    - Return identical HTTP 202 and neutral message:
      *"If an account exists for the provided email, a password reset link has been dispatched."*
- **Verify**: Response parity test (identical status 202, identical message, equalized timing profile).

#### Task 1.6: SMTP Hardening & Zero-Email Drop on Anomaly
- **File**: `backend/app/services/email_service.py`
- **Action**:
  - In `send_password_reset_email(to_email: str, token: str)`:
    - Verify recipient matches strict single email regex before invoking SMTP.
    - Construct link using strictly `settings.FRONTEND_BASE_URL` (Host header poisoning immunity).
    - If recipient is malformed or contains multiple addresses: log `CRITICAL_INJECTION_DETECTED` and abort immediately with ZERO emails sent.
  - Implement `send_password_reset_confirmation_email(to_email: str, ip_address: str | None, user_agent: str | None)`:
    - Sends immediate security alert notifying user of password change.
- **Verify**: Mock tests verifying zero emails sent when malformed input is passed.

#### Task 1.7: Pre-Flight Verification & Atomic Session Revocation
- **Files**:
  - `backend/app/api/auth/routes.py`
  - `backend/app/services/account_service.py`
  - `backend/app/utils/security.py`
- **Action**:
  - In `backend/app/utils/security.py`:
    - Reduce `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES` to 15.
    - Add `jti` to reset token payload.
  - In `backend/app/api/auth/routes.py`:
    - Implement `GET /api/v1/auth/password/reset/verify?token=...`:
      - Idempotent pre-flight check. Returns `{ "valid": true, "email_masked": "u***@domain.com" }` or HTTP 400.
  - In `backend/app/services/account_service.py`:
    - In `reset_password`:
      - Atomic Redis lock: `lock:reset_token:{jti}`.
      - Database row lock: `with_for_update()`.
      - Validate NIST password complexity.
      - Update `user.password_hash`.
      - Invalidate all user refresh tokens and increment token version: `auth_service.revoke_all_user_tokens(user.id)`.
      - Send confirmation security alert email.
      - Record `AuditLog(action="password_reset_success")`.
- **Verify**: Integration test ensuring token cannot be replayed concurrently, and pre-existing session refresh tokens return 401 after reset.

---

### Wave 2: Frontend Web Crypto Client, Intercept-Proof Forms & UX

#### Task 2.1: Browser Web Crypto Hybrid Envelope Encryption
- **File**: `frontend/src/utils/crypto.ts`
- **Action**:
  - Implement `encryptPayload(data: object): Promise<EncryptedEnvelope>` using native `window.crypto.subtle`:
    - Fetches and caches server's RSA-OAEP public key from `/api/v1/auth/crypto/public-key`.
    - Generates ephemeral AES-256-GCM key.
    - Encrypts payload JSON (with `timestamp: Date.now()` and random UUID `nonce`).
    - Encrypts AES key with server's RSA-OAEP public key.
    - Exports `{ key_id, encrypted_key, iv, ciphertext, tag }`.
- **Verify**: Browser test verifying opaque base64 output and successful server decryption.

#### Task 2.2: Live Password Strength Meter Component
- **File**: `frontend/src/components/auth/PasswordStrengthMeter.tsx`
- **Action**:
  - Create interactive visual checklist displaying 5 criteria:
    1. At least 12 characters.
    2. Uppercase letter (A-Z).
    3. Lowercase letter (a-z).
    4. Numeric digit (0-9).
    5. Special character (!@#$%^&*...).
  - Calculates strength score (0-100%) with animated colored progress bar.
- **Verify**: Component renders dynamically as user types.

#### Task 2.3: Hardened ForgotPassword Page
- **File**: `frontend/src/pages/Auth/ForgotPassword.tsx`
- **Action**:
  - Single-email validation before submission (blocks spaces, commas, semicolons).
  - Encrypts payload via `encryptPayload({ email })` before POST.
  - Request body in Burp Suite is 100% encrypted ciphertext.
  - Shows neutral confirmation message:
    *"If an account exists for this email, a reset link will be sent. The link expires in 15 minutes."*
  - 60-second cooldown timer on submit button.
- **Verify**: Inspect network requests; verify encrypted payload and neutral confirmation.

#### Task 2.4: Hardened ResetPassword Page
- **File**: `frontend/src/pages/Auth/ResetPassword.tsx`
- **Action**:
  - Pre-flight token check on mount: calls `authApi.verifyResetToken(token)`.
  - Scrub token from URL: `window.history.replaceState({}, document.title, window.location.pathname)`.
  - If token invalid/expired: shows clear "Link Expired or Already Used" UI with "Request New Link" button.
  - If token valid: shows masked email (`u***@domain.com`), new password field with `PasswordStrengthMeter`, and confirm password field.
  - On submit: encrypts payload `{ token, new_password }` via `encryptPayload`.
  - Zero plaintext password over the wire in Burp Suite.
  - On success: shows success animation, redirects to `/login`.
- **Verify**: Full flow verification with valid and expired tokens.

---

### Wave 3: Automated Security Regression Suite & Compliance Documentation

#### Task 3.1: Burp Suite Injection & Cryptographic Defense Test Suite
- **File**: `backend/tests/test_password_reset_security.py`
- **Action**:
  - Burp Suite simulation tests:
    - Array parameter injection: `{"email": ["alice@target.com", "evil@attacker.com"]}` -> 422/400.
    - Parameter pollution / duplicate keys -> rejected.
    - Comma/semicolon multi-address injection -> rejected, ZERO emails sent.
    - CRLF header injection -> rejected, ZERO emails sent.
    - Tampered ciphertext (1 byte flip) -> GCM tag failure, 400 Bad Request.
    - Replay attack with same nonce -> 400 Bad Request.
    - Expired timestamp (>60s) -> 400 Bad Request.
  - Anti-enumeration tests:
    - Registered email vs unregistered email: identical 202 status code and message.
    - Timing latency indistinguishability check.
  - Session revocation tests:
    - Existing refresh tokens return 401 after password reset.
  - Concurrency tests:
    - Parallel redemption attempts: exactly 1 succeeds, 1 fails.
- **Verify**: `pytest backend/tests/test_password_reset_security.py` passes 100%.

#### Task 3.2: Frontend Unit & Integration Tests
- **Files**:
  - `frontend/src/pages/Auth/ForgotPassword.test.tsx`
  - `frontend/src/pages/Auth/ResetPassword.test.tsx`
- **Action**:
  - Tests ensuring payload encryption is called before network request.
  - Tests ensuring neutral messaging is rendered.
  - Tests for URL history scrubbing and pre-flight token check.
- **Verify**: `npm --prefix frontend test` passes with zero errors.

#### Task 3.3: Enterprise Security Policy Documentation
- **File**: `docs/security/password-reset-policy.md`
- **Action**:
  - Formal documentation of the 14 threat vectors, cryptographic architecture, Burp Suite defense proofs, and SOC 2 / NIST SP 800-63B alignment.
- **Verify**: Document created and committed.
</tasks>

<verification>
1. `pytest backend/tests/test_password_reset_security.py` passes 100%.
2. Burp Suite inspection shows zero plaintext emails or passwords on the wire.
3. Parameter pollution / multi-recipient attacks result in ZERO emails sent.
4. Non-existent email receives identical HTTP 202 and identical neutral message with equalized timing.
5. All active user refresh tokens and sessions are terminated upon reset.
6. `npm --prefix frontend test` and `npm --prefix frontend run build` complete cleanly.
</verification>

<success_criteria>
- Zero user enumeration achieved with verified constant-time behavior.
- Wire inspection in Burp Suite / OWASP ZAP displays only high-entropy encrypted ciphertext.
- Parameter pollution and multi-recipient injection permanently blocked with zero-email abort.
- Host header and Referer header token leakage prevented.
- NIST SP 800-63B 12+ character complexity and breached password blacklisting verified.
- Complete global session revocation on password reset confirmed.
</success_criteria>
