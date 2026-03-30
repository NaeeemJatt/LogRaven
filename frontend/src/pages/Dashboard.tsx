// LogRaven — Dashboard (21st.dev-inspired layout + LogRaven data layer)
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { animate, motion, useInView, useMotionValue, useMotionValueEvent } from 'framer-motion'
import {
  AlertCircle,
  CircleCheck,
  CircleDashed,
  FileBarChart,
  FileText,
  Eye,
  Plus,
  Search,
  Trash2,
} from 'lucide-react'

import Navbar from '../components/layout/Navbar'
import ConfirmModal from '../components/ui/ConfirmModal'
import { investigationsApi } from '../api/investigations'
import type { Investigation } from '../types/investigation'

// ── Animated stat figure (framer-motion animate API) ────────────────────────

function AnimatedValue({ value }: { value: number }) {
  const ref = useRef<HTMLSpanElement>(null)
  const isInView = useInView(ref, { once: true, amount: 0.5 })
  const mv = useMotionValue(0)
  const [display, setDisplay] = useState(0)

  useMotionValueEvent(mv, 'change', (v) => {
    setDisplay(Math.floor(v))
  })

  useEffect(() => {
    if (!isInView) return
    const ctrl = animate(mv, value, { duration: 0.75, ease: [0.22, 1, 0.36, 1] })
    return () => ctrl.stop()
  }, [isInView, value, mv])

  return (
    <span ref={ref} className="tabular-nums">
      {display.toLocaleString('en-GB')}
    </span>
  )
}

// ── Stats card ───────────────────────────────────────────────────────────────

function StatsCard({
  title,
  value,
  icon,
}: {
  title: string
  value: number
  icon: ReactNode
}) {
  const cardRef = useRef<HTMLDivElement>(null)
  const isInView = useInView(cardRef, { once: true, amount: 0.35 })

  return (
    <motion.div
      ref={cardRef}
      initial={{ opacity: 0, y: 16 }}
      animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 16 }}
      transition={{ duration: 0.45 }}
      whileHover={{ scale: 1.02, y: -2 }}
      className="bg-raven-800 border border-raven-700 rounded-lg p-5 shadow-lg"
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-raven-400">{title}</h3>
        <div className="text-electric-400">{icon}</div>
      </div>
      <div className="text-3xl font-bold text-raven-200">
        <AnimatedValue value={value} />
      </div>
    </motion.div>
  )
}

// ── Status pill (maps backend investigation statuses) ──────────────────────

const STATUS_STYLE: Record<
  Investigation['status'],
  { bg: string; text: string; label: string }
> = {
  draft: {
    bg: 'bg-raven-700/50',
    text: 'text-raven-400',
    label: 'Draft',
  },
  queued: {
    bg: 'bg-amber-500/10',
    text: 'text-amber-400',
    label: 'Queued',
  },
  processing: {
    bg: 'bg-electric-500/10',
    text: 'text-electric-400',
    label: 'Processing',
  },
  complete: {
    bg: 'bg-emerald-500/10',
    text: 'text-emerald-400',
    label: 'Complete',
  },
  failed: {
    bg: 'bg-rose-500/10',
    text: 'text-rose-400',
    label: 'Failed',
  },
}

function DashboardStatusBadge({ status }: { status: Investigation['status'] }) {
  const cfg = STATUS_STYLE[status]
  const Icon =
    status === 'complete'
      ? CircleCheck
      : status === 'failed'
        ? AlertCircle
        : status === 'processing' || status === 'queued'
          ? CircleDashed
          : FileText

  return (
    <div
      className={`inline-flex items-center justify-center px-3 py-1.5 rounded-lg ${cfg.bg}`}
    >
      <span className={`flex items-center gap-2 ${cfg.text} font-semibold text-xs uppercase tracking-wide`}>
        <Icon className="w-3.5 h-3.5 shrink-0" strokeWidth={2.5} />
        {cfg.label}
      </span>
    </div>
  )
}

// ── Investigation row (card layout) ────────────────────────────────────────────

function InvestigationRowCard({
  inv,
  onDelete,
  onNavigate,
}: {
  inv: Investigation
  onDelete: (inv: Investigation) => void
  onNavigate: (path: string) => void
}) {
  const fileCount = inv.files?.length ?? 0
  const created = new Date(inv.created_at).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28 }}
      className="bg-raven-800 border border-raven-700 rounded-lg p-4 hover:border-electric-500/40 transition-colors"
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 flex-1">
          <h3 className="text-raven-100 font-semibold text-base mb-1.5 truncate">{inv.name}</h3>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-raven-500">
            <span className="inline-flex items-center gap-1">
              <FileText className="w-3.5 h-3.5" />
              {fileCount} file{fileCount === 1 ? '' : 's'}
            </span>
            <span className="text-raven-700 hidden sm:inline">·</span>
            <span className="font-mono text-xs">{created}</span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <DashboardStatusBadge status={inv.status} />
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => onNavigate(`/investigations/${inv.id}`)}
              className="p-2 rounded-lg bg-electric-500/10 text-electric-400 hover:bg-electric-500/20 transition-colors"
              title="View investigation"
            >
              <Eye className="w-4 h-4" />
            </button>
            {inv.status === 'complete' && (
              <button
                type="button"
                onClick={() => onNavigate(`/investigations/${inv.id}/report`)}
                className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 transition-colors"
                title="Open report"
              >
                <FileBarChart className="w-4 h-4" />
              </button>
            )}
            <button
              type="button"
              onClick={() => onDelete(inv)}
              className="p-2 rounded-lg bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 transition-colors"
              title="Delete investigation"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

// ── Empty state ──────────────────────────────────────────────────────────────

function EmptyState({ onNew }: { onNew: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col items-center justify-center py-16 px-4"
    >
      <div className="bg-raven-800 border border-raven-700 rounded-full p-6 mb-6">
        <Search className="w-12 h-12 text-raven-600" strokeWidth={1.25} />
      </div>
      <h3 className="text-xl font-semibold text-raven-100 mb-2">No investigations yet</h3>
      <p className="text-raven-500 text-center mb-6 max-w-md text-sm">
        Upload logs from Windows, web servers, or cloud — correlate across sources and export a PDF report.
      </p>
      <button
        type="button"
        onClick={onNew}
        className="inline-flex items-center gap-2 px-6 py-3 bg-electric-500 text-raven-950 font-semibold rounded-lg hover:bg-electric-400 transition-colors"
      >
        <Plus className="w-5 h-5" />
        New investigation
      </button>
    </motion.div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [deleteTarget, setDeleteTarget] = useState<Investigation | null>(null)
  const [deleting, setDeleting] = useState(false)

  const { data, isLoading, error } = useQuery<Investigation[]>({
    queryKey: ['investigations'],
    queryFn: async () => {
      const res = await investigationsApi.list()
      return res.data
    },
  })

  const list = data ?? []
  const total = list.length
  const activeCount = list.filter((i) =>
    ['draft', 'queued', 'processing'].includes(i.status),
  ).length
  const completeCount = list.filter((i) => i.status === 'complete').length

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

  return (
    <div className="min-h-screen bg-raven-950 text-raven-200">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between mb-8">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight mb-1">
              Investigations
            </h1>
            <p className="text-raven-500 text-sm">
              Monitor log analysis jobs and open reports when ready.
            </p>
          </div>
          <button
            type="button"
            onClick={() => navigate('/investigations/new')}
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-electric-500 text-raven-950 font-semibold text-sm rounded-lg hover:bg-electric-400 transition-colors shrink-0"
          >
            <Plus className="w-4 h-4" />
            New investigation
          </button>
        </div>

        {error && (
          <p className="text-rose-400 text-xs font-mono mb-4 border border-rose-900/50 bg-rose-950/30 px-3 py-2 rounded-lg">
            Failed to load investigations. Check the API and try again.
          </p>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6 mb-8">
          <StatsCard title="Total" value={total} icon={<FileText className="w-6 h-6" />} />
          <StatsCard
            title="Active"
            value={activeCount}
            icon={<CircleDashed className="w-6 h-6" />}
          />
          <StatsCard
            title="Complete"
            value={completeCount}
            icon={<CircleCheck className="w-6 h-6" />}
          />
        </div>

        <div className="bg-raven-900/80 border border-raven-700 rounded-xl p-4 sm:p-6">
          <h2 className="text-lg font-semibold text-white mb-5">Recent investigations</h2>

          {isLoading && (
            <div className="flex items-center justify-center py-16">
              <div
                className="h-10 w-10 rounded-full border-2 border-raven-700 border-t-electric-500 animate-spin"
                aria-hidden
              />
            </div>
          )}

          {!isLoading && list.length === 0 && (
            <EmptyState onNew={() => navigate('/investigations/new')} />
          )}

          {!isLoading && list.length > 0 && (
            <div className="space-y-3">
              {list.map((inv) => (
                <InvestigationRowCard
                  key={inv.id}
                  inv={inv}
                  onDelete={setDeleteTarget}
                  onNavigate={(path) => navigate(path)}
                />
              ))}
            </div>
          )}
        </div>
      </main>

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
