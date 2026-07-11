import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Plus, Search, AlertTriangle, CheckCircle2,
  Clock, XCircle, FileText, Trash2,
  Activity, ChevronRight, Loader2,
  ArrowUpDown, Radio, ShieldAlert,
} from 'lucide-react'
import { investigationsApi } from '../api/investigations'
import { normalizeApiError } from '../api/errors'
import ConfirmModal from '../components/ui/ConfirmModal'
import { useAuthStore } from '../store/authStore'
import type { Investigation } from '../types/investigation'
import { dateKey, formatDateTime, recentCalendarDays } from '../utils/dateTime'

// ── Activity histogram (7-day) ─────────────────────────────
function ActivityHistogram({
  dates,
  dailyCounts,
  timezone,
}: {
  dates: string[]
  dailyCounts?: Record<string, number>
  timezone?: string | null
}) {
  const counts = recentCalendarDays(7, timezone).map((day) => {
    return {
      label: day.label,
      count:
        dailyCounts?.[day.key] ??
        dates.filter((createdAt) => dateKey(createdAt, timezone) === day.key).length,
    }
  })

  const max = Math.max(...counts.map((c) => c.count), 1)

  return (
    <div className="ops-panel p-5 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-text-muted" />
          <span className="font-mono text-[10px] text-text-secondary tracking-[0.14em] uppercase">7-day intake</span>
        </div>
      </div>

      <div className="relative flex-1 flex items-end gap-2 min-h-[72px]">
        {/* baseline grid */}
        <div className="pointer-events-none absolute inset-0 flex flex-col justify-between opacity-40">
          {[0, 1, 2].map((i) => <div key={i} className="h-px w-full bg-white/[0.05]" />)}
        </div>
        {counts.map((c, i) => (
          <div key={i} className="relative flex-1 flex flex-col items-center justify-end h-full">
            <motion.div
              initial={{ scaleY: 0 }}
              animate={{ scaleY: 1 }}
              transition={{ delay: i * 0.05, duration: 0.5, ease: 'easeOut' }}
              style={{
                height: `${Math.max((c.count / max) * 100, 6)}%`,
                background: c.count > 0 ? 'rgba(227,181,126,0.55)' : 'rgba(255,255,255,0.05)',
                transformOrigin: 'bottom',
              }}
              className="w-full max-w-[22px] rounded-[2px]"
            />
          </div>
        ))}
      </div>
      <div className="flex items-center gap-2 mt-2">
        {counts.map((c, i) => (
          <div key={i} className="flex-1 text-center">
            <span className="font-mono text-[9px] text-text-muted">{c.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Threat posture panel ───────────────────────────────────
function ThreatPosture({ counts }: { counts: Record<string, number> }) {
  const agg = {
    critical: counts.critical ?? 0,
    high: counts.high ?? 0,
    findings: Object.values(counts).reduce((sum, count) => sum + count, 0),
  }

  const rows = [
    { label: 'Critical', value: agg.critical, color: '#D98C8C' },
    { label: 'High', value: agg.high, color: '#D9A878' },
    { label: 'Findings', value: agg.findings, color: '#E3B57E' },
  ]
  const clear = agg.critical === 0 && agg.high === 0

  return (
    <div className="ops-panel p-5 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-3.5 h-3.5 text-text-muted" />
          <span className="font-mono text-[10px] text-text-secondary tracking-[0.14em] uppercase">Threat posture</span>
        </div>
        <span className={`font-mono text-[9px] tracking-wide ${clear ? 'text-[#8FBDAD]' : 'text-[#D9A878]'}`}>
          {clear ? 'Nominal' : 'Elevated'}
        </span>
      </div>

      <div className="flex-1 flex flex-col justify-center gap-3">
        {rows.map((r) => {
          const pct = agg.findings > 0 ? Math.min((r.value / agg.findings) * 100, 100) : 0
          return (
            <div key={r.label}>
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-[10px] uppercase tracking-wider text-text-muted">{r.label}</span>
                <span className="stat-value text-sm" style={{ color: r.color }}>{r.value}</span>
              </div>
              <div className="h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${r.label === 'Findings' ? (agg.findings > 0 ? 100 : 0) : pct}%` }}
                  transition={{ duration: 1, ease: 'easeOut' }}
                  className="h-full rounded-full"
                  style={{ background: r.color, opacity: 0.8 }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Status cell ───────────────────────────────────────────
const STATUS_CFG: Record<Investigation['status'], { icon: React.ElementType; badge: string; text: string; label: string }> = {
  complete:   { icon: CheckCircle2, badge: 'bg-teal-500/10 border-teal-500/20',   text: 'text-teal-400',   label: 'Complete'   },
  processing: { icon: Activity,     badge: 'bg-indigo-500/10 border-indigo-500/20', text: 'text-indigo-400', label: 'Processing' },
  failed:     { icon: XCircle,      badge: 'bg-rose-500/10 border-rose-500/20',   text: 'text-rose-400',   label: 'Failed'     },
  queued:     { icon: Clock,        badge: 'bg-amber-500/10 border-amber-500/20', text: 'text-amber-400',  label: 'Queued'     },
  draft:      { icon: FileText,     badge: 'bg-white/[0.04] border-white/[0.06]', text: 'text-text-muted', label: 'Draft'      },
}

function StatusBadge({ status }: { status: Investigation['status'] }) {
  const cfg = STATUS_CFG[status]
  const Icon = cfg.icon
  return (
    <span className={`inline-flex items-center gap-1 font-mono text-[10px] px-2 py-0.5 rounded border tracking-wide ${cfg.badge} ${cfg.text}`}>
      <Icon className="w-2.5 h-2.5" />
      {cfg.label}
    </span>
  )
}

// ── Severity pills ────────────────────────────────────────
function SeverityPills({ inv }: { inv: Investigation }) {
  const summary = inv.severity_summary
  if (!summary && !inv.findings_count) {
    if (inv.status !== 'complete') return <span className="text-text-ghost font-mono text-[10px]">—</span>
  }

  const critical = summary?.critical ?? 0
  const high = summary?.high ?? 0
  const total = inv.findings_count ?? 0

  if (!critical && !high && !total) return <span className="text-text-ghost font-mono text-[10px]">—</span>

  return (
    <div className="flex items-center gap-1">
      {critical > 0 && (
        <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400">
          {critical}C
        </span>
      )}
      {high > 0 && (
        <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-orange-500/10 border border-orange-500/20 text-orange-400">
          {high}H
        </span>
      )}
      {!critical && !high && total > 0 && (
        <span className="font-mono text-[10px] text-text-muted">{total} findings</span>
      )}
    </div>
  )
}

// ── Table row ─────────────────────────────────────────────
function InvTableRow({
  inv, index, onDelete, timezone,
}: {
  inv: Investigation
  index: number
  onDelete: (inv: Investigation) => void
  timezone?: string | null
}) {
  const navigate = useNavigate()
  const fileCount = (inv as any).file_count ?? inv.files?.length ?? 0
  const canView = inv.status === 'complete'
  const isProcessing = inv.status === 'processing' || inv.status === 'queued'
  const titleNav = isProcessing || inv.status === 'failed'
    ? `/investigations/${inv.id}/status`
    : `/investigations/${inv.id}`

  return (
    <motion.tr
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3, delay: index * 0.04 }}
      className="group border-b border-white/[0.04] last:border-b-0 hover:bg-elevated/30 transition-colors"
    >
      {/* Name */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate(titleNav)}
            className="text-sm font-medium text-text-primary hover:text-indigo-300 transition-colors text-left truncate max-w-[260px]"
          >
            {inv.name}
          </button>
          {inv.status === 'processing' && (
            <motion.span
              animate={{ opacity: [1, 0.4, 1] }}
              transition={{ repeat: Infinity, duration: 1.5 }}
              className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-indigo-400"
            />
          )}
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="font-mono text-[10px] text-text-ghost">{inv.id.slice(0, 8)}</span>
        </div>
      </td>

      {/* Status */}
      <td className="px-4 py-3 whitespace-nowrap">
        <StatusBadge status={inv.status} />
      </td>

      {/* Severity */}
      <td className="px-4 py-3 whitespace-nowrap">
        <SeverityPills inv={inv} />
      </td>

      {/* Files */}
      <td className="px-4 py-3 whitespace-nowrap">
        <span className="font-mono text-xs text-text-muted">{fileCount}</span>
      </td>

      {/* Date */}
      <td className="px-4 py-3 whitespace-nowrap">
        <span className="font-mono text-[11px] text-text-muted">
          {formatDateTime(inv.created_at, timezone, { month: 'short', day: 'numeric', year: '2-digit' })}
        </span>
      </td>

      {/* Actions */}
      <td className="px-4 py-3 whitespace-nowrap">
        <div className="flex items-center gap-1">
          {canView && (
            <Link
              to={`/investigations/${inv.id}/report`}
              className="min-w-11 min-h-11 inline-flex items-center justify-center rounded-lg hover:bg-indigo-500/10 text-text-muted hover:text-indigo-400 transition-all"
              aria-label={`View report for ${inv.name}`}
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          )}
          {isProcessing && (
            <Link
              to={`/investigations/${inv.id}/status`}
              className="min-w-11 min-h-11 inline-flex items-center justify-center rounded-lg hover:bg-indigo-500/10 text-text-muted hover:text-indigo-400 transition-all"
              aria-label={`View status for ${inv.name}`}
            >
              {inv.status === 'processing'
                ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                : <Activity className="w-3.5 h-3.5" />}
            </Link>
          )}
          <button
            onClick={() => onDelete(inv)}
            className="min-w-11 min-h-11 inline-flex items-center justify-center rounded-lg hover:bg-rose-500/10 text-text-muted hover:text-rose-400 transition-all"
            aria-label={`Delete ${inv.name}`}
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </td>
    </motion.tr>
  )
}

// ── Empty state ───────────────────────────────────────────
function EmptyState() {
  return (
    <tr>
      <td colSpan={6}>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-col items-center justify-center py-20 px-4"
        >
          <AlertTriangle className="w-10 h-10 text-text-muted mb-4" strokeWidth={1.25} />
          <h3 className="font-display text-lg font-semibold text-text-primary mb-2">No investigations yet</h3>
          <p className="text-text-muted text-center mb-6 max-w-sm text-sm">
            Upload logs from Windows, web servers, or cloud — correlate across sources and export a PDF report.
          </p>
          <Link
            to="/investigations/new"
            className="btn-sovereign flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold"
          >
            <Plus className="w-4 h-4" /> New investigation
          </Link>
        </motion.div>
      </td>
    </tr>
  )
}

// ── Main Dashboard ────────────────────────────────────────
type SortField = 'name' | 'status' | 'created_at'
type SortDir = 'asc' | 'desc'

export default function Dashboard() {
  const queryClient = useQueryClient()
  const user = useAuthStore((state) => state.user)
  const timezone = user?.timezone
  const [deleteTarget, setDeleteTarget] = useState<Investigation | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [sortField, setSortField] = useState<SortField>('created_at')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [page, setPage] = useState(1)

  const { data, isLoading, isError, refetch, isRefetching } = useQuery({
    queryKey: ['investigations', user?.id, page, search, sortField, sortDir],
    queryFn: () =>
      investigationsApi.list({
        page,
        limit: 20,
        search: search.trim() || undefined,
        sort: sortField,
        direction: sortDir,
      }),
  })
  const {
    data: stats,
    isLoading: statsLoading,
    isError: statsError,
    refetch: refetchStats,
    isRefetching: statsRefetching,
  } = useQuery({
    queryKey: ['dashboard-stats', user?.id],
    queryFn: investigationsApi.getDashboardStats,
  })

  const list = data?.items ?? []
  const filteredTotal = data?.total ?? 0
  const total = stats?.total_investigations ?? filteredTotal
  const activeCount = stats?.active_investigations ?? 0
  const completeCount = stats?.status_counts.complete ?? 0
  const failedCount = stats?.status_counts.failed ?? 0

  useEffect(() => {
    if (!data) return
    const lastPage = Math.max(1, data.totalPages)
    if (page > lastPage) setPage(lastPage)
  }, [data, page])

  const completionPct = total > 0 ? Math.round((completeCount / total) * 100) : 0
  const statusLegend = [
    { label: 'Active', value: activeCount, color: '#D9A878' },
    { label: 'Complete', value: completeCount, color: '#8FBDAD' },
    { label: 'Failed', value: failedCount, color: '#D98C8C' },
  ]

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    setActionError(null)
    try {
      await investigationsApi.delete(deleteTarget.id)
      queryClient.invalidateQueries({ queryKey: ['investigations'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] })
    } catch (error) {
      setActionError(normalizeApiError(error, 'Could not delete the investigation.').message)
    } finally {
      setDeleting(false)
      setDeleteTarget(null)
    }
  }

  const toggleSort = (field: SortField) => {
    if (sortField === field) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortField(field); setSortDir('desc') }
    setPage(1)
  }

  const SortIcon = ({ field }: { field: SortField }) => (
    <ArrowUpDown className={`w-3 h-3 ml-1 inline transition-colors ${sortField === field ? 'text-indigo-400' : 'text-text-ghost'}`} />
  )

  return (
    <div className="pt-16 min-h-screen grid-bg relative">
      {/* soft top ambient wash */}
      <div
        className="pointer-events-none absolute inset-x-0 top-16 h-64"
        style={{ background: 'radial-gradient(ellipse 60% 100% at 30% 0%, rgba(227,181,126,0.05), transparent 70%)' }}
      />

      <div className="relative px-4 sm:px-6 lg:px-8 py-8 max-w-[1400px] mx-auto">

        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
          className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-7"
        >
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full rounded-full bg-[#8FBDAD] opacity-60 animate-ping" />
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-[#8FBDAD]" />
              </span>
              <span className="font-mono text-[10px] text-text-muted tracking-[0.18em] uppercase">
                Operations console
              </span>
            </div>
            <h1 className="font-display font-bold text-text-primary text-3xl sm:text-[2.1rem] leading-none tracking-tight">
              Investigations
            </h1>
          </div>
          <Link
            to="/investigations/new"
            className="btn-sovereign inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold self-start sm:self-auto"
          >
            <Plus className="w-4 h-4" /> New investigation
          </Link>
        </motion.div>

        {isError && (
          <div role="alert" className="mb-6 px-4 py-3 rounded-lg border border-rose-500/30 bg-rose-500/[0.07] text-rose-400 text-xs font-mono flex items-center justify-between gap-3">
            <span>Failed to load investigations. No empty-state conclusion was made.</span>
            <button
              type="button"
              onClick={() => void refetch()}
              disabled={isRefetching}
              className="min-h-11 px-3 rounded border border-rose-400/30 disabled:opacity-50"
            >
              {isRefetching ? 'Retrying…' : 'Retry'}
            </button>
          </div>
        )}
        {actionError && (
          <div role="alert" className="mb-6 px-4 py-3 rounded-lg border border-rose-500/30 bg-rose-500/[0.07] text-rose-400 text-xs font-mono">
            {actionError}
          </div>
        )}

        {/* Bento operations grid */}
        {statsLoading ? (
          <div className="ops-panel mb-4 flex items-center justify-center py-20">
            <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
          </div>
        ) : statsError ? (
          <div role="alert" className="ops-panel mb-4 flex flex-col items-center justify-center gap-3 py-16 text-center">
            <ShieldAlert className="w-7 h-7 text-rose-400" />
            <p className="text-sm text-text-secondary">
              Dashboard totals and threat posture are unavailable. No nominal-state conclusion was made.
            </p>
            <button
              type="button"
              onClick={() => void refetchStats()}
              disabled={statsRefetching}
              className="btn-ghost min-h-11 px-4 rounded-lg text-sm text-text-secondary disabled:opacity-50"
            >
              {statsRefetching ? 'Retrying…' : 'Retry summary'}
            </button>
          </div>
        ) : (
        <motion.div
          initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4"
        >
          {/* Hero metric tile */}
          <div className="ops-panel p-6 md:row-span-2 flex flex-col">
            <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-text-muted">Under watch</span>
            <div className="mt-3 flex items-end gap-2">
              <span className="stat-value text-[4.5rem] leading-[0.85] font-semibold" style={{ color: '#E3B57E' }}>{total}</span>
            </div>
            <span className="text-sm text-text-secondary mt-2">investigations</span>

            <div className="h-px bg-white/[0.07] my-5" />

            <ul className="space-y-2.5">
              {statusLegend.map((s) => (
                <li key={s.label} className="flex items-center gap-2.5">
                  <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: s.color }} />
                  <span className="text-xs text-text-secondary flex-1">{s.label}</span>
                  <span className="stat-value text-sm" style={{ color: s.color }}>{s.value}</span>
                </li>
              ))}
            </ul>

            <div className="mt-auto pt-6">
              <div className="flex items-center justify-between mb-1.5">
                <span className="font-mono text-[10px] uppercase tracking-wider text-text-muted">Completion</span>
                <span className="stat-value text-xs" style={{ color: '#8FBDAD' }}>{completionPct}%</span>
              </div>
              <div className="h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                <motion.div
                  initial={{ width: 0 }} animate={{ width: `${completionPct}%` }}
                  transition={{ duration: 1, ease: 'easeOut', delay: 0.3 }}
                  className="h-full rounded-full" style={{ background: '#8FBDAD', opacity: 0.8 }}
                />
              </div>
            </div>
          </div>

          {/* Intake trend */}
          <div className="md:col-span-2">
            <ActivityHistogram
              dates={stats?.recent_investigation_dates ?? []}
              dailyCounts={stats?.recent_daily_counts}
              timezone={timezone}
            />
          </div>

          {/* Threat posture */}
          <div className="md:col-span-2">
            <ThreatPosture counts={stats?.severity_counts ?? {}} />
          </div>
        </motion.div>
        )}

        {/* Live feed table */}
        <motion.div
          initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.24 }}
          className="ops-panel overflow-hidden"
        >
          {/* Toolbar */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.08] bg-white/[0.015]">
            <div className="flex items-center gap-2.5">
              <Radio className="w-3.5 h-3.5 text-indigo-400" />
              <h2 className="font-mono text-[11px] font-medium text-text-secondary tracking-[0.16em] uppercase">
                Live feed
              </h2>
              <span className="font-mono text-[10px] text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded">
                {list.length}/{filteredTotal}
              </span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-md border border-white/[0.1] bg-void/60 focus-within:border-indigo-500/50 transition-colors">
              <Search className="w-3 h-3 text-text-muted" />
              <input
                type="text"
                placeholder="Filter..."
                aria-label="Search investigations"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value)
                  setPage(1)
                }}
                className="bg-transparent text-xs text-text-secondary placeholder-text-muted outline-none w-28 font-mono"
              />
            </div>
          </div>

          {isLoading && (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
            </div>
          )}

          {!isLoading && !isError && (
            <div className="overflow-x-auto">
              <table className="sovereign-table w-full">
                <thead>
                  <tr>
                    <th
                      aria-sort={sortField === 'name' ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}
                      className="px-4 py-2.5 text-left"
                    >
                      <button type="button" onClick={() => toggleSort('name')} className="min-h-11 font-mono text-[10px] text-text-muted tracking-widest uppercase">
                        Name <SortIcon field="name" />
                      </button>
                    </th>
                    <th
                      aria-sort={sortField === 'status' ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}
                      className="px-4 py-2.5 text-left"
                    >
                      <button type="button" onClick={() => toggleSort('status')} className="min-h-11 font-mono text-[10px] text-text-muted tracking-widest uppercase">
                        Status <SortIcon field="status" />
                      </button>
                    </th>
                    <th className="px-4 py-2.5 text-left">
                      <span className="font-mono text-[10px] text-text-muted tracking-widest uppercase">Findings</span>
                    </th>
                    <th className="px-4 py-2.5 text-left">
                      <span className="font-mono text-[10px] text-text-muted tracking-widest uppercase">Files</span>
                    </th>
                    <th
                      aria-sort={sortField === 'created_at' ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}
                      className="px-4 py-2.5 text-left"
                    >
                      <button type="button" onClick={() => toggleSort('created_at')} className="min-h-11 font-mono text-[10px] text-text-muted tracking-widest uppercase">
                        Date <SortIcon field="created_at" />
                      </button>
                    </th>
                    <th className="px-4 py-2.5" />
                  </tr>
                </thead>
                <tbody>
                  {list.length === 0 && !search && total === 0 && <EmptyState />}
                  {list.length === 0 && (search || total > 0) && (
                    <tr>
                      <td colSpan={6} className="py-12 text-center text-text-muted text-sm">
                        No investigations match your filter.
                      </td>
                    </tr>
                  )}
                  {list.map((inv, i) => (
                    <InvTableRow
                      key={inv.id}
                      inv={inv}
                      index={i}
                      onDelete={setDeleteTarget}
                      timezone={timezone}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {filteredTotal > 0 && (
            <div className="px-4 py-2.5 border-t border-white/[0.06] flex flex-wrap items-center justify-between gap-3">
              <span className="font-mono text-[10px] text-text-muted">
                Page {page} of {data?.totalPages ?? 1} · {filteredTotal} investigations
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  aria-label="Previous page"
                  disabled={page <= 1}
                  onClick={() => setPage((current) => Math.max(1, current - 1))}
                  className="min-h-11 px-3 rounded-lg border border-white/[0.08] text-xs text-text-secondary disabled:opacity-40"
                >
                  Previous
                </button>
                <button
                  type="button"
                  aria-label="Next page"
                  disabled={page >= (data?.totalPages ?? 0)}
                  onClick={() => setPage((current) => current + 1)}
                  className="min-h-11 px-3 rounded-lg border border-white/[0.08] text-xs text-text-secondary disabled:opacity-40"
                >
                  Next
                </button>
                <Link to="/compliance" className="min-h-11 font-mono text-[10px] text-indigo-400/70 hover:text-indigo-400 transition-colors flex items-center gap-1">
                  Compliance <ChevronRight className="w-2.5 h-2.5" />
                </Link>
              </div>
            </div>
          )}
        </motion.div>
      </div>

      <ConfirmModal
        isOpen={deleteTarget !== null}
        title="Delete investigation"
        message={`"${deleteTarget?.name}" and all its files and findings will be permanently deleted.`}
        confirmLabel="Delete"
        isLoading={deleting}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  )
}
