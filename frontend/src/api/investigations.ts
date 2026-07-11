// LogRaven — Investigations API Functions
import client from './client'
import type { Investigation } from '../types/investigation'

export interface InvestigationListParams {
  page?: number
  limit?: number
  search?: string
  sort?: 'name' | 'status' | 'created_at'
  direction?: 'asc' | 'desc'
}

export interface InvestigationPage {
  items: Investigation[]
  page: number
  limit: number
  total: number
  totalPages: number
}

export interface DashboardStats {
  total_investigations: number
  active_investigations: number
  files_analyzed: number
  avg_analysis_time: string
  status_counts: Record<string, number>
  severity_counts: Record<string, number>
  recent_investigation_dates: string[]
  recent_daily_counts: Record<string, number>
}

export interface FeedFinding {
  id: string
  report_id: string
  title: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'informational'
  finding_type: string
  mitre_technique_id?: string | null
  mitre_technique_name?: string | null
  mitre_tactic?: string | null
  description?: string | null
  remediation?: string | null
  source_files: string[]
  confidence: number
  created_at?: string | null
  investigation: { id: string; name: string; created_at?: string | null }
}

export interface FindingsPage {
  items: FeedFinding[]
  page: number
  limit: number
  total: number
  total_pages: number
  severity_counts: Record<string, number>
}

export const investigationsApi = {
  create: (name: string) =>
    client.post('/api/v1/investigations', { name }),

  list: async ({
    page = 1,
    limit = 20,
    search,
    sort = 'created_at',
    direction = 'desc',
  }: InvestigationListParams = {}): Promise<InvestigationPage> => {
    const response = await client.get<Investigation[]>('/api/v1/investigations', {
      params: { page, limit, search, sort, direction },
    })
    return {
      items: response.data,
      page: Number(response.headers['x-page'] ?? page),
      limit,
      total: Number(response.headers['x-total-count'] ?? response.data.length),
      totalPages: Number(response.headers['x-total-pages'] ?? (response.data.length ? 1 : 0)),
    }
  },

  getDashboardStats: async (): Promise<DashboardStats> =>
    (await client.get<DashboardStats>('/api/v1/dashboard/stats')).data,

  get: (id: string) =>
    client.get(`/api/v1/investigations/${id}`),

  update: (id: string, body: { correlation_enabled: boolean }) =>
    client.patch(`/api/v1/investigations/${id}`, body),

  delete: (id: string) =>
    client.delete(`/api/v1/investigations/${id}`),

  uploadFile: (id: string, file: File, sourceType: string, ingestionMode: 'parsers' | 'decoders' = 'parsers') => {
    const form = new FormData()
    form.append('file', file)
    form.append('source_type', sourceType)
    form.append('ingestion_mode', ingestionMode)
    return client.post(`/api/v1/investigations/${id}/files`, form)
  },

  deleteFile: (id: string, fileId: string) =>
    client.delete(`/api/v1/investigations/${id}/files/${fileId}`),

  analyze: (id: string, cloudAiConsent: boolean) =>
    client.post(`/api/v1/investigations/${id}/analyze`, {
      cloud_ai_consent: cloudAiConsent,
    }),

  getStatus: (id: string) =>
    client.get(`/api/v1/investigations/${id}/status`),

  getReport: (id: string) =>
    client.get(`/api/v1/investigations/${id}/report`),

  getReportDownload: (id: string) =>
    client.get(`/api/v1/investigations/${id}/report/download`),
}

export const findingsApi = {
  list: async ({
    page = 1,
    limit = 20,
    severity,
    search,
  }: {
    page?: number
    limit?: number
    severity?: string
    search?: string
  } = {}): Promise<FindingsPage> =>
    (
      await client.get<FindingsPage>('/api/v1/findings', {
        params: { page, limit, severity, search },
      })
    ).data,
}
