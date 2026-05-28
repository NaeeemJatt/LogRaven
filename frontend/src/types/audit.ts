// LogRaven — SOC 2 Compliance Audit TypeScript Types
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
}

export interface AuditStatusResponse {
  audit_id: string
  status: string
  percent?: number | null
  step?: string | null
  company_name?: string | null
  controls_assessed?: number | null
  pass_count?: number | null
  fail_count?: number | null
  partial_count?: number | null
  score_percent?: number | null
  results?: ControlResult[] | null
  error?: string | null
}

export interface AuditStartResponse {
  audit_id: string
  status: string
  message: string
}
