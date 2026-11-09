// LogRaven — Investigation Operations Console
// Hallmark · v2.0.0 | shape: stage | theme: watchtower | genre: modern-minimal

import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Plus,
  Search,
  AlertTriangle,
  CheckCircle2,
  Clock,
  XCircle,
  FileText,
  Trash2,
  Activity,
  ChevronRight,
  Loader2,
  ArrowUpDown,
  Radio,
  ShieldAlert,
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
          <span className="text-xs text-text-muted font-medium">7-day intake volume</span>
        </div>
      </div>

      <div className="relative flex-1 flex items-end gap-2 min-h-[72px]">
        {/* baseline grid */}
        <div className="pointer-events-none absolute inset-0 flex flex-col justify-between opacity-40">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-px w-full bg-white/[0.05]" />
          ))}
        </div>
        {counts.map((c, i) => (
          <div key={i} className="relative flex-1 flex flex-col items-center justify-end h-full">
            <motion.div
              initial={{ scaleY: 0 }}
              animate={{ scaleY: 1 }}
              transition={{ delay: i * 0.05, duration: 0.5, ease: 'easeOut' }}
              style={{
                height: `${Math.max((c.count / max) * 100, 6)}%`,
                transformOrigin: 'bottom',
              }}
              className={`w-full max-w-[22px] rounded-[2px] ${
                c.count > 0 ? 'bg-amber-400/60' : 'bg-white/[0.05]'
              }`}
            />
          </div>
        ))}
      </div>
      <div className="flex items-center gap-2 mt-2">
        {counts.map((c, i) => (
          <div key={i} className="flex-1 text-center">
            <span className="text-[10px] text-text-muted font-mono">{c.label}</span>
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
    { label: 'Critical', value: agg.critical, colorClass: 'text-threat-critical bg-threat-critical' },
    { label: 'High', value: agg.high, colorClass: 'text-threat-high bg-threat-high' },
    { label: 'Findings', value: agg.findings, colorClass: 'text-amber-400 bg-amber-400' },
  ]
  const clear = agg.critical === 0 && agg.high === 0

  return (
    <div className="ops-panel p-5 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-3.5 h-3.5 text-text-muted" />
          <span className="text-xs text-text-muted font-medium">Threat posture</span>
        </div>
        <span className={`text-[10px] font-mono ${clear ? 'text-emerald-400' : 'text-threat-high'}`}>
          {clear ? 'Nominal' : 'Elevated'}
        </span>
      </div>

      <div className="flex-1 flex flex-col justify-center gap-3">
        {rows.map((r) => {
          const pct = agg.findings > 0 ? Math.min((r.value / agg.findings) * 100, 100) : 0
          const [textColor, bgColor] = r.colorClass.split(' ')
          return (
            <div key={r.label}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-text-muted">{r.label}</span>
                <span className={`stat-value text-sm font-mono tabular-nums ${textColor}`}>{r.value}</span>
              </div>
              <div className="h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${r.label === 'Findings' ? (agg.findings > 0 ? 100 : 0) : pct}%` }}
                  transition={{ duration: 1, ease: 'easeOut' }}
                  className={`h-full rounded-full opacity-80 ${bgColor}`}
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
  complete:   { icon: CheckCircle2, badge: 'bg-emerald-500/10 border-emerald-500/20', text: 'text-emerald-400', label: 'Complete'   },
  processing: { icon: Activity,     badge: 'bg-amber-500/10 border-amber-500/20',     text: 'text-amber-400',   label: 'Processing' },
  failed:     { icon: XCircle,      badge: 'bg-rose-500/10 border-rose-500/20',       text: 'text-rose-400',    label: 'Failed'     },
  queued:     { icon: Clock,        badge: 'bg-amber-500/10 border-amber-500/20',     text: 'text-amber-400',   label: 'Queued'     },
  draft:      { icon: FileText,     badge: 'bg-white/[0.04] border-white/[0.06]',     text: 'text-text-muted',  label: 'Draft'      },
}

function StatusBadge({ status }: { status: Investigation['status'] }) {
  const cfg = STATUS_CFG[status]
  const Icon = cfg.icon
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded border ${cfg.badge} ${cfg.text}`}>
      <Icon className="w-2.5 h-2.5" />
      <span>{cfg.label}</span>
    </span>
  )
}

// ── Severity pills ────────────────────────────────────────
function SeverityPills({ inv }: { inv: Investigation }) {
  const summary = inv.severity_summary
  if (!summary && !inv.findings_count) {
    if (inv.status !== 'complete') return <span className="text-text-ghost text-xs font-mono">-</span>
  }

  const critical = summary?.critical ?? 0
  const high = summary?.high ?? 0
  const total = inv.findings_count ?? 0

  if (!critical && !high && !total) return <span className="text-text-ghost text-xs font-mono">-</span>

  return (
    <div className="flex items-center gap-1 font-mono">
      {critical > 0 && (
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-threat-critical/10 border border-threat-critical/20 text-threat-critical">
          {critical}C
        </span>
      )}
      {high > 0 && (
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-threat-high/10 border border-threat-high/20 text-threat-high">
          {high}H
        </span>
      )}
      {!critical && !high && total > 0 && (
        <span className="text-[10px] text-text-muted">{total} findings</span>
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
      className="group border-b border-white/[0.04] last:border-b-0 hover:bg-elevated/40 transition-colors"
    >
      {/* Name */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => navigate(titleNav)}
            className="text-sm font-medium text-text-primary hover:text-amber-300 transition-colors text-left truncate max-w-[260px] focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded"
          >
            {inv.name}
          </button>
          {inv.status === 'processing' && (
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 motion-safe:animate-pulse" />
          )}
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="font-mono text-[10px] text-text-muted">{inv.id.slice(0, 8)}</span>
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
        <span className="font-mono text-xs text-text-muted tabular-nums">{fileCount}</span>
      </td>

      {/* Date */}
      <td className="px-4 py-3 whitespace-nowrap">
        <span className="font-mono text-[11px] text-text-muted tabular-nums">
          {formatDateTime(inv.created_at, timezone, { month: 'short', day: 'numeric', year: '2-digit' })}
        </span>
      </td>

      {/* Actions */}
      <td className="px-4 py-3 whitespace-nowrap">
        <div className="flex items-center gap-1">
          {canView && (
            <Link
              to={`/investigations/${inv.id}/report`}
              className="min-w-9 min-h-9 inline-flex items-center justify-center rounded-lg hover:bg-elevated text-text-muted hover:text-amber-400 transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
              aria-label={`View report for ${inv.name}`}
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          )}
          {isProcessing && (
            <Link
              to={`/investigations/${inv.id}/status`}
              className="min-w-9 min-h-9 inline-flex items-center justify-center rounded-lg hover:bg-elevated text-text-muted hover:text-amber-400 transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
              aria-label={`View status for ${inv.name}`}
            >
              {inv.status === 'processing' ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Activity className="w-3.5 h-3.5" />
              )}
            </Link>
          )}
          <button
            type="button"
            onClick={() => onDelete(inv)}
            className="min-w-9 min-h-9 inline-flex items-center justify-center rounded-lg hover:bg-threat-critical/10 text-text-muted hover:text-threat-critical transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
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
          <p className="text-text-secondary text-sm mb-6 text-center max-w-sm">
            Upload security log files to start an investigation and run detection rules.
          </p>
          <Link
            to="/investigations/new"
            className="btn-sovereign inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
          >
            <Plus className="w-4 h-4" /> Start your first investigation
          </Link>
        </motion.div>
      </td>
    </tr>
  )
}

export default function Dashboard() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [sortField, setSortField] = useState<'created_at' | 'name' | 'status'>('created_at')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [deleteTarget, setDeleteTarget] = useState<Investigation | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const user = useAuthStore((s) => s.user)
  const timezone = user?.timezone

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
    staleTime: 30_000,
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
    staleTime: 60_000,
  })

  const toggleSort = (field: 'created_at' | 'name' | 'status') => {
    if (sortField === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortField(field)
      setSortDir('asc')
    }
  }

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    setActionError(null)
    try {
      await investigationsApi.delete(deleteTarget.id)
      setDeleteTarget(null)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['investigations'] }),
        queryClient.invalidateQueries({ queryKey: ['investigations-stats'] }),
      ])
    } catch (err) {
      setActionError(normalizeApiError(err).message)
    } finally {
      setDeleting(false)
    }
  }

  const list = data?.items ?? []
  const total = stats?.total_investigations ?? data?.total ?? 0
  const filteredTotal = data?.total ?? total

  const counts = stats?.status_counts ?? {}
  const completed = counts.complete ?? 0
  const completionPct = total > 0 ? Math.round((completed / total) * 100) : 0

  const statusLegend = [
    { label: 'Complete', value: counts.complete ?? 0, color: '#3FB6A0' },
    { label: 'Processing', value: counts.processing ?? 0, color: '#E3B57E' },
    { label: 'Failed', value: counts.failed ?? 0, color: '#F0444E' },
    { label: 'Draft', value: counts.draft ?? 0, color: '#767C88' },
  ]

  const SortIcon = ({ field }: { field: 'created_at' | 'name' | 'status' }) => {
    if (sortField !== field) return <ArrowUpDown className="w-3 h-3 text-text-muted inline ml-1" />
    return <ArrowUpDown className="w-3 h-3 text-amber-400 inline ml-1" />
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 w-full space-y-6">
      {isError && (
        <div role="alert" className="p-4 rounded-lg border border-threat-critical/30 bg-threat-critical/[0.07] text-threat-critical text-xs flex items-center justify-between gap-3">
          <span>Failed to load investigations.</span>
          <button
            type="button"
            onClick={() => void refetch()}
            disabled={isRefetching}
            className="px-3 py-1.5 rounded border border-threat-critical/30 hover:bg-threat-critical/10 text-xs disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
          >
            {isRefetching ? 'Retrying…' : 'Retry'}
          </button>
        </div>
      )}

      {actionError && (
        <div role="alert" className="p-4 rounded-lg border border-threat-critical/30 bg-threat-critical/[0.07] text-threat-critical text-xs">
          {actionError}
        </div>
      )}

      {/* Bento operations grid */}
      {statsLoading ? (
        <div className="rounded-xl border border-white/[0.08] bg-surface flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 text-amber-400 animate-spin" />
        </div>
      ) : statsError ? (
        <div role="alert" className="rounded-xl border border-white/[0.08] bg-surface flex flex-col items-center justify-center gap-3 py-16 text-center">
          <ShieldAlert className="w-7 h-7 text-threat-critical" />
          <p className="text-sm text-text-secondary">
            Dashboard totals and threat posture are unavailable.
          </p>
          <button
            type="button"
            onClick={() => void refetchStats()}
            disabled={statsRefetching}
            className="px-4 py-2 rounded-lg border border-white/[0.08] hover:bg-elevated text-sm text-text-secondary disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
          >
            {statsRefetching ? 'Retrying…' : 'Retry summary'}
          </button>
        </div>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-4"
        >
          {/* Hero metric tile */}
          <div className="rounded-xl border border-white/[0.08] bg-surface p-6 md:row-span-2 flex flex-col justify-between">
            <div>
              <div className="text-xs text-text-muted">Under watch</div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="font-display font-bold text-5xl text-amber-400 tabular-nums">{total}</span>
                <span className="text-xs text-text-muted">investigations</span>
              </div>

              <div className="h-px bg-white/[0.06] my-5" />

              <ul className="space-y-2.5">
                {statusLegend.map((s) => (
                  <li key={s.label} className="flex items-center gap-2.5">
                    <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: s.color }} />
                    <span className="text-xs text-text-secondary flex-1">{s.label}</span>
                    <span className="text-sm font-mono tabular-nums text-text-primary">{s.value}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="pt-6 border-t border-white/[0.06] mt-6">
              <div className="flex items-center justify-between mb-1.5 text-xs text-text-muted">
                <span>Completion rate</span>
                <span className="font-mono text-emerald-400 tabular-nums">{completionPct}%</span>
              </div>
              <div className="h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${completionPct}%` }}
                  transition={{ duration: 1, ease: 'easeOut', delay: 0.3 }}
                  className="h-full rounded-full bg-emerald-400 opacity-80"
                />
              </div>
            </div>
          </div>

          {/* Intake trend */}
          <div className="md:col-span-2 rounded-xl border border-white/[0.08] bg-surface overflow-hidden">
            <ActivityHistogram
              dates={stats?.recent_investigation_dates ?? []}
              dailyCounts={stats?.recent_daily_counts}
              timezone={timezone}
            />
          </div>

          {/* Threat posture */}
          <div className="md:col-span-2 rounded-xl border border-white/[0.08] bg-surface overflow-hidden">
            <ThreatPosture counts={stats?.severity_counts ?? {}} />
          </div>
        </motion.div>
      )}

      {/* Live feed table */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.24 }}
        className="rounded-xl border border-white/[0.08] bg-surface overflow-hidden"
      >
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.08] bg-deep">
          <div className="flex items-center gap-2.5">
            <Radio className="w-3.5 h-3.5 text-amber-400" />
            <h2 className="text-xs font-semibold text-text-primary">
              Live investigation feed
            </h2>
            <span className="text-[11px] font-mono text-amber-300 bg-amber-400/10 border border-amber-400/20 px-2 py-0.5 rounded">
              {list.length}/{filteredTotal}
            </span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-white/[0.08] bg-surface focus-within:border-amber-400/50 transition-colors">
            <Search className="w-3 h-3 text-text-muted" />
            <input
              type="text"
              placeholder="Filter investigations..."
              aria-label="Search investigations"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setPage(1)
              }}
              className="bg-transparent text-xs text-text-primary placeholder:text-text-muted outline-none w-36 font-sans"
            />
          </div>
        </div>

        {isLoading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 text-amber-400 animate-spin" />
          </div>
        )}

        {!isLoading && !isError && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-white/[0.06] text-text-muted text-[11px]">
                  <th
                    aria-sort={sortField === 'name' ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}
                    className="px-4 py-3 font-medium text-left"
                  >
                    <button
                      type="button"
                      onClick={() => toggleSort('name')}
                      className="text-text-muted hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded"
                    >
                      Name <SortIcon field="name" />
                    </button>
                  </th>
                  <th
                    aria-sort={sortField === 'status' ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}
                    className="px-4 py-3 font-medium text-left"
                  >
                    <button
                      type="button"
                      onClick={() => toggleSort('status')}
                      className="text-text-muted hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded"
                    >
                      Status <SortIcon field="status" />
                    </button>
                  </th>
                  <th className="px-4 py-3 font-medium text-left">
                    <span>Findings</span>
                  </th>
                  <th className="px-4 py-3 font-medium text-left">
                    <span>Files</span>
                  </th>
                  <th
                    aria-sort={sortField === 'created_at' ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}
                    className="px-4 py-3 font-medium text-left"
                  >
                    <button
                      type="button"
                      onClick={() => toggleSort('created_at')}
                      className="text-text-muted hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded"
                    >
                      Date <SortIcon field="created_at" />
                    </button>
                  </th>
                  <th className="px-4 py-3 text-right" />
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
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
          <div className="px-4 py-3 border-t border-white/[0.06] flex flex-wrap items-center justify-between gap-3 text-xs text-text-muted">
            <span>
              Page {page} of {data?.totalPages ?? 1} · {filteredTotal} investigations
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                aria-label="Previous page"
                disabled={page <= 1}
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                className="px-3 py-1.5 rounded-lg border border-white/[0.08] hover:border-white/[0.18] bg-elevated/40 text-xs text-text-secondary hover:text-text-primary transition-colors disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
              >
                Previous
              </button>
              <button
                type="button"
                aria-label="Next page"
                disabled={page >= (data?.totalPages ?? 0)}
                onClick={() => setPage((current) => current + 1)}
                className="px-3 py-1.5 rounded-lg border border-white/[0.08] hover:border-white/[0.18] bg-elevated/40 text-xs text-text-secondary hover:text-text-primary transition-colors disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
              >
                Next
              </button>
              <Link
                to="/compliance"
                className="text-xs text-amber-400 hover:text-amber-300 transition-colors flex items-center gap-1 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded px-1.5 py-0.5"
              >
                <span>Compliance</span> <ChevronRight className="w-3 h-3" />
              </Link>
            </div>
          </div>
        )}
      </motion.div>

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
