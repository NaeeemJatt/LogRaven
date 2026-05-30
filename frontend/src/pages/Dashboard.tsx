import { useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, useInView } from 'framer-motion'
import {
  Plus, Search, AlertTriangle, CheckCircle2,
  Clock, XCircle, FileText, Trash2,
  Activity, ChevronRight, Loader2,
  ArrowUpDown, BarChart2
} from 'lucide-react'
import { investigationsApi } from '../api/investigations'
import ConfirmModal from '../components/ui/ConfirmModal'
import type { Investigation } from '../types/investigation'

// ── Stat card ─────────────────────────────────────────────
function StatCard({ label, value, color, sub, index }: {
  label: string; value: string | number; color: string; sub: string; index: number
}) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true })

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 24 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.5, delay: index * 0.08 }}
      className="p-5 rounded-xl border border-white/[0.06] bg-surface/60 backdrop-blur overflow-hidden"
    >
      <div className="font-mono text-[10px] text-text-muted tracking-widest uppercase mb-2">{sub} · {label}</div>
      <div className="font-display font-bold text-3xl" style={{ color }}>{value}</div>
    </motion.div>
  )
}

// ── Activity histogram (7-day placeholder) ─────────────────
function ActivityHistogram({ data }: { data: Investigation[] }) {
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  const now = new Date()

  const counts = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(now)
    d.setDate(d.getDate() - (6 - i))
    const dayStr = d.toISOString().slice(0, 10)
    return {
      label: days[(d.getDay() + 6) % 7],
      count: data.filter((inv) => inv.created_at?.slice(0, 10) === dayStr).length,
    }
  })

  const max = Math.max(...counts.map((c) => c.count), 1)

  return (
    <div className="p-5 rounded-xl border border-white/[0.06] bg-surface/40 backdrop-blur">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="font-mono text-[10px] text-text-muted tracking-widest uppercase">Activity</div>
          <div className="text-sm font-semibold text-text-primary mt-0.5">7-day investigation trend</div>
        </div>
        <BarChart2 className="w-4 h-4 text-text-muted" />
      </div>
      <div className="flex items-end gap-1.5 h-12">
        {counts.map((c, i) => (
          <div key={i} className="flex-1 flex flex-col items-center gap-1">
            <motion.div
              initial={{ scaleY: 0 }}
              animate={{ scaleY: 1 }}
              transition={{ delay: i * 0.04, duration: 0.4, ease: 'easeOut' }}
              style={{
                height: `${Math.max((c.count / max) * 100, 8)}%`,
                background: c.count > 0 ? 'rgba(99,102,241,0.5)' : 'rgba(255,255,255,0.05)',
                transformOrigin: 'bottom',
              }}
              className="w-full rounded-sm"
            />
          </div>
        ))}
      </div>
      <div className="flex items-center gap-1.5 mt-2">
        {counts.map((c, i) => (
          <div key={i} className="flex-1 text-center">
            <span className="font-mono text-[9px] text-text-ghost">{c.label}</span>
          </div>
        ))}
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
  const summary = (inv as any).severity_summary
  if (!summary && !(inv as any).findings_count) {
    if (inv.status !== 'complete') return <span className="text-text-ghost font-mono text-[10px]">—</span>
  }

  const critical = summary?.critical ?? 0
  const high = summary?.high ?? 0
  const total = (inv as any).findings_count ?? 0

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
  inv, index, onDelete,
}: {
  inv: Investigation; index: number; onDelete: (inv: Investigation) => void
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
          {new Date(inv.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' })}
        </span>
      </td>

      {/* Actions */}
      <td className="px-4 py-3 whitespace-nowrap">
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {canView && (
            <Link
              to={`/investigations/${inv.id}/report`}
              className="p-1.5 rounded-lg hover:bg-indigo-500/10 text-text-muted hover:text-indigo-400 transition-all"
              title="View report"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          )}
          {isProcessing && (
            <Link
              to={`/investigations/${inv.id}/status`}
              className="p-1.5 rounded-lg hover:bg-indigo-500/10 text-text-muted hover:text-indigo-400 transition-all"
              title="View status"
            >
              {inv.status === 'processing'
                ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                : <Activity className="w-3.5 h-3.5" />}
            </Link>
          )}
          <button
            onClick={() => onDelete(inv)}
            className="p-1.5 rounded-lg hover:bg-rose-500/10 text-text-muted hover:text-rose-400 transition-all"
            title="Delete"
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
            className="btn-sovereign flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white"
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
  const [deleteTarget, setDeleteTarget] = useState<Investigation | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [search, setSearch] = useState('')
  const [sortField, setSortField] = useState<SortField>('created_at')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const { data, isLoading, error } = useQuery<Investigation[]>({
    queryKey: ['investigations'],
    queryFn: async () => {
      const res = await investigationsApi.list()
      return res.data
    },
  })

  const list = data ?? []
  const filtered = list
    .filter((i) => !search || i.name.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      let cmp = 0
      if (sortField === 'name') cmp = a.name.localeCompare(b.name)
      else if (sortField === 'status') cmp = a.status.localeCompare(b.status)
      else cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      return sortDir === 'asc' ? cmp : -cmp
    })

  const total = list.length
  const activeCount = list.filter((i) => ['queued', 'processing'].includes(i.status)).length
  const completeCount = list.filter((i) => i.status === 'complete').length
  const failedCount = list.filter((i) => i.status === 'failed').length

  const stats = [
    { label: 'Investigations', value: total,         color: '#6366F1', sub: 'total',    index: 0 },
    { label: 'Active',         value: activeCount,   color: '#F97316', sub: 'running',  index: 1 },
    { label: 'Complete',       value: completeCount, color: '#14B8A6', sub: 'finished', index: 2 },
    { label: 'Failed',         value: failedCount,   color: '#F43F5E', sub: 'errored',  index: 3 },
  ]

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await investigationsApi.delete(deleteTarget.id)
      queryClient.invalidateQueries({ queryKey: ['investigations'] })
    } finally {
      setDeleting(false)
      setDeleteTarget(null)
    }
  }

  const toggleSort = (field: SortField) => {
    if (sortField === field) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortField(field); setSortDir('desc') }
  }

  const SortIcon = ({ field }: { field: SortField }) => (
    <ArrowUpDown className={`w-3 h-3 ml-1 inline transition-colors ${sortField === field ? 'text-indigo-400' : 'text-text-ghost'}`} />
  )

  return (
    <div className="pt-16 min-h-screen">
      <div className="px-4 sm:px-6 lg:px-8 py-8">

        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
          className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8"
        >
          <div>
            <div className="font-mono text-[10px] text-indigo-400 tracking-widest uppercase mb-1">Workspace</div>
            <h1 className="font-display font-bold text-text-primary text-3xl">Investigations</h1>
          </div>
          <Link
            to="/investigations/new"
            className="btn-sovereign flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold text-white self-start sm:self-auto"
          >
            <Plus className="w-4 h-4" /> New investigation
          </Link>
        </motion.div>

        {error && (
          <div className="mb-6 px-4 py-3 rounded-xl border border-rose-500/20 bg-rose-500/5 text-rose-400 text-xs font-mono">
            Failed to load investigations. Check the API and try again.
          </div>
        )}

        {/* Stats + histogram row */}
        <div className="grid grid-cols-1 xl:grid-cols-5 gap-4 mb-8">
          <div className="xl:col-span-4 grid grid-cols-2 lg:grid-cols-4 gap-3">
            {stats.map((s) => <StatCard key={s.label} {...s} />)}
          </div>
          <div className="xl:col-span-1">
            <ActivityHistogram data={list} />
          </div>
        </div>

        {/* Dense investigations table */}
        <motion.div
          initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.3 }}
          className="rounded-xl border border-white/[0.06] bg-surface/40 backdrop-blur overflow-hidden"
        >
          {/* Toolbar */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
            <div className="flex items-center gap-3">
              <h2 className="font-display font-semibold text-text-primary text-sm">
                Investigations
              </h2>
              <span className="font-mono text-[10px] text-text-muted bg-white/[0.04] px-2 py-0.5 rounded">
                {filtered.length}/{total}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-white/[0.06] bg-white/[0.02]">
                <Search className="w-3 h-3 text-text-muted" />
                <input
                  type="text"
                  placeholder="Filter..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="bg-transparent text-xs text-text-secondary placeholder-text-muted outline-none w-28"
                />
              </div>
            </div>
          </div>

          {isLoading && (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
            </div>
          )}

          {!isLoading && (
            <div className="overflow-x-auto">
              <table className="sovereign-table w-full">
                <thead>
                  <tr>
                    <th onClick={() => toggleSort('name')} className="cursor-pointer select-none px-4 py-2.5 text-left">
                      <span className="font-mono text-[10px] text-text-muted tracking-widest uppercase">
                        Name <SortIcon field="name" />
                      </span>
                    </th>
                    <th onClick={() => toggleSort('status')} className="cursor-pointer select-none px-4 py-2.5 text-left">
                      <span className="font-mono text-[10px] text-text-muted tracking-widest uppercase">
                        Status <SortIcon field="status" />
                      </span>
                    </th>
                    <th className="px-4 py-2.5 text-left">
                      <span className="font-mono text-[10px] text-text-muted tracking-widest uppercase">Findings</span>
                    </th>
                    <th className="px-4 py-2.5 text-left">
                      <span className="font-mono text-[10px] text-text-muted tracking-widest uppercase">Files</span>
                    </th>
                    <th onClick={() => toggleSort('created_at')} className="cursor-pointer select-none px-4 py-2.5 text-left">
                      <span className="font-mono text-[10px] text-text-muted tracking-widest uppercase">
                        Date <SortIcon field="created_at" />
                      </span>
                    </th>
                    <th className="px-4 py-2.5" />
                  </tr>
                </thead>
                <tbody>
                  {filtered.length === 0 && list.length === 0 && <EmptyState />}
                  {filtered.length === 0 && list.length > 0 && (
                    <tr>
                      <td colSpan={6} className="py-12 text-center text-text-muted text-sm">
                        No investigations match your filter.
                      </td>
                    </tr>
                  )}
                  {filtered.map((inv, i) => (
                    <InvTableRow key={inv.id} inv={inv} index={i} onDelete={setDeleteTarget} />
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {list.length > 0 && (
            <div className="px-4 py-2.5 border-t border-white/[0.04] flex items-center justify-between">
              <span className="font-mono text-[10px] text-text-muted">
                {filtered.length} of {total} investigations
              </span>
              <Link to="/compliance" className="font-mono text-[10px] text-indigo-400/70 hover:text-indigo-400 transition-colors flex items-center gap-1">
                SOC 2 compliance <ChevronRight className="w-2.5 h-2.5" />
              </Link>
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
