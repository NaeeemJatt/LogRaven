// LogRaven — Investigation detail (matches dashboard chrome)
import React, { useRef, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, ChevronLeft } from 'lucide-react'
import Navbar from '../components/layout/Navbar'
import { InvestigationSubNav } from '../components/investigation/InvestigationSubNav'
import Badge from '../components/ui/Badge'
import { investigationsApi } from '../api/investigations'
import type { Investigation, InvestigationFile } from '../types/investigation'

const SOURCE_TYPES = [
  { value: 'windows_endpoint', label: 'Windows Endpoint' },
  { value: 'linux_endpoint', label: 'Linux Endpoint' },
  { value: 'firewall', label: 'Firewall' },
  { value: 'network', label: 'Network' },
  { value: 'web_server', label: 'Web Server' },
  { value: 'cloudtrail', label: 'AWS CloudTrail' },
]

function guessSourceType(filename: string): string {
  const ext = filename.toLowerCase().split('.').pop() ?? ''
  if (ext === 'evtx') return 'windows_endpoint'
  if (ext === 'json') return 'cloudtrail'
  return 'linux_endpoint'
}

const FILE_STATUS: Record<string, string> = {
  pending: 'bg-raven-700/50 text-raven-400 border border-raven-600',
  parsing: 'bg-electric-500/10 text-electric-400 border border-electric-500/30',
  parsed: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30',
  failed: 'bg-red-500/10 text-red-400 border border-red-500/30',
}

interface PendingFile {
  file: File
  sourceType: string
  ingestionMode: 'parsers' | 'decoders'
}

const inputClass =
  'rounded-lg bg-raven-900 border border-raven-600 text-raven-200 text-xs px-3 py-1.5 font-mono focus:outline-none focus:border-electric-500 focus:ring-1 focus:ring-electric-500/30 transition-colors'

export default function Investigation() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([])
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [cloudAiConsent, setCloudAiConsent] = useState(false)
  const [analysisError, setAnalysisError] = useState<string | null>(null)

  const { data: inv, isLoading } = useQuery<Investigation>({
    queryKey: ['investigation', id],
    queryFn: async () => (await investigationsApi.get(id!)).data,
    enabled: !!id,
  })

  const canEdit = inv?.status === 'draft' || inv?.status === 'failed'

  const handleFilePick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? [])
    setPendingFiles((p) => [
      ...p,
      ...files.map((f) => ({ file: f, sourceType: guessSourceType(f.name), ingestionMode: 'parsers' as const })),
    ])
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    if (!canEdit) return
    const files = Array.from(e.dataTransfer.files)
    setPendingFiles((p) => [
      ...p,
      ...files.map((f) => ({ file: f, sourceType: guessSourceType(f.name), ingestionMode: 'parsers' as const })),
    ])
  }

  const updateSourceType = (idx: number, sourceType: string) =>
    setPendingFiles((p) => p.map((x, i) => (i === idx ? { ...x, sourceType } : x)))

  const updateIngestionMode = (idx: number, ingestionMode: 'parsers' | 'decoders') =>
    setPendingFiles((p) => p.map((x, i) => (i === idx ? { ...x, ingestionMode } : x)))

  const removePending = (idx: number) => setPendingFiles((p) => p.filter((_, i) => i !== idx))

  const handleUploadAll = async () => {
    setUploading(true)
    setUploadError(null)
    try {
      for (const { file, sourceType, ingestionMode } of pendingFiles) {
        await investigationsApi.uploadFile(id!, file, sourceType, ingestionMode)
      }
      setPendingFiles([])
      queryClient.invalidateQueries({ queryKey: ['investigation', id] })
    } catch (err: unknown) {
      const detail = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined
      setUploadError(detail ?? 'Upload failed.')
    } finally {
      setUploading(false)
    }
  }

  const handleDeleteFile = async (fileId: string) => {
    await investigationsApi.deleteFile(id!, fileId)
    queryClient.invalidateQueries({ queryKey: ['investigation', id] })
  }

  const handleAnalyze = async () => {
    setAnalyzing(true)
    setAnalysisError(null)
    try {
      await investigationsApi.analyze(id!, inv?.cloud_ai_enabled ? cloudAiConsent : false)
      navigate(`/investigations/${id}/status`)
    } catch (err: unknown) {
      const detail = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined
      setAnalysisError(detail ?? 'Could not start analysis.')
    } finally {
      setAnalyzing(false)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-raven-950">
        <Navbar />
        <div className="flex items-center justify-center py-32">
          <div
            className="h-10 w-10 rounded-full border-2 border-raven-700 border-t-electric-500 animate-spin"
            aria-hidden
          />
        </div>
      </div>
    )
  }

  if (!inv) {
    return (
      <div className="min-h-screen bg-raven-950">
        <Navbar />
        <div className="flex items-center justify-center py-32 text-red-400 text-sm font-mono">
          Investigation not found.
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-raven-950 text-raven-200">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1 text-sm text-raven-500 hover:text-electric-400 transition-colors mb-4"
        >
          <ChevronLeft className="h-4 w-4" />
          Investigations
        </Link>

        {id && <InvestigationSubNav investigationId={id} active="files" />}

        <div className="mb-8">
          <div className="flex flex-wrap items-center gap-3 mb-1">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">{inv.name}</h1>
            <Badge value={inv.status} variant="status" />
          </div>
          <p className="text-raven-500 text-sm">
            {inv.status === 'draft' || inv.status === 'failed'
              ? 'Upload logs, set source types, then run analysis.'
              : inv.status === 'complete'
                ? 'Analysis finished. Open the report or review files below.'
                : 'Pipeline is running or queued. Use Analysis progress to watch stages through report generation.'}
          </p>
        </div>

        {['queued', 'processing', 'failed'].includes(inv.status) && (
          <div className="mb-8 rounded-xl border border-electric-500/35 bg-gradient-to-r from-electric-500/10 to-raven-900/80 px-4 py-4 sm:px-5 sm:py-5 shadow-lg shadow-black/20">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-semibold text-electric-300">
                  {inv.status === 'failed' ? 'Analysis needs attention' : 'Analysis pipeline active'}
                </p>
                <p className="text-xs text-raven-500 mt-1 max-w-xl">
                  {inv.status === 'failed'
                    ? 'Open the progress view for the error detail and file states. You can retry from files & setup when the investigation is failed.'
                    : 'Follow live stages (parsing → rules → correlation → AI → report) on the status page until the PDF is ready.'}
                </p>
              </div>
              <Link
                to={`/investigations/${id}/status`}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-electric-500 hover:bg-electric-400 text-raven-950 text-sm font-semibold px-5 py-2.5 transition-colors shrink-0"
              >
                View analysis progress
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        )}

        {inv.status === 'complete' && (
          <div className="mb-8 flex flex-wrap gap-3">
            <Link
              to={`/investigations/${id}/status`}
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-raven-600 bg-raven-800/60 px-4 py-2 text-sm font-medium text-raven-200 hover:border-electric-500/40 hover:text-electric-300 transition-colors"
            >
              View last run progress
            </Link>
          </div>
        )}

        {canEdit && (
          <div className="mb-8">
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className="cursor-pointer rounded-xl border-2 border-dashed border-raven-600 bg-raven-800/40 p-10 text-center transition-colors hover:border-electric-500/50 hover:bg-raven-800/60"
            >
              <p className="text-raven-300 text-sm">Drop log files here or click to browse</p>
              <p className="text-raven-600 text-xs font-mono mt-2">.evtx · .log · .csv · .json · .txt</p>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              accept=".evtx,.csv,.log,.txt,.json"
              onChange={handleFilePick}
            />

            {pendingFiles.length > 0 && (
              <div className="mt-4 overflow-hidden rounded-xl border border-raven-700 bg-raven-900/80">
                {pendingFiles.map((pf, idx) => (
                  <div
                    key={idx}
                    className="flex flex-wrap items-center gap-3 px-4 py-3 border-b border-raven-700 last:border-b-0 bg-raven-800/50"
                  >
                    <span className="flex-1 min-w-[8rem] text-electric-400 font-mono text-xs truncate">
                      {pf.file.name}
                    </span>
                    <span className="text-raven-600 font-mono text-xs">
                      {(pf.file.size / 1024).toFixed(0)} KB
                    </span>
                    <select
                      value={pf.sourceType}
                      onChange={(e) => updateSourceType(idx, e.target.value)}
                      className={inputClass}
                    >
                      {SOURCE_TYPES.map((st) => (
                        <option key={st.value} value={st.value}>
                          {st.label}
                        </option>
                      ))}
                    </select>
                    <select
                      value={pf.ingestionMode}
                      onChange={(e) =>
                        updateIngestionMode(idx, e.target.value as 'parsers' | 'decoders')
                      }
                      className={inputClass}
                      title="Parsers use native LogRaven parsers. Decoders use the configured decoder manager when available."
                    >
                      <option value="parsers">Parsers</option>
                      <option value="decoders">Decoders</option>
                    </select>
                    <button
                      type="button"
                      onClick={() => removePending(idx)}
                      className="text-raven-600 hover:text-red-400 text-xs transition-colors font-mono"
                    >
                      ✕
                    </button>
                  </div>
                ))}

                {uploadError && (
                  <p className="text-red-400 text-xs font-mono px-4 py-2 border-t border-raven-700">
                    {uploadError}
                  </p>
                )}

                <div className="px-4 py-3 flex justify-end bg-raven-950/50 border-t border-raven-700">
                  <button
                    type="button"
                    onClick={handleUploadAll}
                    disabled={uploading}
                    className="inline-flex items-center justify-center rounded-lg bg-electric-500 hover:bg-electric-400 disabled:opacity-60 text-raven-950 text-sm font-semibold px-5 py-2.5 transition-colors"
                  >
                    {uploading ? 'Uploading…' : `Upload ${pendingFiles.length} file${pendingFiles.length > 1 ? 's' : ''}`}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {inv.files && inv.files.length > 0 && (
          <div className="rounded-xl border border-raven-700 bg-raven-900/80 overflow-hidden mb-8 shadow-lg shadow-black/20">
            <div className="px-4 sm:px-5 py-3 border-b border-raven-700 bg-raven-950/80">
              <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-electric-400/90">
                Uploaded files
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[640px]">
                <thead>
                  <tr className="border-b border-raven-700 bg-raven-800/40">
                    {[
                      'Filename',
                      'Source type',
                      'Ingestion',
                      'Log format',
                      'Status',
                      'Events',
                      ...(canEdit ? [''] : []),
                    ].map((h) => (
                      <th
                        key={h || 'actions'}
                        className="text-left px-4 py-3 text-[10px] font-semibold uppercase tracking-widest text-raven-500"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {inv.files.map((f: InvestigationFile) => (
                    <tr
                      key={f.id}
                      className="border-t border-raven-700/80 hover:bg-raven-800/40 transition-colors"
                    >
                      <td className="px-4 py-3 text-electric-400 font-mono text-xs truncate max-w-[220px]">
                        {f.filename}
                      </td>
                      <td className="px-4 py-3 text-raven-400 text-xs font-mono">{f.source_type}</td>
                      <td className="px-4 py-3 text-raven-400 text-xs font-mono max-w-[140px]">
                        <span className="text-raven-300">{f.ingestion_mode ?? 'parsers'}</span>
                        {f.parser_selection_detail?.actual_ingestion_path &&
                        f.parser_selection_detail.actual_ingestion_path !== (f.ingestion_mode ?? 'parsers') ? (
                          <span className="block text-[10px] text-amber-500/90 mt-0.5">
                            → {f.parser_selection_detail.actual_ingestion_path}
                          </span>
                        ) : null}
                        {f.parser_selection_detail?.user_warnings?.length ? (
                          <span
                            className="block text-[10px] text-amber-400/90 mt-1"
                            title={f.parser_selection_detail.user_warnings.join(' ')}
                          >
                            {f.parser_selection_detail.user_warnings[0]}
                          </span>
                        ) : null}
                      </td>
                      <td
                        className="px-4 py-3 text-raven-400 text-xs font-mono max-w-[200px]"
                        title={
                          f.parser_selection_detail
                            ? [
                                `Parser: ${f.log_type ?? '—'}`,
                                f.parser_detection_confidence != null
                                  ? `Detection confidence: ${f.parser_detection_confidence}`
                                  : null,
                                f.parser_selection_detail.parse_quality != null &&
                                f.parser_selection_detail.parse_quality !== undefined
                                  ? `Parse quality: ${f.parser_selection_detail.parse_quality}`
                                  : null,
                                f.parser_selection_detail.fallback_used ? 'Fallback: yes (first-ranked parser had low parse quality)' : null,
                                f.parser_selection_detail.parse_warnings?.length
                                  ? `Warnings: ${f.parser_selection_detail.parse_warnings.join(', ')}`
                                  : null,
                              ]
                                .filter(Boolean)
                                .join('\n')
                            : f.log_type ?? undefined
                        }
                      >
                        <span className="text-electric-400/90">{f.log_type ?? '—'}</span>
                        {f.parser_selection_detail?.fallback_used ? (
                          <span className="ml-1.5 text-[10px] uppercase tracking-wide text-amber-500/90">fallback</span>
                        ) : null}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex px-2.5 py-1 rounded-lg text-[10px] font-semibold uppercase tracking-wide ${FILE_STATUS[f.status] ?? FILE_STATUS.pending}`}
                        >
                          {f.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-raven-300 font-mono text-xs tabular-nums">
                        {f.event_count ?? '—'}
                      </td>
                      {canEdit && (
                        <td className="px-4 py-3 text-right">
                          <button
                            type="button"
                            onClick={() => handleDeleteFile(f.id)}
                            className="text-raven-500 hover:text-red-400 text-xs font-mono transition-colors"
                          >
                            Remove
                          </button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <div className="flex flex-col gap-4">
          {canEdit && inv.files && inv.files.length > 0 && (
            <div className="rounded-xl border border-raven-700 bg-raven-900/80 px-4 py-4">
              {inv.cloud_ai_enabled ? (
                <>
                  <label className="flex items-start gap-3 text-sm text-raven-300">
                    <input
                      type="checkbox"
                      checked={cloudAiConsent}
                      onChange={(e) => setCloudAiConsent(e.target.checked)}
                      className="mt-1 h-4 w-4 rounded border-raven-600 bg-raven-950 text-electric-500 focus:ring-electric-500"
                    />
                    <span>
                      I consent to sending investigation event data to configured cloud AI providers during analysis.
                    </span>
                  </label>
                  <p className="mt-2 text-xs text-raven-500">
                    This deployment has cloud AI enabled. Consent is required before any log-derived data can be sent to external AI services.
                  </p>
                </>
              ) : (
                <p className="text-xs text-raven-500">
                  Cloud AI is not configured for this deployment. Analysis can run without external AI consent.
                </p>
              )}
            </div>
          )}

          {analysisError && (
            <p className="rounded-lg border border-rose-900/50 bg-rose-950/30 px-3 py-2 text-xs font-mono text-rose-400">
              {analysisError}
            </p>
          )}

          <div className="flex flex-wrap justify-end gap-3">
          {canEdit && inv.files && inv.files.length > 0 && (
            <button
              type="button"
              onClick={handleAnalyze}
              disabled={analyzing || (inv.cloud_ai_enabled && !cloudAiConsent)}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-electric-500 hover:bg-electric-400 disabled:opacity-60 text-raven-950 text-sm font-semibold px-6 py-2.5 transition-colors"
            >
              {analyzing ? 'Starting…' : 'Run analysis'}
            </button>
          )}
          {inv.status === 'complete' && (
            <button
              type="button"
              onClick={() => navigate(`/investigations/${id}/report`)}
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-electric-500/60 bg-electric-500/5 px-6 py-2.5 text-sm font-semibold text-electric-400 hover:bg-electric-500/10 hover:border-electric-400 transition-colors"
            >
              View report
              <ArrowRight className="h-4 w-4" />
            </button>
          )}
          </div>
        </div>
      </main>
    </div>
  )
}
