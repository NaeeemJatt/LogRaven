// LogRaven — Next-Gen SIEM Detections Feed & Incident Triage Console
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion'
import {
  Search,
  ChevronRight,
  Loader2,
  ShieldCheck,
  AlertCircle,
  Crosshair,
  Inbox,
  FileText,
  Layers,
  X,
} from 'lucide-react'
import { findingsApi } from '../api/investigations'
import type { FeedFinding } from '../api/investigations'
import { useAuthStore } from '../store/authStore'
import { useModalFocus } from '../hooks/useModalFocus'
import { formatDateTime } from '../utils/dateTime'
import SeverityHexBadge from '../components/detections/SeverityHexBadge'
import MitreMatrixToggle from '../components/detections/MitreMatrixToggle'
import DetectionsTable, { type DetectionTab } from '../components/detections/DetectionsTable'

// ── Severity model (aligned with Watchtower SIEM & backend engine) ─────────
const SEVERITIES = ['all', 'critical', 'high', 'medium', 'low', 'informational'] as const
type Sev = (typeof SEVERITIES)[number]

const SEV_TOKEN_CLASS: Record<string, string> = {
  critical:      'text-threat-critical bg-threat-critical/15 border-threat-critical/30',
  high:          'text-threat-high bg-threat-high/15 border-threat-high/30',
  medium:        'text-threat-medium bg-threat-medium/15 border-threat-medium/30',
  low:           'text-threat-low bg-threat-low/15 border-threat-low/30',
  informational: 'text-threat-info bg-threat-info/15 border-threat-info/30',
}

const SEV_LABEL: Record<string, string> = {
  all: 'All',
  critical: 'Critical',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
  informational: 'Info',
}

// ── Severity navigator rail ───────────────────
function SeverityRail({
  counts,
  active,
  onSelect,
  total,
}: {
  counts: Record<string, number>
  active: Sev
  onSelect: (s: Sev) => void
  total: number
}) {
  return (
    <div className="ops-panel flex flex-col h-full overflow-hidden select-none">
      <div className="px-4 py-3 border-b border-white/[0.07]">
        <span className="text-xs font-semibold text-text-muted">Triage by severity</span>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {SEVERITIES.map((sev) => {
          const isAll = sev === 'all'
          const count = isAll ? total : (counts[sev] ?? 0)
          const selected = active === sev
          return (
            <button
              key={sev}
              type="button"
              onClick={() => onSelect(sev)}
              aria-pressed={selected}
              className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-left transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer ${
                selected ? 'bg-white/[0.05]' : 'hover:bg-white/[0.025]'
              }`}
            >
              {isAll ? (
                <span className="w-2 h-2 rounded-full bg-amber-400 shrink-0" aria-hidden="true" />
              ) : (
                <SeverityHexBadge severity={sev} showLabel={false} />
              )}
              <span className={`flex-1 text-xs font-medium ${selected ? 'text-text-primary' : 'text-text-secondary'}`}>
                {SEV_LABEL[sev] ?? sev}
              </span>
              <span
                className="stat-value text-xs px-1.5 min-w-[22px] text-right tabular-nums text-text-muted"
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
        let bg = 'bg-threat-info'
        if (s === 'critical') bg = 'bg-threat-critical'
        else if (s === 'high') bg = 'bg-threat-high'
        else if (s === 'medium') bg = 'bg-threat-medium'
        else if (s === 'low') bg = 'bg-threat-low'

        return (
          <div
            key={s}
            style={{ width: `${(c / total) * 100}%` }}
            className={`h-full ${bg}`}
            title={`${c} ${s}`}
          />
        )
      })}
    </div>
  )
}

// ── Queue row (split view center pane) ───────────────────────────────
function QueueRow({
  f,
  selected,
  onClick,
}: {
  f: FeedFinding
  selected: boolean
  onClick: () => void
}) {
  const tokenClass = SEV_TOKEN_CLASS[f.severity] ?? 'text-threat-info bg-threat-info/15 border-threat-info/30'

  return (
    <button
      type="button"
      onClick={onClick}
      className={`relative w-full text-left pl-4 pr-3 py-3 border-b border-white/[0.04] transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer ${
        selected ? 'bg-white/[0.05]' : 'hover:bg-white/[0.025]'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs px-2 py-0.5 rounded font-medium border ${tokenClass}`}>
              {SEV_LABEL[f.severity] ?? f.severity}
            </span>
            {f.mitre_technique_id && (
              <span className="font-mono text-[9px] text-text-muted">{f.mitre_technique_id}</span>
            )}
          </div>
          <div className={`text-sm leading-snug truncate ${selected ? 'text-text-primary' : 'text-text-secondary'}`}>
            {f.title}
          </div>
          <div className="font-mono text-[10px] text-text-muted mt-1 truncate">{f.investigation.name}</div>
        </div>
        <ChevronRight className={`w-3.5 h-3.5 shrink-0 mt-1 transition-colors duration-150 ${selected ? 'text-text-secondary' : 'text-text-muted'}`} />
      </div>
    </button>
  )
}

// ── Inspector (slide-over / split preview pane) ─────────────────────────
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
        <Crosshair className="w-8 h-8 text-text-muted mb-3" strokeWidth={1.25} />
        <div className="text-sm text-text-secondary font-medium">No finding selected</div>
        <div className="text-xs text-text-muted mt-1 max-w-[220px]">
          Pick an item from the detections list to inspect its full detail and MITRE mapping.
        </div>
      </div>
    )
  }

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
    <div className="ops-panel relative h-full flex flex-col overflow-hidden bg-deep/95 backdrop-blur-xl border border-white/[0.08] rounded-xl select-none">
      <div className="px-5 pt-5 pb-4 border-b border-white/[0.07] relative">
        {onClose && (
          <button
            type="button"
            data-autofocus
            aria-label="Close finding inspector"
            onClick={onClose}
            className="absolute right-4 top-4 min-w-8 min-h-8 inline-flex items-center justify-center rounded-lg text-text-muted hover:text-text-primary hover:bg-white/[0.05] transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        )}
        <div className="flex items-center gap-2 mb-3">
          <SeverityHexBadge severity={f.severity} />
          <span className="text-xs text-text-muted font-medium">Finding inspector</span>
        </div>
        <h2 className="text-base font-semibold text-text-primary leading-snug pr-8">{f.title}</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        <div>
          <div className="text-xs font-semibold text-text-muted mb-2">Description</div>
          <p className="text-sm text-text-secondary leading-relaxed">
            {f.description || 'No additional details available for this finding.'}
          </p>
        </div>

        {f.remediation && (
          <div>
            <div className="text-xs font-semibold text-amber-300 mb-2">Remediation Guidance</div>
            <p className="text-xs text-text-secondary leading-relaxed p-3 rounded-lg bg-amber-400/[0.04] border border-amber-400/20">
              {f.remediation}
            </p>
          </div>
        )}

        <div className="grid grid-cols-2 gap-px bg-white/[0.06] rounded-lg overflow-hidden border border-white/[0.06]">
          {meta.map((m) => (
            <div key={m.label} className="bg-surface px-3 py-2.5">
              <div className="text-xs text-text-muted mb-1">{m.label}</div>
              <div className="font-mono text-[11px] text-text-secondary break-words">{m.value}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="p-4 border-t border-white/[0.07]">
        <Link
          to={`/investigations/${f.investigation.id}/report`}
          className="btn-sovereign w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer"
        >
          <FileText className="w-4 h-4" /> Open full report
        </Link>
        <div className="flex items-center justify-center gap-1.5 mt-2 font-mono text-[10px] text-text-muted truncate">
          <Layers className="w-3 h-3" /> {f.investigation.name}
        </div>
      </div>
    </div>
  )
}

// ── Main AlertFeed Page ──────────────────────────────────
export default function AlertFeed() {
  const user = useAuthStore((state) => state.user)
  const timezone = user?.timezone
  const [searchParams] = useSearchParams()

  // Primary filter state
  const queryParamSearch = searchParams.get('q') || ''
  const [search, setSearch] = useState(queryParamSearch)
  const [sevFilter, setSevFilter] = useState<Sev>('all')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)

  // Layout & SIEM controls
  const [viewMode, setViewMode] = useState<'table' | 'split'>('table')
  const [activeTab, setActiveTab] = useState<DetectionTab>('detections')
  const [mitreMatrixActive, setMitreMatrixActive] = useState(false)
  const [groupBy, setGroupBy] = useState('none')
  const [sortBy, setSortBy] = useState('time_desc')

  // Selection & Inspector state
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [inspectorFinding, setInspectorFinding] = useState<FeedFinding | null>(null)
  const [mobileOpen, setMobileOpen] = useState(false)

  const reduceMotion = useReducedMotion()
  const closeMobile = useCallback(() => setMobileOpen(false), [])
  const mobileDialogRef = useModalFocus<HTMLDivElement>(mobileOpen, closeMobile)

  // Sync external search query
  useEffect(() => {
    if (queryParamSearch !== search) {
      setSearch(queryParamSearch)
      setPage(1)
    }
  }, [queryParamSearch])

  // Data fetching
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
  const total = data?.total ?? 0
  const totalPages = data?.total_pages ?? 1
  const countTotal = Object.values(counts).reduce((sum, count) => sum + count, 0)
  const hasActiveFilter = sevFilter !== 'all' || search.trim().length > 0

  // Selection handlers
  const handleToggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleToggleSelectAll = () => {
    if (selectedIds.size === findings.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(findings.map((f) => f.id)))
    }
  }

  const handleSelectFinding = (finding: FeedFinding) => {
    setInspectorFinding(finding)
    setMobileOpen(true)
  }

  return (
    <div className="min-h-screen grid-bg pb-12">
      <div className="px-4 sm:px-6 lg:px-8 py-4 sm:py-5 w-full space-y-4">

        {/* SIEM Detections Toolbar & MITRE Matrix Strip */}
        <MitreMatrixToggle
          mitreMatrixActive={mitreMatrixActive}
          onToggleMitreMatrix={setMitreMatrixActive}
          groupBy={groupBy}
          onGroupByChange={setGroupBy}
          sortBy={sortBy}
          onSortByChange={setSortBy}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
        />

        {/* Status, Search & Distribution strip */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <p className="text-xs text-text-muted">
              {isError
                ? 'Findings unavailable'
                : `${countTotal} findings · ${counts.critical ?? 0} critical · ${counts.high ?? 0} high`}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="sm:w-64">
              <DistributionBar counts={counts} total={countTotal} />
              <div className="flex items-center justify-between mt-1 text-[11px] text-text-muted">
                <span>Severity distribution</span>
                <span className="tabular-nums">{findings.length} shown</span>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content Area */}
        {isLoading ? (
          <div className="ops-panel flex items-center justify-center py-32 gap-3">
            <Loader2 className="w-5 h-5 text-amber-400 motion-safe:animate-spin motion-reduce:animate-none" />
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
              className="btn-ghost min-h-11 px-4 rounded-lg text-sm text-text-secondary disabled:opacity-50 cursor-pointer"
            >
              {isRefetching ? 'Retrying…' : 'Retry'}
            </button>
          </div>
        ) : countTotal === 0 && !hasActiveFilter ? (
          <div className="ops-panel flex flex-col items-center justify-center py-28 gap-4">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <ShieldCheck className="w-6 h-6 text-emerald-400" strokeWidth={1.5} />
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
        ) : viewMode === 'table' ? (
          /* Next-Gen SIEM Full-Width Detections Grid */
          <DetectionsTable
            findings={findings}
            selectedIds={selectedIds}
            onToggleSelect={handleToggleSelect}
            onToggleSelectAll={handleToggleSelectAll}
            onSelectFinding={handleSelectFinding}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            currentPage={page}
            totalPages={totalPages}
            totalCount={total}
            onPageChange={setPage}
            pageSize={pageSize}
            onPageSizeChange={setPageSize}
            isLoading={isLoading}
          />
        ) : (
          /* Split View Mode (Severity Rail + Center Queue + Right Inspector) */
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
            className="grid grid-cols-1 lg:grid-cols-[190px_minmax(0,1fr)_340px] gap-4 h-[calc(100vh-12rem)] min-h-[560px]"
          >
            {/* Left — severity rail */}
            <SeverityRail
              counts={counts}
              active={sevFilter}
              onSelect={(severity) => {
                setSevFilter(severity)
                setPage(1)
              }}
              total={countTotal}
            />

            {/* Center — queue */}
            <div className="ops-panel flex flex-col overflow-hidden">
              <div className="flex items-center gap-2 px-3 py-2.5 border-b border-white/[0.07]">
                <Search className="w-3.5 h-3.5 text-text-muted shrink-0" />
                <input
                  type="text"
                  placeholder="Search title or MITRE ID…"
                  aria-label="Search findings"
                  maxLength={100}
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value)
                    setPage(1)
                  }}
                  className="bg-transparent text-xs text-text-secondary placeholder-text-muted outline-none w-full font-mono rounded-sm focus-visible:ring-2 focus-visible:ring-amber-400"
                />
                <span className="font-mono text-[10px] text-text-muted shrink-0 tabular-nums">{total}</span>
              </div>
              <div className="flex-1 overflow-y-auto">
                {findings.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full gap-2 text-center px-4">
                    <Inbox className="w-7 h-7 text-text-muted" strokeWidth={1.25} />
                    <span className="text-sm text-text-muted">No findings match this view.</span>
                  </div>
                ) : (
                  findings.map((f) => (
                    <QueueRow
                      key={f.id}
                      f={f}
                      selected={f.id === inspectorFinding?.id}
                      onClick={() => handleSelectFinding(f)}
                    />
                  ))
                )}
              </div>
            </div>

            {/* Right — inspector */}
            <div className="hidden lg:block h-full">
              <Inspector f={inspectorFinding || findings[0] || null} timezone={timezone} />
            </div>
          </motion.div>
        )}
      </div>

      {/* Slide-Over Inspector Dialog (Works on all screen sizes when a finding is inspected) */}
      <AnimatePresence>
        {mobileOpen && inspectorFinding && (
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label="Finding inspector"
            initial={false}
            animate={{ opacity: 1 }}
            exit={reduceMotion ? undefined : { opacity: 0 }}
            transition={reduceMotion ? { duration: 0 } : undefined}
            className="fixed inset-0 z-[70] bg-black/70 p-4 sm:p-6 flex items-center justify-center sm:justify-end"
            onClick={closeMobile}
          >
            <motion.div
              ref={mobileDialogRef}
              tabIndex={-1}
              initial={false}
              animate={{ x: 0, opacity: 1 }}
              exit={reduceMotion ? undefined : { x: 40, opacity: 0 }}
              className="relative w-full max-w-xl h-[min(90vh,46rem)] overflow-hidden"
              onClick={(event) => event.stopPropagation()}
            >
              <Inspector
                f={inspectorFinding}
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
