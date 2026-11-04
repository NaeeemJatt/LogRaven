// LogRaven — Compliance Audit Form (Multi-Step Assessment Wizard)
//
// Converts the lengthy single-page audit configuration into a streamlined,
// 3-step widescreen wizard matching the modern-minimal color and design language:
//
// Step 1: Compliance Standards & Frameworks Scope
// Step 2: Target Environment & Cloud Credentials (with live connection guide)
// Step 3: Evidence Window, Cadence & Pre-flight Assessment Review

import { useState, useCallback, useMemo, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  CalendarRange, ShieldCheck,
  Loader2, Copy, Check, Terminal, Layers,
  ChevronDown, ChevronRight, X, Sparkles, BellRing, Cloud, Info,
  ArrowLeft, ArrowRight, AlertCircle, CheckCircle2,
} from 'lucide-react'
import { listFrameworks, listCloudAccounts } from '../../api/compliance'
import type { FrameworkInfo, CloudAccount } from '../../types/audit'

const LOGRAVEN_ACCOUNT_ID = import.meta.env.VITE_AWS_ACCOUNT_ID ?? '382764425926'
const STORAGE_KEY = 'lograven_new_audit_form_v2'

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

type StepNumber = 1 | 2 | 3

// ── Framework categories catalog ──────────────────────────────────────────
const FW_CATEGORIES: { id: string; label: string }[] = [
  { id: 'recommended', label: 'Recommended' },
  { id: 'cloud',       label: 'Cloud & Infrastructure' },
  { id: 'privacy',     label: 'Privacy & Data Protection' },
  { id: 'federal',     label: 'US Federal & Government' },
  { id: 'all',         label: 'All Frameworks' },
]

const FW_CATEGORY_IDS: Record<string, string[]> = {
  recommended: ['soc2', 'iso27001', 'pci_dss', 'hipaa'],
  cloud:       ['cis_aws', 'csa_ccm', 'iso27017'],
  privacy:     ['gdpr', 'iso27018', 'hipaa'],
  federal:     ['nist_csf', 'nist_800_53', 'fedramp'],
}

const RECURRENCE_OPTIONS: { key: string; label: string; desc: string }[] = [
  { key: 'none',   label: 'One-time assessment', desc: 'Single point-in-time audit report' },
  { key: 'daily',  label: 'Daily continuous scan', desc: 'Automated 24h regression alerts' },
  { key: 'weekly', label: 'Weekly compliance cadence', desc: 'Scheduled weekly executive snapshot' },
]

const AWS_TRUST_POLICY_JSON = `{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::${LOGRAVEN_ACCOUNT_ID}:root"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}`

const defaultFormData: AuditFormData = {
  companyName: '',
  roleArn: '',
  auditStartDate: '',
  auditEndDate: '',
  frameworks: ['soc2'],
  recurrence: 'none',
}

export default function AuditForm({ onSubmit, isLoading }: AuditFormProps) {
  const [searchParams, setSearchParams] = useSearchParams()

  // Step state synced with URL search param '?step=X'
  const stepParam = searchParams.get('step')
  const parseStep = (val: string | null): StepNumber => {
    if (val === '2') return 2
    if (val === '3') return 3
    return 1
  }
  const currentStep = parseStep(stepParam)

  // Form State with Session Storage persistence
  const [formData, setFormData] = useState<AuditFormData>(() => {
    try {
      const saved = sessionStorage.getItem(STORAGE_KEY)
      if (saved) {
        return { ...defaultFormData, ...JSON.parse(saved) }
      }
    } catch {
      // fallback
    }
    return defaultFormData
  })

  useEffect(() => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(formData))
    } catch {
      // ignore
    }
  }, [formData])

  const [errors, setErrors] = useState<FieldErrors>({})
  const [dirty, setDirty] = useState<DirtyFields>({
    companyName: false,
    roleArn: false,
    auditStartDate: false,
    auditEndDate: false,
  })
  const [stepError, setStepError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [showPolicy, setShowPolicy] = useState(false)
  const [frameworks, setFrameworks] = useState<FrameworkInfo[]>([])
  const [frameworkError, setFrameworkError] = useState(false)
  const [accounts, setAccounts] = useState<CloudAccount[]>([])
  const [fwCategory, setFwCategory] = useState<string>('recommended')

  useEffect(() => {
    let active = true
    listFrameworks()
      .then((list) => {
        if (active) setFrameworks(list)
      })
      .catch(() => {
        if (active) setFrameworkError(true)
      })
    listCloudAccounts()
      .then((accs) => {
        if (active) setAccounts(accs)
      })
      .catch(() => {
        // silent
      })
    return () => {
      active = false
    }
  }, [])

  // ── Validation Rules ───────────────────────────────────────────────────────
  const validateCompanyName = useCallback((value: string): string | undefined => {
    if (!value.trim()) return 'Company name is required'
    if (value.length < 2) return 'Company name must be at least 2 characters'
    if (value.length > 100) return 'Company name must be at most 100 characters'
    return undefined
  }, [])

  const validateRoleArn = useCallback((value: string): string | undefined => {
    if (!value.trim()) return 'AWS Role ARN is required'
    const arnPattern = /^arn:aws:iam::\d{12}:role\/.+$/
    if (!arnPattern.test(value.trim())) return 'Invalid ARN format. Expected: arn:aws:iam::123456789012:role/RoleName'
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

  const isStep1Valid = useCallback((): boolean => {
    return formData.frameworks.length > 0
  }, [formData.frameworks])

  const isStep2Valid = useCallback((): boolean => {
    return (
      Boolean(formData.companyName.trim()) &&
      Boolean(formData.roleArn.trim()) &&
      !validateCompanyName(formData.companyName) &&
      !validateRoleArn(formData.roleArn)
    )
  }, [formData.companyName, formData.roleArn, validateCompanyName, validateRoleArn])

  const isStep3Valid = useCallback((): boolean => {
    return (
      Boolean(formData.auditStartDate) &&
      Boolean(formData.auditEndDate) &&
      !validateStartDate(formData.auditStartDate) &&
      !validateEndDate(formData.auditEndDate, formData.auditStartDate)
    )
  }, [formData.auditStartDate, formData.auditEndDate, validateStartDate, validateEndDate])

  // Navigation Handler with Route Guards
  const goToStep = useCallback((target: StepNumber) => {
    if (target === 2) {
      if (!isStep1Valid()) {
        setStepError('Please select at least one compliance framework.')
        return
      }
    } else if (target === 3) {
      if (!isStep1Valid()) {
        goToStep(1)
        return
      }
      const cErr = validateCompanyName(formData.companyName)
      const rErr = validateRoleArn(formData.roleArn)
      if (cErr || rErr) {
        setDirty((prev) => ({ ...prev, companyName: true, roleArn: true }))
        setErrors((prev) => ({ ...prev, companyName: cErr, roleArn: rErr }))
        setStepError('Please provide a valid company name and AWS Role ARN.')
        return
      }
    }

    setStepError(null)
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.set('tab', 'audit')
      next.set('step', String(target))
      return next
    })
  }, [isStep1Valid, formData.companyName, formData.roleArn, validateCompanyName, validateRoleArn, setSearchParams])

  // URL route guard enforcement
  useEffect(() => {
    if (currentStep === 2 && !isStep1Valid()) {
      setStepError('Please select at least one compliance framework before continuing.')
      goToStep(1)
    } else if (currentStep === 3) {
      if (!isStep1Valid()) {
        goToStep(1)
      } else if (!isStep2Valid()) {
        setStepError('Please complete organization details and cloud role credentials.')
        goToStep(2)
      }
    }
  }, [currentStep, isStep1Valid, isStep2Valid, goToStep])

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

  // Date Presets helper
  const setDatePreset = (days: number) => {
    const end = new Date()
    const start = new Date()
    start.setDate(end.getDate() - days)
    const format = (d: Date) => d.toISOString().split('T')[0]
    setFormData((prev) => ({
      ...prev,
      auditStartDate: format(start),
      auditEndDate: format(end),
    }))
    setDirty((prev) => ({ ...prev, auditStartDate: true, auditEndDate: true }))
    setErrors((prev) => ({ ...prev, auditStartDate: undefined, auditEndDate: undefined }))
    setStepError(null)
  }

  const windowDays = useMemo(() => {
    if (!formData.auditStartDate || !formData.auditEndDate) return null
    const start = new Date(formData.auditStartDate)
    const end = new Date(formData.auditEndDate)
    const d = Math.floor((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24))
    return d > 0 ? d : null
  }, [formData.auditStartDate, formData.auditEndDate])

  // Catalog
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

  const toggleFramework = useCallback((id: string) => {
    setFormData((prev) => {
      const has = prev.frameworks.includes(id)
      const next = has ? prev.frameworks.filter((f) => f !== id) : [...prev.frameworks, id]
      return { ...prev, frameworks: next.length ? next : prev.frameworks }
    })
    setStepError(null)
  }, [])

  const selectRecommended = useCallback(() => {
    const recs = (FW_CATEGORY_IDS.recommended ?? []).filter((id) => catalog.some((f) => f.id === id))
    setFormData((prev) => ({ ...prev, frameworks: recs.length ? recs : ['soc2'] }))
    setStepError(null)
  }, [catalog])

  const totalControls = useMemo(() => {
    return catalog
      .filter((f) => formData.frameworks.includes(f.id))
      .reduce((sum, f) => sum + f.control_count, 0)
  }, [catalog, formData.frameworks])

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
      try {
        sessionStorage.removeItem(STORAGE_KEY)
      } catch {
        // ignore
      }
      onSubmit(formData)
    } else {
      if (newErrors.companyName || newErrors.roleArn) {
        goToStep(2)
      } else {
        setStepError('Please resolve date errors before launching.')
      }
    }
  }

  const copyPolicy = async () => {
    try {
      await navigator.clipboard.writeText(AWS_TRUST_POLICY_JSON)
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch {
      // ignore
    }
  }

  const recurrenceLabel = RECURRENCE_OPTIONS.find((o) => o.key === formData.recurrence)?.label ?? 'One-time assessment'

  return (
    <div className="space-y-5">
      {/* ── Top Header & Wizard Stepper ────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 sm:p-5 rounded-2xl border border-white/[0.08] bg-surface/50">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-amber-400/10 border border-amber-400/20 flex items-center justify-center text-amber-400 flex-shrink-0">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-display text-lg sm:text-xl font-bold text-text-primary tracking-tight">
              New Compliance Assessment
            </h1>
            <p className="text-xs text-text-muted mt-0.5">
              Define evaluation scope, select verified cloud credentials, and trigger automated evidence collection.
            </p>
          </div>
        </div>

        <div className="text-xs text-text-muted flex items-center gap-1.5 self-start sm:self-auto">
          <span>Step {currentStep} of 3</span>
          <ChevronRight className="w-3.5 h-3.5 text-white/20" />
          <span className="text-amber-300 font-medium whitespace-nowrap">
            {currentStep === 1
              ? 'Standards & Scope'
              : currentStep === 2
              ? 'Target Environment'
              : 'Window & Launch'}
          </span>
        </div>
      </div>

      {/* ── Interactive Step Navigator ───────────────────────────────────── */}
      <nav aria-label="Assessment Steps" className="p-2.5 rounded-xl border border-white/[0.08] bg-surface/30">
        <div className="flex items-center justify-between gap-2 sm:gap-4">
          {[
            { num: 1, title: 'Frameworks' },
            { num: 2, title: 'Target Environment' },
            { num: 3, title: 'Period & Review' },
          ].map(({ num, title }, idx) => {
            const isActive = currentStep === num
            const isPassed = currentStep > num
            const isAllowed =
              num === 1 ||
              (num === 2 && isStep1Valid()) ||
              (num === 3 && isStep1Valid() && isStep2Valid())

            return (
              <div key={num} className="flex items-center gap-2 flex-1">
                <button
                  type="button"
                  disabled={!isAllowed}
                  onClick={() => goToStep(num as StepNumber)}
                  className={`flex items-center gap-2 group text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 rounded-lg p-1 transition-opacity ${
                    !isAllowed ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'
                  }`}
                >
                  <span
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold transition-colors duration-150 ${
                      isActive
                        ? 'bg-amber-400 text-stone-950 shadow-sm'
                        : isPassed
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                        : 'bg-white/[0.05] text-text-muted border border-white/[0.08]'
                    }`}
                  >
                    {isPassed ? <Check className="w-3.5 h-3.5" /> : num}
                  </span>
                  <span
                    className={`text-xs font-medium whitespace-nowrap hidden sm:inline ${
                      isActive
                        ? 'text-text-primary font-semibold'
                        : isPassed
                        ? 'text-emerald-400'
                        : 'text-text-muted'
                    }`}
                  >
                    {title}
                  </span>
                </button>
                {idx < 2 && (
                  <div
                    className={`flex-1 h-[1px] ml-1 sm:ml-2 ${
                      currentStep > idx + 1 ? 'bg-emerald-500/40' : 'bg-white/[0.08]'
                    }`}
                  />
                )}
              </div>
            )
          })}
        </div>
      </nav>

      {/* Global Step Validation Banner */}
      {stepError && (
        <div className="p-3.5 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 text-xs flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5 text-rose-400" />
          <div className="flex-1 leading-relaxed">{stepError}</div>
        </div>
      )}

      {/* ═════════════════════════════════════════════════════════════════════
          PAGE 1: Frameworks & Standards Scope (Wide 2-Column Layout)
         ═════════════════════════════════════════════════════════════════════ */}
      {currentStep === 1 && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          {/* Left Column: Category Selector & Framework Cards (8 cols) */}
          <div className="lg:col-span-8 rounded-2xl border border-white/[0.08] bg-deep/80 backdrop-blur-sm p-6 space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold text-text-primary mb-1">
                  Select Compliance Frameworks
                </h2>
                <p className="text-xs text-text-muted">
                  Evidence is collected once and evaluated simultaneously across all standards you select.
                </p>
              </div>

              {/* Category Filter Dropdown */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-text-muted whitespace-nowrap">Filter:</span>
                <div className="relative">
                  <select
                    id="fwCategory"
                    value={fwCategory}
                    onChange={(e) => setFwCategory(e.target.value)}
                    className="sovereign-input appearance-none cursor-pointer pl-3 pr-8 py-1.5 rounded-lg text-xs bg-surface/60 border border-white/[0.08] text-text-primary focus:border-amber-400/60 focus:ring-1 focus:ring-amber-400/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400"
                  >
                    {FW_CATEGORIES.map((c) => (
                      <option key={c.id} value={c.id}>{c.label}</option>
                    ))}
                  </select>
                  <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted" aria-hidden />
                </div>
              </div>
            </div>

            {frameworkError && (
              <p role="alert" className="text-xs text-amber-300 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                The full framework catalog could not be loaded. SOC 2 is active as a fallback.
              </p>
            )}

            {/* Framework cards - Roomy 2-column grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {visibleFrameworks.map((fw) => {
                const active = formData.frameworks.includes(fw.id)
                return (
                  <button
                    key={fw.id}
                    type="button"
                    onClick={() => toggleFramework(fw.id)}
                    aria-pressed={active}
                    className={`cursor-pointer group flex items-start gap-3 rounded-xl border p-4 text-left transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 active:scale-[0.99] ${
                      active
                        ? 'border-amber-400/50 bg-amber-400/10'
                        : 'border-white/[0.08] bg-surface/40 hover:border-white/[0.16] hover:bg-surface/60'
                    }`}
                  >
                    <span
                      className={`mt-0.5 w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 transition-colors duration-150 ${
                        active
                          ? 'border-amber-400 bg-amber-400 text-stone-950 font-bold'
                          : 'border-white/20 bg-white/[0.02]'
                      }`}
                    >
                      {active && <Check className="w-3 h-3 stroke-[3]" aria-hidden />}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className={`block text-xs font-semibold leading-tight ${active ? 'text-amber-300' : 'text-text-primary'}`}>
                        {fw.name}
                      </span>
                      {fw.description && (
                        <span className="block text-[11px] text-text-muted leading-relaxed mt-1 line-clamp-2">
                          {fw.description}
                        </span>
                      )}
                      <span className="block text-[10px] text-text-muted mt-2 tracking-wide">
                        {fw.control_count} controls · {fw.automatable_count} automatable
                      </span>
                    </span>
                  </button>
                )
              })}
            </div>

            {/* Step 1 Actions */}
            <div className="pt-4 border-t border-white/[0.06] flex items-center justify-between">
              <span className="text-xs text-text-muted">
                {formData.frameworks.length} framework{formData.frameworks.length === 1 ? '' : 's'} selected
              </span>
              <button
                type="button"
                onClick={() => goToStep(2)}
                disabled={!isStep1Valid()}
                className="btn-sovereign inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-semibold motion-safe:transition-transform motion-safe:active:scale-[0.98] motion-reduce:transition-none focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
              >
                <span>Next: Target Environment</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Right Column: Selected Frameworks & Assurance (4 cols) */}
          <div className="lg:col-span-4 space-y-4">
            <div className="rounded-2xl border border-white/[0.08] bg-deep/80 backdrop-blur-sm p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold text-text-primary flex items-center gap-2">
                  <Layers className="w-4 h-4 text-amber-400" /> Selected Frameworks ({formData.frameworks.length})
                </h3>
                <button
                  type="button"
                  onClick={selectRecommended}
                  className="inline-flex items-center gap-1 text-[11px] text-amber-400 hover:text-amber-300 font-medium transition-colors"
                >
                  <Sparkles className="w-3 h-3" /> Recommended
                </button>
              </div>

              {/* Removable chips */}
              <div className="flex flex-wrap gap-2">
                {formData.frameworks.map((id) => (
                  <span
                    key={id}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-amber-400/30 bg-amber-400/10 px-2.5 py-1 text-xs font-medium text-amber-300"
                  >
                    <span>{nameOf(id)}</span>
                    <button
                      type="button"
                      onClick={() => toggleFramework(id)}
                      aria-label={`Remove ${nameOf(id)}`}
                      className="cursor-pointer rounded p-0.5 text-text-muted hover:text-rose-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400"
                    >
                      <X className="w-3 h-3" aria-hidden />
                    </button>
                  </span>
                ))}
              </div>

              <div className="p-3.5 rounded-xl bg-surface/40 border border-white/[0.06] space-y-1.5 text-xs">
                <div className="flex justify-between text-text-secondary">
                  <span>Total Assessment Controls:</span>
                  <span className="font-semibold text-text-primary">{totalControls}</span>
                </div>
                <div className="flex justify-between text-text-secondary">
                  <span>Telemetry Grading Engine:</span>
                  <span className="font-semibold text-emerald-400">Automated</span>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-white/[0.08] bg-surface/30 p-5 space-y-2 text-xs text-text-muted leading-relaxed">
              <div className="flex items-center gap-2 text-text-primary font-semibold">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" /> Unified Scope Architecture
              </div>
              <p>
                LogRaven requests raw configuration telemetry from AWS just once, then maps the evidence across every chosen framework concurrently.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ═════════════════════════════════════════════════════════════════════
          PAGE 2: Target Environment & Cloud Credentials (Wide 2-Column Layout)
         ═════════════════════════════════════════════════════════════════════ */}
      {currentStep === 2 && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          {/* Left Column: Organization & IAM Role ARN (7 cols) */}
          <div className="lg:col-span-7 rounded-2xl border border-white/[0.08] bg-deep/80 backdrop-blur-sm p-6 space-y-5">
            <div>
              <h2 className="text-sm font-semibold text-text-primary mb-1">
                Target Organization &amp; Cloud Role
              </h2>
              <p className="text-xs text-text-muted">
                Specify your company identity and provide the cross-account read-only IAM role ARN.
              </p>
            </div>

            {/* Quick-select from Saved Accounts */}
            {accounts.length > 0 ? (
              <div className="p-4 rounded-xl border border-white/[0.08] bg-surface/40 space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-text-secondary flex items-center gap-1.5">
                    <Cloud className="w-4 h-4 text-amber-400" /> Select From Connected Accounts ({accounts.length})
                  </span>
                  <span className="text-[11px] text-amber-300">Click to autofill</span>
                </div>

                <div className="flex flex-wrap gap-2">
                  {accounts.map((acc) => {
                    const isSelected = formData.roleArn === acc.role_arn
                    return (
                      <button
                        key={acc.id}
                        type="button"
                        onClick={() => {
                          if (acc.role_arn) {
                            setFormData((prev) => ({
                              ...prev,
                              roleArn: acc.role_arn ?? prev.roleArn,
                              companyName: prev.companyName || acc.name || `AWS Account ${acc.account_id || ''}`,
                            }))
                            setDirty((prev) => ({ ...prev, roleArn: true, companyName: true }))
                            setErrors((prev) => ({ ...prev, roleArn: undefined, companyName: undefined }))
                            setStepError(null)
                          }
                        }}
                        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none ${
                          isSelected
                            ? 'bg-amber-400/15 border-amber-400/40 text-amber-300 shadow-sm'
                            : 'bg-surface/60 border-white/[0.08] text-text-muted hover:text-text-primary hover:border-white/[0.18]'
                        }`}
                      >
                        <Cloud className={`w-3.5 h-3.5 ${isSelected ? 'text-amber-400' : 'text-text-muted'}`} />
                        <span>{acc.name || acc.account_id}</span>
                        {acc.account_id && (
                          <span className="font-mono text-[10px] text-text-muted">({acc.account_id})</span>
                        )}
                        {isSelected && <Check className="w-3.5 h-3.5 text-amber-400 ml-1" />}
                      </button>
                    )
                  })}
                </div>
              </div>
            ) : (
              <div className="p-3.5 rounded-xl border border-amber-400/25 bg-amber-400/5 flex items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2 text-text-secondary">
                  <Cloud className="w-4 h-4 text-amber-400 flex-shrink-0" />
                  <span>No saved accounts yet. You can paste an ARN below or connect an account.</span>
                </div>
                <Link
                  to="/compliance/connect/step-1"
                  className="font-semibold text-amber-300 hover:text-amber-200 underline whitespace-nowrap"
                >
                  Connect account
                </Link>
              </div>
            )}

            {/* Company Name Input */}
            <div>
              <label htmlFor="companyName" className="block text-xs font-medium text-text-primary mb-1.5">
                Company / Organization Name <span className="text-rose-400">*</span>
              </label>
              <input
                id="companyName"
                type="text"
                required
                value={formData.companyName}
                onChange={(e) => handleChange('companyName', e.target.value)}
                onBlur={() => handleBlur('companyName')}
                placeholder="e.g. Acme Security Corp"
                className={`w-full px-3.5 py-2.5 rounded-xl text-sm bg-surface/60 border text-text-primary focus:border-amber-400/60 focus:ring-1 focus:ring-amber-400/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 transition-colors duration-150 ${
                  dirty.companyName && errors.companyName ? 'border-rose-500/60' : 'border-white/[0.08]'
                }`}
              />
              {dirty.companyName && errors.companyName && (
                <p className="text-xs mt-1.5 text-rose-400">{errors.companyName}</p>
              )}
            </div>

            {/* Role ARN Input */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label htmlFor="roleArn" className="block text-xs font-medium text-text-primary">
                  AWS IAM Role ARN <span className="text-rose-400">*</span>
                </label>
                <div className="relative group inline-block">
                  <button
                    type="button"
                    className="text-text-muted hover:text-amber-300 p-0.5 rounded transition-colors"
                    aria-label="IAM Role ARN Info"
                  >
                    <Info className="w-3.5 h-3.5" />
                  </button>
                  <div className="absolute right-0 bottom-full mb-1.5 hidden group-hover:block group-focus-within:block w-72 p-2.5 rounded-xl bg-void border border-white/[0.12] text-xs text-text-secondary z-30 pointer-events-none">
                    LogRaven needs a cross-account IAM role with SecurityAudit policy attached. We assume this role read-only to audit your AWS environment.
                  </div>
                </div>
              </div>
              <input
                id="roleArn"
                type="text"
                required
                value={formData.roleArn}
                onChange={(e) => handleChange('roleArn', e.target.value)}
                onBlur={() => handleBlur('roleArn')}
                placeholder="arn:aws:iam::123456789012:role/LogRavenAudit"
                className={`w-full px-3.5 py-2.5 rounded-xl text-xs font-mono bg-surface/60 border text-text-primary focus:border-amber-400/60 focus:ring-1 focus:ring-amber-400/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 transition-colors duration-150 ${
                  dirty.roleArn && errors.roleArn ? 'border-rose-500/60' : 'border-white/[0.08]'
                }`}
              />
              {dirty.roleArn && errors.roleArn && (
                <p className="text-xs mt-1.5 text-rose-400">{errors.roleArn}</p>
              )}
              <p className="text-[11px] text-text-muted mt-1.5">
                Create the role with the policy in the connection guide, then paste its ARN here.
              </p>
            </div>

            {/* Step 2 Actions */}
            <div className="pt-4 border-t border-white/[0.06] flex items-center justify-between">
              <button
                type="button"
                onClick={() => goToStep(1)}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium text-text-secondary hover:text-text-primary hover:bg-white/[0.04] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 whitespace-nowrap"
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Back: Frameworks
              </button>
              <button
                type="button"
                onClick={() => goToStep(3)}
                className="btn-sovereign inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-semibold motion-safe:transition-transform motion-safe:active:scale-[0.98] motion-reduce:transition-none focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
              >
                <span>Next: Period &amp; Review</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Right Column: Connection Guide & AWS SecurityAudit Policy (5 cols) */}
          <div className="lg:col-span-5 rounded-2xl border border-white/[0.08] bg-deep/80 backdrop-blur-sm p-6 space-y-4">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-amber-400" />
              <h3 className="text-xs font-semibold text-text-primary">AWS Connection Guide</h3>
            </div>

            <ol className="space-y-2 text-xs text-text-secondary leading-relaxed list-decimal list-inside">
              <li>Open AWS Console &gt; <strong>IAM &gt; Roles &gt; Create role</strong>.</li>
              <li>
                Select <strong>Custom trust policy</strong> and paste the LogRaven trust policy below.
              </li>
              <li>
                Attach the AWS managed <strong>SecurityAudit</strong> policy (strictly read-only).
              </li>
              <li>Copy the created Role ARN and paste it into the field on the left.</li>
            </ol>

            {/* Collapsible IAM trust policy */}
            <div className="rounded-xl border border-white/[0.08] bg-surface/40 overflow-hidden">
              <div className="flex items-center justify-between gap-2 px-3.5 py-2.5 bg-black/40 border-b border-white/[0.06]">
                <button
                  type="button"
                  onClick={() => setShowPolicy((v) => !v)}
                  aria-expanded={showPolicy}
                  className="cursor-pointer inline-flex items-center gap-1.5 text-xs text-text-secondary hover:text-text-primary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 rounded"
                >
                  <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${showPolicy ? 'rotate-180' : ''}`} aria-hidden />
                  {showPolicy ? 'Hide' : 'View'} IAM trust policy JSON
                </button>
                <button
                  type="button"
                  onClick={() => void copyPolicy()}
                  className="cursor-pointer inline-flex items-center gap-1 rounded-lg border border-white/[0.1] bg-surface/90 px-2.5 py-1 text-xs font-mono text-text-secondary hover:text-text-primary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 whitespace-nowrap"
                >
                  {copied ? <Check className="w-3 h-3 text-emerald-400" aria-hidden /> : <Copy className="w-3 h-3" aria-hidden />}
                  <span>{copied ? 'Copied' : 'Copy'}</span>
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
                    <pre className="p-3 font-mono text-[11px] leading-relaxed overflow-auto max-h-[300px] bg-black/60 text-amber-200/90">
                      {AWS_TRUST_POLICY_JSON}
                    </pre>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <div className="p-3.5 rounded-xl border border-white/[0.06] bg-surface/20 text-xs text-text-muted leading-relaxed">
              <span className="font-semibold text-text-primary block mb-0.5">Strictly Read-Only (SecurityAudit):</span>
              Uses standard AWS <code className="text-amber-300 font-mono text-[11px]">arn:aws:iam::aws:policy/SecurityAudit</code> policy. Zero write permissions, zero secret keys.
            </div>
          </div>
        </div>
      )}

      {/* ═════════════════════════════════════════════════════════════════════
          PAGE 3: Evidence Window, Cadence & Review (Wide 2-Column Layout)
         ═════════════════════════════════════════════════════════════════════ */}
      {currentStep === 3 && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          {/* Left Column: Date Range Presets & Cadence (6 cols) */}
          <div className="lg:col-span-6 rounded-2xl border border-white/[0.08] bg-deep/80 backdrop-blur-sm p-6 space-y-5">
            <div>
              <h2 className="text-sm font-semibold text-text-primary mb-1">
                Evidence Window &amp; Cadence
              </h2>
              <p className="text-xs text-text-muted">
                Specify the telemetry lookback range and configure automated assessment frequency.
              </p>
            </div>

            {/* Quick Presets */}
            <div className="space-y-2">
              <label className="block text-xs font-medium text-text-primary">
                Quick Lookback Presets
              </label>
              <div className="flex flex-wrap gap-2">
                {[
                  { days: 30, label: 'Last 30 Days' },
                  { days: 90, label: 'Last 90 Days (Recommended)' },
                  { days: 180, label: 'Last 180 Days' },
                  { days: 365, label: 'Last 365 Days' },
                ].map((preset) => (
                  <button
                    key={preset.days}
                    type="button"
                    onClick={() => setDatePreset(preset.days)}
                    className="px-3 py-1.5 rounded-lg border border-white/[0.08] bg-surface/40 hover:bg-surface/70 hover:border-amber-400/40 text-xs text-text-secondary hover:text-text-primary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 whitespace-nowrap"
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Date Pickers */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="auditStartDate" className="block text-xs font-medium text-text-primary mb-1.5">
                  Start Date <span className="text-rose-400">*</span>
                </label>
                <input
                  id="auditStartDate"
                  type="date"
                  required
                  value={formData.auditStartDate}
                  onChange={(e) => handleChange('auditStartDate', e.target.value)}
                  onBlur={() => handleBlur('auditStartDate')}
                  className={`w-full px-3.5 py-2.5 rounded-xl text-sm bg-surface/60 border text-text-primary [color-scheme:dark] focus:border-amber-400/60 focus:ring-1 focus:ring-amber-400/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 transition-colors duration-150 ${
                    dirty.auditStartDate && errors.auditStartDate ? 'border-rose-500/60' : 'border-white/[0.08]'
                  }`}
                />
                {dirty.auditStartDate && errors.auditStartDate && (
                  <p className="text-xs mt-1.5 text-rose-400">{errors.auditStartDate}</p>
                )}
              </div>

              <div>
                <label htmlFor="auditEndDate" className="block text-xs font-medium text-text-primary mb-1.5">
                  End Date <span className="text-rose-400">*</span>
                </label>
                <input
                  id="auditEndDate"
                  type="date"
                  required
                  value={formData.auditEndDate}
                  onChange={(e) => handleChange('auditEndDate', e.target.value)}
                  onBlur={() => handleBlur('auditEndDate')}
                  className={`w-full px-3.5 py-2.5 rounded-xl text-sm bg-surface/60 border text-text-primary [color-scheme:dark] focus:border-amber-400/60 focus:ring-1 focus:ring-amber-400/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 transition-colors duration-150 ${
                    dirty.auditEndDate && errors.auditEndDate ? 'border-rose-500/60' : 'border-white/[0.08]'
                  }`}
                />
                {dirty.auditEndDate && errors.auditEndDate && (
                  <p className="text-xs mt-1.5 text-rose-400">{errors.auditEndDate}</p>
                )}
              </div>
            </div>

            {windowDays && (
              <p className="inline-flex items-center gap-1.5 text-xs font-mono text-amber-300 rounded-lg border border-amber-400/30 bg-amber-400/10 px-3 py-1.5">
                <CalendarRange className="w-3.5 h-3.5" aria-hidden />
                <span>{windowDays}-day verified evidence window</span>
              </p>
            )}

            {/* Continuous Monitoring Cadence */}
            <div className="space-y-2 pt-2 border-t border-white/[0.06]">
              <label htmlFor="recurrence" className="block text-xs font-medium text-text-primary mb-1.5">
                Assessment Cadence
              </label>
              <div className="relative">
                <select
                  id="recurrence"
                  value={formData.recurrence}
                  onChange={(e) => setFormData((prev) => ({ ...prev, recurrence: e.target.value }))}
                  className="w-full appearance-none cursor-pointer px-3.5 py-2.5 pr-10 rounded-xl text-sm bg-surface/60 border border-white/[0.08] text-text-primary [color-scheme:dark] focus:border-amber-400/60 focus:ring-1 focus:ring-amber-400/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 transition-colors duration-150"
                >
                  {RECURRENCE_OPTIONS.map((opt) => (
                    <option key={opt.key} value={opt.key}>{opt.label} ({opt.desc})</option>
                  ))}
                </select>
                <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" aria-hidden />
              </div>

              {formData.recurrence !== 'none' && (
                <div className="rounded-xl border border-amber-400/25 bg-amber-400/5 p-3.5 flex gap-2.5 text-xs text-text-secondary leading-relaxed">
                  <BellRing className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" aria-hidden />
                  <p>
                    LogRaven automatically re-runs this assessment <strong className="text-text-primary">{formData.recurrence}</strong> and snapshots each result to your evidence vault.
                  </p>
                </div>
              )}
            </div>

            {/* Back button */}
            <div className="pt-2">
              <button
                type="button"
                onClick={() => goToStep(2)}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium text-text-secondary hover:text-text-primary hover:bg-white/[0.04] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 whitespace-nowrap"
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Back: Target Environment
              </button>
            </div>
          </div>

          {/* Right Column: Configuration Review & Run Action (6 cols) */}
          <div className="lg:col-span-6 rounded-2xl border border-white/[0.08] bg-deep/80 backdrop-blur-sm p-6 space-y-5">
            <div>
              <h2 className="text-sm font-semibold text-text-primary mb-1">
                Assessment Scope Summary
              </h2>
              <p className="text-xs text-text-muted">
                Review your parameters before launching the automated evidence collector.
              </p>
            </div>

            {/* Scope Details Card */}
            <div className="rounded-xl border border-white/[0.08] bg-surface/40 p-4 space-y-3.5 text-xs">
              <div className="flex justify-between items-center pb-2.5 border-b border-white/[0.06]">
                <span className="text-text-muted">Organization:</span>
                <span className="font-semibold text-text-primary">{formData.companyName || 'Not configured'}</span>
              </div>

              <div className="flex justify-between items-start pb-2.5 border-b border-white/[0.06]">
                <span className="text-text-muted">Target IAM Role:</span>
                <span className="font-mono text-[11px] text-amber-300 max-w-[260px] truncate text-right">
                  {formData.roleArn || 'Not configured'}
                </span>
              </div>

              <div className="pb-2.5 border-b border-white/[0.06] space-y-1.5">
                <div className="flex justify-between text-text-muted">
                  <span>Selected Standards ({formData.frameworks.length}):</span>
                  <span className="text-text-secondary">{totalControls} controls</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {formData.frameworks.map((id) => (
                    <span key={id} className="px-2 py-0.5 rounded bg-amber-400/10 border border-amber-400/20 text-amber-300 text-[11px]">
                      {nameOf(id)}
                    </span>
                  ))}
                </div>
              </div>

              <div className="flex justify-between items-center pb-2.5 border-b border-white/[0.06]">
                <span className="text-text-muted">Evidence Window:</span>
                <span className="text-text-primary font-medium">
                  {formData.auditStartDate && formData.auditEndDate
                    ? `${formData.auditStartDate} to ${formData.auditEndDate} (${windowDays}d)`
                    : 'Required'}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-text-muted">Monitoring Schedule:</span>
                <span className="text-text-primary font-medium">{recurrenceLabel}</span>
              </div>
            </div>

            <p className="text-[11px] text-text-muted leading-relaxed">
              Starting the audit triggers read-only metadata ingestion from CloudTrail, IAM, KMS, S3, Config, and GuardDuty. Findings will be mapped in real-time.
            </p>

            {/* Launch Primary Action Button */}
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!isStep1Valid() || !isStep2Valid() || !isStep3Valid() || isLoading}
              className="btn-sovereign w-full py-3.5 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 cursor-pointer motion-safe:transition-transform motion-safe:active:scale-[0.98] motion-reduce:transition-none focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap shadow-sm"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden />
                  <span>Starting assessment…</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4" aria-hidden />
                  <span>Run compliance audit ({formData.frameworks.length})</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
