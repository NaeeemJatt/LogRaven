// LogRaven — Investigation TypeScript Types

export interface InvestigationFile {
  id: string
  filename: string
  source_type: string
  log_type: string | null
  status: 'pending' | 'parsing' | 'parsed' | 'failed'
  event_count: number | null
}

export interface Investigation {
  id: string
  name: string
  status: 'draft' | 'queued' | 'processing' | 'complete' | 'failed'
  correlation_enabled: boolean
  files: InvestigationFile[]
  created_at: string
}

export interface InvestigationStatus {
  id: string
  status: string
  progress_stage: string | null
  files: InvestigationFile[]
}
