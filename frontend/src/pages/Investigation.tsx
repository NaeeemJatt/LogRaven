import React, { useRef, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ChevronLeft, Upload, X, FileText, AlertCircle,
  Play, Settings2, GitMerge, CheckCircle2,
  Cloud, Monitor, Wifi, Globe, Server, ArrowRight,
  Loader2, Cpu
} from 'lucide-react'
import { investigationsApi } from '../api/investigations'
import { normalizeApiError } from '../api/errors'
import AlertModal from '../components/ui/AlertModal'
import { useAuthStore } from '../store/authStore'
import type { Investigation, InvestigationFile } from '../types/investigation'

const SOURCE_TYPES = [
  { value: 'windows_endpoint', label: 'Windows Endpoint', icon: Monitor, color: '#E3B57E', extensions: '.evtx, .xml' },
  { value: 'linux_endpoint', label: 'Linux / Syslog', icon: Server, color: '#14B8A6', extensions: '.log, .txt' },
  { value: 'web_server', label: 'Web / Nginx', icon: Globe, color: '#F43F5E', extensions: '.log, .txt' },
  { value: 'cloudtrail', label: 'AWS CloudTrail', icon: Cloud, color: '#8A9CB8', extensions: '.json' },
  { value: 'firewall', label: 'Firewall (Syslog/Text)', icon: AlertCircle, color: '#F97316', extensions: '.log, .txt' },
  { value: 'network', label: 'Network (Syslog/Text)', icon: Wifi, color: '#FBBF24', extensions: '.log, .txt' },
]

function guessSourceType(filename: string): string {
  const ext = filename.toLowerCase().split('.').pop() ?? ''
  if (ext === 'evtx') return 'windows_endpoint'
  if (ext === 'json') return 'cloudtrail'
  return 'linux_endpoint'
}

const FILE_STATUS_STYLE: Record<string, string> = {
  pending: 'bg-white/[0.04] border-white/[0.08] text-text-muted',
  parsing: 'bg-amber-400/10 border-amber-400/20 text-amber-300',
  parsed:  'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
  failed:  'bg-threat-critical/10 border-threat-critical/20 text-threat-critical',
}

// Read-only status indicator for pipeline capabilities that reflect server /
// investigation state (not user-toggleable), so the UI doesn't imply an
// interactive control it can't back.
function StatusTag({ on, onLabel, offLabel }: { on: boolean; onLabel: string; offLabel: string }) {
  return (
    <span
      className={`flex-shrink-0 inline-flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded border ${
        on
          ? 'bg-emerald-500/10 border-emerald-500/25 text-emerald-400'
          : 'bg-white/[0.04] border-white/[0.08] text-text-muted'
      }`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${on ? 'bg-emerald-400' : 'bg-text-muted'}`} />
      {on ? onLabel : offLabel}
    </span>
  )
}

interface PendingFile {
  file: File
  sourceType: string
  ingestionMode: 'parsers' | 'decoders'
}

export default function Investigation() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const userId = useAuthStore((state) => state.user?.id)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [dragOver, setDragOver] = useState(false)
  const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([])
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploadPlanLimit, setUploadPlanLimit] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [cloudAiConsent, setCloudAiConsent] = useState(false)
  const [analysisError, setAnalysisError] = useState<string | null>(null)
  const [analysisPlanLimit, setAnalysisPlanLimit] = useState(false)
  const [updatingCorrelation, setUpdatingCorrelation] = useState(false)
  const [correlationError, setCorrelationError] = useState<string | null>(null)

  const { data: inv, isLoading } = useQuery<Investigation>({
    queryKey: ['investigation', userId, id],
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
    setDragOver(false)
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
    setUploadPlanLimit(false)
    try {
      for (const { file, sourceType, ingestionMode } of pendingFiles) {
        await investigationsApi.uploadFile(id!, file, sourceType, ingestionMode)
      }
      setPendingFiles([])
      queryClient.invalidateQueries({ queryKey: ['investigation', userId, id] })
    } catch (err: unknown) {
      const normalized = normalizeApiError(err, 'Upload failed.')
      setUploadError(normalized.message)
      setUploadPlanLimit(normalized.isPlanLimit)
    } finally {
      setUploading(false)
    }
  }

  const handleDeleteFile = async (fileId: string) => {
    await investigationsApi.deleteFile(id!, fileId)
    queryClient.invalidateQueries({ queryKey: ['investigation', userId, id] })
  }

  const handleCorrelationChange = async (correlationEnabled: boolean) => {
    setUpdatingCorrelation(true)
    setCorrelationError(null)
    try {
      const response = await investigationsApi.update(id!, {
        correlation_enabled: correlationEnabled,
      })
      queryClient.setQueryData(['investigation', userId, id], response.data)
    } catch (err: unknown) {
      const detail = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined
      setCorrelationError(detail ?? 'Could not update correlation.')
    } finally {
      setUpdatingCorrelation(false)
    }
  }

  const handleAnalyze = async () => {
    setAnalyzing(true)
    setAnalysisError(null)
    setAnalysisPlanLimit(false)
    try {
      await investigationsApi.analyze(id!, inv?.cloud_ai_enabled ? cloudAiConsent : false)
      navigate(`/investigations/${id}/status`)
    } catch (err: unknown) {
      const normalized = normalizeApiError(err, 'Could not start analysis.')
      setAnalysisError(normalized.message)
      setAnalysisPlanLimit(normalized.isPlanLimit)
    } finally {
      setAnalyzing(false)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-amber-400 animate-spin" />
      </div>
    )
  }

  if (!inv) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-threat-critical text-sm">Investigation not found.</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      <div className="px-4 sm:px-6 lg:px-8 py-8">

        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-1.5 text-text-muted hover:text-text-secondary text-sm mb-4 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            Back to investigations
          </Link>

          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <h1 className="font-display font-bold text-text-primary text-2xl tracking-tight">{inv.name}</h1>
              <p className="text-text-secondary text-sm mt-0.5">
                {canEdit
                  ? 'Upload logs, set source types, then run analysis.'
                  : inv.status === 'complete'
                    ? 'Analysis finished. View the report or review files below.'
                    : 'Pipeline is running. Track progress on the status page.'}
              </p>
            </div>

            {['queued', 'processing', 'failed'].includes(inv.status) && (
              <Link
                to={`/investigations/${id}/status`}
                className="btn-sovereign flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-semibold text-white self-start focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] motion-reduce:transition-none"
              >
                {inv.status === 'processing' && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                View analysis progress
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            )}

            {inv.status === 'complete' && (
              <Link
                to={`/investigations/${id}/report`}
                className="btn-sovereign flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-semibold text-white self-start focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] motion-reduce:transition-none"
              >
                View report <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            )}
          </div>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: file upload */}
          <div className="lg:col-span-2 space-y-4">

            {/* Drop zone - only when editable */}
            {canEdit && (
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`relative rounded-2xl border border-dashed p-8 text-center transition-colors duration-150 cursor-pointer focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none ${
                  dragOver
                    ? 'border-amber-400/50 bg-amber-400/[0.08]'
                    : 'border-white/[0.12] bg-surface/30 hover:border-amber-400/30 hover:bg-surface/50'
                }`}
              >
                <div className="w-12 h-12 rounded-xl bg-amber-400/10 border border-amber-400/20 flex items-center justify-center mx-auto mb-3 text-amber-400">
                  <Upload className="w-5 h-5" />
                </div>
                <p className="font-semibold text-text-primary text-sm mb-1">Drop log files here</p>
                <p className="text-xs text-text-muted mb-4">Supported: EVTX, syslog, CloudTrail JSON, Nginx/IIS, and text logs</p>
                <span className="inline-flex px-3 py-1.5 rounded-lg text-xs font-semibold text-text-secondary bg-white/[0.04] border border-white/[0.08] pointer-events-none">
                  Browse files
                </span>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  className="hidden"
                  accept=".evtx,.csv,.log,.txt,.json,.gz"
                  onChange={handleFilePick}
                  onClick={(e) => e.stopPropagation()}
                />
              </motion.div>
            )}

            {/* Pending uploads */}
            <AnimatePresence>
              {pendingFiles.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  className="rounded-2xl border border-amber-400/20 bg-surface/60 overflow-hidden"
                >
                  <div className="px-5 py-3 border-b border-white/[0.08] flex items-center justify-between">
                    <span className="text-xs font-semibold text-amber-400">
                      Pending upload ({pendingFiles.length})
                    </span>
                    <button
                      onClick={() => setPendingFiles([])}
                      className="text-xs text-text-muted hover:text-threat-critical transition-colors duration-150 rounded px-1.5 py-0.5 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98]"
                    >
                      Clear
                    </button>
                  </div>
                  <div className="divide-y divide-white/[0.04]">
                    {pendingFiles.map((pf, idx) => (
                      <div key={idx} className="flex flex-wrap items-center gap-3 px-5 py-3">
                        <FileText className="w-4 h-4 text-amber-400 flex-shrink-0" />
                        <span className="flex-1 min-w-[8rem] font-mono text-xs text-text-secondary truncate">
                          {pf.file.name}
                        </span>
                        <span className="text-xs text-text-muted tabular-nums">
                          {(pf.file.size / 1024).toFixed(0)} KB
                        </span>
                        <select
                          value={pf.sourceType}
                          onChange={(e) => updateSourceType(idx, e.target.value)}
                          className="sovereign-input rounded-lg px-2.5 py-1 text-xs focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {SOURCE_TYPES.map((st) => (
                            <option key={st.value} value={st.value}>{st.label}</option>
                          ))}
                        </select>
                        <select
                          value={pf.ingestionMode}
                          onChange={(e) => updateIngestionMode(idx, e.target.value as 'parsers' | 'decoders')}
                          className="sovereign-input rounded-lg px-2.5 py-1 text-xs focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <option value="parsers">Parsers</option>
                          <option value="decoders">Decoders</option>
                        </select>
                        <button
                          onClick={() => removePending(idx)}
                          className="p-1 rounded hover:bg-threat-critical/10 text-text-muted hover:text-threat-critical transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98]"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                  {uploadError && (
                    <div className="px-5 py-2.5 border-t border-threat-critical/20 bg-threat-critical/5 text-xs text-threat-critical">
                      {uploadError}
                      {uploadPlanLimit && (
                        <a href="mailto:support@lograven.io" className="ml-2 underline text-amber-300 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded">
                          Contact support
                        </a>
                      )}
                    </div>
                  )}
                  <div className="px-5 py-3 border-t border-white/[0.08] flex justify-end">
                    <button
                      onClick={handleUploadAll}
                      disabled={uploading}
                      className="btn-sovereign flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed motion-reduce:transition-none"
                    >
                      {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                      {uploading ? 'Uploading…' : `Upload ${pendingFiles.length} file${pendingFiles.length > 1 ? 's' : ''}`}
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Uploaded files */}
            {inv.files && inv.files.length > 0 && (
              <div className="rounded-2xl border border-white/[0.08] bg-surface/40 backdrop-blur overflow-hidden">
                <div className="px-5 py-3 border-b border-white/[0.08]">
                  <span className="text-xs font-semibold text-text-secondary">
                    Uploaded files ({inv.files.length})
                  </span>
                </div>
                <div className="divide-y divide-white/[0.04]">
                  {inv.files.map((f: InvestigationFile, i: number) => {
                    const src = SOURCE_TYPES.find(s => s.value === f.source_type)
                    const SrcIcon = src?.icon ?? FileText
                    const srcColor = src?.color ?? '#94A3B8'
                    return (
                      <motion.div
                        key={f.id}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.05 }}
                        className="flex items-center gap-4 px-5 py-3.5 group hover:bg-elevated/40 transition-colors duration-150"
                      >
                        <div
                          className="w-8 h-8 rounded-lg border flex items-center justify-center flex-shrink-0"
                          style={{ background: `${srcColor}10`, borderColor: `${srcColor}25` }}
                        >
                          <FileText className="w-4 h-4" style={{ color: srcColor }} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-mono text-sm text-text-primary truncate">{f.filename}</div>
                          <div className="flex items-center gap-2 mt-0.5">
                            <SrcIcon className="w-2.5 h-2.5" style={{ color: srcColor }} />
                            <span className="text-xs text-text-muted">{f.source_type}</span>
                            {f.event_count != null && (
                              <>
                                <span className="text-text-ghost">·</span>
                                <span className="text-xs text-text-muted tabular-nums">{f.event_count.toLocaleString()} events</span>
                              </>
                            )}
                          </div>
                        </div>
                        <span className={`text-xs font-medium px-2 py-0.5 rounded border capitalize flex-shrink-0 ${FILE_STATUS_STYLE[f.status] ?? FILE_STATUS_STYLE.pending}`}>
                          {f.status}
                        </span>
                        {canEdit && (
                          <button
                            onClick={() => handleDeleteFile(f.id)}
                            className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-threat-critical/10 text-text-muted hover:text-threat-critical transition-opacity duration-150 focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98]"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </motion.div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Source type guide */}
            <div className="rounded-2xl border border-white/[0.08] bg-surface/40 backdrop-blur overflow-hidden">
              <div className="px-5 py-3 border-b border-white/[0.08]">
                <span className="text-xs font-semibold text-text-secondary">Source type guide</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 divide-x divide-y divide-white/[0.04]">
                {SOURCE_TYPES.map(({ value, label, icon: Icon, color, extensions }) => (
                  <div key={value} className="flex items-center gap-2.5 p-4 hover:bg-elevated/30 transition-colors duration-150">
                    <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
                      style={{ background: `${color}12`, border: `1px solid ${color}25` }}>
                      <Icon className="w-3.5 h-3.5" style={{ color }} />
                    </div>
                    <div>
                      <div className="text-xs font-medium text-text-primary">{label}</div>
                      <div className="font-mono text-xs text-text-muted">{extensions}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right: config panel */}
          <div className="space-y-4">
            {/* Analysis options */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
              className="rounded-2xl border border-white/[0.08] bg-surface/40 backdrop-blur overflow-hidden"
            >
              <div className="px-5 py-3 border-b border-white/[0.08] flex items-center gap-2">
                <Settings2 className="w-3.5 h-3.5 text-text-muted" />
                <span className="text-xs font-semibold text-text-secondary">Analysis pipeline</span>
              </div>
              <div className="p-5 space-y-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <GitMerge className="w-3.5 h-3.5 text-amber-400" />
                      <span className="text-sm font-medium text-text-primary">Cross-file correlation</span>
                    </div>
                    <p className="text-xs text-text-muted leading-relaxed">
                      {inv.correlation_enabled
                        ? 'Runs when 2+ uploaded files parse successfully'
                        : 'Disabled for this investigation'}
                    </p>
                  </div>
                  {canEdit ? (
                    <label className="relative inline-flex flex-shrink-0 cursor-pointer items-center">
                      <input
                        type="checkbox"
                        aria-label="Cross-file correlation"
                        checked={inv.correlation_enabled}
                        disabled={updatingCorrelation}
                        onChange={(event) => handleCorrelationChange(event.target.checked)}
                        className="peer sr-only"
                      />
                      <span
                        aria-hidden="true"
                        className="h-6 w-11 rounded-full border border-white/10 bg-white/5 transition-colors duration-150 peer-checked:border-amber-400/50 peer-checked:bg-amber-400/30 peer-focus-visible:ring-2 peer-focus-visible:ring-amber-400 peer-focus-visible:ring-offset-2 peer-focus-visible:ring-offset-deep peer-disabled:opacity-50"
                      >
                        <span className={`block h-4 w-4 translate-y-[3px] rounded-full transition-transform duration-150 motion-reduce:transition-none ${
                          inv.correlation_enabled
                            ? 'translate-x-6 bg-amber-400'
                            : 'translate-x-1 bg-text-muted'
                        }`} />
                      </span>
                    </label>
                  ) : (
                    <StatusTag on={inv.correlation_enabled} onLabel="On" offLabel="Off" />
                  )}
                </div>
                {correlationError && (
                  <p role="alert" className="text-xs text-threat-critical">
                    {correlationError}
                  </p>
                )}
                <div className="h-px bg-white/[0.04]" />
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <Cpu className="w-3.5 h-3.5 text-amber-400" />
                      <span className="text-sm font-medium text-text-primary">AI analysis</span>
                      <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-amber-400/10 text-amber-300 border border-amber-400/20">
                        LogRaven AI
                      </span>
                    </div>
                    <p className="text-xs text-text-muted leading-relaxed">
                      {inv.cloud_ai_enabled
                        ? 'Contextualizes findings and generates executive summaries (consent required below)'
                        : 'No AI provider configured on this server - analysis runs rules and correlation only'}
                    </p>
                  </div>
                  <StatusTag on={inv.cloud_ai_enabled} onLabel="Available" offLabel="Off" />
                </div>
              </div>
            </motion.div>

            {/* Cloud AI consent */}
            {canEdit && inv.files && inv.files.length > 0 && inv.cloud_ai_enabled && (
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="rounded-2xl border border-amber-400/20 bg-amber-400/5 p-5"
              >
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={cloudAiConsent}
                    onChange={(e) => setCloudAiConsent(e.target.checked)}
                    className="mt-0.5 h-4 w-4 rounded border-white/20 bg-deep text-amber-400 focus-visible:ring-2 focus-visible:ring-amber-400"
                  />
                  <div>
                    <p className="text-xs text-text-secondary leading-relaxed">
                      I consent to sending investigation event data to cloud AI providers during analysis.
                    </p>
                    <p className="text-xs text-text-muted mt-1">Required for cloud AI enrichment</p>
                  </div>
                </label>
              </motion.div>
            )}

            {/* Summary */}
            {inv.files && inv.files.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.25 }}
                className="rounded-2xl border border-white/[0.08] bg-surface/40 backdrop-blur p-5 space-y-3"
              >
                <span className="text-xs font-semibold text-text-secondary">Ready to analyze</span>
                {[
                  { label: `${inv.files.length} file${inv.files.length !== 1 ? 's' : ''} uploaded` },
                  { label: inv.correlation_enabled ? 'Correlation enabled' : 'Correlation disabled' },
                  { label: inv.cloud_ai_enabled ? 'AI enrichment enabled' : 'AI enrichment disabled' },
                ].map(({ label }) => (
                  <div key={label} className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                    <span className="text-sm text-text-secondary">{label}</span>
                  </div>
                ))}
              </motion.div>
            )}

            {/* Analysis error */}
            {analysisError && (
              <div className="px-4 py-3 rounded-xl border border-threat-critical/20 bg-threat-critical/5 text-xs text-threat-critical">
                {analysisError}
                {analysisPlanLimit && (
                  <a href="mailto:support@lograven.io" className="ml-2 underline text-amber-300 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded">
                    Contact support
                  </a>
                )}
              </div>
            )}

            {/* Run button */}
            {canEdit && inv.files && inv.files.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 }}
              >
                <button
                  onClick={handleAnalyze}
                  disabled={analyzing || (inv.cloud_ai_enabled && !cloudAiConsent)}
                  className="btn-sovereign w-full flex items-center justify-center gap-2.5 py-3 rounded-xl text-sm font-semibold text-white focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed motion-reduce:transition-none"
                >
                  {analyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                  {analyzing ? 'Starting analysis…' : 'Run analysis'}
                </button>
                <p className="text-center text-xs text-text-muted mt-2">
                  Estimated time: ~4 minutes
                </p>
              </motion.div>
            )}
          </div>
        </div>
      </div>

      <AlertModal
        isOpen={!!analysisError}
        title="Cannot start analysis"
        message={analysisError ?? ''}
        tone="warning"
        actionLabel={analysisPlanLimit ? 'Contact support' : undefined}
        onAction={
          analysisPlanLimit
            ? () => {
                window.location.href = 'mailto:support@lograven.io'
              }
            : undefined
        }
        dismissLabel="OK"
        onDismiss={() => setAnalysisError(null)}
      />
    </div>
  )
}
