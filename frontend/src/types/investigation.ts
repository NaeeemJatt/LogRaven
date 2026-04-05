// LogRaven — Investigation TypeScript Types

export interface ParserSelectionDetail {
  chosen_log_type?: string
  detection_confidence?: number
  parse_quality?: number | null
  fallback_used?: boolean
  parse_warnings?: string[]
  ranked_candidates?: { log_type: string; confidence: number; reasons: string[] }[]
  attempts?: { log_type: string; parse_quality?: number; event_count?: number; error?: string; skipped?: string }[]
  requested_ingestion_mode?: string
  actual_ingestion_path?: string
  fallback_reason?: string
  user_warnings?: string[]
}

export interface InvestigationFile {
  id: string
  filename: string
  source_type: string
  ingestion_mode?: string
  log_type: string | null
  status: 'pending' | 'parsing' | 'parsed' | 'failed'
  event_count: number | null
  parser_detection_confidence?: number | null
  parser_selection_detail?: ParserSelectionDetail | null
}

export interface Investigation {
  id: string
  name: string
  status: 'draft' | 'queued' | 'processing' | 'complete' | 'failed'
  correlation_enabled: boolean
  cloud_ai_enabled: boolean
  files: InvestigationFile[]
  created_at: string
}

export interface InvestigationStatus {
  id: string
  status: string
  progress_stage: string | null
  error_message?: string | null
  files: InvestigationFile[]
}
