// LogRaven — SOC 2 Audit Results Component
//
// Displays the completed audit: score card, attention section,
// expandable per-control table, and PDF blob download.

import { useState } from 'react'
import type { AuditStatusResponse, ControlResult } from '../../types/audit'
import { downloadAuditReport } from '../../api/compliance'

interface AuditResultsProps {
  results: AuditStatusResponse
  auditId: string
  onStartNew: () => void
}

const STATUS_ORDER: Record<string, number> = { FAIL: 0, PARTIAL: 1, PASS: 2 }
const STATUS_COLOR: Record<string, string> = {
  PASS:    '#3FB950',
  FAIL:    '#F85149',
  PARTIAL: '#D29922',
}

function sortedResults(results: ControlResult[]): ControlResult[] {
  return [...results].sort(
    (a, b) => (STATUS_ORDER[a.status] ?? 3) - (STATUS_ORDER[b.status] ?? 3),
  )
}

export default function AuditResults({ results, auditId, onStartNew }: AuditResultsProps) {
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())
  const [downloading, setDownloading]   = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)

  const controls  = results.results ?? []
  const sorted    = sortedResults(controls)
  const passCount = results.pass_count ?? 0
  const failCount = results.fail_count ?? 0
  const partialCount = results.partial_count ?? 0
  const score     = results.score_percent ?? 0
  const company   = results.company_name ?? ''

  const toggleRow = (controlId: string) => {
    setExpandedRows((prev) => {
      const next = new Set(prev)
      if (next.has(controlId)) {
        next.delete(controlId)
      } else {
        next.add(controlId)
      }
      return next
    })
  }

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

  return (
    <div className="w-full space-y-6">
      {/* ── Header bar ──────────────────────────────────────────────────── */}
      <div
        className="rounded-lg p-5 border flex items-center justify-between gap-4"
        style={{ backgroundColor: '#161B22', borderColor: '#30363D' }}
      >
        <div className="flex items-center gap-3">
          <span
            className="w-8 h-8 flex items-center justify-center rounded-full text-base font-bold flex-shrink-0"
            style={{ backgroundColor: '#3FB950', color: '#0D1117' }}
          >
            ✓
          </span>
          <div>
            <p className="font-semibold text-sm" style={{ color: '#3FB950' }}>
              Audit Complete
            </p>
            <p className="text-xs mt-0.5" style={{ color: '#8B949E' }}>
              {company}
            </p>
          </div>
        </div>
        <button
          onClick={onStartNew}
          className="px-4 py-2 rounded text-sm font-medium border transition-colors hover:opacity-80 flex-shrink-0"
          style={{ borderColor: '#2F81F7', color: '#2F81F7', backgroundColor: 'transparent' }}
        >
          Start New Audit
        </button>
      </div>

      {/* ── Score card ──────────────────────────────────────────────────── */}
      <div
        className="rounded-lg p-6 border"
        style={{ backgroundColor: '#161B22', borderColor: '#30363D' }}
      >
        <div className="flex flex-col items-center mb-6">
          <span className="text-5xl font-bold" style={{ color: '#2F81F7' }}>
            {score.toFixed(1)}%
          </span>
          <span className="text-sm mt-1" style={{ color: '#8B949E' }}>
            Overall Compliance Score
          </span>
        </div>
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: 'PASS',    count: passCount,    color: '#3FB950' },
            { label: 'FAIL',    count: failCount,    color: '#F85149' },
            { label: 'PARTIAL', count: partialCount, color: '#D29922' },
          ].map(({ label, count, color }) => (
            <div
              key={label}
              className="rounded p-4 text-center border"
              style={{ backgroundColor: '#0D1117', borderColor: '#30363D' }}
            >
              <p className="text-2xl font-bold" style={{ color }}>
                {count}
              </p>
              <p className="text-xs font-semibold mt-1" style={{ color }}>
                {label}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Attention Required ──────────────────────────────────────────── */}
      {failCount > 0 && (
        <div
          className="rounded-lg p-5 border"
          style={{ backgroundColor: '#1a0a0a', borderColor: '#F85149' }}
        >
          <p className="text-sm font-semibold mb-3" style={{ color: '#F85149' }}>
            Requires Immediate Attention
          </p>
          <div className="space-y-2">
            {controls
              .filter((r) => r.status === 'FAIL')
              .map((r) => (
                <div key={r.control_id} className="flex gap-2">
                  <span
                    className="text-xs font-mono font-semibold flex-shrink-0 mt-0.5"
                    style={{ color: '#F85149' }}
                  >
                    {r.control_id}
                  </span>
                  <div>
                    <span className="text-xs" style={{ color: '#E6EDF3' }}>
                      {r.control_name}
                    </span>
                    {r.gaps.length > 0 && (
                      <span className="text-xs ml-2" style={{ color: '#8B949E' }}>
                        — {r.gaps[0]}
                      </span>
                    )}
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* ── Control Results table ────────────────────────────────────────── */}
      <div
        className="rounded-lg border overflow-hidden"
        style={{ borderColor: '#30363D' }}
      >
        {/* Table header */}
        <div
          className="grid text-xs font-semibold uppercase tracking-wide px-4 py-3 border-b"
          style={{
            gridTemplateColumns: '90px 1fr 80px 90px 1fr',
            backgroundColor: '#161B22',
            borderColor: '#30363D',
            color: '#8B949E',
          }}
        >
          <span>Control</span>
          <span>Name</span>
          <span>Status</span>
          <span>Confidence</span>
          <span>Summary</span>
        </div>

        {sorted.map((result, idx) => {
          const expanded = expandedRows.has(result.control_id)
          const rowBg    = idx % 2 === 0 ? '#161B22' : '#0D1117'
          const color    = STATUS_COLOR[result.status] ?? '#8B949E'
          const summary  = result.ai_description.length > 100
            ? result.ai_description.slice(0, 100) + '...'
            : result.ai_description

          return (
            <div key={result.control_id} style={{ backgroundColor: rowBg }}>
              {/* Collapsed row */}
              <button
                onClick={() => toggleRow(result.control_id)}
                className="w-full text-left px-4 py-3 grid items-start gap-2 hover:opacity-80 transition-opacity"
                style={{ gridTemplateColumns: '90px 1fr 80px 90px 1fr' }}
              >
                <span className="text-xs font-mono font-semibold" style={{ color: '#2F81F7' }}>
                  {result.control_id}
                </span>
                <span className="text-xs" style={{ color: '#E6EDF3' }}>
                  {result.control_name}
                </span>
                <span>
                  <span
                    className="inline-block px-2 py-0.5 rounded text-xs font-semibold"
                    style={{ backgroundColor: color + '22', color }}
                  >
                    {result.status}
                  </span>
                </span>
                <span className="text-xs" style={{ color: '#8B949E' }}>
                  {result.confidence}
                </span>
                <span className="text-xs" style={{ color: '#8B949E' }}>
                  {expanded ? '▲ collapse' : summary}
                </span>
              </button>

              {/* Expanded detail */}
              {expanded && (
                <div
                  className="px-4 pb-5 pt-1 border-t space-y-4"
                  style={{ borderColor: '#30363D' }}
                >
                  <div>
                    <p className="text-xs font-semibold mb-1" style={{ color: '#2F81F7' }}>
                      Assessment
                    </p>
                    <p className="text-xs leading-relaxed" style={{ color: '#E6EDF3' }}>
                      {result.ai_description}
                    </p>
                  </div>
                  {result.evidence_references.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold mb-1" style={{ color: '#2F81F7' }}>
                        Evidence References
                      </p>
                      <ul className="space-y-1">
                        {result.evidence_references.map((ref, i) => (
                          <li
                            key={`${result.control_id}-ref-${i}`}
                            className="text-xs"
                            style={{ color: '#8B949E' }}
                          >
                            • {ref}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <div>
                    <p className="text-xs font-semibold mb-1" style={{ color: '#2F81F7' }}>
                      Gaps Identified
                    </p>
                    {result.gaps.length > 0 ? (
                      <ul className="space-y-1">
                        {result.gaps.map((g, i) => (
                          <li key={`${result.control_id}-gap-${i}`} className="text-xs flex gap-2" style={{ color: '#F85149' }}>
                            <span>•</span>
                            <span>{g}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs" style={{ color: '#3FB950' }}>
                        None identified
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* ── PDF download ────────────────────────────────────────────────── */}
      <div>
        {downloadError && (
          <p
            className="text-xs mb-3 px-3 py-2 rounded border"
            style={{ color: '#F85149', backgroundColor: '#1a0a0a', borderColor: '#F85149' }}
          >
            {downloadError}
          </p>
        )}
        <button
          onClick={() => { void handleDownload() }}
          disabled={downloading}
          className="w-full py-3 rounded font-medium text-sm flex items-center justify-center gap-2 transition-opacity"
          style={{
            backgroundColor: downloading ? '#4B5563' : '#2F81F7',
            color: '#E6EDF3',
            opacity: downloading ? 0.7 : 1,
            cursor: downloading ? 'not-allowed' : 'pointer',
          }}
        >
          {downloading ? (
            <>
              <span
                className="inline-block w-4 h-4 border-2 border-transparent rounded-full animate-spin"
                style={{ borderTopColor: '#E6EDF3', borderRightColor: '#E6EDF3' }}
              />
              Downloading...
            </>
          ) : (
            'Download Evidence Package (PDF)'
          )}
        </button>
      </div>

      {/* ── Disclaimer ──────────────────────────────────────────────────── */}
      <p className="text-xs text-center pb-2" style={{ color: '#8B949E' }}>
        This report is AI-assisted. All findings should be reviewed by a qualified security
        professional before submission to a certification body.
      </p>
    </div>
  )
}
