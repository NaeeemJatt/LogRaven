// LogRaven — Multi-Framework Compliance API Client
//
// Wraps all compliance endpoints through the shared Axios client so
// auth cookies, the 401 → refresh interceptor, and withCredentials are
// applied automatically — identical to investigations.ts / reports.ts.

import client from './client'
import type {
  AuditStartResponse,
  AuditStatusResponse,
  CrosswalkResponse,
  FrameworkInfo,
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

export async function getPosture(): Promise<Record<string, unknown>> {
  const res = await client.get('/api/v1/compliance/posture')
  return res.data as Record<string, unknown>
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

export async function listAudits(): Promise<AuditSummary[]> {
  const res = await client.get<AuditSummary[]>('/api/v1/audits')
  return res.data
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
