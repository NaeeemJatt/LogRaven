import { useState, useMemo, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Search, ChevronRight, Loader2, ShieldCheck,
  Crosshair, Inbox, FileText, Layers,
} from 'lucide-react'
import { investigationsApi } from '../api/investigations'
import type { Investigation } from '../types/investigation'

// ── Severity model (soft, muted but distinct) ─────────────
const SEVERITIES = ['all', 'critical', 'high', 'medium', 'low', 'info'] as const
type Sev = (typeof SEVERITIES)[number]

const SEV_COLOR: Record<string, string> = {
  critical: '#DB8585',
  high:     '#E0A86F',
  medium:   '#D9C27E',
  low:      '#8FBDAD',
  info:     '#93A4B5',
}
const SEV_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }

interface Finding {
  id: string
  title: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  finding_type: string
  mitre_technique_id?: string
  description?: string
  timestamp?: string
  source_file?: string
}
interface ReportData {
  findings: Finding[]
  investigation_name: string
  investigation_id: string
  created_at?: string
}
type FeedFinding = Finding & { invName: string; invId: string }

async function fetchAllFindings(investigations: Investigation[]): Promise<FeedFinding[]> {
  const complete = investigations.filter((inv) => inv.status === 'complete').slice(0, 10)
  const results = await Promise.allSettled(
    complete.map(async (inv) => {
      const res = await investigationsApi.getReport(inv.id)
      const data = res.data as ReportData
      return (data.findings ?? []).map((f) => ({ ...f, invName: inv.name, invId: inv.id }))
    })
  )
  return results
    .filter((r): r is PromiseFulfilledResult<FeedFinding[]> => r.status === 'fulfilled')
    .flatMap((r) => r.value)
    .sort((a, b) => (SEV_ORDER[a.severity] ?? 5) - (SEV_ORDER[b.severity] ?? 5))
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
              className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-left transition-colors ${
                selected ? 'bg-white/[0.05]' : 'hover:bg-white/[0.025]'
              }`}
            >
              <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
              <span className={`flex-1 text-xs font-medium capitalize ${selected ? 'text-text-primary' : 'text-text-secondary'}`}>
                {sev}
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
      {(['critical', 'high', 'medium', 'low', 'info'] as const).map((s) => {
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
              {f.severity}
            </span>
            {f.mitre_technique_id && (
              <span className="font-mono text-[9px] text-text-muted">{f.mitre_technique_id}</span>
            )}
          </div>
          <div className={`text-sm leading-snug truncate ${selected ? 'text-text-primary' : 'text-text-secondary'}`}>
            {f.title}
          </div>
          <div className="font-mono text-[10px] text-text-ghost mt-1 truncate">{f.invName}</div>
        </div>
        <ChevronRight className={`w-3.5 h-3.5 flex-shrink-0 mt-1 transition-colors ${selected ? 'text-text-secondary' : 'text-text-ghost'}`} />
      </div>
    </button>
  )
}

// ── Inspector (right pane) ────────────────────────────────
function Inspector({ f }: { f: FeedFinding | null }) {
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
    { label: 'Source file', value: f.source_file || '—' },
    { label: 'Timestamp', value: f.timestamp ? new Date(f.timestamp).toLocaleString() : '—' },
  ]
  return (
    <div className="ops-panel h-full flex flex-col overflow-hidden">
      <div className="px-5 pt-5 pb-4 border-b border-white/[0.07]">
        <div className="flex items-center gap-2 mb-3">
          <span className="font-mono text-[10px] px-2 py-0.5 rounded uppercase tracking-wide" style={{ color, background: `${color}1f` }}>
            {f.severity}
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
          to={`/investigations/${f.invId}/report`}
          className="btn-sovereign w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold"
        >
          <FileText className="w-4 h-4" /> Open full report
        </Link>
        <div className="flex items-center justify-center gap-1.5 mt-2 font-mono text-[10px] text-text-ghost truncate">
          <Layers className="w-3 h-3" /> {f.invName}
        </div>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────
export default function AlertFeed() {
  const [sevFilter, setSevFilter] = useState<Sev>('all')
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const { data: investigations, isLoading: loadingInvs } = useQuery<Investigation[]>({
    queryKey: ['investigations'],
    queryFn: async () => (await investigationsApi.list()).data,
  })

  const { data: allFindings, isLoading: loadingFindings } = useQuery({
    queryKey: ['alert-feed', investigations?.map((i) => i.id).join(',')],
    queryFn: () => fetchAllFindings(investigations ?? []),
    enabled: (investigations?.length ?? 0) > 0,
  })

  const isLoading = loadingInvs || loadingFindings
  const findings = allFindings ?? []

  const counts = useMemo(() => {
    const c: Record<string, number> = {}
    findings.forEach((f) => { c[f.severity] = (c[f.severity] ?? 0) + 1 })
    return c
  }, [findings])

  const filtered = useMemo(() => findings.filter((f) => {
    if (sevFilter !== 'all' && f.severity !== sevFilter) return false
    if (search &&
        !f.title.toLowerCase().includes(search.toLowerCase()) &&
        !(f.mitre_technique_id ?? '').toLowerCase().includes(search.toLowerCase())) return false
    return true
  }), [findings, sevFilter, search])

  const findingKey = (f: FeedFinding, i: number) => `${f.invId}-${f.id ?? i}`

  // keep a valid selection as the filter changes
  useEffect(() => {
    if (filtered.length === 0) { setSelectedId(null); return }
    if (!selectedId || !filtered.some((f, i) => findingKey(f, i) === selectedId)) {
      setSelectedId(findingKey(filtered[0], 0))
    }
  }, [filtered, selectedId])

  const selected = filtered.find((f, i) => findingKey(f, i) === selectedId) ?? null
  const total = findings.length

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
                {total} findings · {counts.critical ?? 0} critical · {counts.high ?? 0} high
              </p>
            </div>
          </div>
          <div className="lg:w-72">
            <DistributionBar counts={counts} total={total} />
            <div className="flex items-center justify-between mt-1.5 font-mono text-[9px] text-text-ghost uppercase tracking-wider">
              <span>Severity distribution</span>
              <span>{filtered.length} shown</span>
            </div>
          </div>
        </motion.div>

        {isLoading ? (
          <div className="ops-panel flex items-center justify-center py-32 gap-3">
            <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
            <span className="text-sm text-text-muted">Aggregating findings…</span>
          </div>
        ) : total === 0 ? (
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
            className="grid grid-cols-1 md:grid-cols-[190px_minmax(0,1fr)_330px] gap-4 h-[calc(100vh-13rem)] min-h-[520px]"
          >
            {/* Left — severity rail */}
            <SeverityRail counts={counts} active={sevFilter} onSelect={setSevFilter} total={total} />

            {/* Center — queue */}
            <div className="ops-panel flex flex-col overflow-hidden">
              <div className="flex items-center gap-2 px-3 py-2.5 border-b border-white/[0.07]">
                <Search className="w-3.5 h-3.5 text-text-muted flex-shrink-0" />
                <input
                  type="text"
                  placeholder="Search title or MITRE ID…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="bg-transparent text-xs text-text-secondary placeholder-text-muted outline-none w-full font-mono"
                />
                <span className="font-mono text-[10px] text-text-ghost flex-shrink-0">{filtered.length}</span>
              </div>
              <div className="flex-1 overflow-y-auto">
                {filtered.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full gap-2 text-center px-4">
                    <Inbox className="w-7 h-7 text-text-ghost" strokeWidth={1.25} />
                    <span className="text-sm text-text-muted">No findings match this view.</span>
                  </div>
                ) : (
                  filtered.map((f, i) => (
                    <QueueRow
                      key={findingKey(f, i)}
                      f={f}
                      selected={findingKey(f, i) === selectedId}
                      onClick={() => setSelectedId(findingKey(f, i))}
                    />
                  ))
                )}
              </div>
            </div>

            {/* Right — inspector */}
            <AnimatePresence mode="wait">
              <motion.div
                key={selectedId ?? 'empty'}
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
                className="hidden md:block h-full"
              >
                <Inspector f={selected} />
              </motion.div>
            </AnimatePresence>
          </motion.div>
        )}
      </div>
    </div>
  )
}
