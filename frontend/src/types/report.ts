// LogRaven — Report TypeScript Types

export interface Finding {
  id: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'informational'
  title: string
  description: string
  mitre_technique_id: string | null
  mitre_technique_name: string | null
  mitre_tactic: string | null
  iocs: string[]
  remediation: string | null
  finding_type: 'correlated' | 'single'
  source_files: string[]
  confidence: number
}

export interface Report {
  id: string
  investigation_id: string
  summary: string | null
  severity_counts: Record<string, number>
  correlated_findings: Finding[]
  single_source_findings: Finding[]
  mitre_techniques: string[]
  created_at: string
}
