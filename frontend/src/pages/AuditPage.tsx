// LogRaven — SOC 2 Compliance Audit Page
//
// State machine managing the 3-step audit flow:
//   form → progress → results
// All transitions handled here; no sub-routes.

import { useState, useCallback } from 'react'
import AuditForm from '../components/audit/AuditForm'
import AuditProgress from '../components/audit/AuditProgress'
import AuditResults from '../components/audit/AuditResults'
import type { AuditFormData } from '../components/audit/AuditForm'
import type { AuditStatusResponse } from '../types/audit'
import { startAudit } from '../api/compliance'

type AuditStep = 'form' | 'progress' | 'results'

const STEP_LABELS: Record<AuditStep, string> = {
  form:     'Form Setup',
  progress: 'Running Audit',
  results:  'Results',
}
const STEP_ORDER: AuditStep[] = ['form', 'progress', 'results']

export default function AuditPage() {
  const [currentStep, setCurrentStep]   = useState<AuditStep>('form')
  const [auditId, setAuditId]           = useState<string | null>(null)
  const [companyName, setCompanyName]   = useState('')
  const [auditResults, setAuditResults] = useState<AuditStatusResponse | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // ── form → progress ──────────────────────────────────────────────────────
  const handleFormSubmit = async (formData: AuditFormData) => {
    setIsSubmitting(true)
    setErrorMessage(null)
    try {
      const data = await startAudit({
        company_name:     formData.companyName,
        role_arn:         formData.roleArn,
        audit_start_date: formData.auditStartDate,
        audit_end_date:   formData.auditEndDate,
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

  // ── progress → results ───────────────────────────────────────────────────
  const handleProgressComplete = useCallback((data: AuditStatusResponse) => {
    setAuditResults(data)
    setCurrentStep('results')
  }, [])

  // ── progress → form (failure or cancel) ──────────────────────────────────
  const handleProgressError = useCallback((error: string) => {
    setErrorMessage(error)
    setCurrentStep('form')
  }, [])

  // ── results → form (start new) ───────────────────────────────────────────
  const handleStartNew = () => {
    setCurrentStep('form')
    setAuditId(null)
    setCompanyName('')
    setAuditResults(null)
    setErrorMessage(null)
  }

  return (
    <div className="pt-16 min-h-screen">
      <main className="px-4 sm:px-6 lg:px-8 py-8">
        {/* ── Page title ─────────────────────────────────────────────────── */}
        <div className="mb-8">
          <div className="font-mono text-[10px] text-indigo-400 tracking-widest uppercase mb-1">Compliance</div>
          <h1 className="font-display text-2xl font-bold text-text-primary tracking-tight">
            SOC 2 Compliance Audit
          </h1>
          <p className="text-sm mt-1 text-text-muted">
            Automated evidence collection and control mapping
          </p>
        </div>

        {/* ── Step indicator ─────────────────────────────────────────────── */}
        <div className="flex items-center gap-2 mb-8">
          {STEP_ORDER.map((step, idx) => {
            const stepIdx    = STEP_ORDER.indexOf(currentStep)
            const isActive   = step === currentStep
            const isComplete = STEP_ORDER.indexOf(step) < stepIdx

            return (
              <div key={step} className="flex items-center gap-2">
                <div className="flex items-center gap-2">
                  <span
                    className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 font-mono"
                    style={{
                      backgroundColor: isComplete ? 'rgba(20,184,166,0.2)' : isActive ? 'rgba(99,102,241,0.2)' : 'rgba(255,255,255,0.05)',
                      color: isComplete ? '#14B8A6' : isActive ? '#818CF8' : '#475569',
                      border: isComplete ? '1px solid rgba(20,184,166,0.4)' : isActive ? '1px solid rgba(99,102,241,0.4)' : '1px solid rgba(255,255,255,0.08)',
                    }}
                  >
                    {isComplete ? '✓' : idx + 1}
                  </span>
                  <span
                    className="text-sm font-medium"
                    style={{
                      color: isActive ? '#F1F5F9' : isComplete ? '#14B8A6' : '#475569',
                    }}
                  >
                    {STEP_LABELS[step]}
                  </span>
                </div>
                {idx < STEP_ORDER.length - 1 && (
                  <span className="mx-1 text-text-ghost">—</span>
                )}
              </div>
            )
          })}
        </div>

        {/* ── Error banner ───────────────────────────────────────────────── */}
        {errorMessage && (
          <div className="mb-6 px-4 py-3 rounded-xl border border-rose-500/20 bg-rose-500/5 flex items-start justify-between gap-3">
            <p className="text-sm text-rose-400">{errorMessage}</p>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-xs flex-shrink-0 text-rose-400/70 hover:text-rose-400 transition-colors"
              aria-label="Dismiss error"
            >
              ✕
            </button>
          </div>
        )}

        {/* ── Step content ───────────────────────────────────────────────── */}
        {currentStep === 'form' && (
          <AuditForm
            onSubmit={(data) => { void handleFormSubmit(data) }}
            isLoading={isSubmitting}
          />
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
          <AuditResults
            results={auditResults}
            auditId={auditId}
            onStartNew={handleStartNew}
          />
        )}
      </main>
    </div>
  )
}