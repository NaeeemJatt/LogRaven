// LogRaven — Audit history (GET /api/v1/audits)
//
// Lists the user's past compliance audits, newest first. Complete audits can
// be opened (results view) or shared; in-flight ones resume the progress view.

import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import {
  History, Loader2, AlertOctagon, Share2, ArrowRight,
  RefreshCw, Building2, CalendarDays, Repeat,
} from 'lucide-react'
import { listAudits } from '../../api/compliance'
import type { AuditSummary } from '../../api/compliance'
import { useAuthStore } from '../../store/authStore'
import { formatDateTime } from '../../utils/dateTime'

interface AuditHistoryProps {
  onOpen: (audit: AuditSummary) => void
  onShare: (audit: AuditSummary) => void
  onRetry: (audit: AuditSummary) => void
  retryingAuditId: string | null
}

const STATUS_STYLE: Record<string, { color: string; label: string }> = {
  complete:   { color: '#8FBDAD', label: 'Complete' },
  failed:     { color: '#DB8585', label: 'Failed' },
  pending:    { color: '#D9C27E', label: 'Pending' },
  processing: { color: '#D9C27E', label: 'Running' },
  running:    { color: '#D9C27E', label: 'Running' },
  retried:    { color: '#93A4B5', label: 'Retried' },
}

function scoreColor(score: number): string {
  return score >= 80 ? '#8FBDAD' : score >= 50 ? '#D9C27E' : '#DB8585'
}

export default function AuditHistory({
  onOpen,
  onShare,
  onRetry,
  retryingAuditId,
}: AuditHistoryProps) {
  const user = useAuthStore((state) => state.user)
  const timezone = user?.timezone
  const [page, setPage] = useState(1)
  const { data, isLoading, isError, refetch, isRefetching } = useQuery({
    queryKey: ['audits', user?.id, page],
    queryFn: () => listAudits(page),
  })

  useEffect(() => {
    if (!data) return
    const lastPage = Math.max(1, data.totalPages)
    if (page > lastPage) setPage(lastPage)
  }, [data, page])

  if (isLoading) {
    return (
      <div className="ops-panel p-12 flex items-center justify-center text-sm text-text-muted">
        <Loader2 className="w-4 h-4 animate-spin mr-2" /> Loading audit history…
      </div>
    )
  }

  if (isError) {
    return (
      <div role="alert" className="ops-panel p-10 flex flex-col items-center text-center gap-3">
        <AlertOctagon className="w-6 h-6 text-threat-critical" />
        <p className="text-sm text-text-secondary">Could not load your audit history.</p>
        <button
          onClick={() => { void refetch() }}
          className="btn-ghost inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium text-text-secondary"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Retry
        </button>
      </div>
    )
  }

  const audits = data?.items ?? []

  if (audits.length === 0) {
    return (
      <div className="ops-panel p-12 flex flex-col items-center text-center gap-2">
        <History className="w-8 h-8 text-text-ghost" strokeWidth={1.25} />
        <p className="text-sm font-medium text-text-secondary">No audits yet</p>
        <p className="text-xs text-text-muted max-w-sm">
          Run your first compliance audit from the New audit tab — every run will appear here
          with its score and evidence.
        </p>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}
      className="ops-panel overflow-hidden"
    >
      <div className="px-5 py-3.5 border-b border-white/[0.07] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-indigo-300" />
          <span className="text-sm font-semibold text-text-primary">Audit history</span>
          <span className="font-mono text-[10px] text-text-muted">({data?.total ?? audits.length})</span>
        </div>
        <button
          onClick={() => { void refetch() }}
          className="inline-flex items-center gap-1.5 text-[11px] font-mono text-text-muted hover:text-text-secondary transition-colors"
        >
          <RefreshCw className={`w-3 h-3 ${isRefetching ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      <div className="divide-y divide-white/[0.05]">
        {audits.map((audit) => {
          const status = STATUS_STYLE[audit.status] ?? { color: '#93A4B5', label: audit.status }
          const isComplete = audit.status === 'complete'
          const isInFlight = audit.status === 'pending' || audit.status === 'processing' || audit.status === 'running'
          return (
            <div key={audit.audit_id} className="px-5 py-4 flex flex-col sm:flex-row sm:items-center gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <Building2 className="w-3.5 h-3.5 text-text-muted flex-shrink-0" />
                  <span className="text-sm font-semibold text-text-primary truncate">{audit.company_name}</span>
                  <span
                    className="text-[9px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded-full border"
                    style={{ color: status.color, backgroundColor: status.color + '1f', borderColor: status.color + '3a' }}
                  >
                    {status.label}
                  </span>
                </div>
                <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                  <span className="inline-flex items-center gap-1 font-mono text-[10px] text-text-muted">
                    <CalendarDays className="w-3 h-3" />{' '}
                    {formatDateTime(audit.created_at, timezone, {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                    })}
                  </span>
                  {audit.recurrence && audit.recurrence !== 'none' && (
                    <span className="inline-flex items-center gap-1 font-mono text-[10px] text-text-muted">
                      <Repeat className="w-3 h-3" /> {audit.recurrence}
                    </span>
                  )}
                  <span className="flex flex-wrap gap-1">
                    {audit.frameworks.map((fw) => (
                      <span key={fw} className="rounded-md border border-white/[0.08] bg-white/[0.02] px-1.5 py-0.5 text-[9px] font-mono uppercase text-text-muted">
                        {fw}
                      </span>
                    ))}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3 flex-shrink-0">
                {audit.score_percent != null && (
                  <span
                    className="font-mono text-sm font-semibold tabular-nums"
                    style={{ color: scoreColor(audit.score_percent) }}
                  >
                    {audit.score_percent.toFixed(0)}%
                  </span>
                )}
                {isComplete && (
                  <button
                    onClick={() => onShare(audit)}
                    className="btn-ghost inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-text-secondary hover:text-text-primary"
                  >
                    <Share2 className="w-3.5 h-3.5" /> Share
                  </button>
                )}
                {(isComplete || isInFlight) && (
                  <button
                    onClick={() => onOpen(audit)}
                    className="btn-sovereign inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold text-white"
                  >
                    {isComplete ? 'Open' : 'Resume'} <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                )}
                {audit.status === 'failed' && (
                  <button
                    type="button"
                    onClick={() => onRetry(audit)}
                    disabled={retryingAuditId !== null}
                    className="btn-sovereign min-h-11 inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
                  >
                    {retryingAuditId === audit.audit_id ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <RefreshCw className="w-3.5 h-3.5" />
                    )}
                    Retry
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
      {(data?.total ?? 0) > 0 && (
        <div className="px-5 py-2.5 border-t border-white/[0.07] flex items-center justify-between">
          <span className="font-mono text-[10px] text-text-muted">
            Page {page} of {Math.max(1, data?.totalPages ?? 1)}
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              className="min-h-11 px-3 text-xs text-text-secondary disabled:opacity-40"
            >
              Previous
            </button>
            <button
              type="button"
              disabled={page >= (data?.totalPages ?? 0)}
              onClick={() => setPage((current) => current + 1)}
              className="min-h-11 px-3 text-xs text-text-secondary disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </motion.div>
  )
}
