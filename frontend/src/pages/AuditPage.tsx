// LogRaven — SOC 2 Compliance "Control Room"
//
// Persistent console shell: a sticky mission rail (phase nav + guidance + trust)
// on the left, and a working stage on the right that swaps between
// form → progress → results. State machine unchanged.

import { useState, useCallback, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ShieldCheck, Cloud,
  PlusCircle, History, Gauge,
} from 'lucide-react'
import AuditForm from '../components/audit/AuditForm'
import AuditProgress from '../components/audit/AuditProgress'
import AuditResults from '../components/audit/AuditResults'
import AuditHistory from '../components/audit/AuditHistory'
import CompliancePosture from '../components/audit/CompliancePosture'
import CloudAccountsManager from '../components/audit/CloudAccountsManager'
import ShareAuditModal from '../components/audit/ShareAuditModal'
import AuditorShareModal from '../components/audit/AuditorShareModal'
import type { AuditFormData } from '../components/audit/AuditForm'
import type { AuditStatusResponse } from '../types/audit'
import { startAudit, getAuditStatus, retryAudit } from '../api/compliance'
import type { AuditSummary } from '../api/compliance'

type AuditStep = 'form' | 'progress' | 'results'
type PageTab = 'audit' | 'accounts' | 'history' | 'posture'

const PAGE_TABS: { key: PageTab; label: string; icon: React.ElementType }[] = [
  { key: 'audit',    label: 'New audit',      icon: PlusCircle },
  { key: 'accounts', label: 'Cloud accounts', icon: Cloud },
  { key: 'history',  label: 'History',        icon: History },
  { key: 'posture',  label: 'Posture',        icon: Gauge },
]

export default function AuditPage() {
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const tabParam = searchParams.get('tab') as PageTab | null
  const tab: PageTab = (tabParam && ['audit', 'accounts', 'history', 'posture'].includes(tabParam))
    ? tabParam
    : 'audit'

  const setTab = useCallback((newTab: PageTab) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.set('tab', newTab)
      return next
    }, { replace: true })
  }, [setSearchParams])

  const [currentStep, setCurrentStep]   = useState<AuditStep>('form')
  const [auditId, setAuditId]           = useState<string | null>(null)
  const [companyName, setCompanyName]   = useState('')
  const [auditResults, setAuditResults] = useState<AuditStatusResponse | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [retryingAuditId, setRetryingAuditId] = useState<string | null>(null)
  const [shareTarget, setShareTarget]   = useState<{ auditId: string; companyName?: string } | null>(null)
  const [isAuditorModalOpen, setIsAuditorModalOpen] = useState(false)

  useEffect(() => {
    if (tabParam === ('auditor' as unknown as PageTab)) {
      setIsAuditorModalOpen(true)
    }
  }, [tabParam])

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

  const handleStartNew = () => {
    setTab('audit')
    setCurrentStep('form')
    setAuditId(null)
    setCompanyName('')
    setAuditResults(null)
    setErrorMessage(null)
  }

  const handleRetryAudit = async (failedAuditId: string, failedCompanyName: string) => {
    setRetryingAuditId(failedAuditId)
    setErrorMessage(null)
    try {
      const retry = await retryAudit(failedAuditId)
      setAuditId(retry.audit_id)
      setCompanyName(failedCompanyName)
      setAuditResults(null)
      setCurrentStep('progress')
      setTab('audit')
      await queryClient.invalidateQueries({ queryKey: ['audits'] })
    } catch (error: unknown) {
      const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data
        ?.detail
      setErrorMessage(detail ?? 'Could not retry that audit.')
    } finally {
      setRetryingAuditId(null)
    }
  }

  // Open a past audit from History: complete → results; in-flight → resume the
  // progress poller (which flips to results itself once the audit finishes).
  const handleOpenAudit = async (audit: AuditSummary) => {
    setErrorMessage(null)
    setAuditId(audit.audit_id)
    setCompanyName(audit.company_name)
    if (audit.status === 'complete') {
      try {
        const data = await getAuditStatus(audit.audit_id)
        setAuditResults(data)
        setCurrentStep('results')
        setTab('audit')
      } catch {
        setErrorMessage('Could not load that audit — please try again.')
      }
    } else {
      setAuditResults(null)
      setCurrentStep('progress')
      setTab('audit')
    }
  }

  return (
    <div className="pt-4 sm:pt-6 pb-12 min-h-screen grid-bg relative">
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-72"
        aria-hidden
        style={{ background: 'radial-gradient(ellipse 70% 100% at 20% 0%, rgba(227,181,126,0.05), transparent 70%)' }}
      />

      <div className="relative px-4 sm:px-6 lg:px-8 py-6 max-w-[1400px] mx-auto">
        <main className="min-w-0">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
            <div>
              <div className="flex items-center gap-2 font-mono text-[10px] text-indigo-400 tracking-[0.2em] uppercase">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
                Continuous Compliance
              </div>
              <h1 className="font-display text-2xl font-bold text-text-primary mt-1">
                Compliance Control Room
              </h1>
            </div>

            <button
              type="button"
              onClick={() => setIsAuditorModalOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-2 text-xs font-semibold text-emerald-300 hover:bg-emerald-500/20 transition-colors shadow-sm self-start sm:self-auto"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" /> Invite Auditor
            </button>
          </div>

          {/* Page tabs: new audit flow / history / posture */}
          <div className="flex items-center justify-between gap-3 mb-6 flex-wrap">
            <div role="tablist" aria-label="Compliance views" className="ops-panel p-1.5 inline-flex flex-wrap gap-1">
                {PAGE_TABS.map(({ key, label, icon: Icon }) => {
                  const isActive = tab === key
                  return (
                    <button
                      key={key}
                      id={`compliance-tab-${key}`}
                      role="tab"
                      aria-selected={isActive}
                      aria-controls="compliance-tabpanel"
                      tabIndex={isActive ? 0 : -1}
                      onClick={() => setTab(key)}
                      onKeyDown={(event) => {
                        if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
                        event.preventDefault()
                        const current = PAGE_TABS.findIndex((item) => item.key === key)
                        const nextIndex =
                          event.key === 'Home'
                            ? 0
                            : event.key === 'End'
                              ? PAGE_TABS.length - 1
                              : (current + (event.key === 'ArrowRight' ? 1 : -1) + PAGE_TABS.length) %
                                PAGE_TABS.length
                        const next = PAGE_TABS[nextIndex].key
                        setTab(next)
                        requestAnimationFrame(() =>
                          document.getElementById(`compliance-tab-${next}`)?.focus(),
                        )
                      }}
                      className={`inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-medium transition-colors ${
                        isActive
                          ? 'bg-indigo-500/12 text-indigo-300 border border-indigo-500/40'
                          : 'text-text-muted hover:text-text-secondary border border-transparent'
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" /> {label}
                    </button>
                  )
                })}
              </div>

            </div>

            {errorMessage && (
              <motion.div
                role="alert"
                aria-live="assertive"
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
                id="compliance-tabpanel"
                role="tabpanel"
                aria-labelledby={`compliance-tab-${tab}`}
                key={`${tab}-${currentStep}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.25 }}
              >
                {tab === 'history' && (
                  <AuditHistory
                    onOpen={(audit) => { void handleOpenAudit(audit) }}
                    onShare={(audit) => setShareTarget({ auditId: audit.audit_id, companyName: audit.company_name })}
                    onRetry={(audit) => {
                      void handleRetryAudit(audit.audit_id, audit.company_name)
                    }}
                    retryingAuditId={retryingAuditId}
                  />
                )}
                {tab === 'accounts' && (
                  <CloudAccountsManager
                    onStartAudit={(accAuditId, accName) => {
                      setAuditId(accAuditId)
                      setCompanyName(accName)
                      setAuditResults(null)
                      setCurrentStep('progress')
                      setTab('audit')
                    }}
                  />
                )}
                {tab === 'posture' && <CompliancePosture />}
                {tab === 'audit' && currentStep === 'form' && (
                  <AuditForm onSubmit={(data) => { void handleFormSubmit(data) }} isLoading={isSubmitting} />
                )}
                {tab === 'audit' && currentStep === 'progress' && auditId && (
                  <AuditProgress
                    auditId={auditId}
                    companyName={companyName}
                    onComplete={handleProgressComplete}
                    onLeave={() => {
                      setTab('history')
                      setCurrentStep('form')
                      void queryClient.invalidateQueries({ queryKey: ['audits'] })
                    }}
                    onRetry={() => handleRetryAudit(auditId, companyName)}
                    isRetrying={retryingAuditId === auditId}
                  />
                )}
                {tab === 'audit' && currentStep === 'results' && auditResults && auditId && (
                  <AuditResults
                    results={auditResults}
                    auditId={auditId}
                    onStartNew={handleStartNew}
                    onShare={() => setShareTarget({ auditId, companyName })}
                  />
                )}
              </motion.div>
            </AnimatePresence>
          </main>
      </div>

      {shareTarget && (
        <ShareAuditModal
          auditId={shareTarget.auditId}
          companyName={shareTarget.companyName}
          onClose={() => setShareTarget(null)}
        />
      )}

      <AuditorShareModal
        isOpen={isAuditorModalOpen}
        companyName={companyName || 'Organization'}
        onClose={() => setIsAuditorModalOpen(false)}
      />
    </div>
  )
}
