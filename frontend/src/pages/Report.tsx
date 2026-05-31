import { useState, useMemo, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ChevronLeft, Download, Loader2, GitMerge, Target, Fingerprint,
  FileText, ListTree, Layers,
} from 'lucide-react'
import { investigationsApi } from '../api/investigations'
import type { Finding, Report } from '../types/report'

const SEV_ORDER = ['critical', 'high', 'medium', 'low', 'informational']

function sortBySeverity(findings: Finding[]): Finding[] {
  return [...findings].sort((a, b) => SEV_ORDER.indexOf(a.severity) - SEV_ORDER.indexOf(b.severity))
}

function buildMitreHits(findings: Finding[]): { tactic: string; techniques: string[] }[] {
  const map = new Map<string, Set<string>>()
  for (const f of findings) {
    if (f.mitre_tactic && f.mitre_technique_id) {
      if (!map.has(f.mitre_tactic)) map.set(f.mitre_tactic, new Set())
      map.get(f.mitre_tactic)!.add(f.mitre_technique_id)
    }
  }
  return Array.from(map.entries()).map(([tactic, techniques]) => ({ tactic, techniques: Array.from(techniques) }))
}

function collectIOCs(findings: Finding[]): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const f of findings) {
    for (const ioc of f.iocs ?? []) {
      const s = String(ioc).trim()
      if (s && !seen.has(s)) { seen.add(s); out.push(s) }
    }
  }
  return out
}

// Soft, muted severity palette (matches the rest of the console)
const SEVERITY_COLOR: Record<string, string> = {
  critical:      '#DB8585',
  high:          '#E0A86F',
  medium:        '#D9C27E',
  low:           '#8FBDAD',
  informational: '#93A4B5',
  info:          '#93A4B5',
}

// ── Severity bar chart (aside) ────────────────────────────
function SeverityChart({ counts }: { counts: Record<string, number> }) {
  const bars = [
    { label: 'Critical', key: 'critical' },
    { label: 'High',     key: 'high' },
    { label: 'Medium',   key: 'medium' },
    { label: 'Low',      key: 'low' },
    { label: 'Info',     key: 'informational' },
  ]
  const max = Math.max(...bars.map((b) => counts[b.key] ?? 0), 1)
  return (
    <div className="space-y-2.5">
      {bars.map(({ label, key }) => {
        const count = counts[key] ?? 0
        const color = SEVERITY_COLOR[key]
        return (
          <div key={label} className="flex items-center gap-3">
            <span className="font-mono text-[10px] w-12 text-text-muted">{label}</span>
            <div className="flex-1 h-1.5 rounded-full bg-white/[0.05] overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: count > 0 ? `${(count / max) * 100}%` : '0%' }}
                transition={{ duration: 1, ease: 'easeOut', delay: 0.2 }}
                className="h-full rounded-full"
                style={{ background: count > 0 ? color : 'transparent' }}
              />
            </div>
            <span className="stat-value text-xs w-3" style={{ color: count > 0 ? color : '#475569' }}>{count}</span>
          </div>
        )
      })}
    </div>
  )
}

// ── Reading pane: a single finding rendered as a document ──
function FindingReader({ finding }: { finding: Finding }) {
  const color = SEVERITY_COLOR[finding.severity] ?? '#93A4B5'
  const isCorrelated = finding.finding_type === 'correlated'
  return (
    <article className="p-6 sm:p-8 max-w-3xl">
      <div className="flex items-center gap-2 flex-wrap mb-3">
        <span className="font-mono text-[10px] px-2 py-0.5 rounded uppercase tracking-wide"
          style={{ color, background: `${color}1f` }}>{finding.severity}</span>
        {finding.mitre_technique_id && <span className="font-mono text-[10px] text-text-muted">{finding.mitre_technique_id}</span>}
        {isCorrelated && (
          <span className="inline-flex items-center gap-1 font-mono text-[9px] px-1.5 py-0.5 rounded border text-indigo-300 bg-indigo-500/10 border-indigo-500/25">
            <GitMerge className="w-2.5 h-2.5" /> correlated
          </span>
        )}
      </div>

      <h2 className="font-display font-bold text-text-primary text-2xl leading-tight">{finding.title}</h2>

      <div className="flex items-center gap-3 mt-2 flex-wrap">
        {finding.mitre_tactic && <span className="font-mono text-[10px] text-text-muted">{finding.mitre_tactic}</span>}
        {finding.source_files?.length > 0 && (
          <span className="inline-flex items-center gap-1.5 font-mono text-[10px] text-text-muted">
            <Layers className="w-3 h-3" /> {finding.source_files.join(', ')}
          </span>
        )}
      </div>

      {finding.description && (
        <p className="text-sm text-text-secondary leading-relaxed mt-6">{finding.description}</p>
      )}

      {finding.iocs?.length > 0 && (
        <div className="mt-6">
          <div className="font-mono text-[10px] text-text-muted tracking-widest uppercase mb-2">Indicators of compromise</div>
          <div className="flex flex-wrap gap-2">
            {finding.iocs.map((ioc) => (
              <span key={ioc} className="font-mono text-[11px] px-2.5 py-1 rounded-lg border border-white/[0.07] bg-deep text-text-secondary">{ioc}</span>
            ))}
          </div>
        </div>
      )}

      {finding.remediation && (
        <div className="mt-6">
          <div className="font-mono text-[10px] text-text-muted tracking-widest uppercase mb-2">Remediation</div>
          <p className="text-sm text-text-secondary leading-relaxed border-l-2 border-indigo-500/40 pl-4">{finding.remediation}</p>
        </div>
      )}
    </article>
  )
}

export default function Report() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [pdfLoading, setPdfLoading] = useState(false)
  const [selected, setSelected] = useState<string>('overview')

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

  const allFindings = useMemo(() => sortBySeverity(report?.findings ?? []), [report])
  const findingKey = (f: Finding, i: number) => String(f.id ?? `f-${i}`)

  useEffect(() => {
    if (report && !report.summary && allFindings.length > 0 && selected === 'overview') {
      setSelected(findingKey(allFindings[0], 0))
    }
  }, [report, allFindings, selected])

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
        <button onClick={() => navigate(`/investigations/${id}/status`)} className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors">
          Check analysis status →
        </button>
      </div>
    )
  }

  const correlated = allFindings.filter((f) => f.finding_type === 'correlated')
  const iocs = collectIOCs(allFindings)
  const mitreHits = buildMitreHits(allFindings)
  const counts = report.severity_counts ?? {}
  const mitreCount = mitreHits.reduce((acc, { techniques }) => acc + techniques.length, 0)

  const selectedFinding = allFindings.find((f, i) => findingKey(f, i) === selected) ?? null

  const statStrip = [
    { label: 'Findings', value: allFindings.length, color: '#E3B57E' },
    { label: 'Critical', value: counts.critical ?? 0, color: SEVERITY_COLOR.critical },
    { label: 'High', value: counts.high ?? 0, color: SEVERITY_COLOR.high },
    { label: 'Correlated', value: correlated.length, color: '#8FBDAD' },
    { label: 'IOCs', value: iocs.length, color: '#93A4B5' },
    { label: 'MITRE', value: mitreCount, color: '#D9C27E' },
  ]

  return (
    <div className="pt-16 min-h-screen grid-bg">
      <div className="px-4 sm:px-6 lg:px-8 py-6 max-w-[1500px] mx-auto">

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <button onClick={() => navigate('/dashboard')} className="inline-flex items-center gap-1.5 text-text-muted hover:text-text-secondary text-sm mb-4 transition-colors">
            <ChevronLeft className="w-3.5 h-3.5" /> Back to investigations
          </button>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
            <div>
              <h1 className="font-display font-bold text-text-primary text-2xl leading-none">Security report</h1>
              <p className="text-text-muted text-xs font-mono mt-1.5">
                {new Date(report.created_at).toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
              </p>
            </div>
            <button onClick={handleDownloadPdf} disabled={pdfLoading}
              className="btn-sovereign flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold self-start disabled:opacity-50">
              {pdfLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
              {pdfLoading ? 'Preparing…' : 'Export PDF'}
            </button>
          </div>

          {/* Stat strip */}
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 mb-5">
            {statStrip.map((s) => (
              <div key={s.label} className="ops-panel px-3 py-2.5">
                <div className="stat-value text-xl" style={{ color: s.color }}>{s.value}</div>
                <div className="font-mono text-[9px] text-text-muted uppercase tracking-wide">{s.label}</div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Split reader */}
        <motion.div
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-[240px_minmax(0,1fr)_280px] gap-4 md:h-[calc(100vh-17rem)] min-h-[520px]"
        >
          {/* Outline rail */}
          <div className="ops-panel flex flex-col overflow-hidden">
            <div className="px-4 py-3 border-b border-white/[0.07] flex items-center gap-2">
              <ListTree className="w-3.5 h-3.5 text-text-muted" />
              <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-text-muted">Findings · {allFindings.length}</span>
            </div>
            <div className="flex-1 overflow-y-auto">
              {report.summary && (
                <button
                  onClick={() => setSelected('overview')}
                  className={`relative w-full text-left pl-4 pr-3 py-3 border-b border-white/[0.05] transition-colors ${selected === 'overview' ? 'bg-white/[0.05]' : 'hover:bg-white/[0.025]'}`}
                >
                  {selected === 'overview' && <span className="absolute left-0 top-0 bottom-0 w-[3px] bg-indigo-400" />}
                  <div className="flex items-center gap-2">
                    <FileText className="w-3.5 h-3.5 text-indigo-300" />
                    <span className={`text-sm font-semibold ${selected === 'overview' ? 'text-text-primary' : 'text-text-secondary'}`}>Executive summary</span>
                  </div>
                </button>
              )}
              {allFindings.length === 0 ? (
                <div className="px-4 py-10 text-center text-sm text-text-muted">No findings generated.</div>
              ) : (
                allFindings.map((f, i) => {
                  const key = findingKey(f, i)
                  const color = SEVERITY_COLOR[f.severity] ?? '#93A4B5'
                  const sel = key === selected
                  return (
                    <button
                      key={key}
                      onClick={() => setSelected(key)}
                      className={`relative w-full text-left pl-4 pr-3 py-3 border-b border-white/[0.04] transition-colors ${sel ? 'bg-white/[0.05]' : 'hover:bg-white/[0.025]'}`}
                    >
                      <span className="absolute left-0 top-0 bottom-0 w-[3px]" style={{ background: color, opacity: sel ? 1 : 0.5 }} />
                      <div className="flex items-center gap-2 mb-1">
                        <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
                        {f.mitre_technique_id && <span className="font-mono text-[9px] text-text-muted">{f.mitre_technique_id}</span>}
                        {f.finding_type === 'correlated' && <GitMerge className="w-2.5 h-2.5 text-indigo-300" />}
                      </div>
                      <div className={`text-xs leading-snug ${sel ? 'text-text-primary' : 'text-text-secondary'}`}>{f.title}</div>
                    </button>
                  )
                })
              )}
            </div>
          </div>

          {/* Reading pane */}
          <div className="ops-panel overflow-y-auto">
            <AnimatePresence mode="wait">
              <motion.div key={selected} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
                {selected === 'overview' ? (
                  <article className="p-6 sm:p-8 max-w-3xl">
                    <div className="font-mono text-[10px] text-indigo-400 tracking-[0.18em] uppercase mb-2">Executive summary</div>
                    <h2 className="font-display font-bold text-text-primary text-2xl leading-tight mb-4">Investigation overview</h2>
                    {report.summary
                      ? <p className="text-sm text-text-secondary leading-relaxed whitespace-pre-line">{report.summary}</p>
                      : <p className="text-sm text-text-muted">No executive summary available. Select a finding to read its detail.</p>}
                  </article>
                ) : selectedFinding ? (
                  <FindingReader finding={selectedFinding} />
                ) : (
                  <div className="h-full flex items-center justify-center text-sm text-text-muted py-20">Select a finding to read.</div>
                )}
              </motion.div>
            </AnimatePresence>
          </div>

          {/* IOC / MITRE aside */}
          <div className="ops-panel flex flex-col overflow-hidden">
            <div className="flex-1 overflow-y-auto divide-y divide-white/[0.06]">
              <section className="p-4">
                <div className="font-mono text-[10px] text-text-muted tracking-widest uppercase mb-3">Severity breakdown</div>
                <SeverityChart counts={counts} />
              </section>

              <section className="p-4">
                <div className="flex items-center gap-1.5 font-mono text-[10px] text-text-muted tracking-widest uppercase mb-3">
                  <Target className="w-3 h-3" /> MITRE ATT&CK
                </div>
                {mitreHits.length === 0 ? (
                  <p className="text-xs text-text-muted">No techniques mapped.</p>
                ) : (
                  <div className="space-y-2.5">
                    {mitreHits.map(({ tactic, techniques }) => (
                      <div key={tactic}>
                        <div className="font-mono text-[9px] text-text-muted mb-1 truncate">{tactic}</div>
                        <div className="flex flex-wrap gap-1.5">
                          {techniques.map((t) => (
                            <span key={t} className="mitre-cell bg-indigo-500/12 border border-indigo-500/25 text-indigo-300">{t}</span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              <section className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="flex items-center gap-1.5 font-mono text-[10px] text-text-muted tracking-widest uppercase">
                    <Fingerprint className="w-3 h-3" /> IOCs
                  </span>
                  <span className="font-mono text-[10px] text-text-ghost">{iocs.length}</span>
                </div>
                {iocs.length === 0 ? (
                  <p className="text-xs text-text-muted">None extracted.</p>
                ) : (
                  <div className="space-y-1.5">
                    {iocs.map((ioc, i) => (
                      <div key={i} className="font-mono text-[11px] text-text-secondary break-all px-2 py-1.5 rounded border border-white/[0.05] bg-deep/60">{ioc}</div>
                    ))}
                  </div>
                )}
              </section>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
