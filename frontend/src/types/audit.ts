// LogRaven — Multi-Framework Compliance Audit TypeScript Types
//
// Mirrors the Pydantic models from backend/app/api/compliance/routes.py

export interface ControlException {
  id: string
  business_justification: string
  compensating_controls?: string | null
  risk_level?: string
  suppressed_by: string
  expires_at?: string | null
}

export interface RemediationGuide {
  control_id: string
  title: string
  threat_rationale: string
  estimated_time_minutes: number
  console_steps: string[]
  aws_cli_command: string
  terraform_snippet: string
  verification_command: string
}

export interface ControlResult {
  control_id: string
  control_name: string
  status: 'PASS' | 'FAIL' | 'PARTIAL' | 'SUPPRESSED' | string
  confidence: 'HIGH' | 'MEDIUM' | 'LOW' | string
  ai_description: string
  gaps: string[]
  evidence_references: string[]
  framework?: string | null
  category?: string | null
  automatable?: boolean | null
  remediation?: string | null
  exception?: ControlException | null
  remediation_guide?: RemediationGuide | null
}

export interface FrameworkResult {
  framework_id: string
  framework_name: string
  controls_assessed: number
  pass_count: number
  fail_count: number
  partial_count: number
  suppressed_count?: number
  score_percent: number
  raw_score_percent?: number | null
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
  suppressed_count?: number | null
  score_percent?: number | null
  raw_score_percent?: number | null
  results?: ControlResult[] | null
  // Multi-framework breakdown:
  framework_results?: FrameworkResult[] | null
  error?: string | null
}

export interface ExceptionResponse {
  id: string
  company_name: string
  framework: string
  control_id: string
  business_justification: string
  compensating_controls?: string | null
  risk_level: string
  suppressed_by: string
  status: string
  expires_at?: string | null
  created_at: string
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

export interface CloudAccount {
  id: string
  name: string
  provider: 'aws' | 'gcp' | 'azure' | string
  role_arn?: string | null
  account_id?: string | null
  gcp_project_id?: string | null
  gcp_service_account_email?: string | null
  gcp_workload_identity_pool?: string | null
  azure_tenant_id?: string | null
  azure_subscription_id?: string | null
  azure_client_id?: string | null
  default_frameworks: string[]
  scan_schedule: 'none' | 'daily' | 'weekly' | 'monthly' | string
  next_run_at?: string | null
  last_scanned_at?: string | null
  last_verified_at?: string | null
  is_active?: boolean
  external_id?: string | null
  health_status: 'connected' | 'permission_error' | 'unverified' | string
  health_error?: string | null
  created_at: string
  updated_at?: string | null
  latest_score_percent?: number | null
}

export interface CreateCloudAccountBody {
  name: string
  provider?: 'aws' | 'gcp' | 'azure' | string
  role_arn?: string
  gcp_project_id?: string
  gcp_service_account_email?: string
  gcp_workload_identity_pool?: string
  azure_tenant_id?: string
  azure_subscription_id?: string
  azure_client_id?: string
  default_frameworks?: string[]
  scan_schedule?: string
}

export interface UpdateCloudAccountBody {
  name?: string
  default_frameworks?: string[]
  scan_schedule?: string
  role_arn?: string
  gcp_project_id?: string
  gcp_service_account_email?: string
  gcp_workload_identity_pool?: string
  azure_tenant_id?: string
  azure_subscription_id?: string
  azure_client_id?: string
}

export interface AuditorAccessToken {
  id: string
  company_name: string
  recipient_name?: string | null
  recipient_email?: string | null
  allowed_frameworks: string[]
  can_download_raw_evidence: boolean
  expires_at: string
  is_expired: boolean
  is_revoked: boolean
  access_count: number
  last_accessed_at?: string | null
  created_at: string
}

export interface CreateAuditorTokenBody {
  company_name: string
  cloud_account_id?: string | null
  recipient_name?: string
  recipient_email?: string
  passcode?: string
  duration_days?: number
  allowed_frameworks?: string[]
  can_download_raw_evidence?: boolean
}

export interface AuditorTokenCreatedResponse {
  id: string
  token: string
  company_name: string
  recipient_name?: string | null
  recipient_email?: string | null
  allowed_frameworks: string[]
  can_download_raw_evidence: boolean
  expires_at: string
  created_at: string
}

export interface AuditorPortalOverview {
  company_name: string
  recipient_name?: string | null
  expires_at: string
  allowed_frameworks: string[]
  can_download_raw_evidence: boolean
  latest_audit?: {
    audit_id: string
    score_percent: number
    raw_score_percent: number
    frameworks: string[]
    completed_at?: string | null
    controls_passed: number
    controls_failed: number
    controls_partial: number
    controls_suppressed: number
    total_controls: number
  } | null
  recent_audits: Array<{
    audit_id: string
    score_percent: number
    raw_score_percent: number
    frameworks: string[]
    completed_at?: string | null
  }>
  active_exceptions_count: number
}

export interface AuditorPortalException {
  id: string
  control_id: string
  framework: string
  status: string
  justification: string
  compensating_controls?: string | null
  authorized_by?: string | null
  expires_at?: string | null
  created_at?: string | null
}

export type GraphCategory =
  | 'internet'
  | 'network'
  | 'compute'
  | 'identity'
  | 'storage'
  | 'database'
  | 'security_service'

export type GraphSeverity = 'clean' | 'low' | 'medium' | 'high' | 'critical'

export interface GraphNode {
  id: string
  label: string
  category: GraphCategory
  provider: string
  severity: GraphSeverity
  failing_controls: string[]
  metadata: Record<string, unknown>
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  relationship: 'exposes' | 'attaches_to' | 'assumes_role' | 'reads_from' | 'writes_to' | 'encrypts' | 'monitors'
  is_attack_path: boolean
}

export interface CriticalPath {
  path_id: string
  title: string
  severity: GraphSeverity
  description: string
  node_ids: string[]
}

export interface AttackPathGraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
  toxic_combinations_count: number
  critical_paths: CriticalPath[]
  assessed_at?: string | null
}



