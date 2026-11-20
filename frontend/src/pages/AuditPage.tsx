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
  ShieldCheck, Loader2, PlusCircle,
} from 'lucide-react'
import AuditForm from '../components/audit/AuditForm'
import AuditProgress from '../components/audit/AuditProgress'
import AuditResults, { type ViewMode } from '../components/audit/AuditResults'
import AuditHistory from '../components/audit/AuditHistory'
import CloudAccountsManager from '../components/audit/CloudAccountsManager'
import RuleCatalogExplorer from '../components/audit/RuleCatalogExplorer'
import ShareAuditModal from '../components/audit/ShareAuditModal'
import AuditorShareModal from '../components/audit/AuditorShareModal'
import type { AuditFormData } from '../components/audit/AuditForm'
import type { AuditStatusResponse, ControlResult } from '../types/audit'
import { getAuditStatus, retryAudit, listAudits, runNativeCloudScan } from '../api/compliance'
import type { AuditSummary } from '../api/compliance'

type AuditStep = 'form' | 'progress' | 'results'
type PageTab = 'audit' | 'accounts' | 'history' | 'results' | 'catalog'

export default function AuditPage() {
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const tabParam = searchParams.get('tab') as PageTab | null
  const tab: PageTab = (tabParam && ['audit', 'accounts', 'history', 'results', 'catalog'].includes(tabParam))
    ? tabParam
    : (tabParam === ('posture' as unknown as PageTab) ? 'results' : 'audit')

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
  const viewParam = (searchParams.get('view') as ViewMode | null) || 'controls'

  useEffect(() => {
    let isMounted = true
    const loadRequestedAudit = async () => {
      if (tabParam === 'results' || auditIdParam) {
        setIsLoadingResults(true)
        try {
          let targetAuditId = auditIdParam && auditIdParam !== 'latest' ? auditIdParam : null
          if (!targetAuditId) {
            // Guard: If we already have an active audit in memory, check if it already contains the requested framework
            if (auditResults && auditId) {
              if (!fwParam) {
                setIsLoadingResults(false)
                return
              }
              const currentFrameworks = auditResults.framework_results?.map((f) => f.framework_id) || auditResults.frameworks || []
              const cleanFw = fwParam.toLowerCase().replace(/[^a-z0-9]/g, '')
              const alreadyHasFramework = currentFrameworks.some((f) => {
                const cf = f.toLowerCase().replace(/[^a-z0-9]/g, '')
                return cf.includes(cleanFw) || cleanFw.includes(cf)
              })
              if (alreadyHasFramework) {
                setIsLoadingResults(false)
                return
              }
            }

            const audits = await listAudits(1, 10)
            const completedAudits = audits.items.filter((a) => a.status === 'complete')
            let completed = null
            if (fwParam) {
              const cleanFw = fwParam.toLowerCase().replace(/[^a-z0-9]/g, '')
              // First prioritize audits that have MULTIPLE frameworks including this framework
              completed = completedAudits.find((a) =>
                (a.frameworks?.length ?? 0) > 1 &&
                a.frameworks?.some((f) => {
                  const cf = f.toLowerCase().replace(/[^a-z0-9]/g, '')
                  return cf.includes(cleanFw) || cleanFw.includes(cf)
                })
              ) || completedAudits.find((a) =>
                a.frameworks?.some((f) => {
                  const cf = f.toLowerCase().replace(/[^a-z0-9]/g, '')
                  return cf.includes(cleanFw) || cleanFw.includes(cf)
                })
              )
            }
            if (!completed) {
              completed = completedAudits.find((a) => (a.frameworks?.length ?? 0) > 1) || completedAudits[0] || audits.items[0]
            }
            if (completed) {
              targetAuditId = completed.audit_id
            }
          }
          if (targetAuditId) {
            // Guard: If auditResults is already active in memory matching targetAuditId, skip redundant network fetch
            if (auditResults && (auditResults.audit_id === targetAuditId || auditId === targetAuditId)) {
              setIsLoadingResults(false)
              return
            }
            const data = await getAuditStatus(targetAuditId)
            if (!isMounted) return
            setAuditId(targetAuditId)
            setCompanyName(data.company_name || '')
            if (data.status === 'complete') {
              setAuditResults(data)
              setCurrentStep('results')
              setSearchParams((prev) => {
                const next = new URLSearchParams(prev)
                next.set('auditId', targetAuditId)
                return next
              }, { replace: true })
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
      let provider = 'AWS'
      if (formData.roleArn?.startsWith('azure:')) provider = 'AZURE'
      else if (formData.roleArn?.startsWith('gcp:')) provider = 'GCP'

      // Always execute rule-based compliance audit scan (0% AI)
      await handleNativeScan(provider, formData.companyName || 'Cloud Compliance Audit')
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setErrorMessage(detail ?? 'Failed to start compliance audit')
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

  const handleNativeScan = async (provider = 'AWS', customCompanyName?: string) => {
    setIsSubmitting(true)
    setErrorMessage(null)
    try {
      const res = await runNativeCloudScan({ provider })
      const controlsList: Array<{
        cid?: string
        control_id?: string
        title?: string
        provider?: string
        service?: string
        criticality?: string
        status?: 'PASS' | 'FAIL'
        reason?: string
        mandates?: string[]
        passed_resources?: string[]
        failing_resources?: string[]
      }> = Array.isArray(res.controls)
        ? (res.controls as any)
        : Object.values(res.controls || {})

      const mappedControls: ControlResult[] = controlsList.map((c) => ({
        control_id: c.cid ? `LR-${c.provider || 'CLOUD'}-CID-${c.cid}` : (c.control_id || 'LR-CONTROL'),
        control_name: c.title || 'Cloud Security Benchmark Control',
        status: (c.status === 'PASS' ? 'PASS' : 'FAIL') as 'PASS' | 'FAIL',
        confidence: 'HIGH',
        automatable: true,
        category: c.service || 'Security',
        ai_description: c.reason || `Deterministic compliance assessment against live ${c.provider || 'cloud'} ${c.service || 'infrastructure'} configurations.`,
        evidence_references: [
          `Service: ${c.service || 'Cloud Engine'}`,
          `Provider: ${c.provider || 'AWS'}`,
          `Engine: LogRaven Deterministic Rule AST Evaluator`,
        ],
        gaps: c.status === 'FAIL' ? [c.reason || 'Asset configuration violates security baseline.'] : [],
        remediation: `Review and harden ${c.service || 'resource'} policies. Ensure all non-compliant resource policies are locked down.`,
        failing_resources: c.failing_resources || [],
        passed_resources: c.passed_resources || [],
      }))

      const passCount = mappedControls.filter((c) => c.status === 'PASS').length
      const score = Math.round((passCount / Math.max(1, mappedControls.length)) * 100)

      const nativeAuditResult: AuditStatusResponse = {
        audit_id: res.session_id || `audit-${Date.now()}`,
        status: 'complete',
        company_name: customCompanyName || 'LogRaven Native Cloud Compliance Scanner',
        frameworks: ['LOGRAVEN-CSPM-NATIVE'],
        framework_results: [
          {
            framework_id: 'LOGRAVEN-CSPM-NATIVE',
            framework_name: 'LogRaven Enterprise Cloud Benchmark (1,565 Controls)',
            score_percent: score,
            controls_assessed: mappedControls.length,
            pass_count: passCount,
            fail_count: mappedControls.length - passCount,
            partial_count: 0,
            suppressed_count: 0,
            results: mappedControls,
          },
        ],
        results: mappedControls,
        score_percent: score,
        pass_count: passCount,
        fail_count: mappedControls.length - passCount,
      }

      setAuditId(nativeAuditResult.audit_id)
      setCompanyName(nativeAuditResult.company_name || 'Native Cloud Scan')
      setAuditResults(nativeAuditResult)
      setErrorMessage(null)
      setCurrentStep('results')
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          next.set('tab', 'results')
          next.set('auditId', nativeAuditResult.audit_id)
          return next
        },
        { replace: true },
      )
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setErrorMessage(detail ?? 'Failed to execute LogRaven Native Cloud Compliance Scanner.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleFrameworkChange = useCallback((fwId: string) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.set('fw', fwId)
      if (auditId) {
        next.set('auditId', auditId)
      }
      return next
    }, { replace: true })
  }, [setSearchParams, auditId])

  const handleViewChange = useCallback((newView: ViewMode) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.set('view', newView)
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
    <div className="pb-10 min-h-screen relative">
      <div className="relative px-4 sm:px-6 lg:px-8 pt-3 sm:pt-4 pb-6 w-full">
        <main className="min-w-0">
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
                {tab === 'catalog' && (
                  <RuleCatalogExplorer onRunNativeScan={() => void handleNativeScan('AWS')} />
                )}
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
                {tab === 'audit' && currentStep === 'form' && (
                  <AuditForm
                    onSubmit={(data) => { void handleFormSubmit(data) }}
                    isLoading={isSubmitting}
                    onRunNativeScan={() => void handleNativeScan('AWS')}
                  />
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
                    initialView={viewParam}
                    onFrameworkChange={handleFrameworkChange}
                    onViewChange={handleViewChange}
                    onStartNew={handleStartNew}
                    onShare={() => setShareTarget({ auditId, companyName })}
                  />
                )}
                {tab === 'results' && (!auditResults || !auditId) && (
                  <div className="rounded-2xl border border-white/[0.08] bg-deep/80 backdrop-blur-sm p-12 text-center space-y-4">
                    {isLoadingResults ? (
                      <div className="flex flex-col items-center gap-3">
                        <Loader2 className="w-8 h-8 text-amber-400 animate-spin" />
                        <p className="text-xs text-text-muted">Loading posture and gaps…</p>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center gap-3">
                        <ShieldCheck className="w-10 h-10 text-text-muted" />
                        <h3 className="text-sm font-semibold text-text-primary">No Posture and Gaps Available</h3>
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
