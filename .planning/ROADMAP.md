# Roadmap: LogRaven Security & Compliance

## Overview

Hardening LogRaven SIEM and Compliance platform: remediating vulnerabilities across multi-tenancy, authentication, session management, cryptographic controls, and cloud collectors.

## Phases

- [x] **Phase 1: Password Reset** - Enterprise zero-knowledge password reset with hybrid envelope crypto and Watchtower SIEM UI.
- [x] **Phase 2: Vulnerability Remediation** - Remediate the 9 critical, high, and medium security vulnerabilities identified across multi-tenancy, session revocation, input validation, and rate limiting.

## Phase Details

### Phase 1: Password Reset
**Goal**: Enterprise zero-knowledge password reset with hybrid envelope crypto and Watchtower SIEM UI.
**Depends on**: Nothing (first phase)
**Requirements**: PWD-SEC-01 to PWD-SEC-14
**Success Criteria** (what must be TRUE):
  1. Password reset flow uses hybrid Web Crypto envelope encryption and zero-knowledge enumeration defense.
  2. Watchtower design system theme is consistently applied across all auth states.
**Plans**: 1 plan

Plans:
- [x] 01-01: Enterprise Password Reset & Hardening

### Phase 2: Vulnerability Remediation
**Goal**: Remediate the 9 cataloged security vulnerabilities across multi-tenancy isolation, token invalidation, password complexity, rate limiting, and transport security.
**Depends on**: Phase 1
**Requirements**: LR-VULN-01, LR-VULN-02, LR-VULN-03, LR-VULN-04, LR-VULN-05, LR-VULN-06, LR-VULN-07, LR-VULN-08, LR-VULN-09
**Success Criteria** (what must be TRUE):
  1. Compliance exceptions and auditor portal enforce strict tenant isolation (user_id matching current user or token owner).
  2. Password change invalidates all existing sessions and access tokens via Redis timestamp tracking checked in get_current_user().
  3. Registration and password change enforce NIST SP 800-63B password complexity and maximum length bounds (128 chars).
  4. Password change and auditor portal passcode verification are protected by strict rate limiters.
  5. Auditor access token is passed securely via Authorization header instead of GET path parameters.
  6. Nonce replay prevention in crypto_envelope.py is backed by Redis atomic locking rather than in-memory set.
  7. Passcode hash verification uses constant-time comparison.
  8. Secure cookies are enforced in non-debug/production environments.
**Plans**: 3 plans

Plans:
- [x] 02-01-PLAN.md — Tenant Isolation & Auditor Room Access Control Hardening (LR-VULN-01, LR-VULN-05, LR-VULN-07)
- [x] 02-02-PLAN.md — Authentication, Global Session Invalidation & Password Policies (LR-VULN-02, LR-VULN-03, LR-VULN-04)
- [x] 02-03-PLAN.md — Cryptographic Nonces, Production Cookies & Cloud Collector Hardening (LR-VULN-06, LR-VULN-08, LR-VULN-09)

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Password Reset | 1/1 | Complete | 2026-10-29 |
| 2. Vulnerability Remediation | 3/3 | Complete | 2026-10-29 |

