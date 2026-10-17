import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion'
import {
  Search, ChevronRight, Loader2, ShieldCheck, AlertCircle,
  Crosshair, Inbox, FileText, Layers, X,
} from 'lucide-react'
import { findingsApi } from '../api/investigations'
import type { FeedFinding } from '../api/investigations'
import { useAuthStore } from '../store/authStore'
import { useModalFocus } from '../hooks/useModalFocus'
import { formatDateTime } from '../utils/dateTime'

// ── Severity model (soft, muted but distinct) ─────────────
// Backend emits 'informational' (see app/ai/cloud/engine.py, report builder);
// keep the value aligned and only shorten the visible label to "Info".
const SEVERITIES = ['all', 'critical', 'high', 'medium', 'low', 'informational'] as const
type Sev = (typeof SEVERITIES)[number]

const SEV_COLOR: Record<string, string> = {
  critical:      '#DB8585',
  high:          '#E0A86F',
  medium:        '#D9C27E',
  low:           '#8FBDAD',
  informational: '#93A4B5',
}
const SEV_LABEL: Record<string, string> = {
  all: 'All', critical: 'Critical', high: 'High', medium: 'Medium', low: 'Low', informational: 'Info',
}

// ── Severity navigator rail (left pane) ───────────────────
function SeverityRail({
  counts, active, onSelect, total,
}: {
  counts: Record<string, number>; active: Sev; onSelect: (s: Sev) => void; total: number
}) {
  return (
    <div className="ops-panel flex flex-col h-full overflow-hidden">
      <div className="px-4 py-3 border-b border-white/[0.07]">
        <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-text-muted">Triage by severity</span>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {SEVERITIES.map((sev) => {
          const isAll = sev === 'all'
          const count = isAll ? total : (counts[sev] ?? 0)
          const color = isAll ? '#E3B57E' : SEV_COLOR[sev]
          const selected = active === sev
          return (
            <button
              key={sev}
              onClick={() => onSelect(sev)}
              aria-pressed={selected}
              className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-left transition-colors ${
                selected ? 'bg-white/[0.05]' : 'hover:bg-white/[0.025]'
              }`}
            >
              <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
              <span className={`flex-1 text-xs font-medium ${selected ? 'text-text-primary' : 'text-text-secondary'}`}>
                {SEV_LABEL[sev] ?? sev}
              </span>
              <span
                className="stat-value text-xs px-1.5 min-w-[22px] text-right"
                style={{ color: count > 0 ? color : '#4A4E58' }}
              >
                {count}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ── Distribution bar ──────────────────────────────────────
function DistributionBar({ counts, total }: { counts: Record<string, number>; total: number }) {
  if (total === 0) return <div className="h-1.5 rounded-full bg-white/[0.05]" />
  return (
    <div className="flex h-1.5 rounded-full overflow-hidden bg-white/[0.05]">
      {(['critical', 'high', 'medium', 'low', 'informational'] as const).map((s) => {
        const c = counts[s] ?? 0
        if (!c) return null
        return (
          <div key={s} style={{ width: `${(c / total) * 100}%`, background: SEV_COLOR[s] }} title={`${c} ${s}`} />
        )
      })}
    </div>
  )
}

// ── Queue row (center pane) ───────────────────────────────
function QueueRow({
  f, selected, onClick,
}: {
  f: FeedFinding; selected: boolean; onClick: () => void
}) {
  const color = SEV_COLOR[f.severity] ?? '#93A4B5'
  return (
    <button
      onClick={onClick}
      className={`relative w-full text-left pl-4 pr-3 py-3 border-b border-white/[0.04] transition-colors ${
        selected ? 'bg-white/[0.05]' : 'hover:bg-white/[0.025]'
      }`}
    >
      <span className="absolute left-0 top-0 bottom-0 w-[3px]" style={{ background: color, opacity: selected ? 1 : 0.55 }} />
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span
              className="font-mono text-[9px] px-1.5 py-0.5 rounded uppercase tracking-wide"
              style={{ color, background: `${color}1f` }}
            >
              {SEV_LABEL[f.severity] ?? f.severity}
            </span>
            {f.mitre_technique_id && (
              <span className="font-mono text-[9px] text-text-muted">{f.mitre_technique_id}</span>
            )}
          </div>
          <div className={`text-sm leading-snug truncate ${selected ? 'text-text-primary' : 'text-text-secondary'}`}>
            {f.title}
          </div>
          <div className="font-mono text-[10px] text-text-ghost mt-1 truncate">{f.investigation.name}</div>
        </div>
        <ChevronRight className={`w-3.5 h-3.5 flex-shrink-0 mt-1 transition-colors ${selected ? 'text-text-secondary' : 'text-text-ghost'}`} />
      </div>
    </button>
  )
}

// ── Inspector (right pane) ────────────────────────────────
function Inspector({
  f,
  timezone,
  onClose,
}: {
  f: FeedFinding | null
  timezone?: string | null
  onClose?: () => void
}) {
  if (!f) {
    return (
      <div className="ops-panel h-full flex flex-col items-center justify-center text-center px-6">
        <Crosshair className="w-8 h-8 text-text-ghost mb-3" strokeWidth={1.25} />
        <div className="text-sm text-text-secondary font-medium">No finding selected</div>
        <div className="text-xs text-text-muted mt-1 max-w-[220px]">
          Pick an item from the queue to inspect its full detail and MITRE mapping.
        </div>
      </div>
    )
  }
  const color = SEV_COLOR[f.severity] ?? '#93A4B5'
  const meta = [
    { label: 'MITRE technique', value: f.mitre_technique_id || '—' },
    { label: 'Finding type', value: f.finding_type || 'single' },
    { label: 'Source file', value: f.source_files?.join(', ') || '—' },
    {
      label: 'Timestamp',
      value: formatDateTime(f.created_at, timezone, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      }),
    },
  ]
  return (
    <div className="ops-panel relative h-full flex flex-col overflow-hidden">
      <div className="px-5 pt-5 pb-4 border-b border-white/[0.07]">
        {onClose && (
          <button
            type="button"
            data-autofocus
            aria-label="Close finding inspector"
            onClick={onClose}
            className="absolute right-4 top-4 min-w-11 min-h-11 inline-flex items-center justify-center text-text-muted"
          >
            <X className="w-4 h-4" />
          </button>
        )}
        <div className="flex items-center gap-2 mb-3">
          <span className="font-mono text-[10px] px-2 py-0.5 rounded uppercase tracking-wide" style={{ color, background: `${color}1f` }}>
            {SEV_LABEL[f.severity] ?? f.severity}
          </span>
          <span className="font-mono text-[10px] text-text-muted">Finding inspector</span>
        </div>
        <h2 className="text-base font-semibold text-text-primary leading-snug">{f.title}</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        <div>
          <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted mb-2">Description</div>
          <p className="text-sm text-text-secondary leading-relaxed">
            {f.description || 'No additional details available for this finding.'}
          </p>
        </div>

        <div className="grid grid-cols-2 gap-px bg-white/[0.06] rounded-lg overflow-hidden">
          {meta.map((m) => (
            <div key={m.label} className="bg-surface px-3 py-2.5">
              <div className="font-mono text-[9px] uppercase tracking-wider text-text-muted mb-1">{m.label}</div>
              <div className="font-mono text-[11px] text-text-secondary break-words">{m.value}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="p-4 border-t border-white/[0.07]">
        <Link
          to={`/investigations/${f.investigation.id}/report`}
          className="btn-sovereign w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold"
        >
          <FileText className="w-4 h-4" /> Open full report
        </Link>
        <div className="flex items-center justify-center gap-1.5 mt-2 font-mono text-[10px] text-text-ghost truncate">
          <Layers className="w-3 h-3" /> {f.investigation.name}
        </div>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────
export default function AlertFeed() {
  const user = useAuthStore((state) => state.user)
  const timezone = user?.timezone
  const [sevFilter, setSevFilter] = useState<Sev>('all')
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [mobileOpen, setMobileOpen] = useState(false)
  const reduceMotion = useReducedMotion()
  const closeMobile = useCallback(() => setMobileOpen(false), [])
  const mobileDialogRef = useModalFocus<HTMLDivElement>(mobileOpen, closeMobile)

  const { data, isLoading, isError, refetch, isRefetching } = useQuery({
    queryKey: ['findings', user?.id, page, sevFilter, search],
    queryFn: () =>
      findingsApi.list({
        page,
        limit: 20,
        severity: sevFilter === 'all' ? undefined : sevFilter,
        search: search.trim() || undefined,
      }),
    placeholderData: (previous) => previous,
  })

  const findings = useMemo(() => data?.items ?? [], [data])
  const counts = data?.severity_counts ?? {}
  const findingKey = (f: FeedFinding) => `${f.investigation.id}-${f.id}`

  // keep a valid selection as the filter changes
  useEffect(() => {
    if (findings.length === 0) { setSelectedId(null); return }
    if (!selectedId || !findings.some((f) => findingKey(f) === selectedId)) {
      setSelectedId(findingKey(findings[0]))
    }
  }, [findings, selectedId])

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const desktop = window.matchMedia('(min-width: 1024px)')
    const closeOnDesktop = (event: MediaQueryListEvent) => {
      if (event.matches) closeMobile()
    }
    desktop.addEventListener('change', closeOnDesktop)
    if (desktop.matches) closeMobile()
    return () => desktop.removeEventListener('change', closeOnDesktop)
  }, [closeMobile])

  const selected = findings.find((f) => findingKey(f) === selectedId) ?? null
  const total = data?.total ?? 0
  const countTotal = Object.values(counts).reduce((sum, count) => sum + count, 0)
  const hasActiveFilter = sevFilter !== 'all' || search.trim().length > 0

  return (
    <div className="pt-16 min-h-screen grid-bg">
      <div className="px-4 sm:px-6 lg:px-8 py-6 max-w-[1500px] mx-auto">

        {/* Command bar */}
        <motion.div
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
          className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-5"
        >
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-white/[0.04] border border-white/[0.08] flex items-center justify-center">
              <Crosshair className="w-4 h-4 text-indigo-300" />
            </div>
            <div>
              <h1 className="font-display font-bold text-text-primary text-2xl leading-none">Triage console</h1>
              <p className="font-mono text-[10px] text-text-muted tracking-wide mt-1.5 uppercase">
                {isError
                  ? 'Findings unavailable'
                  : `${countTotal} findings · ${counts.critical ?? 0} critical · ${counts.high ?? 0} high`}
              </p>
            </div>
          </div>
          <div className="lg:w-72">
            <DistributionBar counts={counts} total={countTotal} />
            <div className="flex items-center justify-between mt-1.5 font-mono text-[9px] text-text-ghost uppercase tracking-wider">
              <span>Severity distribution</span>
              <span>{findings.length} shown</span>
            </div>
          </div>
        </motion.div>

        {isLoading ? (
          <div className="ops-panel flex items-center justify-center py-32 gap-3">
            <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
            <span className="text-sm text-text-muted">Aggregating findings…</span>
          </div>
        ) : isError ? (
          <div role="alert" className="ops-panel flex flex-col items-center justify-center py-24 gap-4 text-center">
            <AlertCircle className="w-7 h-7 text-rose-400" />
            <p className="text-sm text-text-secondary">Findings could not be loaded. No security conclusion was made.</p>
            <button
              type="button"
              onClick={() => void refetch()}
              disabled={isRefetching}
              className="btn-ghost min-h-11 px-4 rounded-lg text-sm text-text-secondary disabled:opacity-50"
            >
              {isRefetching ? 'Retrying…' : 'Retry'}
            </button>
          </div>
        ) : countTotal === 0 && !hasActiveFilter ? (
          <div className="ops-panel flex flex-col items-center justify-center py-28 gap-4">
            <div className="w-12 h-12 rounded-xl bg-[#8FBDAD]/10 border border-[#8FBDAD]/20 flex items-center justify-center">
              <ShieldCheck className="w-6 h-6 text-[#8FBDAD]" strokeWidth={1.5} />
            </div>
            <div className="text-center">
              <h3 className="font-display text-lg font-semibold text-text-primary mb-1">Queue is clear</h3>
              <p className="text-text-muted text-sm max-w-sm">
                No findings across completed investigations yet. Run an investigation to populate the triage queue.
              </p>
            </div>
            <Link to="/investigations/new" className="btn-sovereign flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold">
              <FileText className="w-4 h-4" /> New investigation
            </Link>
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.1 }}
            className="grid grid-cols-1 lg:grid-cols-[190px_minmax(0,1fr)_330px] gap-4 h-[calc(100vh-13rem)] min-h-[520px]"
          >
            {/* Left — severity rail */}
            <SeverityRail
              counts={counts}
              active={sevFilter}
              onSelect={(severity) => {
                setSevFilter(severity)
                setPage(1)
                setMobileOpen(false)
              }}
              total={countTotal}
            />

            {/* Center — queue */}
            <div className="ops-panel flex flex-col overflow-hidden">
              <div className="flex items-center gap-2 px-3 py-2.5 border-b border-white/[0.07]">
                <Search className="w-3.5 h-3.5 text-text-muted flex-shrink-0" />
                <input
                  type="text"
                  placeholder="Search title or MITRE ID…"
                  aria-label="Search findings"
                  maxLength={100}
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value)
                    setPage(1)
                    setMobileOpen(false)
                  }}
                  className="bg-transparent text-xs text-text-secondary placeholder-text-muted outline-none w-full font-mono rounded-sm focus-visible:ring-2 focus-visible:ring-indigo-500/60"
                />
                <span className="font-mono text-[10px] text-text-ghost flex-shrink-0">{total}</span>
              </div>
              <div className="flex-1 overflow-y-auto">
                {findings.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full gap-2 text-center px-4">
                    <Inbox className="w-7 h-7 text-text-ghost" strokeWidth={1.25} />
                    <span className="text-sm text-text-muted">No findings match this view.</span>
                  </div>
                ) : (
                  findings.map((f) => (
                    <QueueRow
                      key={findingKey(f)}
                      f={f}
                      selected={findingKey(f) === selectedId}
                      onClick={() => {
                        setSelectedId(findingKey(f))
                        const isDesktop =
                          typeof window.matchMedia === 'function' &&
                          window.matchMedia('(min-width: 1024px)').matches
                        if (!isDesktop) setMobileOpen(true)
                      }}
                    />
                  ))
                )}
              </div>
              {total > 0 && (
                <div className="border-t border-white/[0.07] px-3 py-2 flex items-center justify-between">
                  <span className="font-mono text-[10px] text-text-muted">
                    Page {page} of {data?.total_pages ?? 1}
                  </span>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      aria-label="Previous findings page"
                      disabled={page <= 1}
                      onClick={() => setPage((current) => Math.max(1, current - 1))}
                      className="min-h-11 px-3 text-xs text-text-secondary disabled:opacity-40"
                    >
                      Previous
                    </button>
                    <button
                      type="button"
                      aria-label="Next findings page"
                      disabled={page >= (data?.total_pages ?? 0)}
                      onClick={() => setPage((current) => current + 1)}
                      className="min-h-11 px-3 text-xs text-text-secondary disabled:opacity-40"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Right — inspector */}
            <AnimatePresence mode="wait">
              <motion.div
                key={selectedId ?? 'empty'}
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
                className="hidden lg:block h-full"
              >
                <Inspector f={selected} timezone={timezone} />
              </motion.div>
            </AnimatePresence>
          </motion.div>
        )}
      </div>
      <AnimatePresence>
        {mobileOpen && selected && (
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label="Finding inspector"
            initial={reduceMotion ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={reduceMotion ? undefined : { opacity: 0 }}
            transition={reduceMotion ? { duration: 0 } : undefined}
            className="fixed inset-0 z-[70] lg:hidden bg-black/70 p-3 flex items-end"
            onClick={closeMobile}
          >
            <motion.div
              ref={mobileDialogRef}
              tabIndex={-1}
              initial={reduceMotion ? false : { y: 40 }}
              animate={{ y: 0 }}
              exit={reduceMotion ? undefined : { y: 40 }}
              className="relative w-full h-[min(88vh,42rem)] overflow-hidden"
              onClick={(event) => event.stopPropagation()}
            >
              <Inspector
                f={selected}
                timezone={timezone}
                onClose={closeMobile}
              />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
