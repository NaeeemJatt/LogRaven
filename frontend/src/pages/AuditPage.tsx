// LogRaven — SOC 2 Compliance "Control Room"
//
// Persistent console shell: a sticky mission rail (phase nav + guidance + trust)
// on the left, and a working stage on the right that swaps between
// form → progress → results. State machine unchanged.

import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ShieldCheck, Cloud, Eye, FileCheck2, Lock,
  SlidersHorizontal, Radar, FileBarChart2, Plug, ScanSearch, Check,
} from 'lucide-react'
import AuditForm from '../components/audit/AuditForm'
import AuditProgress from '../components/audit/AuditProgress'
import AuditResults from '../components/audit/AuditResults'
import type { AuditFormData } from '../components/audit/AuditForm'
import type { AuditStatusResponse } from '../types/audit'
import { startAudit } from '../api/compliance'

type AuditStep = 'form' | 'progress' | 'results'

const STEPS: { key: AuditStep; label: string; hint: string; icon: React.ElementType }[] = [
  { key: 'form',     label: 'Configure', hint: 'Scope & credentials',    icon: SlidersHorizontal },
  { key: 'progress', label: 'Assess',    hint: 'Collect & map evidence', icon: Radar },
  { key: 'results',  label: 'Report',    hint: 'Score & evidence pack',  icon: FileBarChart2 },
]
const STEP_ORDER: AuditStep[] = ['form', 'progress', 'results']

const FRAMEWORK_TAGS = [
  { icon: ShieldCheck, label: 'SOC 2 · ISO 27001' },
  { icon: Cloud,       label: 'CIS · PCI DSS' },
  { icon: Eye,         label: 'HIPAA · NIST' },
  { icon: FileCheck2,  label: 'Collect once' },
]

const HOW_IT_WORKS = [
  { icon: Plug,       title: 'Connect', body: 'Assume your read-only IAM role.' },
  { icon: ScanSearch, title: 'Collect', body: 'Pull AWS evidence once, normalize to signals.' },
  { icon: FileCheck2, title: 'Map',     body: 'AI grades every selected framework.' },
]

// ── Sticky mission rail ───────────────────────────────────
function MissionRail({ activeIdx }: { activeIdx: number }) {
  return (
    <aside className="md:sticky md:top-20 space-y-4">
      {/* Brand */}
      <div className="ops-panel p-5">
        <div className="flex items-center gap-2 font-mono text-[10px] text-indigo-400 tracking-[0.22em] uppercase mb-2">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
          Continuous compliance
        </div>
        <h1 className="font-display text-xl font-bold text-text-primary leading-tight">
          Compliance <span className="gradient-text">Control Room</span>
        </h1>
        <div className="flex flex-wrap gap-1.5 mt-3">
          {FRAMEWORK_TAGS.map(({ icon: Icon, label }) => (
            <span key={label} className="inline-flex items-center gap-1 rounded-md border border-white/[0.08] bg-white/[0.02] px-1.5 py-1 text-[10px] font-mono text-text-muted">
              <Icon className="w-3 h-3 text-indigo-400/70" /> {label}
            </span>
          ))}
        </div>
      </div>

      {/* Phase tracker */}
      <div className="ops-panel p-3">
        <div className="px-2 py-1.5 font-mono text-[10px] uppercase tracking-[0.16em] text-text-muted">Phases</div>
        <ol className="space-y-0.5">
          {STEPS.map((s, idx) => {
            const isActive = idx === activeIdx
            const isComplete = idx < activeIdx
            const Icon = s.icon
            return (
              <li key={s.key}>
                <div className={`relative flex items-center gap-3 px-2.5 py-2.5 rounded-lg transition-colors ${isActive ? 'bg-white/[0.05]' : ''}`}>
                  {isActive && <span className="absolute left-0 top-2 bottom-2 w-[2px] rounded-full bg-indigo-400" />}
                  <span className={`w-8 h-8 rounded-lg flex items-center justify-center border flex-shrink-0 ${
                    isComplete ? 'bg-[#8FBDAD]/12 border-[#8FBDAD]/35 text-[#8FBDAD]'
                    : isActive ? 'bg-indigo-500/12 border-indigo-500/35 text-indigo-300'
                    : 'bg-white/[0.02] border-white/[0.08] text-text-muted'
                  }`}>
                    {isComplete ? <Check className="w-4 h-4" strokeWidth={3} /> : <Icon className="w-4 h-4" />}
                  </span>
                  <div className="min-w-0">
                    <div className={`text-sm font-semibold leading-tight ${isActive ? 'text-text-primary' : isComplete ? 'text-[#8FBDAD]' : 'text-text-muted'}`}>
                      {s.label}
                    </div>
                    <div className="text-[10px] text-text-muted truncate">{s.hint}</div>
                  </div>
                </div>
                {idx < STEPS.length - 1 && <div className="ml-[1.4rem] h-2 w-px bg-white/[0.07]" />}
              </li>
            )
          })}
        </ol>
      </div>

      {/* How it works */}
      <div className="ops-panel p-4">
        <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-text-muted mb-3">How it works</div>
        <ol className="space-y-2.5">
          {HOW_IT_WORKS.map(({ icon: Icon, title, body }) => (
            <li key={title} className="flex gap-2.5">
              <Icon className="w-3.5 h-3.5 text-indigo-400/70 flex-shrink-0 mt-0.5" />
              <div>
                <span className="text-xs font-semibold text-text-secondary">{title}</span>
                <span className="text-[11px] text-text-muted"> — {body}</span>
              </div>
            </li>
          ))}
        </ol>
      </div>

      {/* Trust */}
      <div className="rounded-xl border border-[#8FBDAD]/20 bg-[#8FBDAD]/[0.04] p-4 flex gap-2.5">
        <Lock className="w-4 h-4 text-[#8FBDAD] flex-shrink-0 mt-0.5" />
        <p className="text-[11px] text-text-muted leading-relaxed">
          <span className="text-text-secondary font-semibold">Read-only &amp; scoped.</span> LogRaven only
          lists/gets CloudTrail, IAM and GuardDuty — never writes to your account.
        </p>
      </div>
    </aside>
  )
}

export default function AuditPage() {
  const [currentStep, setCurrentStep]   = useState<AuditStep>('form')
  const [auditId, setAuditId]           = useState<string | null>(null)
  const [companyName, setCompanyName]   = useState('')
  const [auditResults, setAuditResults] = useState<AuditStatusResponse | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleFormSubmit = async (formData: AuditFormData) => {
    setIsSubmitting(true)
    setErrorMessage(null)
    try {
      const data = await startAudit({
        company_name:     formData.companyName,
        role_arn:         formData.roleArn,
        audit_start_date: formData.auditStartDate,
        audit_end_date:   formData.auditEndDate,
        frameworks:       formData.frameworks,
        recurrence:       formData.recurrence,
      })
      setAuditId(data.audit_id)
      setCompanyName(formData.companyName)
      setCurrentStep('progress')
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setErrorMessage(detail ?? 'Failed to start audit')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleProgressComplete = useCallback((data: AuditStatusResponse) => {
    setAuditResults(data)
    setCurrentStep('results')
  }, [])

  const handleProgressError = useCallback((error: string) => {
    setErrorMessage(error)
    setCurrentStep('form')
  }, [])

  const handleStartNew = () => {
    setCurrentStep('form')
    setAuditId(null)
    setCompanyName('')
    setAuditResults(null)
    setErrorMessage(null)
  }

  const activeIdx = STEP_ORDER.indexOf(currentStep)

  return (
    <div className="pt-16 min-h-screen grid-bg relative">
      <div
        className="pointer-events-none absolute inset-x-0 top-16 h-72"
        aria-hidden
        style={{ background: 'radial-gradient(ellipse 70% 100% at 20% 0%, rgba(227,181,126,0.05), transparent 70%)' }}
      />

      <div className="relative px-4 sm:px-6 lg:px-8 py-6 max-w-[1400px] mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-[260px_minmax(0,1fr)] gap-6 items-start">
          <MissionRail activeIdx={activeIdx} />

          <main className="min-w-0">
            {errorMessage && (
              <motion.div
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-5 px-4 py-3 rounded-xl border border-threat-critical/25 bg-threat-critical/[0.06] flex items-start justify-between gap-3"
              >
                <p className="text-sm text-threat-critical">{errorMessage}</p>
                <button
                  onClick={() => setErrorMessage(null)}
                  className="text-xs flex-shrink-0 text-threat-critical/70 hover:text-threat-critical transition-colors"
                  aria-label="Dismiss error"
                >
                  ✕
                </button>
              </motion.div>
            )}

            <AnimatePresence mode="wait">
              <motion.div
                key={currentStep}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.25 }}
              >
                {currentStep === 'form' && (
                  <AuditForm onSubmit={(data) => { void handleFormSubmit(data) }} isLoading={isSubmitting} />
                )}
                {currentStep === 'progress' && auditId && (
                  <AuditProgress
                    auditId={auditId}
                    companyName={companyName}
                    onComplete={handleProgressComplete}
                    onError={handleProgressError}
                  />
                )}
                {currentStep === 'results' && auditResults && auditId && (
                  <AuditResults results={auditResults} auditId={auditId} onStartNew={handleStartNew} />
                )}
              </motion.div>
            </AnimatePresence>
          </main>
        </div>
      </div>
    </div>
  )
}
