// LogRaven — SOC 2 Audit Results (Control Room stage)
//
// Master-detail control navigator: score summary + actions on top, a
// filterable control list on the left, and a control detail pane on the right.

import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Download, Loader2, RotateCcw, FileText, ListChecks, AlertOctagon,
} from 'lucide-react'
import type { AuditStatusResponse, ControlResult } from '../../types/audit'
import { downloadAuditReport } from '../../api/compliance'

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

function sortedResults(results: ControlResult[]): ControlResult[] {
  return [...results].sort((a, b) => (STATUS_ORDER[a.status] ?? 3) - (STATUS_ORDER[b.status] ?? 3))
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
  const [downloading, setDownloading]   = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)
  const [filter, setFilter] = useState<StatusFilter>('ALL')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const controls  = results.results ?? []
  const sorted    = useMemo(() => sortedResults(controls), [controls])
  const passCount = results.pass_count ?? 0
  const failCount = results.fail_count ?? 0
  const partialCount = results.partial_count ?? 0
  const score     = results.score_percent ?? 0
  const company   = results.company_name ?? ''

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

  const selected = visible.find((r) => r.control_id === selectedId) ?? null

  const handleDownload = async () => {
    setDownloading(true)
    setDownloadError(null)
    try {
      const blob = await downloadAuditReport(auditId)
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href     = url
      a.download = `${company.replace(/\s+/g, '_')}_SOC2_Evidence.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      setDownloadError(err instanceof Error ? err.message : 'Download failed')
    } finally {
      setDownloading(false)
    }
  }

  const filters: { key: StatusFilter; label: string; count: number; color?: string }[] = [
    { key: 'ALL',     label: 'All',     count: controls.length },
    { key: 'FAIL',    label: 'Fail',    count: failCount,    color: STATUS_COLOR.FAIL },
    { key: 'PARTIAL', label: 'Partial', count: partialCount, color: STATUS_COLOR.PARTIAL },
    { key: 'PASS',    label: 'Pass',    count: passCount,    color: STATUS_COLOR.PASS },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
      className="space-y-4"
    >
      {/* ── Summary strip + actions ──────────────────────────────────────── */}
      <div className="ops-panel p-5 flex flex-col sm:flex-row sm:items-center gap-5">
        <ScoreGauge score={score} color={scoreColor} />

        <div className="flex-1 grid grid-cols-3 gap-2.5">
          {[
            { label: 'Pass', count: passCount, color: STATUS_COLOR.PASS },
            { label: 'Partial', count: partialCount, color: STATUS_COLOR.PARTIAL },
            { label: 'Fail', count: failCount, color: STATUS_COLOR.FAIL },
          ].map(({ label, count, color }) => (
            <div key={label} className="rounded-xl p-3 border bg-deep/50" style={{ borderColor: color + '2E' }}>
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />
                <p className="text-[10px] font-mono uppercase tracking-wider text-text-muted">{label}</p>
              </div>
              <p className="stat-value text-2xl mt-1.5" style={{ color }}>{count}</p>
            </div>
          ))}
        </div>

        <div className="flex sm:flex-col gap-2 sm:w-44">
          <button
            onClick={() => { void handleDownload() }}
            disabled={downloading}
            className="btn-sovereign flex-1 py-2.5 rounded-lg font-semibold text-sm flex items-center justify-center gap-2 disabled:opacity-60"
          >
            {downloading
              ? <><Loader2 className="w-4 h-4 animate-spin" /> Preparing…</>
              : <><Download className="w-4 h-4" /> Evidence pack</>}
          </button>
          <button
            onClick={onStartNew}
            className="btn-ghost flex-1 py-2.5 rounded-lg text-sm font-medium text-text-secondary hover:text-text-primary inline-flex items-center justify-center gap-2"
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

      {/* ── Master-detail control navigator ──────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-[300px_minmax(0,1fr)] gap-4 md:h-[calc(100vh-20rem)] min-h-[460px]">
        {/* List */}
        <div className="ops-panel flex flex-col overflow-hidden">
          <div className="px-3 py-2.5 border-b border-white/[0.07] flex flex-wrap items-center gap-1.5">
            <ListChecks className="w-3.5 h-3.5 text-text-muted mr-0.5" />
            {filters.map((f) => {
              const active = filter === f.key
              return (
                <button
                  key={f.key}
                  onClick={() => setFilter(f.key)}
                  className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-medium transition-colors ${
                    active ? 'border-indigo-500/50 bg-indigo-500/15 text-indigo-300'
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
                <div className="flex items-center gap-2 mb-2">
                  <span className="font-mono text-xs font-semibold text-indigo-300">{selected.control_id}</span>
                  {(() => { const color = STATUS_COLOR[selected.status] ?? '#93A4B5'; return (
                    <span className="text-[10px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full border"
                      style={{ color, backgroundColor: color + '1f', borderColor: color + '3a' }}>
                      {selected.status}
                    </span>
                  )})()}
                  <span className="ml-auto font-mono text-[10px] text-text-muted">confidence: {selected.confidence}</span>
                </div>
                <h2 className="text-base font-semibold text-text-primary leading-snug">{selected.control_name}</h2>
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
              </div>
            </>
          )}
        </div>
      </div>

      <p className="flex items-center justify-center gap-1.5 text-xs text-center text-text-muted">
        <FileText className="w-3.5 h-3.5 flex-shrink-0" />
        AI-assisted report. Review by a qualified security professional before submission.
      </p>
    </motion.div>
  )
}
