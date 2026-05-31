// LogRaven — SOC 2 Audit Form (Control Room stage)
//
// Workbench layout: scope inputs on the left, a persistent AWS connection
// guide (role steps + copyable IAM policy) on the right.

import { useState, useCallback, useMemo, type ReactNode } from 'react'
import {
  Building2, KeyRound, CalendarRange, ShieldCheck,
  Loader2, Copy, Check, Terminal,
} from 'lucide-react'

const LOGRAVEN_ACCOUNT_ID = import.meta.env.VITE_AWS_ACCOUNT_ID ?? 'YOUR_LOGRAVEN_ACCOUNT_ID'

interface AuditFormProps {
  onSubmit: (formData: AuditFormData) => void
  isLoading: boolean
}

export interface AuditFormData {
  companyName: string
  roleArn: string
  auditStartDate: string
  auditEndDate: string
}

interface FieldErrors {
  companyName?: string
  roleArn?: string
  auditStartDate?: string
  auditEndDate?: string
}
interface DirtyFields {
  companyName: boolean
  roleArn: boolean
  auditStartDate: boolean
  auditEndDate: boolean
}

const IAM_POLICY_JSON = `{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudtrail:LookupEvents",
        "iam:GetAccountSummary",
        "iam:GetAccountPasswordPolicy",
        "iam:ListUsers",
        "iam:ListMFADevices",
        "guardduty:ListDetectors",
        "guardduty:ListFindings",
        "guardduty:GetFindings"
      ],
      "Resource": "*"
    }
  ]
}`

export default function AuditForm({ onSubmit, isLoading }: AuditFormProps) {
  const [formData, setFormData] = useState<AuditFormData>({
    companyName: '', roleArn: '', auditStartDate: '', auditEndDate: '',
  })
  const [errors, setErrors] = useState<FieldErrors>({})
  const [dirty, setDirty] = useState<DirtyFields>({
    companyName: false, roleArn: false, auditStartDate: false, auditEndDate: false,
  })
  const [copied, setCopied] = useState(false)

  const validateCompanyName = useCallback((value: string): string | undefined => {
    if (!value.trim()) return 'Company name is required'
    if (value.length < 2) return 'Company name must be at least 2 characters'
    if (value.length > 100) return 'Company name must be at most 100 characters'
    return undefined
  }, [])

  const validateRoleArn = useCallback((value: string): string | undefined => {
    if (!value.trim()) return 'AWS Role ARN is required'
    const arnPattern = /^arn:aws:iam::\d{12}:role\/.+$/
    if (!arnPattern.test(value)) return 'Invalid ARN format. Expected: arn:aws:iam::123456789012:role/RoleName'
    return undefined
  }, [])

  const validateStartDate = useCallback((value: string): string | undefined => {
    if (!value) return 'Audit start date is required'
    const date = new Date(value)
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    if (date > today) return 'Start date cannot be in the future'
    return undefined
  }, [])

  const validateEndDate = useCallback((value: string, startDate: string): string | undefined => {
    if (!value) return 'Audit end date is required'
    if (!startDate) return undefined
    const start = new Date(startDate)
    const end = new Date(value)
    if (end <= start) return 'End date must be after start date'
    const daysDiff = Math.floor((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24))
    if (daysDiff > 365) return 'Audit period cannot exceed 365 days'
    return undefined
  }, [])

  const handleBlur = useCallback((field: keyof AuditFormData) => {
    setDirty((prev) => ({ ...prev, [field]: true }))
    let error: string | undefined
    if (field === 'companyName') error = validateCompanyName(formData.companyName)
    else if (field === 'roleArn') error = validateRoleArn(formData.roleArn)
    else if (field === 'auditStartDate') error = validateStartDate(formData.auditStartDate)
    else if (field === 'auditEndDate') error = validateEndDate(formData.auditEndDate, formData.auditStartDate)
    setErrors((prev) => ({ ...prev, [field]: error }))
  }, [formData, validateCompanyName, validateRoleArn, validateStartDate, validateEndDate])

  const handleChange = useCallback((field: keyof AuditFormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
    if (dirty[field] && value.trim()) setErrors((prev) => ({ ...prev, [field]: undefined }))
  }, [dirty])

  const hasErrors = Object.values(errors).some((e) => e !== undefined)
  const hasAllFields = formData.companyName.trim() && formData.roleArn.trim() && formData.auditStartDate && formData.auditEndDate
  const isFormValid = hasAllFields && !hasErrors

  const windowDays = useMemo(() => {
    if (!formData.auditStartDate || !formData.auditEndDate) return null
    const start = new Date(formData.auditStartDate)
    const end = new Date(formData.auditEndDate)
    const d = Math.floor((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24))
    return d > 0 ? d : null
  }, [formData.auditStartDate, formData.auditEndDate])

  const handleSubmit = () => {
    setDirty({ companyName: true, roleArn: true, auditStartDate: true, auditEndDate: true })
    const newErrors: FieldErrors = {
      companyName: validateCompanyName(formData.companyName),
      roleArn: validateRoleArn(formData.roleArn),
      auditStartDate: validateStartDate(formData.auditStartDate),
      auditEndDate: validateEndDate(formData.auditEndDate, formData.auditStartDate),
    }
    setErrors(newErrors)
    if (Object.values(newErrors).every((e) => !e)) onSubmit(formData)
  }

  const copyPolicy = async () => {
    try {
      await navigator.clipboard.writeText(IAM_POLICY_JSON)
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch { /* clipboard unavailable */ }
  }

  // = RENDER HELPERS =
  const fieldClass = (hasError?: string, mono = false) =>
    `sovereign-input w-full px-3.5 py-2.5 rounded-lg text-sm ${mono ? 'font-mono' : ''} ${
      hasError ? '!border-threat-critical/60 focus:!border-threat-critical/60' : ''
    }`

  const sectionLabel = (n: string, icon: ReactNode, title: string) => (
    <div className="flex items-center gap-2.5 mb-3.5">
      <span className="w-7 h-7 rounded-lg bg-indigo-500/10 border border-indigo-500/25 flex items-center justify-center text-indigo-300">
        {icon}
      </span>
      <div>
        <div className="font-mono text-[9px] text-text-muted tracking-wider">{n}</div>
        <div className="text-sm font-semibold text-text-primary leading-none">{title}</div>
      </div>
    </div>
  )

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_minmax(0,380px)] gap-5 items-start">
      {/* ── Scope inputs ─────────────────────────────────────────────────── */}
      <div className="ops-panel overflow-hidden">
        <div className="px-6 py-4 border-b border-white/[0.07]">
          <h2 className="font-display text-base font-bold text-text-primary tracking-tight">New assessment</h2>
          <p className="text-xs mt-0.5 text-text-muted">Define the scope, then run the evidence collector.</p>
        </div>

        <div className="px-6 py-6 space-y-7">
          <section>
            {sectionLabel('01', <Building2 className="w-3.5 h-3.5" />, 'Organization')}
            <input
              type="text"
              value={formData.companyName}
              onChange={(e) => handleChange('companyName', e.target.value)}
              onBlur={() => handleBlur('companyName')}
              placeholder="Company name — e.g., Acme Inc."
              className={fieldClass(dirty.companyName ? errors.companyName : undefined)}
            />
            {dirty.companyName && errors.companyName && (
              <p className="text-xs mt-1.5 text-threat-critical">{errors.companyName}</p>
            )}
          </section>

          <section>
            {sectionLabel('02', <KeyRound className="w-3.5 h-3.5" />, 'AWS connection')}
            <input
              type="text"
              value={formData.roleArn}
              onChange={(e) => handleChange('roleArn', e.target.value)}
              onBlur={() => handleBlur('roleArn')}
              placeholder="arn:aws:iam::123456789012:role/LogRavenAudit"
              className={fieldClass(dirty.roleArn ? errors.roleArn : undefined, true)}
            />
            {dirty.roleArn && errors.roleArn && (
              <p className="text-xs mt-1.5 text-threat-critical">{errors.roleArn}</p>
            )}
            <p className="text-[11px] text-text-muted mt-2">
              Create the role with the policy on the right, then paste its ARN here.
            </p>
          </section>

          <section>
            {sectionLabel('03', <CalendarRange className="w-3.5 h-3.5" />, 'Evidence window')}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-[10px] font-mono uppercase tracking-wider text-text-muted mb-1.5">Start date</label>
                <input
                  type="date"
                  value={formData.auditStartDate}
                  onChange={(e) => handleChange('auditStartDate', e.target.value)}
                  onBlur={() => handleBlur('auditStartDate')}
                  className={`${fieldClass(dirty.auditStartDate ? errors.auditStartDate : undefined)} [color-scheme:dark]`}
                />
                {dirty.auditStartDate && errors.auditStartDate && (
                  <p className="text-xs mt-1.5 text-threat-critical">{errors.auditStartDate}</p>
                )}
              </div>
              <div>
                <label className="block text-[10px] font-mono uppercase tracking-wider text-text-muted mb-1.5">End date</label>
                <input
                  type="date"
                  value={formData.auditEndDate}
                  onChange={(e) => handleChange('auditEndDate', e.target.value)}
                  onBlur={() => handleBlur('auditEndDate')}
                  className={`${fieldClass(dirty.auditEndDate ? errors.auditEndDate : undefined)} [color-scheme:dark]`}
                />
                {dirty.auditEndDate && errors.auditEndDate && (
                  <p className="text-xs mt-1.5 text-threat-critical">{errors.auditEndDate}</p>
                )}
              </div>
            </div>
            {windowDays && (
              <p className="mt-2.5 inline-flex items-center gap-1.5 text-[11px] font-mono text-text-secondary rounded-md border border-white/[0.07] bg-white/[0.02] px-2 py-1">
                <CalendarRange className="w-3 h-3 text-indigo-400/70" />
                {windowDays}-day evidence window
              </p>
            )}
          </section>

          <button
            onClick={handleSubmit}
            disabled={!isFormValid || isLoading}
            className="btn-sovereign w-full py-3 rounded-lg font-semibold text-sm flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading
              ? <><Loader2 className="w-4 h-4 animate-spin" /> Starting assessment…</>
              : <><ShieldCheck className="w-4 h-4" /> Run SOC 2 audit</>}
          </button>
        </div>
      </div>

      {/* ── Connection guide (persistent) ────────────────────────────────── */}
      <div className="ops-panel overflow-hidden xl:sticky xl:top-20">
        <div className="px-5 py-3.5 border-b border-white/[0.07] flex items-center gap-2">
          <Terminal className="w-3.5 h-3.5 text-indigo-300" />
          <span className="text-sm font-semibold text-text-primary">Connection guide</span>
        </div>
        <div className="px-5 py-5 space-y-4">
          <ol className="space-y-2.5 text-xs text-text-secondary">
            <li className="flex gap-2"><span className="font-mono text-indigo-400">1</span> IAM → Roles → Create role.</li>
            <li className="flex gap-2"><span className="font-mono text-indigo-400">2</span> Trusted entity “Another AWS account”, ID{' '}
              <span className="font-mono font-semibold text-text-primary break-all">{LOGRAVEN_ACCOUNT_ID}</span>.</li>
            <li className="flex gap-2"><span className="font-mono text-indigo-400">3</span> Attach this read-only inline policy:</li>
          </ol>

          <div className="relative">
            <button
              type="button"
              onClick={() => void copyPolicy()}
              className="absolute right-2 top-2 z-10 inline-flex items-center gap-1 rounded-md border border-white/[0.1] bg-surface/90 px-2 py-1 text-[10px] font-mono text-text-secondary hover:text-text-primary transition-colors"
            >
              {copied ? <Check className="w-3 h-3 text-[#8FBDAD]" /> : <Copy className="w-3 h-3" />}
              {copied ? 'Copied' : 'Copy'}
            </button>
            <pre className="p-3 pr-14 rounded-lg font-mono text-[10.5px] leading-relaxed overflow-auto max-h-[340px] border border-white/[0.07] bg-void/80 text-text-muted">
              {IAM_POLICY_JSON}
            </pre>
          </div>
        </div>
      </div>
    </div>
  )
}
