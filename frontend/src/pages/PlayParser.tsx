// LogRaven — PlayParser sandbox (compare parsers + quality scores, no investigations DB)
import React, { useEffect, useId, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Sparkles,
  WifiOff,
} from 'lucide-react'
import type { AxiosError } from 'axios'
import {
  playParserApi,
  type PlayParserDetectCandidate,
  type PlayParserEvaluateCompareResponse,
  type PlayParserEvaluateItem,
  type PlayParserPreviewMatch,
  type PlayParserPreviewResponse,
  type PlayParserRunMode,
} from '../api/playParser'
import { PlayParserAlert } from './playParser/PlayParserAlert'
import {
  playFocusRing,
  playPageBg,
  playPageGrid,
  playPanel,
  playSection,
  playSectionTitle,
  playSubsectionTitle,
} from './playParser/playParserClasses'

const DECODERS_NOT_APPLICABLE_CODE = 'DECODERS_NOT_APPLICABLE'
const PREVIEW_TARGET_DECODER = 'decoder'

const PARSER_OPTIONS: { key: string; label: string }[] = [
  { key: 'windows_event', label: 'Windows EVTX' },
  { key: 'syslog', label: 'Syslog' },
  { key: 'cloudtrail', label: 'CloudTrail (JSON)' },
  { key: 'nginx', label: 'Nginx / Apache' },
  { key: 'iis', label: 'IIS W3C' },
]

const RUN_MODE_OPTIONS: {
  v: PlayParserRunMode
  label: string
  description: string
}[] = [
  { v: 'parsers_only', label: 'Parsers only', description: 'Native parsers only' },
  { v: 'decoders_only', label: 'Decoders only', description: 'Decoder manager only' },
  { v: 'both', label: 'Side-by-side', description: 'Compare both paths' },
]

const COMPARE_SOURCE_TYPES = [
  { value: 'linux_endpoint', label: 'Linux endpoint' },
  { value: 'windows_endpoint', label: 'Windows endpoint' },
  { value: 'web_server', label: 'Web server' },
  { value: 'cloudtrail', label: 'CloudTrail' },
  { value: 'firewall', label: 'Firewall' },
  { value: 'network', label: 'Network' },
] as const

const EVTX_DECODERS_HINT_ID = 'playparser-evtx-decoders-hint'

const EVTX_FORMAT_TOOLTIP =
  '.evtx is binary and only meaningful for the Windows EVTX parser; other parsers may score low or error.'

const MATCH_HELP: Record<PlayParserPreviewMatch, string> = {
  exact: 'Parsed output aligns with the raw line for this row.',
  substring: 'Parsed text appears as a substring of the raw line.',
  index: 'Paired by line index only; content alignment may be weak.',
  none: 'No strong alignment signal for this row.',
}

function matchBadgeClass(m: PlayParserPreviewMatch): string {
  const base = 'inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide'
  switch (m) {
    case 'exact':
      return `${base} bg-emerald-500/15 text-emerald-300 border border-emerald-500/25`
    case 'substring':
      return `${base} bg-slate-500/20 text-slate-300 border border-slate-500/30`
    case 'index':
      return `${base} bg-play-warm/15 text-play-warm-bright border border-play-warm/30`
    default:
      return `${base} bg-play-surface-2 text-play-muted border border-play-border`
  }
}

function requestedUrl(ax: AxiosError): string {
  const cfg = ax.config
  if (!cfg?.url) return '(unknown)'
  const b = (cfg.baseURL || '').replace(/\/+$/, '')
  const p = cfg.url.startsWith('/') ? cfg.url : `/${cfg.url}`
  return b ? `${b}${p}` : p
}

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

function previewNoteVariant(note: string): 'warning' | 'info' {
  const lower = note.toLowerCase()
  if (
    lower.includes('unreachable') ||
    lower.includes('error') ||
    lower.includes('failed') ||
    lower.includes('warn')
  ) {
    return 'warning'
  }
  return 'info'
}

function formatJsonTinted(json: string): React.ReactNode {
  return json.split(/("[^"]*"\s*:)/g).map((part, i) => {
    if (/^"[^"]*"\s*:$/.test(part)) {
      return (
        <span key={i} className="text-teal-300/95">
          {part}
        </span>
      )
    }
    return <span key={i}>{part}</span>
  })
}

export default function PlayParser() {
  const fileInputId = useId()
  const [file, setFile] = useState<File | null>(null)
  const [selected, setSelected] = useState<Record<string, boolean>>({})
  const [runLoading, setRunLoading] = useState(false)
  const [detectLoading, setDetectLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [results, setResults] = useState<PlayParserEvaluateItem[] | null>(null)
  const [hints, setHints] = useState<PlayParserDetectCandidate[] | null>(null)
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const [compareResults, setCompareResults] = useState<PlayParserEvaluateCompareResponse | null>(null)
  const [playMode, setPlayMode] = useState<PlayParserRunMode>('both')
  const [lastRunMode, setLastRunMode] = useState<PlayParserRunMode | null>(null)
  const [compareSourceType, setCompareSourceType] = useState<string>('linux_endpoint')
  const [previewActive, setPreviewActive] = useState<string | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState<string | null>(null)
  const [previewPayload, setPreviewPayload] = useState<PlayParserPreviewResponse | null>(null)
  const [dropActive, setDropActive] = useState(false)
  const [evtxDecodersTooltipOpen, setEvtxDecodersTooltipOpen] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const isEvtxFile = useMemo(
    () => !!(file?.name && file.name.toLowerCase().endsWith('.evtx')),
    [file],
  )

  useEffect(() => {
    if (!isEvtxFile) return
    setPlayMode((m) => (m === 'decoders_only' ? 'parsers_only' : m))
  }, [isEvtxFile])

  useEffect(() => {
    if (!isEvtxFile) setEvtxDecodersTooltipOpen(false)
  }, [isEvtxFile])

  const selectedKeys = useMemo(
    () => PARSER_OPTIONS.filter((p) => selected[p.key]).map((p) => p.key),
    [selected],
  )

  const toggleParser = (key: string) => {
    setSelected((s) => ({ ...s, [key]: !s[key] }))
  }

  const clearPreview = () => {
    setPreviewActive(null)
    setPreviewPayload(null)
    setPreviewError(null)
  }

  const onFileChosen = (f: File | null) => {
    setFile(f)
    setResults(null)
    setHints(null)
    setCompareResults(null)
    setLastRunMode(null)
    clearPreview()
  }

  const runPlay = async () => {
    setError(null)
    setResults(null)
    setCompareResults(null)
    clearPreview()
    if (!file) {
      setError('Choose a log file first.')
      return
    }
    if (playMode !== 'decoders_only' && selectedKeys.length === 0) {
      setError('Select at least one parser.')
      return
    }

    const keys = playMode === 'decoders_only' ? [] : selectedKeys

    setRunLoading(true)
    try {
      const res = await playParserApi.evaluateCompare(file, keys, {
        sourceType: compareSourceType,
        includeDecoders: playMode === 'both',
        playMode,
      })
      setLastRunMode(playMode)
      if (playMode === 'parsers_only') {
        setResults(res.data.parser_results)
        setCompareResults(null)
      } else if (playMode === 'decoders_only') {
        setCompareResults(res.data)
        setResults(null)
      } else {
        setCompareResults(res.data)
        setResults(res.data.parser_results)
      }
    } catch (e: unknown) {
      setError(apiErrorMessage(e))
      setLastRunMode(null)
    } finally {
      setRunLoading(false)
    }
  }

  const loadPreview = async (target: string) => {
    if (!file) {
      setError('Choose a log file first.')
      return
    }
    setPreviewActive(target)
    setPreviewLoading(true)
    setPreviewError(null)
    setPreviewPayload(null)
    try {
      const res = await playParserApi.preview(file, target, {
        sourceType: compareSourceType,
        lineLimit: 50,
      })
      setPreviewPayload(res.data)
    } catch (e: unknown) {
      setPreviewError(apiErrorMessage(e))
      setPreviewActive(null)
    } finally {
      setPreviewLoading(false)
    }
  }

  const showDecoderPreviewButton =
    !!compareResults &&
    lastRunMode != null &&
    (lastRunMode === 'both' || lastRunMode === 'decoders_only') &&
    compareResults.decoders.manager_reachable &&
    !compareResults.decoders.warning_codes?.includes(DECODERS_NOT_APPLICABLE_CODE)

  const showParserPreviewButtons = lastRunMode === 'parsers_only' || lastRunMode === 'both'

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

  const compareIdle =
    !compareResults ||
    !(lastRunMode === 'both' || lastRunMode === 'decoders_only')

  const compareStatusLabel =
    compareIdle ? 'Decoders idle' : lastRunMode === 'both' && compareResults?.compare ? 'Compared' : 'Decoders run'

  return (
    <div className={`${playPageBg} relative pt-16`}>
      <div
        className={`pointer-events-none absolute inset-0 z-0 opacity-[0.28] ${playPageGrid}`}
        aria-hidden
      />
      <div className="relative z-10">
        <main className="px-4 sm:px-6 lg:px-8 py-8">
          <span id={EVTX_DECODERS_HINT_ID} className="sr-only">
            {EVTX_FORMAT_TOOLTIP}
          </span>
          <div className="flex flex-wrap items-start justify-between gap-4 mb-10">
            <header className="min-w-0 max-w-3xl flex-1 space-y-4">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <h1 className="text-3xl sm:text-4xl font-bold tracking-tight font-play bg-gradient-to-r from-white via-teal-100 to-cyan-200/90 bg-clip-text text-transparent drop-shadow-[0_0_20px_rgba(45,212,191,0.15)]">
                  PlayParser
                </h1>
                <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-teal-400/80">
                  SANDBOX
                </span>
              </div>
              <p className="text-play-muted text-sm leading-relaxed">
                Choose parsers only, decoders only, or both. Inspect summary metrics, then open line-by-line raw vs parsed
                previews for each parser or decoders (PlayParser sandbox only).
              </p>
            </header>
            <Link
              to="/dashboard"
              className={`group inline-flex shrink-0 items-center gap-2 rounded-full border border-teal-500/30 bg-teal-950/25 px-3 py-1.5 text-sm text-teal-100/80 hover:text-teal-200 hover:border-teal-400/50 hover:bg-teal-900/35 ${playFocusRing} transition-colors duration-150 motion-reduce:transition-none`}
            >
              <span className="flex h-7 w-7 items-center justify-center rounded-full border border-teal-400/35 bg-teal-950/50 text-teal-300 group-hover:border-teal-300/60 group-hover:text-teal-200">
                <ChevronLeft className="h-4 w-4" aria-hidden />
              </span>
              Dashboard
            </Link>
          </div>

          <div className="space-y-6">
            <div className="grid grid-cols-1 min-w-0 gap-6 lg:grid-cols-[minmax(0,13fr)_minmax(0,7fr)] lg:gap-8 items-start">
              <div className={`${playPanel} min-w-0 overflow-hidden`}>
                <div className={`${playSection} flex flex-col gap-4`}>
                  <div>
                    <label htmlFor={fileInputId} className={playSubsectionTitle}>
                      Log file
                    </label>
                    <input
                      ref={fileInputRef}
                      id={fileInputId}
                      type="file"
                      accept=".evtx,.log,.csv,.json,.txt"
                      className="sr-only"
                      onChange={(e) => onFileChosen(e.target.files?.[0] ?? null)}
                    />
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      onDragEnter={(e) => {
                        e.preventDefault()
                        setDropActive(true)
                      }}
                      onDragOver={(e) => {
                        e.preventDefault()
                        setDropActive(true)
                      }}
                      onDragLeave={() => setDropActive(false)}
                      onDrop={(e) => {
                        e.preventDefault()
                        setDropActive(false)
                        const f = e.dataTransfer.files?.[0]
                        if (f) onFileChosen(f)
                      }}
                      className={`w-full rounded-xl border-2 border-dashed px-4 py-8 text-left transition-colors duration-150 motion-reduce:transition-none ${playFocusRing} ${
                        dropActive
                          ? 'border-teal-400/70 bg-teal-500/15 shadow-[inset_0_0_40px_rgba(45,212,191,0.08)]'
                          : 'border-teal-600/40 bg-teal-950/20 hover:border-teal-500/55 hover:bg-teal-900/25'
                      }`}
                    >
                      <p className="text-sm text-play-fg font-medium">
                        {file ? (
                          <span
                            className="font-play-mono text-teal-300 truncate block max-w-full"
                            title={file.name}
                          >
                            {file.name}
                          </span>
                        ) : (
                          <>Drop a log here or click to browse</>
                        )}
                      </p>
                      <p className="text-play-muted text-xs mt-2">
                        Allowed: .evtx, .log, .csv, .json, .txt (same as investigations). Size follows your account tier.
                      </p>
                    </button>
                  </div>

                  <div>
                    <span className={playSectionTitle}>Parsers to compare</span>
                  {playMode === 'decoders_only' ? (
                    <PlayParserAlert variant="info" title="Parsers disabled" className="mb-4">
                      In decoders-only mode, native parsers are not run. Switch mode if you need parser quality scores.
                    </PlayParserAlert>
                  ) : null}
                  <div
                    className={`grid grid-cols-1 min-w-0 sm:grid-cols-2 gap-2 ${playMode === 'decoders_only' ? 'opacity-45 pointer-events-none' : ''}`}
                    aria-disabled={playMode === 'decoders_only'}
                  >
                    {PARSER_OPTIONS.map((p) => {
                      const on = !!selected[p.key]
                      return (
                        <button
                          key={p.key}
                          type="button"
                          disabled={playMode === 'decoders_only'}
                          aria-pressed={on}
                          onClick={() => toggleParser(p.key)}
                          className={`inline-flex w-full min-w-0 items-center gap-2 rounded-lg border px-3 py-2 text-left text-sm transition-colors duration-150 motion-reduce:transition-none ${playFocusRing} disabled:cursor-not-allowed ${
                            on
                              ? 'border-teal-400/55 bg-teal-900/35 text-teal-50 shadow-[0_0_16px_-6px_rgba(45,212,191,0.25)]'
                              : 'border-slate-600/45 bg-slate-900/35 text-slate-300 hover:border-teal-700/50 hover:bg-slate-800/45'
                          }`}
                        >
                          <span
                            className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border ${
                              on ? 'border-teal-300 bg-teal-500/30 text-teal-200' : 'border-slate-500 bg-slate-800/80'
                            }`}
                            aria-hidden
                          >
                            {on ? <Check className="h-3 w-3" strokeWidth={3} /> : null}
                          </span>
                          <span className="min-w-0 truncate text-play-fg">{p.label}</span>
                          <span className="font-play-mono text-[10px] text-play-subtle shrink-0">{p.key}</span>
                        </button>
                      )
                    })}
                  </div>
                  </div>
                </div>
              </div>

              <div className={`${playPanel} min-w-0 overflow-hidden flex flex-col`}>
                <div className={`${playSection} flex flex-col gap-4`}>
                  <div>
                    <span className={playSectionTitle}>Run mode</span>
                    <div className="flex flex-col gap-2">
                      {RUN_MODE_OPTIONS.map((opt) => {
                        const active = playMode === opt.v
                        const blockedEvtxDecoders = isEvtxFile && opt.v === 'decoders_only'
                        const modeButton = (
                          <button
                            type="button"
                            disabled={blockedEvtxDecoders}
                            aria-describedby={blockedEvtxDecoders ? EVTX_DECODERS_HINT_ID : undefined}
                            onClick={() => {
                              if (!blockedEvtxDecoders) setPlayMode(opt.v)
                            }}
                            className={`rounded-xl border px-3 py-3 text-left w-full transition-all duration-150 motion-reduce:transition-none ${playFocusRing} ${
                              active
                                ? 'border-teal-400/60 bg-gradient-to-br from-teal-900/50 to-cyan-950/30 shadow-[0_0_20px_-8px_rgba(45,212,191,0.35)]'
                                : 'border-slate-600/50 bg-slate-900/40 hover:border-teal-600/40 hover:bg-slate-800/50'
                            } ${blockedEvtxDecoders ? 'opacity-45 cursor-not-allowed pointer-events-none' : ''}`}
                          >
                            <span className="block text-sm font-semibold text-play-fg">{opt.label}</span>
                            <span className="block text-xs text-play-muted mt-0.5">{opt.description}</span>
                          </button>
                        )

                        if (opt.v === 'decoders_only') {
                          return (
                            <div
                              key={opt.v}
                              className="relative w-full"
                              onMouseEnter={() => {
                                if (isEvtxFile) setEvtxDecodersTooltipOpen(true)
                              }}
                              onMouseLeave={() => setEvtxDecodersTooltipOpen(false)}
                            >
                              {modeButton}
                              {isEvtxFile && evtxDecodersTooltipOpen ? (
                                <div
                                  role="tooltip"
                                  className="absolute left-0 right-0 top-full z-50 mt-1.5 rounded-lg border border-cyan-500/40 bg-slate-900/95 px-3 py-2.5 text-xs text-teal-50/95 shadow-[0_8px_30px_-8px_rgba(0,0,0,0.6)] ring-1 ring-teal-400/15 backdrop-blur-sm pointer-events-none"
                                >
                                  <span className="font-play-mono text-[11px] text-cyan-100/90 leading-relaxed block">
                                    {EVTX_FORMAT_TOOLTIP}
                                  </span>
                                </div>
                              ) : null}
                            </div>
                          )
                        }

                        return <React.Fragment key={opt.v}>{modeButton}</React.Fragment>
                      })}
                    </div>
                  </div>

                  {(playMode === 'decoders_only' || playMode === 'both') && (
                    <div className="space-y-2">
                      <span className={playSubsectionTitle}>Source type (for decoders)</span>
                      <div className="relative w-full max-w-md">
                        <select
                          value={compareSourceType}
                          onChange={(e) => setCompareSourceType(e.target.value)}
                          className={`w-full appearance-none rounded-xl border border-cyan-600/35 bg-slate-900/80 pl-3 pr-10 py-2.5 text-sm text-cyan-50 font-play-mono ${playFocusRing} transition-colors hover:border-cyan-400/45 hover:bg-slate-900`}
                        >
                          {COMPARE_SOURCE_TYPES.map((o) => (
                            <option key={o.value} value={o.value}>
                              {o.label}
                            </option>
                          ))}
                        </select>
                        <ChevronDown
                          className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-cyan-400/80"
                          aria-hidden
                        />
                      </div>
                    </div>
                  )}

                  <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
                    <button
                      type="button"
                      disabled={runLoading}
                      onClick={() => void runPlay()}
                      title="Run evaluation (keyboard: focus this control and press Enter)"
                      className={`inline-flex min-w-[8.5rem] w-full sm:w-auto items-center justify-center gap-2 rounded-xl bg-teal-500 px-5 py-2.5 text-sm font-bold text-slate-950 shadow-[0_4px_24px_-4px_rgba(45,212,191,0.55)] hover:bg-teal-400 active:bg-teal-600 disabled:opacity-50 ${playFocusRing} transition-colors duration-150 motion-reduce:transition-none`}
                    >
                      {runLoading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
                      {runLoading ? 'Running…' : 'Run'}
                    </button>
                    <button
                      type="button"
                      disabled={detectLoading}
                      onClick={() => void runDetectorHint()}
                      className={`inline-flex w-full sm:w-auto items-center justify-center gap-2 rounded-xl border border-amber-500/35 bg-amber-950/20 px-5 py-2.5 text-sm font-medium text-amber-100/90 hover:bg-amber-950/40 hover:border-amber-400/45 disabled:opacity-50 ${playFocusRing} transition-colors duration-150 motion-reduce:transition-none`}
                    >
                      {detectLoading ? (
                        <Loader2 className="h-4 w-4 animate-spin text-play-accent" aria-hidden />
                      ) : (
                        <Sparkles className="h-4 w-4 text-play-warm-bright" aria-hidden />
                      )}
                      Detector hint
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {error || (hints && hints.length > 0) ? (
              <div className={`${playPanel} overflow-hidden`}>
                {error ? (
                  <div className={playSection}>
                    <PlayParserAlert
                      variant="danger"
                      title="Something went wrong"
                      onDismiss={() => setError(null)}
                      collapsibleDetail={error.length > 200 ? error : undefined}
                    >
                      {error.length > 200 ? `${error.slice(0, 200).trim()}…` : error}
                    </PlayParserAlert>
                  </div>
                ) : null}
                {hints && hints.length > 0 ? (
                  <div className={`${playSection} ${error ? 'border-t border-play-border/60' : ''}`}>
                    <PlayParserAlert variant="info" title="Suggested log types">
                      <ul className="space-y-3">
                        {hints.map((h) => (
                          <li
                            key={`${h.log_type}-${h.confidence}-${h.reasons?.join(',')}`}
                            className="rounded-lg border border-teal-600/30 bg-slate-900/60 px-3 py-2"
                          >
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="rounded-md border border-teal-400/40 bg-teal-950/50 px-2 py-0.5 font-play-mono text-xs text-teal-200">
                                {h.log_type}
                              </span>
                              <span className="text-xs text-cyan-200/70 tabular-nums">
                                {(h.confidence * 100).toFixed(0)}% confidence
                              </span>
                            </div>
                            <div className="mt-2 h-1.5 w-full max-w-xs overflow-hidden rounded-full bg-slate-700/80">
                              <div
                                className="h-full rounded-full bg-gradient-to-r from-teal-600 to-cyan-400 transition-[width] duration-200 motion-reduce:transition-none"
                                style={{ width: `${Math.round(h.confidence * 100)}%` }}
                              />
                            </div>
                            {h.reasons?.length ? (
                              <p className="mt-2 text-xs text-play-subtle leading-relaxed">{h.reasons.join('; ')}</p>
                            ) : null}
                          </li>
                        ))}
                      </ul>
                    </PlayParserAlert>
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>

          {compareResults && (lastRunMode === 'both' || lastRunMode === 'decoders_only') && (
            <section className={`${playPanel} mt-10 overflow-hidden`} aria-labelledby="compare-heading">
              <div className={`${playSection} flex flex-wrap items-center justify-between gap-3 border-b border-teal-500/20`}>
                <h2 id="compare-heading" className="text-lg font-semibold font-play text-teal-50">
                  {lastRunMode === 'decoders_only' ? 'Decoders result' : 'Parsers vs decoders'}
                </h2>
                <span className="rounded-full border border-cyan-500/35 bg-cyan-950/40 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-cyan-200">
                  {compareStatusLabel}
                </span>
              </div>
              <div className={`${playSection} grid sm:grid-cols-2 gap-4`}>
                <div className="rounded-xl border border-teal-600/25 bg-gradient-to-br from-teal-950/30 to-slate-900/50 p-4 space-y-3">
                  <p className={playSubsectionTitle}>Decoder status</p>
                  {!compareResults.decoders.manager_reachable ? (
                    <div className="flex items-center gap-2 text-amber-300">
                      <WifiOff className="h-5 w-5 shrink-0" aria-hidden />
                      <span className="text-sm font-medium">Manager unreachable</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-emerald-400">
                      <Check className="h-5 w-5 shrink-0" aria-hidden />
                      <span className="text-sm">Manager reachable</span>
                    </div>
                  )}
                  <p className="text-sm text-play-muted">
                    Decoder run:{' '}
                    <span className={compareResults.decoders.ok ? 'text-emerald-400 font-medium' : 'text-play-subtle'}>
                      {compareResults.decoders.ok ? 'OK' : 'Not OK'}
                    </span>
                    <span className="text-play-subtle"> · </span>
                    <span className="tabular-nums text-play-fg">{compareResults.decoders.event_count}</span>
                    <span className="text-play-muted"> events</span>
                  </p>
                  {compareResults.decoders.user_messages?.length ? (
                    <PlayParserAlert variant="warning" title="Decoder messages">
                      <ul className="list-disc pl-4 space-y-1">
                        {compareResults.decoders.user_messages.map((m, i) => (
                          <li key={i}>{m}</li>
                        ))}
                      </ul>
                    </PlayParserAlert>
                  ) : null}
                  {compareResults.decoders.error ? (
                    <PlayParserAlert variant="danger" title="Decoder error">
                      {compareResults.decoders.error}
                    </PlayParserAlert>
                  ) : null}
                </div>
                {lastRunMode === 'both' && compareResults.compare ? (
                  <div className="rounded-xl border border-cyan-600/25 bg-gradient-to-br from-cyan-950/25 to-slate-900/50 p-4">
                    <p className={playSubsectionTitle}>Compare sample</p>
                    <dl className="grid grid-cols-2 gap-x-4 gap-y-3 mt-2">
                      <div>
                        <dt className="text-[10px] uppercase tracking-wider text-play-muted">Native events</dt>
                        <dd className="text-2xl font-play-mono tabular-nums text-play-fg">
                          {compareResults.compare.native_event_count}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-[10px] uppercase tracking-wider text-play-muted">Decoder events</dt>
                        <dd className="text-2xl font-play-mono tabular-nums text-play-fg">
                          {compareResults.compare.decoder_event_count}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-[10px] uppercase tracking-wider text-play-muted">Δ count</dt>
                        <dd className="text-lg font-play-mono tabular-nums text-amber-300">
                          {compareResults.compare.count_delta}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-[10px] uppercase tracking-wider text-play-muted">Timestamp match</dt>
                        <dd className="text-lg font-play-mono tabular-nums text-teal-300">
                          {(compareResults.compare.timestamp_agreement_ratio * 100).toFixed(0)}%
                        </dd>
                      </div>
                      <div className="col-span-2">
                        <dt className="text-[10px] uppercase tracking-wider text-play-muted">Source IP agreement</dt>
                        <dd className="text-lg font-play-mono tabular-nums text-play-fg">
                          {(compareResults.compare.source_ip_agreement_ratio * 100).toFixed(0)}%
                        </dd>
                      </div>
                    </dl>
                  </div>
                ) : lastRunMode === 'both' ? (
                  <p className="text-play-muted text-sm self-center">No comparison metrics (need both paths to produce events).</p>
                ) : null}
              </div>
              <div className="overflow-x-auto border-t border-play-border/60">
                <table className="min-w-full text-sm">
                  <thead className="sticky top-0 z-[1] bg-slate-900/95 backdrop-blur-sm border-b border-teal-500/20 text-left text-[10px] uppercase tracking-wider text-teal-200/80">
                    <tr>
                      <th className="px-4 py-3 font-semibold">Parser</th>
                      <th className="px-4 py-3 font-semibold">OK</th>
                      <th className="px-4 py-3 font-semibold tabular-nums">Events</th>
                    </tr>
                  </thead>
                  <tbody>
                    {compareResults.parser_results.length === 0 ? (
                      <tr>
                        <td colSpan={3} className="px-4 py-3 text-slate-400 text-xs">
                          No native parsers in this run.
                        </td>
                      </tr>
                    ) : (
                      compareResults.parser_results.map((row, idx) => (
                        <tr
                          key={row.parser_key}
                          className={`border-b border-slate-700/50 transition-colors duration-150 hover:bg-teal-950/20 motion-reduce:transition-none ${idx % 2 === 1 ? 'bg-slate-900/40' : ''}`}
                        >
                          <td className="px-4 py-2.5 font-play-mono text-play-fg">{row.parser_key}</td>
                          <td className="px-4 py-2.5">
                            {row.ok ? (
                              <span className="inline-flex rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold uppercase text-emerald-300 border border-emerald-500/25">
                                Yes
                              </span>
                            ) : (
                              <span className="inline-flex rounded-full bg-rose-500/15 px-2 py-0.5 text-[10px] font-semibold uppercase text-rose-300 border border-rose-500/25">
                                No
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-2.5 tabular-nums text-play-muted">{row.event_count}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {results &&
            results.length > 0 &&
            (lastRunMode === 'parsers_only' || lastRunMode === 'both') && (
              <section className={`${playPanel} mt-10 overflow-hidden`} aria-labelledby="quality-heading">
                <div className={`${playSection} border-b border-teal-500/20 pb-4`}>
                  <h2 id="quality-heading" className="text-lg font-semibold text-teal-50 font-play">
                    Native parser quality
                  </h2>
                  <p className="text-xs text-play-muted mt-1">Expanded samples and scores from the last run.</p>
                </div>
                <div className="overflow-x-auto max-h-[min(70vh,48rem)] overflow-y-auto">
                  <table className="min-w-full text-sm">
                    <thead className="sticky top-0 z-[1] bg-slate-900/95 backdrop-blur-sm border-b border-teal-500/20 text-left text-[10px] uppercase tracking-wider text-teal-200/80">
                      <tr>
                        <th className="px-4 py-3 font-semibold">Parser</th>
                        <th className="px-4 py-3 font-semibold">Status</th>
                        <th className="px-4 py-3 font-semibold tabular-nums">Events</th>
                        <th className="px-4 py-3 font-semibold">Score</th>
                        <th className="px-4 py-3 font-semibold">Warnings</th>
                        <th className="px-4 py-3 font-semibold w-10" />
                      </tr>
                    </thead>
                    <tbody>
                      {results.map((row) => (
                        <React.Fragment key={row.parser_key}>
                          <tr className="border-b border-slate-700/40 hover:bg-teal-950/15 transition-colors duration-150 motion-reduce:transition-none">
                            <td className="px-4 py-3 font-play-mono text-play-fg">{row.parser_key}</td>
                            <td className="px-4 py-3">
                              {row.ok ? (
                                <span className="text-emerald-400 text-xs font-semibold">OK</span>
                              ) : (
                                <span className="text-rose-400 text-xs font-semibold">Error</span>
                              )}
                            </td>
                            <td className="px-4 py-3 tabular-nums text-play-muted">
                              {row.event_count}
                              {row.events_trimmed ? (
                                <span className="block text-[10px] text-amber-400/90">trimmed to cap</span>
                              ) : null}
                            </td>
                            <td className="px-4 py-3">
                              {row.quality ? (
                                <div className="space-y-1 max-w-[140px]">
                                  <div className="flex justify-between text-xs tabular-nums text-play-fg">
                                    <span>{(row.quality.score * 100).toFixed(1)}%</span>
                                  </div>
                                  <div className="h-1.5 w-full rounded-full bg-slate-700 overflow-hidden">
                                    <div
                                      className="h-full rounded-full bg-gradient-to-r from-teal-700 via-teal-400 to-cyan-300 transition-[width] duration-200 motion-reduce:transition-none"
                                      style={{ width: `${Math.min(100, row.quality.score * 100)}%` }}
                                    />
                                  </div>
                                  <span className="block text-[10px] text-play-subtle font-normal">
                                    ts {(row.quality.valid_timestamp_ratio * 100).toFixed(0)}% · struct{' '}
                                    {(row.quality.structured_ratio * 100).toFixed(0)}%
                                  </span>
                                </div>
                              ) : (
                                <span className="text-play-subtle">—</span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-xs text-play-muted max-w-xs">
                              {row.quality?.warnings?.length
                                ? row.quality.warnings.join(', ')
                                : row.error ?? '—'}
                            </td>
                            <td className="px-4 py-3">
                              {row.ok && row.sample_events?.length ? (
                                <button
                                  type="button"
                                  className={`p-1.5 rounded-lg text-slate-400 hover:text-teal-300 hover:bg-teal-950/40 ${playFocusRing}`}
                                  aria-expanded={!!expanded[row.parser_key]}
                                  aria-label={expanded[row.parser_key] ? 'Collapse samples' : 'Expand samples'}
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
                            <tr className="bg-slate-950/80 border-b border-teal-900/30">
                              <td colSpan={6} className="px-4 py-3">
                                <pre className="text-[11px] font-play-mono text-slate-300 overflow-x-auto max-h-64 overflow-y-auto whitespace-pre-wrap break-all rounded-lg border border-teal-800/40 bg-slate-950/90 p-3">
                                  {formatJsonTinted(JSON.stringify(row.sample_events, null, 2))}
                                </pre>
                              </td>
                            </tr>
                          ) : null}
                        </React.Fragment>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

          {lastRunMode && file && (
            <section className={`${playPanel} mt-10 overflow-hidden`} aria-labelledby="preview-heading">
              <div className={`${playSection} border-b border-teal-500/20`}>
                <h2 id="preview-heading" className="text-lg font-semibold text-teal-50 font-play">
                  Line preview
                </h2>
                <p className="text-xs text-play-muted mt-1 max-w-2xl">
                  First lines from the file: raw text vs parsed fields. Best-effort pairing; JSON and binary logs may not
                  align one-to-one.
                </p>
              </div>
              <div className={playSection}>
                <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1 [scrollbar-width:thin]">
                  {showParserPreviewButtons &&
                    selectedKeys.map((key) => {
                      const label = PARSER_OPTIONS.find((p) => p.key === key)?.label ?? key
                      const active = previewActive === key
                      return (
                        <button
                          key={key}
                          type="button"
                          disabled={previewLoading}
                          onClick={() => void loadPreview(key)}
                          className={`shrink-0 rounded-lg border px-3 py-1.5 text-xs font-play-mono transition-colors duration-150 ${playFocusRing} disabled:opacity-50 ${
                            active
                              ? 'border-teal-400/70 bg-teal-900/40 text-teal-200 shadow-[0_0_14px_-5px_rgba(45,212,191,0.4)]'
                              : 'border-slate-600/50 bg-slate-900/50 text-slate-300 hover:border-teal-600/45'
                          }`}
                        >
                          {label}
                        </button>
                      )
                    })}
                  {showDecoderPreviewButton ? (
                    <button
                      type="button"
                      disabled={previewLoading}
                      onClick={() => void loadPreview(PREVIEW_TARGET_DECODER)}
                      className={`shrink-0 rounded-lg border px-3 py-1.5 text-xs font-semibold transition-colors duration-150 ${playFocusRing} disabled:opacity-50 ${
                        previewActive === PREVIEW_TARGET_DECODER
                          ? 'border-amber-400/70 bg-amber-950/50 text-amber-200 shadow-[0_0_14px_-4px_rgba(251,191,36,0.35)]'
                          : 'border-slate-600/50 bg-slate-900/50 text-slate-300 hover:border-amber-600/45'
                      }`}
                    >
                      Decoders
                    </button>
                  ) : null}
                </div>

                <div className="mt-4 flex flex-wrap gap-2 text-[10px] font-play-mono text-cyan-200/80">
                  {previewPayload ? (
                    <>
                      <span className="rounded-md border border-cyan-500/35 bg-cyan-950/40 px-2 py-0.5 text-cyan-100">
                        {previewPayload.preview_kind}
                      </span>
                      <span className="rounded-md border border-teal-500/35 bg-teal-950/40 px-2 py-0.5 text-teal-100">
                        {previewPayload.key}
                      </span>
                      <span className="rounded-md border border-slate-500/40 bg-slate-800/60 px-2 py-0.5 text-slate-200">
                        {previewPayload.line_limit} lines max
                      </span>
                    </>
                  ) : null}
                </div>

                {previewLoading ? (
                  <div
                    className="mt-4 rounded-xl border border-teal-600/30 overflow-hidden bg-slate-950/50"
                    aria-busy="true"
                    aria-label="Loading preview"
                  >
                    <div className="grid grid-cols-[2rem_1fr_1fr_5rem] gap-0 border-b border-teal-500/25 bg-teal-950/30 px-2 py-2 text-[10px] uppercase text-teal-200/90 font-semibold tracking-wider">
                      <div>#</div>
                      <div>Raw</div>
                      <div>Parsed</div>
                      <div>Match</div>
                    </div>
                    <div className="divide-y divide-slate-700/50 bg-slate-900/40 p-2 space-y-2">
                      {[0, 1, 2, 3, 4].map((i) => (
                        <div key={i} className="grid grid-cols-[2rem_1fr_1fr_5rem] gap-2 items-center py-2">
                          <div className="h-3 w-6 rounded bg-teal-900/50 animate-pulse motion-reduce:animate-none" />
                          <div className="h-3 rounded bg-slate-600/60 animate-pulse motion-reduce:animate-none" />
                          <div className="h-3 rounded bg-cyan-950/40 animate-pulse motion-reduce:animate-none" />
                          <div className="h-5 w-12 rounded-full bg-amber-900/40 animate-pulse motion-reduce:animate-none" />
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}

                {previewError ? (
                  <div className="mt-4">
                    <PlayParserAlert
                      variant="danger"
                      title="Preview failed"
                      onDismiss={() => setPreviewError(null)}
                      collapsibleDetail={previewError.length > 200 ? previewError : undefined}
                    >
                      {previewError.length > 200 ? `${previewError.slice(0, 200).trim()}…` : previewError}
                    </PlayParserAlert>
                  </div>
                ) : null}

                {!previewLoading && !previewPayload && !previewError ? (
                  <div className="mt-4 rounded-xl border border-dashed border-teal-500/35 bg-teal-950/15 px-4 py-8 text-center text-sm text-teal-100/70">
                    Select a parser or Decoders above to load a line-by-line preview.
                  </div>
                ) : null}

                {previewPayload ? (
                  <div className="mt-4 space-y-3">
                    {previewPayload.note ? (
                      <PlayParserAlert
                        variant={previewNoteVariant(previewPayload.note)}
                        title={previewNoteVariant(previewPayload.note) === 'warning' ? 'Preview note' : 'Note'}
                      >
                        {previewPayload.note}
                      </PlayParserAlert>
                    ) : null}
                    <div className="overflow-x-auto max-h-[28rem] overflow-y-auto rounded-xl border border-teal-600/25">
                      <table className="min-w-full text-xs">
                        <thead className="sticky top-0 z-[1] bg-slate-900/98 backdrop-blur-sm border-b border-teal-500/25 text-left text-[10px] uppercase tracking-wider text-teal-200/85">
                          <tr>
                            <th className="px-2 py-2 w-10 font-semibold">#</th>
                            <th className="px-2 py-2 min-w-[200px] font-semibold bg-slate-800/90 text-slate-200">Raw</th>
                            <th className="px-2 py-2 min-w-[240px] font-semibold bg-teal-950/50 text-teal-100/90">Parsed</th>
                            <th className="px-2 py-2 w-24 font-semibold">Match</th>
                          </tr>
                        </thead>
                        <tbody>
                          {previewPayload.rows.map((r) => (
                            <tr
                              key={r.line_no}
                              className="border-b border-slate-700/40 align-top transition-colors duration-150 hover:bg-teal-950/10 motion-reduce:transition-none"
                            >
                              <td className="px-2 py-2 tabular-nums text-slate-500 font-play-mono">{r.line_no}</td>
                              <td className="px-2 py-2 font-play-mono text-slate-200 whitespace-pre-wrap break-all max-w-md bg-slate-900/70">
                                {r.raw}
                              </td>
                              <td className="px-2 py-2 font-play-mono text-teal-100/85 whitespace-pre-wrap break-all max-w-xl bg-teal-950/25">
                                {r.parsed ? JSON.stringify(r.parsed, null, 2) : '—'}
                              </td>
                              <td className="px-2 py-2">
                                <span className={matchBadgeClass(r.match)} title={MATCH_HELP[r.match]}>
                                  {r.match}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <PlayParserAlert variant="info" className="!py-2 !px-3">
                      <p className="text-xs text-play-muted">
                        Line pairing is best-effort; JSON and binary formats may not align 1:1.
                      </p>
                    </PlayParserAlert>
                  </div>
                ) : null}
              </div>
            </section>
          )}
        </main>
      </div>
    </div>
  )
}
