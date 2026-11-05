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
  Cloud,
  PlusCircle, History, Gauge, ShieldCheck, Loader2,
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
import { startAudit, getAuditStatus, retryAudit, listAudits } from '../api/compliance'
import type { AuditSummary } from '../api/compliance'

type AuditStep = 'form' | 'progress' | 'results'
type PageTab = 'audit' | 'accounts' | 'history' | 'posture' | 'results'

const BASE_PAGE_TABS: { key: PageTab; label: string; icon: React.ElementType }[] = [
  { key: 'results',  label: 'Scan Result',    icon: ShieldCheck },
  { key: 'audit',    label: 'New audit',      icon: PlusCircle },
  { key: 'accounts', label: 'Cloud accounts', icon: Cloud },
  { key: 'history',  label: 'History',        icon: History },
  { key: 'posture',  label: 'Posture',        icon: Gauge },
]

export default function AuditPage() {
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const tabParam = searchParams.get('tab') as PageTab | null
  const tab: PageTab = (tabParam && ['audit', 'accounts', 'history', 'posture', 'results'].includes(tabParam))
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
  const [isLoadingResults, setIsLoadingResults] = useState(false)
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

  const auditIdParam = searchParams.get('auditId') || searchParams.get('audit_id')
  const fwParam = searchParams.get('fw')

  useEffect(() => {
    let isMounted = true
    const loadRequestedAudit = async () => {
      if (tabParam === 'results' || auditIdParam) {
        setIsLoadingResults(true)
        try {
          let targetAuditId = auditIdParam && auditIdParam !== 'latest' ? auditIdParam : null
          if (!targetAuditId) {
            const audits = await listAudits(1, 5)
            const completed = audits.items.find((a) => a.status === 'complete') || audits.items[0]
            if (completed) {
              targetAuditId = completed.audit_id
            }
          }
          if (targetAuditId) {
            const data = await getAuditStatus(targetAuditId)
            if (!isMounted) return
            setAuditId(targetAuditId)
            setCompanyName(data.company_name || '')
            if (data.status === 'complete') {
              setAuditResults(data)
              setCurrentStep('results')
            } else if (data.status === 'pending' || data.status === 'running') {
              setAuditResults(null)
              setCurrentStep('progress')
            } else {
              setErrorMessage(data.error || 'Audit failed.')
              setCurrentStep('form')
            }
          }
        } catch {
          if (!isMounted) return
          setErrorMessage('Could not load the requested compliance audit.')
        } finally {
          if (isMounted) setIsLoadingResults(false)
        }
      }
    }
    void loadRequestedAudit()
    return () => {
      isMounted = false
    }
  }, [tabParam, auditIdParam, setTab])

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
    setAuditId(data.audit_id)
    setCompanyName(data.company_name || '')
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.set('tab', 'results')
      if (data.audit_id) {
        next.set('auditId', data.audit_id)
      }
      return next
    }, { replace: true })
  }, [setSearchParams])

  const handleStartNew = () => {
    setSearchParams(() => {
      const next = new URLSearchParams()
      next.set('tab', 'audit')
      return next
    }, { replace: true })
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
        setSearchParams((prev) => {
          const next = new URLSearchParams(prev)
          next.set('tab', 'results')
          next.set('auditId', audit.audit_id)
          return next
        }, { replace: true })
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
    <div className="pb-10 min-h-screen grid-bg relative">
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-72"
        aria-hidden
        style={{ background: 'radial-gradient(ellipse 70% 100% at 20% 0%, rgba(227,181,126,0.05), transparent 70%)' }}
      />

      <div className="relative px-4 sm:px-6 lg:px-8 pt-3 sm:pt-4 pb-6 max-w-[1400px] mx-auto">
        <main className="min-w-0">
          {/* Page tabs: results / new audit / accounts / history / posture */}
          <div className="flex items-center justify-between gap-3 mb-4">
            <div role="tablist" aria-label="Compliance views" className="ops-panel p-1 inline-flex flex-wrap gap-1">
              {BASE_PAGE_TABS.map(({ key, label, icon: Icon }) => {
                const isActive = tab === key
                return (
                  <button
                    key={key}
                    id={`compliance-tab-${key}`}
                    role="tab"
                    aria-selected={isActive}
                    aria-controls="compliance-tabpanel"
                    tabIndex={isActive ? 0 : -1}
                    onClick={() => {
                      if (key === 'audit') {
                        handleStartNew()
                      } else {
                        setTab(key)
                      }
                    }}
                    onKeyDown={(event) => {
                      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
                      event.preventDefault()
                      const current = BASE_PAGE_TABS.findIndex((item) => item.key === key)
                      const nextIndex =
                        event.key === 'Home'
                          ? 0
                          : event.key === 'End'
                            ? BASE_PAGE_TABS.length - 1
                            : (current + (event.key === 'ArrowRight' ? 1 : -1) + BASE_PAGE_TABS.length) %
                              BASE_PAGE_TABS.length
                      const next = BASE_PAGE_TABS[nextIndex].key
                      if (next === 'audit') {
                        handleStartNew()
                      } else {
                        setTab(next)
                      }
                      requestAnimationFrame(() =>
                        document.getElementById(`compliance-tab-${next}`)?.focus(),
                      )
                    }}
                    className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] ${
                      isActive
                        ? 'bg-amber-400/10 text-amber-300 border border-amber-400/30'
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
                {tab === 'results' && auditResults && auditId && (
                  <AuditResults
                    results={auditResults}
                    auditId={auditId}
                    initialFrameworkId={fwParam || undefined}
                    onStartNew={handleStartNew}
                    onShare={() => setShareTarget({ auditId, companyName })}
                  />
                )}
                {tab === 'results' && (!auditResults || !auditId) && (
                  <div className="rounded-2xl border border-white/[0.08] bg-deep/80 backdrop-blur-sm p-12 text-center space-y-4">
                    {isLoadingResults ? (
                      <div className="flex flex-col items-center gap-3">
                        <Loader2 className="w-8 h-8 text-amber-400 animate-spin" />
                        <p className="text-xs text-text-muted">Loading scan result...</p>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center gap-3">
                        <ShieldCheck className="w-10 h-10 text-text-muted" />
                        <h3 className="text-sm font-semibold text-text-primary">No Scan Result Available</h3>
                        <p className="text-xs text-text-muted max-w-sm">
                          No compliance assessments have been run yet. Start a new scan to evaluate controls across your cloud infrastructure.
                        </p>
                        <button
                          type="button"
                          onClick={handleStartNew}
                          className="btn-sovereign inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold cursor-pointer"
                        >
                          <PlusCircle className="w-3.5 h-3.5" /> Start New Scan
                        </button>
                      </div>
                    )}
                  </div>
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
