// LogRaven — Compliance Audit Results (Control Room stage)
//
// Multi-framework master-detail navigator: framework tabs + score summary on
// top, then either a filterable control browser (list + detail with evidence &
// remediation) or a shared-signal crosswalk view.

import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Download, Loader2, RotateCcw, FileText, ListChecks, AlertOctagon,
  Wrench, Network, FileSpreadsheet, TrendingUp, TrendingDown,
} from 'lucide-react'
import type {
  AuditStatusResponse, ControlResult, CrosswalkResponse, FrameworkResult,
} from '../../types/audit'
import { downloadAuditReport, downloadEvidencePack, getCrosswalk } from '../../api/compliance'

interface AuditResultsProps {
  results: AuditStatusResponse
  auditId: string
  onStartNew: () => void
}

const STATUS_ORDER: Record<string, number> = { FAIL: 0, PARTIAL: 1, PASS: 2 }
const STATUS_COLOR: Record<string, string> = {
  PASS:    '#8FBDAD',
  FAIL:    '#DB8585',
  PARTIAL: '#D9C27E',
}
type StatusFilter = 'ALL' | 'FAIL' | 'PARTIAL' | 'PASS'
type ViewMode = 'controls' | 'crosswalk'

function sortedResults(results: ControlResult[]): ControlResult[] {
  return [...results].sort((a, b) => (STATUS_ORDER[a.status] ?? 3) - (STATUS_ORDER[b.status] ?? 3))
}

function deriveFrameworks(results: AuditStatusResponse): FrameworkResult[] {
  if (results.framework_results?.length) return results.framework_results
  // Fall back to the legacy flat shape (single framework).
  const controls = results.results ?? []
  return [{
    framework_id: results.frameworks?.[0] ?? 'soc2',
    framework_name: results.frameworks?.[0] ?? 'SOC 2',
    controls_assessed: controls.length,
    pass_count: results.pass_count ?? 0,
    fail_count: results.fail_count ?? 0,
    partial_count: results.partial_count ?? 0,
    score_percent: results.score_percent ?? 0,
    results: controls,
  }]
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// ── Radial score gauge ────────────────────────────────────
function ScoreGauge({ score, color }: { score: number; color: string }) {
  const r = 48
  const c = 2 * Math.PI * r
  const offset = c - (Math.min(100, Math.max(0, score)) / 100) * c
  return (
    <div className="relative w-[120px] h-[120px] flex-shrink-0">
      <svg viewBox="0 0 130 130" className="w-full h-full -rotate-90">
        <circle cx="65" cy="65" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="9" />
        <motion.circle
          cx="65" cy="65" r={r} fill="none" stroke={color} strokeWidth="9" strokeLinecap="round"
          strokeDasharray={c}
          initial={{ strokeDashoffset: c }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1, ease: 'easeOut', delay: 0.15 }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="stat-value text-3xl font-semibold leading-none" style={{ color }}>
          {score.toFixed(0)}<span className="text-base">%</span>
        </span>
        <span className="text-[9px] font-mono uppercase tracking-[0.18em] text-text-muted mt-1">Score</span>
      </div>
    </div>
  )
}

export default function AuditResults({ results, auditId, onStartNew }: AuditResultsProps) {
  const frameworks = useMemo(() => deriveFrameworks(results), [results])
  const [activeFwId, setActiveFwId] = useState(frameworks[0]?.framework_id ?? 'soc2')
  const [view, setView] = useState<ViewMode>('controls')
  const [downloading, setDownloading] = useState<string | null>(null)
  const [downloadError, setDownloadError] = useState<string | null>(null)
  const [filter, setFilter] = useState<StatusFilter>('ALL')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [crosswalk, setCrosswalk] = useState<CrosswalkResponse | null>(null)

  const active = frameworks.find((f) => f.framework_id === activeFwId) ?? frameworks[0]
  const controls = active?.results ?? []
  const sorted = useMemo(() => sortedResults(controls), [controls])
  const company = results.company_name ?? ''
  const score = active?.score_percent ?? 0
  const scoreColor = score >= 80 ? '#8FBDAD' : score >= 50 ? '#D9C27E' : '#DB8585'

  const visible = useMemo(
    () => (filter === 'ALL' ? sorted : sorted.filter((r) => r.status === filter)),
    [sorted, filter],
  )

  useEffect(() => {
    if (visible.length === 0) { setSelectedId(null); return }
    if (!selectedId || !visible.some((r) => r.control_id === selectedId)) {
      setSelectedId(visible[0].control_id)
    }
  }, [visible, selectedId])

  useEffect(() => {
    if (view !== 'crosswalk' || crosswalk) return
    const ids = frameworks.map((f) => f.framework_id)
    getCrosswalk(ids).then(setCrosswalk).catch(() => setCrosswalk({ crosswalk: [], reuse_factor: null }))
  }, [view, crosswalk, frameworks])

  const selected = visible.find((r) => r.control_id === selectedId) ?? null

  const runDownload = async (key: string, fn: () => Promise<void>) => {
    setDownloading(key)
    setDownloadError(null)
    try { await fn() }
    catch (err) { setDownloadError(err instanceof Error ? err.message : 'Download failed') }
    finally { setDownloading(null) }
  }

  const handleDownloadPdf = () => runDownload('pdf', async () => {
    const blob = await downloadAuditReport(auditId, active?.framework_id, 'pdf')
    downloadBlob(blob, `${company.replace(/\s+/g, '_')}_${active?.framework_id}_evidence.pdf`)
  })
  const handleDownloadCsv = () => runDownload('csv', async () => {
    const blob = await downloadAuditReport(auditId, active?.framework_id, 'csv')
    downloadBlob(blob, `${company.replace(/\s+/g, '_')}_${active?.framework_id}_results.csv`)
  })
  const handleDownloadZip = () => runDownload('zip', async () => {
    const blob = await downloadEvidencePack(auditId)
    downloadBlob(blob, `${company.replace(/\s+/g, '_')}_evidence_pack.zip`)
  })

  const filters: { key: StatusFilter; label: string; count: number; color?: string }[] = [
    { key: 'ALL',     label: 'All',     count: controls.length },
    { key: 'FAIL',    label: 'Fail',    count: active?.fail_count ?? 0,    color: STATUS_COLOR.FAIL },
    { key: 'PARTIAL', label: 'Partial', count: active?.partial_count ?? 0, color: STATUS_COLOR.PARTIAL },
    { key: 'PASS',    label: 'Pass',    count: active?.pass_count ?? 0,    color: STATUS_COLOR.PASS },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
      className="space-y-4"
    >
      {/* ── Framework tabs (only when multiple) ──────────────────────────── */}
      {frameworks.length > 1 && (
        <div className="ops-panel p-2 flex flex-wrap gap-1.5">
          {frameworks.map((fw) => {
            const isActive = fw.framework_id === activeFwId
            const c = fw.score_percent >= 80 ? '#8FBDAD' : fw.score_percent >= 50 ? '#D9C27E' : '#DB8585'
            return (
              <button
                key={fw.framework_id}
                onClick={() => { setActiveFwId(fw.framework_id); setView('controls') }}
                className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium transition-colors border ${
                  isActive ? 'border-indigo-500/50 bg-indigo-500/12 text-text-primary'
                           : 'border-white/[0.07] bg-white/[0.02] text-text-muted hover:text-text-secondary'
                }`}
              >
                <span className="font-semibold">{fw.framework_name}</span>
                <span className="font-mono tabular-nums" style={{ color: c }}>{fw.score_percent.toFixed(0)}%</span>
              </button>
            )
          })}
        </div>
      )}

      {/* ── Summary strip + actions ──────────────────────────────────────── */}
      <div className="ops-panel p-5 flex flex-col sm:flex-row sm:items-center gap-5">
        <ScoreGauge score={score} color={scoreColor} />

        <div className="flex-1 grid grid-cols-3 gap-2.5">
          {[
            { label: 'Pass', count: active?.pass_count ?? 0, color: STATUS_COLOR.PASS },
            { label: 'Partial', count: active?.partial_count ?? 0, color: STATUS_COLOR.PARTIAL },
            { label: 'Fail', count: active?.fail_count ?? 0, color: STATUS_COLOR.FAIL },
          ].map(({ label, count, color }) => (
            <div key={label} className="rounded-xl p-3 border bg-deep/50" style={{ borderColor: color + '2E' }}>
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />
                <p className="text-[10px] font-mono uppercase tracking-wider text-text-muted">{label}</p>
              </div>
              <p className="stat-value text-2xl mt-1.5" style={{ color }}>{count}</p>
            </div>
          ))}
          {active?.score_delta != null && active.score_delta !== 0 && (
            <div className="col-span-3 flex items-center gap-1.5 text-[11px] font-mono"
              style={{ color: active.score_delta > 0 ? '#8FBDAD' : '#DB8585' }}>
              {active.score_delta > 0 ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
              {active.score_delta > 0 ? '+' : ''}{active.score_delta.toFixed(1)} pts since last scan
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-1 gap-2 sm:w-48">
          <button
            onClick={() => { void handleDownloadPdf() }}
            disabled={downloading !== null}
            className="btn-sovereign py-2.5 rounded-lg font-semibold text-sm flex items-center justify-center gap-2 disabled:opacity-60"
          >
            {downloading === 'pdf' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            PDF
          </button>
          <button
            onClick={() => { void handleDownloadCsv() }}
            disabled={downloading !== null}
            className="btn-ghost py-2.5 rounded-lg text-sm font-medium text-text-secondary hover:text-text-primary inline-flex items-center justify-center gap-2"
          >
            {downloading === 'csv' ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileSpreadsheet className="w-4 h-4" />}
            CSV
          </button>
          <button
            onClick={() => { void handleDownloadZip() }}
            disabled={downloading !== null}
            className="btn-ghost py-2.5 rounded-lg text-sm font-medium text-text-secondary hover:text-text-primary inline-flex items-center justify-center gap-2"
          >
            {downloading === 'zip' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            Evidence ZIP
          </button>
          <button
            onClick={onStartNew}
            className="btn-ghost py-2.5 rounded-lg text-sm font-medium text-text-secondary hover:text-text-primary inline-flex items-center justify-center gap-2"
          >
            <RotateCcw className="w-3.5 h-3.5" /> New audit
          </button>
        </div>
      </div>

      {downloadError && (
        <p className="text-xs px-3 py-2.5 rounded-lg border border-threat-critical/30 bg-threat-critical/[0.06] text-threat-critical">
          {downloadError}
        </p>
      )}

      {/* ── View switch ──────────────────────────────────────────────────── */}
      <div className="flex gap-1.5">
        {([
          { key: 'controls' as ViewMode, label: 'Control browser', icon: ListChecks },
          { key: 'crosswalk' as ViewMode, label: 'Crosswalk', icon: Network },
        ]).map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setView(key)}
            className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
              view === key ? 'border-indigo-500/50 bg-indigo-500/12 text-indigo-300'
                           : 'border-white/[0.08] bg-white/[0.02] text-text-muted hover:text-text-secondary'
            }`}
          >
            <Icon className="w-3.5 h-3.5" /> {label}
          </button>
        ))}
      </div>

      {view === 'crosswalk' ? (
        <CrosswalkView data={crosswalk} />
      ) : (
        /* ── Master-detail control navigator ──────────────────────────────── */
        <div className="grid grid-cols-1 md:grid-cols-[300px_minmax(0,1fr)] gap-4 md:h-[calc(100vh-22rem)] min-h-[460px]">
          {/* List */}
          <div className="ops-panel flex flex-col overflow-hidden">
            <div className="px-3 py-2.5 border-b border-white/[0.07] flex flex-wrap items-center gap-1.5">
              <ListChecks className="w-3.5 h-3.5 text-text-muted mr-0.5" />
              {filters.map((f) => {
                const fActive = filter === f.key
                return (
                  <button
                    key={f.key}
                    onClick={() => setFilter(f.key)}
                    className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-medium transition-colors ${
                      fActive ? 'border-indigo-500/50 bg-indigo-500/15 text-indigo-300'
                              : 'border-white/[0.08] bg-white/[0.02] text-text-muted hover:text-text-secondary'
                    }`}
                  >
                    {f.color && <span className="w-1.5 h-1.5 rounded-full" style={{ background: f.color }} />}
                    {f.label}<span className="font-mono tabular-nums opacity-70">{f.count}</span>
                  </button>
                )
              })}
            </div>
            <div className="flex-1 overflow-y-auto">
              {visible.length === 0 ? (
                <div className="px-4 py-10 text-center text-sm text-text-muted">No controls match this filter.</div>
              ) : (
                visible.map((r) => {
                  const color = STATUS_COLOR[r.status] ?? '#93A4B5'
                  const sel = r.control_id === selectedId
                  return (
                    <button
                      key={r.control_id}
                      onClick={() => setSelectedId(r.control_id)}
                      className={`relative w-full text-left pl-4 pr-3 py-3 border-b border-white/[0.04] transition-colors ${sel ? 'bg-white/[0.05]' : 'hover:bg-white/[0.025]'}`}
                    >
                      <span className="absolute left-0 top-0 bottom-0 w-[3px]" style={{ background: color, opacity: sel ? 1 : 0.5 }} />
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono text-xs font-semibold text-indigo-300">{r.control_id}</span>
                        <span className="text-[9px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded-full border"
                          style={{ color, backgroundColor: color + '1f', borderColor: color + '3a' }}>
                          {r.status}
                        </span>
                      </div>
                      <div className={`text-xs mt-1 leading-snug ${sel ? 'text-text-primary' : 'text-text-secondary'}`}>{r.control_name}</div>
                    </button>
                  )
                })
              )}
            </div>
          </div>

          {/* Detail */}
          <div className="ops-panel flex flex-col overflow-hidden">
            {!selected ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center px-6">
                <ListChecks className="w-8 h-8 text-text-ghost mb-3" strokeWidth={1.25} />
                <div className="text-sm text-text-secondary">Select a control to inspect its assessment.</div>
              </div>
            ) : (
              <>
                <div className="px-5 pt-5 pb-4 border-b border-white/[0.07]">
                  <div className="flex items-center gap-2 mb-2 flex-wrap">
                    <span className="font-mono text-xs font-semibold text-indigo-300">{selected.control_id}</span>
                    {(() => { const color = STATUS_COLOR[selected.status] ?? '#93A4B5'; return (
                      <span className="text-[10px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full border"
                        style={{ color, backgroundColor: color + '1f', borderColor: color + '3a' }}>
                        {selected.status}
                      </span>
                    )})()}
                    {selected.automatable === false && (
                      <span className="text-[9px] font-mono uppercase tracking-wide px-2 py-0.5 rounded-full border border-white/15 text-text-muted">
                        manual evidence
                      </span>
                    )}
                    <span className="ml-auto font-mono text-[10px] text-text-muted">confidence: {selected.confidence}</span>
                  </div>
                  <h2 className="text-base font-semibold text-text-primary leading-snug">{selected.control_name}</h2>
                  {selected.category && <div className="text-[11px] text-text-muted mt-1">{selected.category}</div>}
                </div>

                <div className="flex-1 overflow-y-auto p-5 space-y-5">
                  <div>
                    <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted mb-1.5">Assessment</div>
                    <p className="text-sm text-text-secondary leading-relaxed">{selected.ai_description}</p>
                  </div>

                  {selected.evidence_references.length > 0 && (
                    <div>
                      <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted mb-1.5">Evidence references</div>
                      <ul className="space-y-1">
                        {selected.evidence_references.map((ref, i) => (
                          <li key={i} className="font-mono text-[11px] text-text-muted flex gap-2"><span className="text-indigo-400/60">·</span>{ref}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div>
                    <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted mb-1.5">Gaps identified</div>
                    {selected.gaps.length > 0 ? (
                      <ul className="space-y-1.5">
                        {selected.gaps.map((g, i) => (
                          <li key={i} className="text-xs flex gap-2 text-threat-critical/90"><AlertOctagon className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />{g}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-[#8FBDAD]">None identified.</p>
                    )}
                  </div>

                  {selected.remediation && (
                    <div className="rounded-lg border border-indigo-500/20 bg-indigo-500/[0.04] p-3">
                      <div className="font-mono text-[10px] uppercase tracking-wider text-indigo-300 mb-1.5 flex items-center gap-1.5">
                        <Wrench className="w-3 h-3" /> Recommended remediation
                      </div>
                      <p className="text-xs text-text-secondary leading-relaxed">{selected.remediation}</p>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      )}

      <p className="flex items-center justify-center gap-1.5 text-xs text-center text-text-muted">
        <FileText className="w-3.5 h-3.5 flex-shrink-0" />
        AI-assisted report. Review by a qualified security professional before submission.
      </p>
    </motion.div>
  )
}

// ── Crosswalk view: one shared signal → controls across frameworks ─────────
function CrosswalkView({ data }: { data: CrosswalkResponse | null }) {
  if (!data) {
    return (
      <div className="ops-panel p-10 flex items-center justify-center text-sm text-text-muted">
        <Loader2 className="w-4 h-4 animate-spin mr-2" /> Building crosswalk…
      </div>
    )
  }
  return (
    <div className="ops-panel overflow-hidden">
      <div className="px-5 py-3.5 border-b border-white/[0.07] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Network className="w-4 h-4 text-indigo-300" />
          <span className="text-sm font-semibold text-text-primary">Evidence crosswalk</span>
        </div>
        {data.reuse_factor != null && (
          <span className="font-mono text-[11px] text-text-muted">
            reuse factor <span className="text-indigo-300 font-semibold">{data.reuse_factor}×</span>
          </span>
        )}
      </div>
      <div className="max-h-[calc(100vh-24rem)] min-h-[400px] overflow-y-auto divide-y divide-white/[0.05]">
        {data.crosswalk.length === 0 ? (
          <div className="px-5 py-10 text-center text-sm text-text-muted">No shared signals for these frameworks.</div>
        ) : (
          data.crosswalk.map((row) => (
            <div key={row.signal} className="px-5 py-3.5">
              <div className="flex items-center justify-between gap-3">
                <span className="font-mono text-xs font-semibold text-indigo-300">{row.signal}</span>
                <span className="text-[10px] font-mono text-text-muted">
                  {row.framework_count} frameworks · {row.control_count} controls
                </span>
              </div>
              <p className="text-[11px] text-text-muted mt-0.5">{row.description}</p>
              <div className="flex flex-wrap gap-1.5 mt-2">
                {row.controls.map((c) => (
                  <span key={`${c.framework_id}-${c.control_id}`}
                    className="inline-flex items-center gap-1 rounded-md border border-white/[0.08] bg-white/[0.02] px-1.5 py-0.5 text-[10px] font-mono text-text-muted">
                    <span className="text-indigo-400/70">{c.framework_id}</span> {c.control_id}
                  </span>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
