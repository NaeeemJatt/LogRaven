// LogRaven — Compliance Audit Form (Control Room stage)
//
// Workbench layout: a collapsible, dropdown-driven scope builder on the left and
// a persistent AWS connection guide (role steps + copyable IAM policy) on the
// right. Sections collapse to keep the form roomy; frameworks are browsed by
// category; monitoring reveals contextual options on demand.

import { useState, useCallback, useMemo, useEffect, type ReactNode } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Building2, KeyRound, CalendarRange, ShieldCheck,
  Loader2, Copy, Check, Terminal, Layers, RefreshCw,
  ChevronDown, X, Sparkles, BellRing,
} from 'lucide-react'
import { listFrameworks } from '../../api/compliance'
import type { FrameworkInfo } from '../../types/audit'

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
  frameworks: string[]
  recurrence: string
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

type SectionId = 'org' | 'aws' | 'window' | 'frameworks' | 'monitoring'

// ── Framework browsing: group the catalog into pickable categories ─────────
const FW_CATEGORIES: { id: string; label: string }[] = [
  { id: 'recommended', label: 'Recommended' },
  { id: 'cloud',       label: 'Cloud & infrastructure' },
  { id: 'privacy',     label: 'Privacy & data protection' },
  { id: 'federal',     label: 'US federal & government' },
  { id: 'all',         label: 'All frameworks' },
]
const FW_CATEGORY_IDS: Record<string, string[]> = {
  recommended: ['soc2', 'iso27001', 'pci_dss', 'hipaa'],
  cloud:       ['cis_aws', 'csa_ccm', 'iso27017'],
  privacy:     ['gdpr', 'iso27018', 'hipaa'],
  federal:     ['nist_csf', 'nist_800_53', 'fedramp'],
}

const RECURRENCE_OPTIONS: { key: string; label: string }[] = [
  { key: 'none',   label: 'One-time assessment' },
  { key: 'daily',  label: 'Daily re-scan' },
  { key: 'weekly', label: 'Weekly re-scan' },
]

const IAM_POLICY_JSON = `{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudtrail:LookupEvents",
        "cloudtrail:DescribeTrails",
        "iam:GetAccountSummary",
        "iam:GetAccountPasswordPolicy",
        "iam:ListUsers",
        "iam:ListMFADevices",
        "iam:GenerateCredentialReport",
        "iam:GetCredentialReport",
        "iam:ListEntitiesForPolicy",
        "access-analyzer:ListAnalyzers",
        "access-analyzer:ListFindingsV2",
        "guardduty:ListDetectors",
        "guardduty:ListFindings",
        "guardduty:GetFindings",
        "s3:ListAllMyBuckets",
        "s3:GetEncryptionConfiguration",
        "s3:GetAccountPublicAccessBlock",
        "ec2:GetEbsEncryptionByDefault",
        "ec2:DescribeFlowLogs",
        "ec2:DescribeSecurityGroups",
        "rds:DescribeDBInstances",
        "kms:ListKeys",
        "kms:DescribeKey",
        "kms:GetKeyRotationStatus",
        "config:DescribeConfigurationRecorderStatus",
        "securityhub:DescribeHub",
        "inspector2:BatchGetAccountStatus",
        "logs:DescribeLogGroups",
        "cloudwatch:DescribeAlarms",
        "backup:ListBackupPlans",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}`

// ── Collapsible section shell ──────────────────────────────────────────────
function Section({
  index, icon, title, summary, complete, open, onToggle, children,
}: {
  index: string
  icon: ReactNode
  title: string
  summary?: string
  complete?: boolean
  open: boolean
  onToggle: () => void
  children: ReactNode
}) {
  return (
    <div className="border-b border-white/[0.06] last:border-b-0">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="w-full flex items-center gap-3.5 px-6 py-4 text-left cursor-pointer transition-colors hover:bg-white/[0.02] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50 focus-visible:ring-inset"
      >
        <span
          aria-hidden
          className={`w-9 h-9 rounded-lg flex items-center justify-center border flex-shrink-0 transition-colors ${
            complete
              ? 'bg-[#8FBDAD]/12 border-[#8FBDAD]/35 text-[#8FBDAD]'
              : 'bg-indigo-500/10 border-indigo-500/25 text-indigo-300'
          }`}
        >
          {complete ? <Check className="w-4 h-4" strokeWidth={3} /> : icon}
        </span>
        <span className="min-w-0">
          <span className="block font-mono text-[9px] text-text-muted tracking-[0.18em]">{index}</span>
          <span className="block text-sm font-semibold text-text-primary leading-tight">{title}</span>
        </span>
        <span className="ml-auto flex items-center gap-3 pl-3">
          {summary && (
            <span className="hidden sm:block text-[11px] font-mono text-text-muted truncate max-w-[180px]">{summary}</span>
          )}
          <ChevronDown
            aria-hidden
            className={`w-4 h-4 text-text-muted transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
          />
        </span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="px-6 pb-6 pt-0.5">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default function AuditForm({ onSubmit, isLoading }: AuditFormProps) {
  const [formData, setFormData] = useState<AuditFormData>({
    companyName: '', roleArn: '', auditStartDate: '', auditEndDate: '',
    frameworks: ['soc2'], recurrence: 'none',
  })
  const [errors, setErrors] = useState<FieldErrors>({})
  const [dirty, setDirty] = useState<DirtyFields>({
    companyName: false, roleArn: false, auditStartDate: false, auditEndDate: false,
  })
  const [copied, setCopied] = useState(false)
  const [showPolicy, setShowPolicy] = useState(false)
  const [frameworks, setFrameworks] = useState<FrameworkInfo[]>([])
  const [fwCategory, setFwCategory] = useState<string>('recommended')
  const [open, setOpen] = useState<Record<SectionId, boolean>>({
    org: true, aws: true, window: true, frameworks: true, monitoring: false,
  })

  const toggleSection = useCallback((id: SectionId) => {
    setOpen((prev) => ({ ...prev, [id]: !prev[id] }))
  }, [])

  useEffect(() => {
    let active = true
    listFrameworks()
      .then((list) => { if (active) setFrameworks(list) })
      .catch(() => { /* non-fatal: form still works with the soc2 default */ })
    return () => { active = false }
  }, [])

  const toggleFramework = useCallback((id: string) => {
    setFormData((prev) => {
      const has = prev.frameworks.includes(id)
      const next = has ? prev.frameworks.filter((f) => f !== id) : [...prev.frameworks, id]
      return { ...prev, frameworks: next.length ? next : prev.frameworks }
    })
  }, [])

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

  const handleBlur = useCallback((field: keyof DirtyFields) => {
    setDirty((prev) => ({ ...prev, [field]: true }))
    let error: string | undefined
    if (field === 'companyName') error = validateCompanyName(formData.companyName)
    else if (field === 'roleArn') error = validateRoleArn(formData.roleArn)
    else if (field === 'auditStartDate') error = validateStartDate(formData.auditStartDate)
    else if (field === 'auditEndDate') error = validateEndDate(formData.auditEndDate, formData.auditStartDate)
    setErrors((prev) => ({ ...prev, [field]: error }))
  }, [formData, validateCompanyName, validateRoleArn, validateStartDate, validateEndDate])

  const handleChange = useCallback((field: keyof DirtyFields, value: string) => {
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

  // Catalog (falls back to a sensible SOC 2 default while frameworks load).
  const catalog = useMemo<FrameworkInfo[]>(
    () => (frameworks.length
      ? frameworks
      : [{ id: 'soc2', name: 'SOC 2 Type II', control_count: 11, automatable_count: 11, version: '', description: 'Trust Services Criteria for security, availability and confidentiality.' }]),
    [frameworks],
  )

  const visibleFrameworks = useMemo<FrameworkInfo[]>(() => {
    if (fwCategory === 'all') return catalog
    const ids = FW_CATEGORY_IDS[fwCategory] ?? []
    const inCat = catalog.filter((f) => ids.includes(f.id))
    return inCat.length ? inCat : catalog
  }, [catalog, fwCategory])

  const nameOf = useCallback(
    (id: string) => catalog.find((f) => f.id === id)?.name ?? id.toUpperCase(),
    [catalog],
  )

  const selectRecommended = useCallback(() => {
    const recs = (FW_CATEGORY_IDS.recommended ?? []).filter((id) => catalog.some((f) => f.id === id))
    setFormData((prev) => ({ ...prev, frameworks: recs.length ? recs : ['soc2'] }))
  }, [catalog])

  const handleSubmit = () => {
    setDirty({ companyName: true, roleArn: true, auditStartDate: true, auditEndDate: true })
    const newErrors: FieldErrors = {
      companyName: validateCompanyName(formData.companyName),
      roleArn: validateRoleArn(formData.roleArn),
      auditStartDate: validateStartDate(formData.auditStartDate),
      auditEndDate: validateEndDate(formData.auditEndDate, formData.auditStartDate),
    }
    setErrors(newErrors)
    if (Object.values(newErrors).every((e) => !e)) {
      onSubmit(formData)
    } else {
      // Re-open any section that now has an error so it isn't hidden.
      setOpen((prev) => ({
        ...prev,
        org: prev.org || !!newErrors.companyName,
        aws: prev.aws || !!newErrors.roleArn,
        window: prev.window || !!newErrors.auditStartDate || !!newErrors.auditEndDate,
      }))
    }
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

  const recurrenceLabel = RECURRENCE_OPTIONS.find((o) => o.key === formData.recurrence)?.label ?? 'One-time'

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_minmax(0,380px)] gap-5 items-start">
      {/* ── Scope builder (collapsible sections) ─────────────────────────── */}
      <div className="ops-panel overflow-hidden">
        <div className="px-6 py-5 border-b border-white/[0.07]">
          <h2 className="font-display text-base font-bold text-text-primary tracking-tight">New assessment</h2>
          <p className="text-xs mt-1 text-text-muted">Define the scope, then run the evidence collector. Tap a section to expand or collapse it.</p>
        </div>

        {/* 01 — Frameworks (dropdown-driven browser) */}
        <Section
          index="01" icon={<Layers className="w-4 h-4" />} title="Frameworks"
          summary={`${formData.frameworks.length} selected`}
          complete={formData.frameworks.length > 0}
          open={open.frameworks} onToggle={() => toggleSection('frameworks')}
        >
          <p className="text-[11px] text-text-muted mb-4">
            Evidence is collected once and graded against every framework you select.
          </p>

          {/* Selected summary chips (cross-category) */}
          <div className="flex flex-wrap items-center gap-2 mb-4">
            {formData.frameworks.map((id) => (
              <span key={id} className="inline-flex items-center gap-1.5 rounded-md border border-indigo-500/40 bg-indigo-500/12 pl-2.5 pr-1.5 py-1 text-[11px] font-medium text-text-primary">
                {nameOf(id)}
                <button
                  type="button"
                  onClick={() => toggleFramework(id)}
                  aria-label={`Remove ${nameOf(id)}`}
                  className="cursor-pointer rounded p-0.5 text-text-muted hover:text-threat-critical transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50"
                >
                  <X className="w-3 h-3" aria-hidden />
                </button>
              </span>
            ))}
            <button
              type="button"
              onClick={selectRecommended}
              className="cursor-pointer inline-flex items-center gap-1.5 rounded-md border border-white/[0.1] bg-white/[0.02] px-2.5 py-1 text-[11px] font-medium text-text-secondary hover:text-text-primary hover:border-white/20 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50"
            >
              <Sparkles className="w-3 h-3 text-indigo-400/80" aria-hidden /> Use recommended
            </button>
          </div>

          {/* Category dropdown */}
          <label htmlFor="fwCategory" className="block text-[10px] font-mono uppercase tracking-wider text-text-muted mb-1.5">
            Browse by category
          </label>
          <div className="relative">
            <select
              id="fwCategory"
              value={fwCategory}
              onChange={(e) => setFwCategory(e.target.value)}
              className="sovereign-input w-full appearance-none cursor-pointer px-3.5 py-2.5 pr-10 rounded-lg text-sm [color-scheme:dark]"
            >
              {FW_CATEGORIES.map((c) => (
                <option key={c.id} value={c.id}>{c.label}</option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" aria-hidden />
          </div>

          {/* Framework cards for the chosen category — roomy 2-col grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4">
            {visibleFrameworks.map((fw) => {
              const active = formData.frameworks.includes(fw.id)
              return (
                <button
                  key={fw.id}
                  type="button"
                  onClick={() => toggleFramework(fw.id)}
                  aria-pressed={active}
                  className={`cursor-pointer group flex items-start gap-3 rounded-xl border p-3.5 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50 ${
                    active
                      ? 'border-indigo-500/50 bg-indigo-500/12'
                      : 'border-white/[0.08] bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.04]'
                  }`}
                >
                  <span className={`mt-0.5 w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 ${active ? 'border-indigo-400 bg-indigo-500/40' : 'border-white/25'}`}>
                    {active && <Check className="w-3 h-3 text-indigo-100" strokeWidth={3} aria-hidden />}
                  </span>
                  <span className="min-w-0">
                    <span className={`block text-sm font-semibold leading-tight ${active ? 'text-text-primary' : 'text-text-secondary'}`}>{fw.name}</span>
                    {fw.description && (
                      <span className="block text-[11px] text-text-muted leading-snug mt-1 line-clamp-2">{fw.description}</span>
                    )}
                    <span className="block text-[9px] font-mono text-text-muted mt-2 tracking-wide">
                      {fw.control_count} controls · {fw.automatable_count} automatable
                    </span>
                  </span>
                </button>
              )
            })}
          </div>
        </Section>

        {/* 02 — Organization */}
        <Section
          index="02" icon={<Building2 className="w-4 h-4" />} title="Organization"
          summary={formData.companyName.trim() || 'Required'}
          complete={!!formData.companyName.trim() && !errors.companyName}
          open={open.org} onToggle={() => toggleSection('org')}
        >
          <label htmlFor="companyName" className="block text-[10px] font-mono uppercase tracking-wider text-text-muted mb-1.5">
            Company name
          </label>
          <input
            id="companyName"
            type="text"
            value={formData.companyName}
            onChange={(e) => handleChange('companyName', e.target.value)}
            onBlur={() => handleBlur('companyName')}
            placeholder="e.g., Acme Inc."
            className={fieldClass(dirty.companyName ? errors.companyName : undefined)}
          />
          {dirty.companyName && errors.companyName && (
            <p className="text-xs mt-1.5 text-threat-critical">{errors.companyName}</p>
          )}
        </Section>

        {/* 03 — AWS connection */}
        <Section
          index="03" icon={<KeyRound className="w-4 h-4" />} title="AWS connection"
          summary={formData.roleArn.trim() ? (errors.roleArn ? 'Check ARN' : 'Role set') : 'Required'}
          complete={!!formData.roleArn.trim() && !errors.roleArn}
          open={open.aws} onToggle={() => toggleSection('aws')}
        >
          <label htmlFor="roleArn" className="block text-[10px] font-mono uppercase tracking-wider text-text-muted mb-1.5">
            IAM role ARN
          </label>
          <input
            id="roleArn"
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
            Create the role with the policy in the connection guide, then paste its ARN here.
          </p>
        </Section>

        {/* 04 — Evidence window */}
        <Section
          index="04" icon={<CalendarRange className="w-4 h-4" />} title="Evidence window"
          summary={windowDays ? `${windowDays} days` : 'Required'}
          complete={!!windowDays && !errors.auditStartDate && !errors.auditEndDate}
          open={open.window} onToggle={() => toggleSection('window')}
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="auditStartDate" className="block text-[10px] font-mono uppercase tracking-wider text-text-muted mb-1.5">Start date</label>
              <input
                id="auditStartDate"
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
              <label htmlFor="auditEndDate" className="block text-[10px] font-mono uppercase tracking-wider text-text-muted mb-1.5">End date</label>
              <input
                id="auditEndDate"
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
            <p className="mt-3 inline-flex items-center gap-1.5 text-[11px] font-mono text-text-secondary rounded-md border border-white/[0.07] bg-white/[0.02] px-2 py-1">
              <CalendarRange className="w-3 h-3 text-indigo-400/70" aria-hidden />
              {windowDays}-day evidence window
            </p>
          )}
        </Section>

        {/* 05 — Continuous monitoring (dropdown + contextual options) */}
        <Section
          index="05" icon={<RefreshCw className="w-4 h-4" />} title="Continuous monitoring"
          summary={recurrenceLabel}
          complete={formData.recurrence !== 'none'}
          open={open.monitoring} onToggle={() => toggleSection('monitoring')}
        >
          <label htmlFor="recurrence" className="block text-[10px] font-mono uppercase tracking-wider text-text-muted mb-1.5">
            Cadence
          </label>
          <div className="relative">
            <select
              id="recurrence"
              value={formData.recurrence}
              onChange={(e) => setFormData((prev) => ({ ...prev, recurrence: e.target.value }))}
              className="sovereign-input w-full appearance-none cursor-pointer px-3.5 py-2.5 pr-10 rounded-lg text-sm [color-scheme:dark]"
            >
              {RECURRENCE_OPTIONS.map((opt) => (
                <option key={opt.key} value={opt.key}>{opt.label}</option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" aria-hidden />
          </div>

          <AnimatePresence initial={false}>
            {formData.recurrence !== 'none' && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <div className="mt-3 rounded-lg border border-indigo-500/20 bg-indigo-500/[0.05] p-3.5 flex gap-2.5">
                  <BellRing className="w-4 h-4 text-indigo-300 flex-shrink-0 mt-0.5" aria-hidden />
                  <p className="text-[11px] text-text-secondary leading-relaxed">
                    LogRaven re-runs this assessment <span className="font-semibold text-text-primary">{formData.recurrence}</span> and
                    snapshots each result to the evidence vault. You’ll see a posture trend and be flagged when a control regresses.
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </Section>

        {/* Run bar */}
        <div className="px-6 py-5 border-t border-white/[0.07] bg-white/[0.015]">
          <div className="flex items-center justify-between gap-3 mb-3 text-[11px] font-mono text-text-muted">
            <span>{formData.frameworks.length} framework{formData.frameworks.length === 1 ? '' : 's'}</span>
            <span>{windowDays ? `${windowDays}-day window` : 'No window set'} · {recurrenceLabel}</span>
          </div>
          <button
            onClick={handleSubmit}
            disabled={!isFormValid || isLoading}
            className="btn-sovereign w-full py-3 rounded-lg font-semibold text-sm flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading
              ? <><Loader2 className="w-4 h-4 animate-spin" aria-hidden /> Starting assessment…</>
              : <><ShieldCheck className="w-4 h-4" aria-hidden /> Run compliance audit ({formData.frameworks.length})</>}
          </button>
        </div>
      </div>

      {/* ── Connection guide (persistent, collapsible policy) ────────────── */}
      <div className="ops-panel overflow-hidden xl:sticky xl:top-20">
        <div className="px-5 py-3.5 border-b border-white/[0.07] flex items-center gap-2">
          <Terminal className="w-3.5 h-3.5 text-indigo-300" aria-hidden />
          <span className="text-sm font-semibold text-text-primary">Connection guide</span>
        </div>
        <div className="px-5 py-5 space-y-4">
          <ol className="space-y-2.5 text-xs text-text-secondary">
            <li className="flex gap-2"><span className="font-mono text-indigo-400">1</span> IAM → Roles → Create role.</li>
            <li className="flex gap-2"><span className="font-mono text-indigo-400">2</span> Trusted entity “Another AWS account”, ID{' '}
              <span className="font-mono font-semibold text-text-primary break-all">{LOGRAVEN_ACCOUNT_ID}</span>.</li>
            <li className="flex gap-2"><span className="font-mono text-indigo-400">3</span> Attach the read-only inline policy below, then paste the role ARN.</li>
          </ol>

          {/* Collapsible IAM policy */}
          <div className="rounded-lg border border-white/[0.07] overflow-hidden">
            <div className="flex items-center justify-between gap-2 px-3 py-2 bg-void/60">
              <button
                type="button"
                onClick={() => setShowPolicy((v) => !v)}
                aria-expanded={showPolicy}
                className="cursor-pointer inline-flex items-center gap-1.5 text-[11px] font-mono text-text-secondary hover:text-text-primary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50 rounded"
              >
                <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${showPolicy ? 'rotate-180' : ''}`} aria-hidden />
                {showPolicy ? 'Hide' : 'View'} IAM policy JSON
              </button>
              <button
                type="button"
                onClick={() => void copyPolicy()}
                className="cursor-pointer inline-flex items-center gap-1 rounded-md border border-white/[0.1] bg-surface/90 px-2 py-1 text-[10px] font-mono text-text-secondary hover:text-text-primary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50"
              >
                {copied ? <Check className="w-3 h-3 text-[#8FBDAD]" aria-hidden /> : <Copy className="w-3 h-3" aria-hidden />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
            <AnimatePresence initial={false}>
              {showPolicy && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <pre className="p-3 rounded-b-lg font-mono text-[10.5px] leading-relaxed overflow-auto max-h-[340px] bg-void/80 text-text-muted">
                    {IAM_POLICY_JSON}
                  </pre>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  )
}
