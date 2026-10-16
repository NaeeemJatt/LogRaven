// LogRaven — Multi-Framework Compliance API Client
//
// Wraps all compliance endpoints through the shared Axios client so
// auth cookies, the 401 → refresh interceptor, and withCredentials are
// applied automatically — identical to investigations.ts / reports.ts.

import axios from 'axios'
import client from './client'
import { normalizeApiBase } from './normalizeApiBase'
import type {
  AuditStartResponse,
  AuditStatusResponse,
  ControlResult,
  CrosswalkResponse,
  ExceptionResponse,
  FrameworkInfo,
  CloudAccount,
  CreateCloudAccountBody,
  UpdateCloudAccountBody,
  AuditorAccessToken,
  CreateAuditorTokenBody,
  AuditorTokenCreatedResponse,
  AuditorPortalOverview,
  AuditorPortalException,
  AttackPathGraph,
} from '../types/audit'


export interface AuditStartBody {
  company_name: string
  role_arn: string
  audit_start_date: string
  audit_end_date: string
  frameworks?: string[]
  recurrence?: string
}

export async function listFrameworks(): Promise<FrameworkInfo[]> {
  const res = await client.get<FrameworkInfo[]>('/api/v1/compliance/frameworks')
  return res.data
}

export async function startAudit(body: AuditStartBody): Promise<AuditStartResponse> {
  const res = await client.post<AuditStartResponse>('/api/v1/audit/start', body)
  return res.data
}

export async function retryAudit(auditId: string): Promise<AuditStartResponse> {
  const res = await client.post<AuditStartResponse>(`/api/v1/audit/${auditId}/retry`)
  return res.data
}

export async function getAuditStatus(auditId: string): Promise<AuditStatusResponse> {
  const res = await client.get<AuditStatusResponse>(`/api/v1/audit/${auditId}/status`)
  return res.data
}

export async function downloadAuditReport(
  auditId: string,
  framework?: string,
  format: 'pdf' | 'csv' = 'pdf',
): Promise<Blob> {
  const params: Record<string, string> = { format }
  if (framework) params.framework = framework
  const res = await client.get(`/api/v1/audit/${auditId}/report`, { params, responseType: 'blob' })
  return res.data as Blob
}

export async function downloadEvidencePack(auditId: string): Promise<Blob> {
  const res = await client.get(`/api/v1/audit/${auditId}/evidence`, { responseType: 'blob' })
  return res.data as Blob
}

export async function getCrosswalk(frameworks?: string[]): Promise<CrosswalkResponse> {
  const params = frameworks?.length ? { frameworks: frameworks.join(',') } : undefined
  const res = await client.get<CrosswalkResponse>('/api/v1/compliance/crosswalk', { params })
  return res.data
}

export interface PostureCard {
  framework_id: string
  framework_name: string
  score_percent: number
  pass_count: number
  fail_count: number
  partial_count: number
  score_delta: number | null
  as_of: string | null
}

export interface PostureResponse {
  frameworks: PostureCard[]
  overall_score: number | null
  reuse_factor: number | null
  total_audits: number
}

export async function getPosture(): Promise<PostureResponse> {
  const res = await client.get<PostureResponse>('/api/v1/compliance/posture')
  return res.data
}

/**
 * Public, token-scoped read-only audit results (no auth).
 *
 * Uses a bare axios call: the shared client's 401 interceptor would try to
 * refresh a session and bounce anonymous visitors to /login, but here a 401
 * simply means the share link is invalid or expired.
 */
export async function getSharedAudit(token: string): Promise<AuditStatusResponse> {
  const base = normalizeApiBase(import.meta.env.VITE_API_URL)
  const res = await axios.get<AuditStatusResponse>(`${base}/api/v1/audit/shared/${token}`)
  return res.data
}

export interface AuditSummary {
  audit_id: string
  company_name: string
  frameworks: string[]
  status: string
  created_at: string
  recurrence: string
  score_percent?: number | null
}

export interface AuditHistoryPage {
  items: AuditSummary[]
  page: number
  total: number
  totalPages: number
}

export async function listAudits(page = 1, limit = 20): Promise<AuditHistoryPage> {
  const res = await client.get<AuditSummary[]>('/api/v1/audits', { params: { page, limit } })
  return {
    items: res.data,
    page: Number(res.headers['x-page'] ?? page),
    total: Number(res.headers['x-total-count'] ?? res.data.length),
    totalPages: Number(res.headers['x-total-pages'] ?? (res.data.length ? 1 : 0)),
  }
}

export async function createShareLink(
  auditId: string,
  expiresDays = 7,
): Promise<{ token: string; url: string; expires_days: number }> {
  const res = await client.post(`/api/v1/audit/${auditId}/share`, null, {
    params: { expires_days: expiresDays },
  })
  return res.data as { token: string; url: string; expires_days: number }
}

export interface SuppressControlBody {
  business_justification: string
  compensating_controls?: string
  risk_level?: 'low' | 'medium' | 'high' | 'critical'
  expires_at?: string
}

export async function suppressControl(
  auditId: string,
  controlId: string,
  framework: string,
  body: SuppressControlBody,
): Promise<ControlResult> {
  const res = await client.post<ControlResult>(
    `/api/v1/audit/${auditId}/controls/${controlId}/suppress`,
    body,
    { params: { framework } },
  )
  return res.data
}

export async function unsuppressControl(
  auditId: string,
  controlId: string,
  framework: string,
): Promise<ControlResult> {
  const res = await client.delete<ControlResult>(
    `/api/v1/audit/${auditId}/controls/${controlId}/suppress`,
    { params: { framework } },
  )
  return res.data
}

export async function listAuditExceptions(auditId: string): Promise<ExceptionResponse[]> {
  const res = await client.get<ExceptionResponse[]>(`/api/v1/audit/${auditId}/exceptions`)
  return res.data
}

// ── Cloud Accounts (Fleet Management) ──────────────────────────────────────

export async function listCloudAccounts(): Promise<CloudAccount[]> {
  const res = await client.get<CloudAccount[]>('/api/v1/compliance/accounts')
  return res.data
}

export async function createCloudAccount(body: CreateCloudAccountBody): Promise<CloudAccount> {
  const res = await client.post<CloudAccount>('/api/v1/compliance/accounts', body)
  return res.data
}

export async function updateCloudAccount(
  accountId: string,
  body: UpdateCloudAccountBody,
): Promise<CloudAccount> {
  const res = await client.patch<CloudAccount>(`/api/v1/compliance/accounts/${accountId}`, body)
  return res.data
}

export async function deleteCloudAccount(accountId: string): Promise<void> {
  await client.delete(`/api/v1/compliance/accounts/${accountId}`)
}

export async function verifyCloudAccount(accountId: string): Promise<CloudAccount> {
  const res = await client.post<CloudAccount>(`/api/v1/compliance/accounts/${accountId}/verify`)
  return res.data
}

export async function triggerAccountScan(
  accountId: string,
): Promise<{
  audit_id: string
  cloud_account_id: string
  status: string
  message?: string
  company_name?: string
  frameworks?: string[]
}> {
  const res = await client.post<{
    audit_id: string
    cloud_account_id: string
    status: string
    message?: string
    company_name?: string
    frameworks?: string[]
  }>(`/api/v1/compliance/accounts/${accountId}/scan`)
  return res.data
}

// ── Auditor Portal & Evidence Vault API ──────────────────────────────────────

export async function createAuditorToken(
  body: CreateAuditorTokenBody,
): Promise<AuditorTokenCreatedResponse> {
  const res = await client.post<AuditorTokenCreatedResponse>(
    '/api/v1/compliance/auditor/tokens',
    body,
  )
  return res.data
}

export async function listAuditorTokens(): Promise<AuditorAccessToken[]> {
  const res = await client.get<AuditorAccessToken[]>('/api/v1/compliance/auditor/tokens')
  return res.data
}

export async function revokeAuditorToken(tokenId: string): Promise<void> {
  await client.delete(`/api/v1/compliance/auditor/tokens/${tokenId}`)
}

export async function verifyAuditorToken(
  token: string,
  passcode?: string,
): Promise<{
  valid: boolean
  company_name: string
  recipient_name?: string | null
  expires_at: string
  allowed_frameworks: string[]
  can_download_raw_evidence: boolean
}> {
  const res = await client.post('/api/v1/compliance/auditor/portal/verify', {
    token,
    passcode: passcode || undefined,
  })
  return res.data
}

export async function getAuditorPortalOverview(
  token: string,
  passcode?: string,
): Promise<AuditorPortalOverview> {
  const params = passcode ? { passcode } : {}
  const res = await client.get<AuditorPortalOverview>(
    `/api/v1/compliance/auditor/portal/${token}/overview`,
    { params },
  )
  return res.data
}

export async function getAuditorPortalExceptions(
  token: string,
  passcode?: string,
): Promise<AuditorPortalException[]> {
  const params = passcode ? { passcode } : {}
  const res = await client.get<AuditorPortalException[]>(
    `/api/v1/compliance/auditor/portal/${token}/exceptions`,
    { params },
  )
  return res.data
}

export function getEvidenceVaultDownloadUrl(token: string, passcode?: string): string {
  const base = normalizeApiBase(import.meta.env.VITE_API_URL)
  const url = `${base}/api/v1/compliance/auditor/portal/${token}/evidence-vault`
  return passcode ? `${url}?passcode=${encodeURIComponent(passcode)}` : url
}

// ── Attack Path & Asset Relationship Graph API ───────────────────────────────

export async function getAuditAttackPathGraph(auditId: string): Promise<AttackPathGraph> {
  const res = await client.get<AttackPathGraph>(`/api/v1/compliance/graph/audits/${auditId}`)
  return res.data
}

export async function getAccountAttackPathGraph(accountId: string): Promise<AttackPathGraph> {
  const res = await client.get<AttackPathGraph>(`/api/v1/compliance/graph/accounts/${accountId}`)
  return res.data
}
