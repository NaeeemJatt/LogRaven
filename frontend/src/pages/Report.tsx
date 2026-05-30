import { useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion, useInView, AnimatePresence } from 'framer-motion'
import {
  ChevronLeft, Download, AlertTriangle,
  Shield, ChevronDown, ExternalLink, Target,
  GitMerge, Loader2, LayoutList, LayoutGrid
} from 'lucide-react'
import { investigationsApi } from '../api/investigations'
import type { Finding, Report } from '../types/report'

const SEV_ORDER = ['critical', 'high', 'medium', 'low', 'informational']

function sortBySeverity(findings: Finding[]): Finding[] {
  return [...findings].sort(
    (a, b) => SEV_ORDER.indexOf(a.severity) - SEV_ORDER.indexOf(b.severity),
  )
}

// Group findings by tactic for MITRE matrix
function buildMitreHits(findings: Finding[]): { tactic: string; techniques: string[] }[] {
  const map = new Map<string, Set<string>>()
  for (const f of findings) {
    if (f.mitre_tactic && f.mitre_technique_id) {
      if (!map.has(f.mitre_tactic)) map.set(f.mitre_tactic, new Set())
      map.get(f.mitre_tactic)!.add(f.mitre_technique_id)
    }
  }
  return Array.from(map.entries()).map(([tactic, techniques]) => ({
    tactic,
    techniques: Array.from(techniques),
  }))
}

// Collect unique IOC strings across all findings
function collectIOCs(findings: Finding[]): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const f of findings) {
    for (const ioc of f.iocs ?? []) {
      const s = String(ioc).trim()
      if (s && !seen.has(s)) {
        seen.add(s)
        out.push(s)
      }
    }
  }
  return out
}

const SEVERITY_COLOR: Record<string, string> = {
  critical:     '#F43F5E',
  high:         '#F97316',
  medium:       '#FBBF24',
  low:          '#14B8A6',
  informational:'#818CF8',
  info:         '#818CF8',
}

// ── Severity bar chart ────────────────────────────────────
function SeverityChart({ counts }: { counts: Record<string, number> }) {
  const bars = [
    { label: 'Critical', key: 'critical', color: '#F43F5E' },
    { label: 'High',     key: 'high',     color: '#F97316' },
    { label: 'Medium',   key: 'medium',   color: '#FBBF24' },
    { label: 'Low',      key: 'low',      color: '#14B8A6' },
    { label: 'Info',     key: 'informational', color: '#818CF8' },
  ]
  const max = Math.max(...bars.map((b) => counts[b.key] ?? 0), 1)

  return (
    <div className="space-y-3">
      {bars.map(({ label, key, color }) => {
        const count = counts[key] ?? 0
        return (
          <div key={label} className="flex items-center gap-3">
            <span className="font-mono text-[10px] w-12 text-text-muted">{label}</span>
            <div className="flex-1 h-1.5 rounded-full bg-white/[0.05] overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: count > 0 ? `${(count / max) * 100}%` : '0%' }}
                transition={{ duration: 1.2, ease: 'easeOut', delay: 0.3 }}
                className="h-full rounded-full"
                style={{ background: count > 0 ? color : 'transparent' }}
              />
            </div>
            <span className="font-mono text-xs font-bold w-3" style={{ color: count > 0 ? color : '#475569' }}>
              {count}
            </span>
          </div>
        )
      })}
    </div>
  )
}

// ── MITRE matrix ──────────────────────────────────────────
function MitreMatrix({ hits }: { hits: { tactic: string; techniques: string[] }[] }) {
  if (hits.length === 0) {
    return (
      <p className="text-sm text-text-muted py-6 text-center">No MITRE ATT&CK techniques mapped.</p>
    )
  }
  return (
    <div className="space-y-2">
      {hits.map(({ tactic, techniques }) => (
        <div key={tactic} className="flex items-start gap-2">
          <span className="font-mono text-[9px] text-text-muted w-28 flex-shrink-0 pt-1 truncate">{tactic}</span>
          <div className="flex flex-wrap gap-1.5 flex-1">
            {techniques.map((t) => (
              <motion.span
                key={t}
                whileHover={{ scale: 1.05 }}
                className="mitre-cell bg-indigo-500/15 border border-indigo-500/25 text-indigo-300 cursor-pointer hover:bg-indigo-500/25"
              >
                {t}
              </motion.span>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Finding card ──────────────────────────────────────────
function FindingCard({ finding, index }: { finding: Finding; index: number }) {
  const [expanded, setExpanded] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-40px' })
  const isCorrelated = finding.finding_type === 'correlated'
  const severityColor = SEVERITY_COLOR[finding.severity] ?? '#818CF8'

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 20 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ delay: index * 0.06, duration: 0.5 }}
      className="rounded-xl border border-white/[0.06] bg-surface/40 overflow-hidden transition-all duration-300"
      style={{ borderLeftColor: severityColor, borderLeftWidth: '3px' }}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-start gap-4 p-4 text-left hover:bg-elevated/30 transition-all"
      >
        <div
          className="w-2 h-2 rounded-full flex-shrink-0 mt-1.5"
          style={{ background: severityColor, boxShadow: `0 0 6px ${severityColor}60` }}
        />

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3 mb-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-semibold text-text-primary font-display">{finding.title}</span>
              {isCorrelated && (
                <span className="flex items-center gap-1 font-mono text-[9px] px-1.5 py-0.5 rounded border text-indigo-400 bg-indigo-500/10 border-indigo-500/20">
                  <GitMerge className="w-2.5 h-2.5" />
                  correlated
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <span className="font-mono text-[10px] text-text-muted">{finding.mitre_technique_id}</span>
              <span
                className="font-mono text-[10px] px-2 py-0.5 rounded border uppercase tracking-wider"
                style={{
                  background: `${severityColor}18`,
                  borderColor: `${severityColor}30`,
                  color: severityColor,
                }}
              >
                {finding.severity}
              </span>
              <ChevronDown className={`w-3.5 h-3.5 text-text-muted transition-transform ${expanded ? 'rotate-180' : ''}`} />
            </div>
          </div>
          <div className="flex items-center gap-3">
            {finding.mitre_tactic && (
              <>
                <span className="font-mono text-[10px] text-text-muted">{finding.mitre_tactic}</span>
                <span className="text-text-ghost">·</span>
              </>
            )}
            {finding.source_files?.length > 0 && (
              <span className="font-mono text-[10px] text-text-muted truncate">
                {finding.source_files.join(', ')}
              </span>
            )}
          </div>
        </div>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="px-10 pb-4 space-y-4 border-t border-white/[0.04]">
              <p className="text-sm text-text-secondary leading-relaxed pt-4">{finding.description}</p>

              {finding.iocs?.length > 0 && (
                <div>
                  <div className="font-mono text-[10px] text-text-muted tracking-widest uppercase mb-2">Indicators of Compromise</div>
                  <div className="flex flex-wrap gap-2">
                    {finding.iocs.map((ioc) => (
                      <span key={ioc} className="font-mono text-[11px] px-2.5 py-1 rounded-lg border border-white/[0.06] bg-deep text-text-secondary">
                        {ioc}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {finding.remediation && (
                <p className="text-xs text-text-muted leading-relaxed border-l-2 border-indigo-500/30 pl-3">
                  {finding.remediation}
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

// ── Finding table row (dense table view) ─────────────────
function FindingTableRow({ finding, color }: { finding: Finding; color: string }) {
  const [expanded, setExpanded] = useState(false)
  const isCorrelated = finding.finding_type === 'correlated'

  return (
    <>
      <tr
        className="border-b border-white/[0.04] last:border-b-0 hover:bg-elevated/30 transition-colors cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <td className="w-0.5 py-0" style={{ padding: 0 }}>
          <div className="w-0.5 min-h-[44px]" style={{ background: color, opacity: 0.7 }} />
        </td>
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded border uppercase"
              style={{ color, background: `${color}15`, borderColor: `${color}30` }}>
              {finding.severity}
            </span>
            <span className="text-sm font-medium text-text-primary">{finding.title}</span>
          </div>
        </td>
        <td className="px-4 py-3 whitespace-nowrap">
          {finding.mitre_technique_id
            ? <span className="mitre-cell font-mono text-[10px]">{finding.mitre_technique_id}</span>
            : <span className="text-text-ghost font-mono text-[10px]">—</span>}
        </td>
        <td className="px-4 py-3 whitespace-nowrap">
          <span className="font-mono text-[10px] text-text-muted">{finding.mitre_tactic ?? '—'}</span>
        </td>
        <td className="px-4 py-3 whitespace-nowrap">
          {isCorrelated ? (
            <span className="flex items-center gap-1 font-mono text-[10px] px-1.5 py-0.5 rounded border bg-violet-500/10 border-violet-500/20 text-violet-400">
              <GitMerge className="w-2.5 h-2.5" /> correlated
            </span>
          ) : (
            <span className="font-mono text-[10px] text-text-ghost">single</span>
          )}
        </td>
        <td className="px-4 py-3 whitespace-nowrap">
          <ChevronDown className={`w-3.5 h-3.5 text-text-muted transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`} />
        </td>
      </tr>
      <AnimatePresence>
        {expanded && (
          <motion.tr
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="bg-deep/40 border-b border-white/[0.04]"
          >
            <td />
            <td colSpan={5} className="px-4 py-4">
              {finding.description && (
                <p className="text-sm text-text-secondary leading-relaxed mb-3 max-w-3xl">{finding.description}</p>
              )}
              {finding.iocs?.length > 0 && (
                <div className="mb-3">
                  <div className="font-mono text-[10px] text-text-muted tracking-widest uppercase mb-1.5">IOCs</div>
                  <div className="flex flex-wrap gap-1.5">
                    {finding.iocs.map((ioc) => (
                      <span key={ioc} className="font-mono text-[11px] px-2 py-0.5 rounded border border-white/[0.06] bg-deep text-text-secondary">
                        {ioc}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {finding.source_files?.length > 0 && (
                <div className="font-mono text-[10px] text-text-muted">
                  Source: {finding.source_files.join(', ')}
                </div>
              )}
            </td>
          </motion.tr>
        )}
      </AnimatePresence>
    </>
  )
}

// ── Main Report ───────────────────────────────────────────
export default function Report() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [activeSection, setActiveSection] = useState<'findings' | 'mitre' | 'iocs'>('findings')
  const [pdfLoading, setPdfLoading] = useState(false)
  const [viewMode, setViewMode] = useState<'cards' | 'table'>('table')

  const { data: report, isLoading, error } = useQuery<Report>({
    queryKey: ['report', id],
    queryFn: async () => (await investigationsApi.getReport(id!)).data,
    enabled: !!id,
  })

  const handleDownloadPdf = async () => {
    setPdfLoading(true)
    try {
      const res = await investigationsApi.getReportDownload(id!)
      window.open(res.data.download_url, '_blank', 'noopener,noreferrer')
    } catch {
      alert('PDF not ready. Run analysis first.')
    } finally {
      setPdfLoading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="pt-16 min-h-screen flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
      </div>
    )
  }

  if (error || !report) {
    return (
      <div className="pt-16 min-h-screen flex flex-col items-center justify-center gap-4 px-4">
        <div className="px-5 py-4 rounded-xl border border-rose-500/20 bg-rose-500/5 text-rose-400 text-sm text-center max-w-md">
          Report not available. The analysis may still be running.
        </div>
        <button
          onClick={() => navigate(`/investigations/${id}/status`)}
          className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors"
        >
          Check analysis status →
        </button>
      </div>
    )
  }

  const allFindings: Finding[] = sortBySeverity(report.findings ?? [])
  const correlated = allFindings.filter((f) => f.finding_type === 'correlated')
  const single = allFindings.filter((f) => f.finding_type !== 'correlated')
  const iocs = collectIOCs(allFindings)
  const mitreHits = buildMitreHits(allFindings)
  const counts = report.severity_counts ?? {}

  const totalFindings = allFindings.length
  const criticalCount = counts.critical ?? 0
  const highCount = counts.high ?? 0
  const correlatedCount = correlated.length
  const iocsCount = iocs.length
  const mitreCount = mitreHits.reduce((acc, { techniques }) => acc + techniques.length, 0)

  const stats = [
    { label: 'Total findings',    value: totalFindings,   color: '#6366F1' },
    { label: 'Critical',          value: criticalCount,   color: '#F43F5E' },
    { label: 'High',              value: highCount,       color: '#F97316' },
    { label: 'Correlated',        value: correlatedCount, color: '#14B8A6' },
    { label: 'IOCs extracted',    value: iocsCount,       color: '#818CF8' },
    { label: 'MITRE techniques',  value: mitreCount,      color: '#FBBF24' },
  ]

  return (
    <div className="pt-16 min-h-screen">
      <div className="px-4 sm:px-6 lg:px-8 py-8">

        {/* ── Header ──────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <button
            onClick={() => navigate('/dashboard')}
            className="inline-flex items-center gap-1.5 text-text-muted hover:text-text-secondary text-sm mb-4 transition-colors"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            Back to investigations
          </button>

          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
            <div>
              <h1 className="font-display font-bold text-text-primary text-2xl mb-1">Security Report</h1>
              <p className="text-text-secondary text-sm font-mono">
                {new Date(report.created_at).toLocaleString('en-US', {
                  month: 'short', day: 'numeric', year: 'numeric',
                  hour: '2-digit', minute: '2-digit',
                })}
              </p>
            </div>

            <button
              onClick={handleDownloadPdf}
              disabled={pdfLoading}
              className="btn-sovereign flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold text-white self-start disabled:opacity-50"
            >
              {pdfLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
              {pdfLoading ? 'Preparing…' : 'Export PDF'}
            </button>
          </div>
        </motion.div>

        {/* ── Stats row ────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-8"
        >
          {stats.map(({ label, value, color }, i) => (
            <motion.div
              key={label}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="p-4 rounded-xl border border-white/[0.06] bg-surface/40 text-center"
            >
              <div className="font-display font-bold text-2xl mb-0.5" style={{ color }}>{value}</div>
              <div className="font-mono text-[9px] text-text-muted tracking-wide uppercase leading-tight">{label}</div>
            </motion.div>
          ))}
        </motion.div>

        {/* ── Summary ──────────────────────────────────── */}
        {report.summary && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mb-6 p-5 rounded-xl border border-white/[0.06] bg-surface/40"
          >
            <div className="font-mono text-[10px] text-text-muted tracking-widest uppercase mb-3">Executive Summary</div>
            <p className="text-sm text-text-secondary leading-relaxed">{report.summary}</p>
          </motion.div>
        )}

        {/* ── Section tabs ─────────────────────────────── */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-1 p-1 rounded-xl border border-white/[0.06] bg-deep/80 w-fit">
            {[
              { id: 'findings', label: 'Findings', icon: AlertTriangle },
              { id: 'mitre',    label: 'MITRE ATT&CK', icon: Target },
              { id: 'iocs',     label: 'IOCs', icon: Shield },
            ].map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveSection(id as typeof activeSection)}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
                  activeSection === id
                    ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/20'
                    : 'text-text-muted hover:text-text-secondary'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {label}
              </button>
            ))}
          </div>

          {activeSection === 'findings' && (
            <div className="flex items-center gap-1 p-1 rounded-lg border border-white/[0.06] bg-deep/80">
              <button
                onClick={() => setViewMode('table')}
                className={`p-1.5 rounded transition-all ${viewMode === 'table' ? 'bg-indigo-500/15 text-indigo-300' : 'text-text-muted hover:text-text-secondary'}`}
                title="Table view"
              >
                <LayoutList className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setViewMode('cards')}
                className={`p-1.5 rounded transition-all ${viewMode === 'cards' ? 'bg-indigo-500/15 text-indigo-300' : 'text-text-muted hover:text-text-secondary'}`}
                title="Card view"
              >
                <LayoutGrid className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>

        {/* ── Main content ─────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-3">
            <AnimatePresence mode="wait">
              {activeSection === 'findings' && (
                <motion.div
                  key="findings"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  {allFindings.length === 0 ? (
                    <div className="py-16 text-center rounded-xl border border-white/[0.06] bg-surface/40">
                      <p className="text-text-muted text-sm">No findings generated.</p>
                      <p className="text-text-ghost font-mono text-xs mt-2">AI analysis may have found no threats.</p>
                    </div>
                  ) : viewMode === 'table' ? (
                    /* Dense table view */
                    <div className="rounded-xl border border-white/[0.06] bg-surface/40 overflow-hidden">
                      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
                        <span className="font-mono text-[10px] text-text-muted tracking-widest uppercase">
                          All findings ({allFindings.length})
                        </span>
                        {correlated.length > 0 && (
                          <span className="flex items-center gap-1 font-mono text-[10px] text-indigo-400">
                            <GitMerge className="w-3 h-3" /> {correlated.length} correlated
                          </span>
                        )}
                      </div>
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
                                <span className="font-mono text-[10px] text-text-muted tracking-widest uppercase">Tactic</span>
                              </th>
                              <th className="px-4 py-2.5 text-left">
                                <span className="font-mono text-[10px] text-text-muted tracking-widest uppercase">Type</span>
                              </th>
                              <th className="px-4 py-2.5 w-8" />
                            </tr>
                          </thead>
                          <tbody>
                            {allFindings.map((f, i) => {
                              const color = SEVERITY_COLOR[f.severity] ?? '#818CF8'
                              return (
                                <FindingTableRow key={f.id ?? i} finding={f} color={color} />
                              )
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ) : (
                    /* Card view */
                    <div className="space-y-3">
                      {correlated.length > 0 && (
                        <div className="mb-6">
                          <div className="font-mono text-[10px] text-text-muted tracking-widest uppercase mb-3 flex items-center gap-2">
                            <GitMerge className="w-3 h-3" /> Correlated findings ({correlated.length})
                          </div>
                          <div className="space-y-3">
                            {correlated.map((f, i) => <FindingCard key={f.id} finding={f} index={i} />)}
                          </div>
                        </div>
                      )}
                      {single.length > 0 && (
                        <div>
                          <div className="font-mono text-[10px] text-text-muted tracking-widest uppercase mb-3">
                            Individual findings ({single.length})
                          </div>
                          <div className="space-y-3">
                            {single.map((f, i) => <FindingCard key={f.id} finding={f} index={i} />)}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </motion.div>
              )}

              {activeSection === 'mitre' && (
                <motion.div
                  key="mitre"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="rounded-2xl border border-white/[0.06] bg-surface/40 p-6"
                >
                  <div className="flex items-center gap-2 mb-6">
                    <Target className="w-4 h-4 text-indigo-400" />
                    <h2 className="font-display font-semibold text-text-primary">MITRE ATT&CK Coverage</h2>
                  </div>
                  <p className="text-sm text-text-muted mb-6">
                    Techniques detected in this investigation, mapped to the ATT&CK Enterprise framework.
                  </p>
                  <MitreMatrix hits={mitreHits} />
                  <div className="mt-6 pt-6 border-t border-white/[0.04] flex items-center gap-4">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-sm bg-indigo-500/30 border border-indigo-500/40" />
                      <span className="font-mono text-[10px] text-text-muted">Detected technique</span>
                    </div>
                  </div>
                </motion.div>
              )}

              {activeSection === 'iocs' && (
                <motion.div
                  key="iocs"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="rounded-2xl border border-white/[0.06] bg-surface/40 overflow-hidden"
                >
                  <div className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Shield className="w-4 h-4 text-indigo-400" />
                      <h2 className="font-display font-semibold text-text-primary text-sm">Indicators of Compromise</h2>
                    </div>
                    <span className="font-mono text-[10px] text-text-muted">{iocs.length} IOCs extracted</span>
                  </div>
                  {iocs.length === 0 ? (
                    <div className="py-12 text-center text-text-muted text-sm">No IOCs extracted.</div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full sovereign-table">
                        <thead>
                          <tr>
                            <th>Value</th>
                            <th></th>
                          </tr>
                        </thead>
                        <tbody>
                          {iocs.map((ioc, i) => (
                            <tr key={i} className="border-b border-white/[0.04] hover:bg-indigo-500/[0.03] transition-colors group">
                              <td className="px-4 py-3">
                                <span className="font-mono text-xs text-text-primary">{ioc}</span>
                              </td>
                              <td className="px-4 py-3 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button className="p-1 rounded hover:bg-indigo-500/10 text-text-muted hover:text-indigo-400 transition-colors">
                                  <ExternalLink className="w-3 h-3" />
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            <div className="rounded-2xl border border-white/[0.06] bg-surface/40 p-5">
              <div className="font-mono text-[10px] text-text-muted tracking-widest uppercase mb-4">Severity Breakdown</div>
              <SeverityChart counts={counts} />
            </div>

            <div className="rounded-2xl border border-white/[0.06] bg-surface/40 p-5 space-y-3">
              <div className="font-mono text-[10px] text-text-muted tracking-widest uppercase mb-2">Investigation Summary</div>
              {[
                { label: 'Total findings', value: String(totalFindings) },
                { label: 'Correlated',     value: String(correlatedCount) },
                { label: 'MITRE techniques', value: String(mitreCount) },
                { label: 'IOCs extracted', value: String(iocsCount) },
              ].map(({ label, value }) => (
                <div key={label} className="flex items-center justify-between">
                  <span className="text-xs text-text-muted">{label}</span>
                  <span className="font-mono text-xs text-text-secondary">{value}</span>
                </div>
              ))}
            </div>

            <button
              onClick={handleDownloadPdf}
              disabled={pdfLoading}
              className="w-full btn-sovereign flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold text-white disabled:opacity-50"
            >
              {pdfLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
              {pdfLoading ? 'Preparing…' : 'Download PDF'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
