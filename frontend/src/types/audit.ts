// LogRaven — Multi-Framework Compliance Audit TypeScript Types
//
// Mirrors the Pydantic models from backend/app/api/compliance/routes.py

export interface ControlResult {
  control_id: string
  control_name: string
  status: 'PASS' | 'FAIL' | 'PARTIAL' | string
  confidence: 'HIGH' | 'MEDIUM' | 'LOW' | string
  ai_description: string
  gaps: string[]
  evidence_references: string[]
  framework?: string | null
  category?: string | null
  automatable?: boolean | null
  remediation?: string | null
}

export interface FrameworkResult {
  framework_id: string
  framework_name: string
  controls_assessed: number
  pass_count: number
  fail_count: number
  partial_count: number
  score_percent: number
  score_delta?: number | null
  results: ControlResult[]
}

export interface AuditStatusResponse {
  audit_id: string
  status: string
  percent?: number | null
  step?: string | null
  company_name?: string | null
  frameworks?: string[] | null
  // Legacy/primary-framework flat fields:
  controls_assessed?: number | null
  pass_count?: number | null
  fail_count?: number | null
  partial_count?: number | null
  score_percent?: number | null
  results?: ControlResult[] | null
  // Multi-framework breakdown:
  framework_results?: FrameworkResult[] | null
  error?: string | null
}

export interface AuditStartResponse {
  audit_id: string
  status: string
  message: string
}

export interface FrameworkInfo {
  id: string
  name: string
  version: string
  description: string
  control_count: number
  automatable_count: number
}

export interface CrosswalkRow {
  signal: string
  description: string
  framework_count: number
  control_count: number
  controls: {
    framework_id: string
    framework_name: string
    control_id: string
    control_name: string
  }[]
}

export interface CrosswalkResponse {
  crosswalk: CrosswalkRow[]
  reuse_factor: number | null
}
