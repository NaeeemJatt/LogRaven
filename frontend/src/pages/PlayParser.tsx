// LogRaven — PlayParser sandbox (compare parsers + quality scores, no investigations DB)
import React, { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronDown, ChevronLeft, ChevronRight, FlaskConical, Loader2, Sparkles } from 'lucide-react'
import Navbar from '../components/layout/Navbar'
import type { AxiosError } from 'axios'
import {
  playParserApi,
  type PlayParserDetectCandidate,
  type PlayParserEvaluateItem,
} from '../api/playParser'

const PARSER_OPTIONS: { key: string; label: string }[] = [
  { key: 'windows_event', label: 'Windows EVTX' },
  { key: 'syslog', label: 'Syslog' },
  { key: 'cloudtrail', label: 'CloudTrail (JSON)' },
  { key: 'nginx', label: 'Nginx / Apache' },
  { key: 'iis', label: 'IIS W3C' },
]

function requestedUrl(ax: AxiosError): string {
  const cfg = ax.config
  if (!cfg?.url) return '(unknown)'
  const b = (cfg.baseURL || '').replace(/\/+$/, '')
  const p = cfg.url.startsWith('/') ? cfg.url : `/${cfg.url}`
  return b ? `${b}${p}` : p
}

/** FastAPI uses string detail or an array of { loc, msg, type } for 422. */
function formatFastApiDetail(detail: unknown): string | null {
  if (detail == null) return null
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const parts = detail.map((item) => {
      if (item && typeof item === 'object' && 'msg' in item) {
        const o = item as { loc?: unknown[]; msg: string }
        const loc = Array.isArray(o.loc) ? o.loc.join('.') : ''
        return loc ? `${loc}: ${o.msg}` : o.msg
      }
      return typeof item === 'string' ? item : JSON.stringify(item)
    })
    return parts.length ? parts.join('; ') : null
  }
  if (typeof detail === 'object') return JSON.stringify(detail)
  return String(detail)
}

function apiErrorMessage(err: unknown): string {
  if (!err || typeof err !== 'object') return 'Request failed.'
  const ax = err as AxiosError<Record<string, unknown>>
  const res = ax.response
  const url = requestedUrl(ax)

  if (!res) {
    return (
      `${ax.message || 'Network error'}${ax.code ? ` (${ax.code})` : ''}. ` +
      `Request: ${url}. ` +
      'Ensure the API is running (e.g. uvicorn on 127.0.0.1:8000). With Vite dev, check VITE_DEV_API_PROXY_TARGET matches that host.'
    )
  }

  const status = res.status
  const data = res.data

  if (status === 404) {
    return (
      `PlayParser API not found (404) for ${url}. ` +
      'Set VITE_API_URL to the API root only (e.g. http://127.0.0.1:8000): do not append /api or /api/v1, or leave it empty to use the Vite dev proxy. ' +
      'Restart the API after pulling updates, then open GET /api/v1/play-parser/meta on that host.'
    )
  }

  if (status === 429) {
    const fromBody =
      data && typeof data === 'object'
        ? formatFastApiDetail(data.detail) || (typeof data.error === 'string' ? data.error : null)
        : null
    return fromBody || 'Too many PlayParser requests (rate limit). Wait and retry, or run fewer comparisons.'
  }

  if (data && typeof data === 'object') {
    const d = formatFastApiDetail(data.detail)
    if (d) return d
    if (typeof data.error === 'string') return data.error
    if (typeof data.message === 'string') return data.message
  }

  const text = res.statusText?.trim()
  return text ? `${text} (${status}) — ${url}` : `HTTP ${status} — ${url}`
}

export default function PlayParser() {
  const [file, setFile] = useState<File | null>(null)
  const [selected, setSelected] = useState<Record<string, boolean>>({})
  const [loading, setLoading] = useState(false)
  const [detectLoading, setDetectLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [results, setResults] = useState<PlayParserEvaluateItem[] | null>(null)
  const [hints, setHints] = useState<PlayParserDetectCandidate[] | null>(null)
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})

  const selectedKeys = useMemo(
    () => PARSER_OPTIONS.filter((p) => selected[p.key]).map((p) => p.key),
    [selected],
  )

  const toggleParser = (key: string) => {
    setSelected((s) => ({ ...s, [key]: !s[key] }))
  }

  const runComparison = async () => {
    setError(null)
    setResults(null)
    if (!file) {
      setError('Choose a log file first.')
      return
    }
    if (selectedKeys.length === 0) {
      setError('Select at least one parser.')
      return
    }
    setLoading(true)
    try {
      const res = await playParserApi.evaluate(file, selectedKeys)
      setResults(res.data.results)
    } catch (e: unknown) {
      setError(apiErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  const runDetectorHint = async () => {
    setError(null)
    setHints(null)
    if (!file) {
      setError('Choose a log file first.')
      return
    }
    setDetectLoading(true)
    try {
      const res = await playParserApi.detect(file)
      setHints(res.data.candidates)
    } catch (e: unknown) {
      setError(apiErrorMessage(e))
    } finally {
      setDetectLoading(false)
    }
  }

  const inputClass =
    'w-full rounded-lg bg-raven-900 border border-raven-600 text-raven-200 text-sm px-3 py-2.5 font-mono focus:outline-none focus:border-electric-500 focus:ring-1 focus:ring-electric-500/30 transition-colors file:mr-3 file:rounded file:border-0 file:bg-raven-800 file:px-3 file:py-1 file:text-xs file:text-raven-300'

  return (
    <div className="min-h-screen bg-raven-950 text-raven-200">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1 text-sm text-raven-500 hover:text-electric-400 transition-colors mb-8"
        >
          <ChevronLeft className="h-4 w-4" />
          Dashboard
        </Link>

        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <FlaskConical className="h-7 w-7 text-electric-400" strokeWidth={1.75} aria-hidden />
              <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">PlayParser</h1>
            </div>
            <p className="text-raven-500 text-sm max-w-2xl">
              Upload one file and run the same parsers the investigation pipeline uses. Compare event counts and
              heuristic quality scores before you commit to a full investigation.
            </p>
            <p className="text-amber-500/90 text-xs mt-2 font-mono">
              Tip: .evtx is binary and only meaningful for the Windows EVTX parser; other parsers may score low or error.
            </p>
          </div>
        </div>

        <div className="rounded-xl border border-raven-700 bg-raven-900/80 p-6 sm:p-8 shadow-lg shadow-black/20 space-y-6">
          <div>
            <label className="block text-[11px] font-semibold uppercase tracking-[0.15em] text-raven-500 mb-1.5">
              Log file
            </label>
            <input
              type="file"
              accept=".evtx,.log,.csv,.json,.txt"
              className={inputClass}
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null)
                setResults(null)
                setHints(null)
              }}
            />
            <p className="text-raven-600 text-xs mt-1.5">
              Allowed: .evtx, .log, .csv, .json, .txt (same as investigations). Size follows your account tier.
            </p>
          </div>

          <div>
            <span className="block text-[11px] font-semibold uppercase tracking-[0.15em] text-raven-500 mb-2">
              Parsers to compare
            </span>
            <div className="flex flex-wrap gap-3">
              {PARSER_OPTIONS.map((p) => (
                <label
                  key={p.key}
                  className="inline-flex items-center gap-2 rounded-lg border border-raven-600 bg-raven-950/50 px-3 py-2 cursor-pointer hover:border-electric-500/40 transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={!!selected[p.key]}
                    onChange={() => toggleParser(p.key)}
                    className="rounded border-raven-600 text-electric-500 focus:ring-electric-500/30"
                  />
                  <span className="text-sm text-raven-200">{p.label}</span>
                  <span className="text-[10px] font-mono text-raven-600">{p.key}</span>
                </label>
              ))}
            </div>
          </div>

          {error && (
            <p className="text-rose-400 text-xs font-mono border border-rose-900/50 bg-rose-950/30 px-3 py-2 rounded-lg">
              {error}
            </p>
          )}

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              disabled={loading}
              onClick={() => void runComparison()}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-electric-600 hover:bg-electric-500 disabled:opacity-50 text-white text-sm font-semibold px-5 py-2.5 transition-colors"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Run comparison
            </button>
            <button
              type="button"
              disabled={detectLoading}
              onClick={() => void runDetectorHint()}
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-raven-600 bg-raven-950 hover:bg-raven-800 disabled:opacity-50 text-raven-200 text-sm font-medium px-5 py-2.5 transition-colors"
            >
              {detectLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4 text-amber-400" />
              )}
              Detector hint
            </button>
          </div>

          {hints && hints.length > 0 && (
            <div className="rounded-lg border border-raven-700 bg-raven-950/60 p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-raven-500 mb-2">Suggested log types</h3>
              <ul className="space-y-2 text-sm">
                {hints.map((h) => (
                  <li key={`${h.log_type}-${h.confidence}`} className="flex flex-wrap items-baseline gap-2">
                    <span className="font-mono text-electric-400">{h.log_type}</span>
                    <span className="text-raven-500">confidence {(h.confidence * 100).toFixed(0)}%</span>
                    {h.reasons?.length ? (
                      <span className="text-raven-600 text-xs">— {h.reasons.join('; ')}</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {results && results.length > 0 && (
          <div className="mt-10 overflow-x-auto rounded-xl border border-raven-700 bg-raven-900/40">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-raven-700 text-left text-[11px] uppercase tracking-wider text-raven-500">
                  <th className="px-4 py-3 font-semibold">Parser</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                  <th className="px-4 py-3 font-semibold tabular-nums">Events</th>
                  <th className="px-4 py-3 font-semibold tabular-nums">Score</th>
                  <th className="px-4 py-3 font-semibold">Warnings</th>
                  <th className="px-4 py-3 font-semibold w-10" />
                </tr>
              </thead>
              <tbody>
                {results.map((row) => (
                  <React.Fragment key={row.parser_key}>
                    <tr className="border-b border-raven-800/80 hover:bg-white/[0.02]">
                      <td className="px-4 py-3 font-mono text-raven-200">{row.parser_key}</td>
                      <td className="px-4 py-3">
                        {row.ok ? (
                          <span className="text-emerald-400 text-xs font-semibold">OK</span>
                        ) : (
                          <span className="text-rose-400 text-xs font-semibold">Error</span>
                        )}
                      </td>
                      <td className="px-4 py-3 tabular-nums text-raven-300">
                        {row.event_count}
                        {row.events_trimmed ? (
                          <span className="block text-[10px] text-amber-500/90">trimmed to cap</span>
                        ) : null}
                      </td>
                      <td className="px-4 py-3 tabular-nums text-raven-200">
                        {row.quality ? (row.quality.score * 100).toFixed(1) + '%' : '—'}
                        {row.quality ? (
                          <span className="block text-[10px] text-raven-600 font-normal">
                            ts {(row.quality.valid_timestamp_ratio * 100).toFixed(0)}% · struct{' '}
                            {(row.quality.structured_ratio * 100).toFixed(0)}%
                          </span>
                        ) : null}
                      </td>
                      <td className="px-4 py-3 text-xs text-raven-500 max-w-xs">
                        {row.quality?.warnings?.length
                          ? row.quality.warnings.join(', ')
                          : row.error ?? '—'}
                      </td>
                      <td className="px-4 py-3">
                        {row.ok && row.sample_events?.length ? (
                          <button
                            type="button"
                            className="p-1 rounded text-raven-500 hover:text-electric-400"
                            aria-expanded={!!expanded[row.parser_key]}
                            onClick={() =>
                              setExpanded((e) => ({ ...e, [row.parser_key]: !e[row.parser_key] }))
                            }
                          >
                            {expanded[row.parser_key] ? (
                              <ChevronDown className="h-4 w-4" />
                            ) : (
                              <ChevronRight className="h-4 w-4" />
                            )}
                          </button>
                        ) : null}
                      </td>
                    </tr>
                    {expanded[row.parser_key] && row.sample_events?.length ? (
                      <tr className="bg-raven-950/80 border-b border-raven-800/80">
                        <td colSpan={6} className="px-4 py-3">
                          <pre className="text-[11px] font-mono text-raven-400 overflow-x-auto max-h-64 overflow-y-auto whitespace-pre-wrap break-all">
                            {JSON.stringify(row.sample_events, null, 2)}
                          </pre>
                        </td>
                      </tr>
                    ) : null}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  )
}
