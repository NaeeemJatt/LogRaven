// LogRaven — Cross-framework compliance posture (GET /api/v1/compliance/posture)
//
// Latest score per framework across all the user's completed audits, plus an
// overall readiness figure and the evidence reuse factor.

import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Gauge, Loader2, AlertOctagon, RefreshCw, TrendingUp, TrendingDown, Network,
} from 'lucide-react'
import { getPosture } from '../../api/compliance'
import type { PostureCard } from '../../api/compliance'
import { useAuthStore } from '../../store/authStore'
import { formatDateTime } from '../../utils/dateTime'

function scoreColor(score: number): string {
  return score >= 80 ? '#8FBDAD' : score >= 50 ? '#D9C27E' : '#DB8585'
}

function FrameworkCard({
  card,
  index,
  timezone,
}: {
  card: PostureCard
  index: number
  timezone?: string | null
}) {
  const color = scoreColor(card.score_percent)
  const total = card.pass_count + card.fail_count + card.partial_count
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: index * 0.05 }}
      className="ops-panel p-5"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-text-primary truncate">{card.framework_name}</div>
          <div className="font-mono text-[10px] text-text-muted mt-0.5">
            as of{' '}
            {formatDateTime(card.as_of, timezone, {
              month: 'short',
              day: 'numeric',
              year: 'numeric',
            })}
          </div>
        </div>
        <span className="stat-value text-2xl font-semibold tabular-nums flex-shrink-0" style={{ color }}>
          {card.score_percent.toFixed(0)}<span className="text-sm">%</span>
        </span>
      </div>

      {/* Score bar */}
      <div className="mt-4 h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ background: color }}
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(100, Math.max(0, card.score_percent))}%` }}
          transition={{ duration: 0.7, ease: 'easeOut', delay: 0.15 + index * 0.05 }}
        />
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2">
        {[
          { label: 'Pass', count: card.pass_count, color: '#8FBDAD' },
          { label: 'Partial', count: card.partial_count, color: '#D9C27E' },
          { label: 'Fail', count: card.fail_count, color: '#DB8585' },
        ].map(({ label, count, color: c }) => (
          <div key={label} className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-2.5 py-2">
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: c }} />
              <span className="text-[9px] font-mono uppercase tracking-wider text-text-muted">{label}</span>
            </div>
            <div className="stat-value text-lg mt-1" style={{ color: c }}>{count}</div>
          </div>
        ))}
      </div>

      <div className="mt-3 flex items-center justify-between">
        <span className="font-mono text-[10px] text-text-muted">{total} controls assessed</span>
        {card.score_delta != null && card.score_delta !== 0 && (
          <span
            className="inline-flex items-center gap-1 font-mono text-[10px]"
            style={{ color: card.score_delta > 0 ? '#8FBDAD' : '#DB8585' }}
          >
            {card.score_delta > 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            {card.score_delta > 0 ? '+' : ''}{card.score_delta.toFixed(1)} pts
          </span>
        )}
      </div>
    </motion.div>
  )
}

export default function CompliancePosture() {
  const user = useAuthStore((state) => state.user)
  const timezone = user?.timezone
  const { data, isLoading, isError, refetch, isRefetching } = useQuery({
    queryKey: ['compliance-posture', user?.id],
    queryFn: getPosture,
  })

  if (isLoading) {
    return (
      <div className="ops-panel p-12 flex items-center justify-center text-sm text-text-muted">
        <Loader2 className="w-4 h-4 animate-spin mr-2" /> Loading compliance posture…
      </div>
    )
  }

  if (isError) {
    return (
      <div role="alert" className="ops-panel p-10 flex flex-col items-center text-center gap-3">
        <AlertOctagon className="w-6 h-6 text-threat-critical" />
        <p className="text-sm text-text-secondary">Could not load your compliance posture.</p>
        <button
          onClick={() => { void refetch() }}
          className="btn-ghost inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium text-text-secondary"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Retry
        </button>
      </div>
    )
  }

  const posture = data
  if (!posture || posture.frameworks.length === 0) {
    return (
      <div className="ops-panel p-12 flex flex-col items-center text-center gap-2">
        <Gauge className="w-8 h-8 text-text-ghost" strokeWidth={1.25} />
        <p className="text-sm font-medium text-text-secondary">No posture data yet</p>
        <p className="text-xs text-text-muted max-w-sm">
          Complete a compliance audit and each assessed framework will appear here with its
          latest score and trend.
        </p>
      </div>
    )
  }

  const overallColor = posture.overall_score != null ? scoreColor(posture.overall_score) : '#93A4B5'

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}
      className="space-y-4"
    >
      {/* Summary strip */}
      <div className="ops-panel p-5 flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="flex items-center gap-4 flex-1">
          <div
            className="w-14 h-14 rounded-2xl flex items-center justify-center border flex-shrink-0"
            style={{ background: overallColor + '14', borderColor: overallColor + '35' }}
          >
            <Gauge className="w-6 h-6" style={{ color: overallColor }} />
          </div>
          <div>
            <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-text-muted">Overall readiness</div>
            <div className="stat-value text-3xl font-semibold mt-0.5" style={{ color: overallColor }}>
              {posture.overall_score != null ? `${posture.overall_score.toFixed(0)}%` : '—'}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-6">
          <div>
            <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted">Audits run</div>
            <div className="stat-value text-xl text-text-primary mt-0.5">{posture.total_audits}</div>
          </div>
          {posture.reuse_factor != null && (
            <div>
              <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted flex items-center gap-1">
                <Network className="w-3 h-3" /> Evidence reuse
              </div>
              <div className="stat-value text-xl text-indigo-300 mt-0.5">{posture.reuse_factor}×</div>
            </div>
          )}
          <button
            onClick={() => { void refetch() }}
            className="inline-flex items-center gap-1.5 text-[11px] font-mono text-text-muted hover:text-text-secondary transition-colors"
          >
            <RefreshCw className={`w-3 h-3 ${isRefetching ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>
      </div>

      {/* Framework cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {posture.frameworks.map((card, i) => (
          <FrameworkCard key={card.framework_id} card={card} index={i} timezone={timezone} />
        ))}
      </div>
    </motion.div>
  )
}
