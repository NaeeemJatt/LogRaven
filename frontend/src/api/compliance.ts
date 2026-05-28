// LogRaven — SOC 2 Compliance API Client
//
// Wraps all compliance endpoints through the shared Axios client so
// auth cookies, the 401 → refresh interceptor, and withCredentials are
// applied automatically — identical to investigations.ts / reports.ts.

import client from './client'
import type { AuditStartResponse, AuditStatusResponse } from '../types/audit'

export interface AuditStartBody {
  company_name: string
  role_arn: string
  audit_start_date: string
  audit_end_date: string
}

export async function startAudit(body: AuditStartBody): Promise<AuditStartResponse> {
  const res = await client.post<AuditStartResponse>('/api/v1/audit/start', body)
  return res.data
}

export async function getAuditStatus(auditId: string): Promise<AuditStatusResponse> {
  const res = await client.get<AuditStatusResponse>(`/api/v1/audit/${auditId}/status`)
  return res.data
}

export async function downloadAuditReport(auditId: string): Promise<Blob> {
  const res = await client.get(`/api/v1/audit/${auditId}/report`, { responseType: 'blob' })
  return res.data as Blob
}
