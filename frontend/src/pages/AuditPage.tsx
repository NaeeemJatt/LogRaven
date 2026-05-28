// LogRaven — SOC 2 Compliance Audit Page
//
// State machine managing the 3-step audit flow:
//   form → progress → results
// All transitions handled here; no sub-routes.

import { useState, useCallback } from 'react'
import Navbar from '../components/layout/Navbar'
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
    <div className="min-h-screen bg-raven-950 text-raven-200">
      <Navbar />

      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
        {/* ── Page title ─────────────────────────────────────────────────── */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold tracking-tight" style={{ color: '#E6EDF3' }}>
            SOC 2 Compliance Audit
          </h1>
          <p className="text-sm mt-1" style={{ color: '#8B949E' }}>
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
                    className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                    style={{
                      backgroundColor: isComplete ? '#3FB950' : isActive ? '#2F81F7' : '#30363D',
                      color: isComplete || isActive ? '#0D1117' : '#8B949E',
                    }}
                  >
                    {isComplete ? '✓' : idx + 1}
                  </span>
                  <span
                    className="text-sm font-medium"
                    style={{
                      color: isActive ? '#E6EDF3' : isComplete ? '#3FB950' : '#8B949E',
                    }}
                  >
                    {STEP_LABELS[step]}
                  </span>
                </div>
                {idx < STEP_ORDER.length - 1 && (
                  <span className="mx-1 text-xs" style={{ color: '#30363D' }}>
                    —
                  </span>
                )}
              </div>
            )
          })}
        </div>

        {/* ── Error banner ───────────────────────────────────────────────── */}
        {errorMessage && (
          <div
            className="mb-6 px-4 py-3 rounded border flex items-start justify-between gap-3"
            style={{ backgroundColor: '#1a0a0a', borderColor: '#F85149' }}
          >
            <p className="text-sm" style={{ color: '#F85149' }}>
              {errorMessage}
            </p>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-xs flex-shrink-0 hover:opacity-70 transition-opacity"
              style={{ color: '#F85149' }}
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
