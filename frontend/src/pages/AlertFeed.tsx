import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  AlertTriangle, Search, Filter, ChevronRight,
  Clock, Loader2, Shield, XCircle, CheckCircle2
} from 'lucide-react'
import { investigationsApi } from '../api/investigations'
import type { Investigation } from '../types/investigation'

// ── Severity filter ───────────────────────────────────────
const SEVERITIES = ['All', 'Critical', 'High', 'Medium', 'Low'] as const
type SeverityFilter = (typeof SEVERITIES)[number]

const SEV_COLOR: Record<string, string> = {
  critical: '#F43F5E',
  high:     '#F97316',
  medium:   '#FBBF24',
  low:      '#22D3EE',
  info:     '#94A3B8',
}

// ── Finding from real API shape ───────────────────────────
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

// ── Fetches all reports for all complete investigations ────
async function fetchAllFindings(investigations: Investigation[]): Promise<Array<Finding & { invName: string; invId: string }>> {
  const complete = investigations.filter((inv) => inv.status === 'complete').slice(0, 10)
  const results = await Promise.allSettled(
    complete.map(async (inv) => {
      const res = await investigationsApi.getReport(inv.id)
      const data = res.data as ReportData
      return (data.findings ?? []).map((f) => ({
        ...f,
        invName: inv.name,
        invId: inv.id,
      }))
    })
  )
  return results
    .filter((r): r is PromiseFulfilledResult<any[]> => r.status === 'fulfilled')
    .flatMap((r) => r.value)
    .sort((a, b) => {
      const order = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
      return (order[a.severity as keyof typeof order] ?? 5) - (order[b.severity as keyof typeof order] ?? 5)
    })
}

// ── Inline finding row ────────────────────────────────────
function FindingRow({ finding }: { finding: Finding & { invName: string; invId: string } }) {
  const [expanded, setExpanded] = useState(false)
  const color = SEV_COLOR[finding.severity] ?? '#94A3B8'

  return (
    <>
      <tr
        className="border-b border-white/[0.04] last:border-b-0 hover:bg-elevated/30 transition-colors cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Severity stripe */}
        <td className="w-1 py-0" style={{ padding: 0 }}>
          <div className="w-0.5 h-full min-h-[44px]" style={{ background: color, opacity: 0.7 }} />
        </td>

        {/* Finding name */}
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            <span
              className="font-mono text-[10px] px-1.5 py-0.5 rounded border"
              style={{ color, background: `${color}15`, borderColor: `${color}30` }}
            >
              {finding.severity.toUpperCase()}
            </span>
            <span className="text-sm font-medium text-text-primary">{finding.title}</span>
          </div>
        </td>

        {/* MITRE */}
        <td className="px-4 py-3 whitespace-nowrap">
          {finding.mitre_technique_id ? (
            <span className="mitre-cell font-mono text-[10px]">{finding.mitre_technique_id}</span>
          ) : (
            <span className="text-text-ghost font-mono text-[10px]">—</span>
          )}
        </td>

        {/* Type */}
        <td className="px-4 py-3 whitespace-nowrap">
          <span className={`font-mono text-[10px] px-1.5 py-0.5 rounded border ${
            finding.finding_type === 'correlated'
              ? 'bg-violet-500/10 border-violet-500/20 text-violet-400'
              : 'bg-white/[0.04] border-white/[0.08] text-text-muted'
          }`}>
            {finding.finding_type ?? 'single'}
          </span>
        </td>

        {/* Investigation */}
        <td className="px-4 py-3">
          <Link
            to={`/investigations/${finding.invId}/report`}
            onClick={(e) => e.stopPropagation()}
            className="font-mono text-[10px] text-indigo-400/80 hover:text-indigo-300 transition-colors truncate max-w-[160px] block"
          >
            {finding.invName}
          </Link>
        </td>

        {/* Expand toggle */}
        <td className="px-4 py-3 whitespace-nowrap">
          <ChevronRight
            className={`w-3.5 h-3.5 text-text-muted transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`}
          />
        </td>
      </tr>

      {/* Inline expansion */}
      {expanded && (
        <motion.tr
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.15 }}
          className="bg-deep/40 border-b border-white/[0.04]"
        >
          <td />
          <td colSpan={5} className="px-4 py-4">
            {finding.description ? (
              <p className="text-sm text-text-secondary leading-relaxed max-w-3xl">{finding.description}</p>
            ) : (
              <p className="text-sm text-text-muted italic">No additional details available.</p>
            )}
            <div className="flex items-center gap-4 mt-3">
              {finding.timestamp && (
                <span className="flex items-center gap-1.5 font-mono text-[10px] text-text-muted">
                  <Clock className="w-3 h-3" /> {new Date(finding.timestamp).toLocaleString()}
                </span>
              )}
              {finding.source_file && (
                <span className="font-mono text-[10px] text-text-muted">
                  Source: {finding.source_file}
                </span>
              )}
              <Link
                to={`/investigations/${finding.invId}/report`}
                className="flex items-center gap-1 font-mono text-[10px] text-indigo-400 hover:text-indigo-300 transition-colors"
              >
                View full report <ChevronRight className="w-3 h-3" />
              </Link>
            </div>
          </td>
        </motion.tr>
      )}
    </>
  )
}

// ── Alert Feed page ───────────────────────────────────────
export default function AlertFeed() {
  const [sevFilter, setSevFilter] = useState<SeverityFilter>('All')
  const [search, setSearch] = useState('')

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

  const filtered = findings.filter((f) => {
    if (sevFilter !== 'All' && f.severity.toLowerCase() !== sevFilter.toLowerCase()) return false
    if (search && !f.title.toLowerCase().includes(search.toLowerCase()) &&
        !(f.mitre_technique_id ?? '').toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const critical = findings.filter((f) => f.severity === 'critical').length
  const high = findings.filter((f) => f.severity === 'high').length

  return (
    <div className="pt-16 min-h-screen">
      <div className="px-4 sm:px-6 lg:px-8 py-8">

        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
          className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8"
        >
          <div>
            <div className="font-mono text-[10px] text-rose-400/80 tracking-widest uppercase mb-1">Threat intelligence</div>
            <h1 className="font-display font-bold text-text-primary text-3xl">Alert Feed</h1>
            <p className="text-text-muted text-sm mt-1">All findings across completed investigations, sorted by severity</p>
          </div>
          <div className="flex items-center gap-3 self-start sm:self-auto">
            {critical > 0 && (
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/10 border border-rose-500/20">
                <XCircle className="w-3.5 h-3.5 text-rose-400" />
                <span className="font-mono text-xs text-rose-400">{critical} critical</span>
              </div>
            )}
            {high > 0 && (
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-orange-500/10 border border-orange-500/20">
                <AlertTriangle className="w-3.5 h-3.5 text-orange-400" />
                <span className="font-mono text-xs text-orange-400">{high} high</span>
              </div>
            )}
          </div>
        </motion.div>

        {/* Severity filters + search toolbar */}
        <motion.div
          initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
          className="flex flex-wrap items-center gap-3 mb-6"
        >
          <div className="flex items-center gap-1 p-1 rounded-lg bg-surface border border-white/[0.06]">
            {SEVERITIES.map((sev) => (
              <button
                key={sev}
                onClick={() => setSevFilter(sev)}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                  sevFilter === sev
                    ? 'bg-indigo-500/15 border border-indigo-500/25 text-indigo-300'
                    : 'text-text-muted hover:text-text-secondary'
                }`}
              >
                {sev}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-white/[0.06] bg-white/[0.02] flex-1 max-w-xs">
            <Search className="w-3 h-3 text-text-muted flex-shrink-0" />
            <input
              type="text"
              placeholder="Search findings, MITRE IDs..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-transparent text-xs text-text-secondary placeholder-text-muted outline-none w-full"
            />
          </div>

          {!isLoading && (
            <span className="font-mono text-[10px] text-text-muted ml-auto">
              {filtered.length} findings
            </span>
          )}
        </motion.div>

        {/* Table */}
        <motion.div
          initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.3 }}
          className="rounded-xl border border-white/[0.06] bg-surface/40 backdrop-blur overflow-hidden"
        >
          {isLoading && (
            <div className="flex items-center justify-center py-20 gap-3">
              <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
              <span className="text-sm text-text-muted">Loading findings...</span>
            </div>
          )}

          {!isLoading && findings.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 gap-4">
              <CheckCircle2 className="w-10 h-10 text-teal-400" strokeWidth={1.25} />
              <div className="text-center">
                <h3 className="font-display text-lg font-semibold text-text-primary mb-1">No findings yet</h3>
                <p className="text-text-muted text-sm max-w-sm">
                  Complete an investigation to see findings here. Start by uploading log files.
                </p>
              </div>
              <Link to="/investigations/new" className="btn-sovereign flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white">
                <Shield className="w-4 h-4" /> New investigation
              </Link>
            </div>
          )}

          {!isLoading && findings.length > 0 && (
            <div className="overflow-x-auto">
              <table className="sovereign-table w-full">
                <thead>
                  <tr>
                    <th className="w-0.5 p-0" />
                    <th className="px-4 py-2.5 text-left">
                      <span className="font-mono text-[10px] text-text-muted tracking-widest uppercase">Finding</span>
                    </th>
                    <th className="px-4 py-2.5 text-left">
                      <span className="font-mono text-[10px] text-text-muted tracking-widest uppercase">MITRE</span>
                    </th>
                    <th className="px-4 py-2.5 text-left">
                      <span className="font-mono text-[10px] text-text-muted tracking-widest uppercase">Type</span>
                    </th>
                    <th className="px-4 py-2.5 text-left">
                      <span className="font-mono text-[10px] text-text-muted tracking-widest uppercase">Investigation</span>
                    </th>
                    <th className="px-4 py-2.5 w-8" />
                  </tr>
                </thead>
                <tbody>
                  {filtered.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-10 text-center text-text-muted text-sm">
                        No findings match your filters.
                      </td>
                    </tr>
                  ) : (
                    filtered.map((f, i) => (
                      <FindingRow key={`${f.invId}-${f.id ?? i}`} finding={f} />
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}

          {!isLoading && filtered.length > 0 && (
            <div className="px-4 py-2.5 border-t border-white/[0.04]">
              <div className="flex items-center gap-4">
                {['critical', 'high', 'medium', 'low'].map((s) => {
                  const count = findings.filter((f) => f.severity === s).length
                  if (!count) return null
                  const color = SEV_COLOR[s]
                  return (
                    <div key={s} className="flex items-center gap-1.5">
                      <div className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />
                      <span className="font-mono text-[10px] text-text-muted">{count} {s}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </motion.div>

        {(investigations?.filter((i) => i.status === 'complete').length ?? 0) === 0 && !isLoading && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
            className="mt-6 p-5 rounded-xl border border-dashed border-white/[0.08] flex items-center gap-4"
          >
            <Filter className="w-5 h-5 text-text-muted flex-shrink-0" />
            <div>
              <div className="text-sm font-medium text-text-secondary">Complete an investigation to see alerts</div>
              <div className="text-xs text-text-muted">Upload log files, run analysis, and findings will appear here.</div>
            </div>
            <Link to="/investigations/new" className="btn-ghost flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-text-secondary ml-auto flex-shrink-0">
              New investigation <ChevronRight className="w-3 h-3" />
            </Link>
          </motion.div>
        )}
      </div>
    </div>
  )
}
