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
import type { Investigation, InvestigationFile } from '../types/investigation'

const SOURCE_TYPES = [
  { value: 'windows_endpoint', label: 'Windows Endpoint', icon: Monitor, color: '#E3B57E', extensions: '.evtx, .xml' },
  { value: 'linux_endpoint', label: 'Linux / Syslog', icon: Server, color: '#14B8A6', extensions: '.log, .gz' },
  { value: 'firewall', label: 'Firewall', icon: AlertCircle, color: '#F97316', extensions: '.log, .txt' },
  { value: 'network', label: 'Network', icon: Wifi, color: '#FBBF24', extensions: '.pcap, .log' },
  { value: 'web_server', label: 'Web / Nginx', icon: Globe, color: '#F43F5E', extensions: '.log, .txt' },
  { value: 'cloudtrail', label: 'AWS CloudTrail', icon: Cloud, color: '#8A9CB8', extensions: '.json, .gz' },
]

function guessSourceType(filename: string): string {
  const ext = filename.toLowerCase().split('.').pop() ?? ''
  if (ext === 'evtx') return 'windows_endpoint'
  if (ext === 'json') return 'cloudtrail'
  return 'linux_endpoint'
}

const FILE_STATUS_STYLE: Record<string, string> = {
  pending: 'bg-white/[0.04] border-white/[0.08] text-text-muted',
  parsing: 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400',
  parsed:  'bg-teal-500/10 border-teal-500/20 text-teal-400',
  failed:  'bg-rose-500/10 border-rose-500/20 text-rose-400',
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
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [dragOver, setDragOver] = useState(false)
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
      <div className="pt-16 min-h-screen flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
      </div>
    )
  }

  if (!inv) {
    return (
      <div className="pt-16 min-h-screen flex items-center justify-center">
        <div className="text-rose-400 text-sm font-mono">Investigation not found.</div>
      </div>
    )
  }

  return (
    <div className="pt-16 min-h-screen">
      <div className="px-4 sm:px-6 lg:px-8 py-8">

        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-1.5 text-text-muted hover:text-text-secondary text-sm mb-4 transition-colors"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            Back to investigations
          </Link>

          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <h1 className="font-display font-bold text-text-primary text-2xl">{inv.name}</h1>
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
                className="btn-sovereign flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-semibold text-white self-start"
              >
                {inv.status === 'processing' && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                View analysis progress
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            )}

            {inv.status === 'complete' && (
              <Link
                to={`/investigations/${id}/report`}
                className="btn-sovereign flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-semibold text-white self-start"
              >
                View report <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            )}
          </div>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: file upload */}
          <div className="lg:col-span-2 space-y-4">

            {/* Drop zone — only when editable */}
            {canEdit && (
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`relative rounded-2xl border-2 border-dashed p-10 text-center transition-all duration-300 cursor-pointer ${
                  dragOver
                    ? 'border-indigo-500/50 bg-indigo-500/[0.08]'
                    : 'border-white/[0.08] hover:border-indigo-500/25 hover:bg-indigo-500/[0.04]'
                }`}
              >
                <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mx-auto mb-4">
                  <Upload className="w-6 h-6 text-indigo-400" />
                </div>
                <p className="font-medium text-text-primary mb-1">Drop log files here</p>
                <p className="text-sm text-text-muted mb-4">EVTX, syslog, CloudTrail, Nginx, firewall — any format</p>
                <span className="btn-ghost px-4 py-2 rounded-lg text-sm font-medium text-text-secondary pointer-events-none">
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
                  className="rounded-2xl border border-indigo-500/20 bg-indigo-500/5 overflow-hidden"
                >
                  <div className="px-5 py-3 border-b border-indigo-500/10 flex items-center justify-between">
                    <span className="font-mono text-[10px] text-indigo-400 tracking-widest uppercase">
                      Pending upload ({pendingFiles.length})
                    </span>
                    <button
                      onClick={() => setPendingFiles([])}
                      className="font-mono text-[10px] text-text-muted hover:text-rose-400 transition-colors"
                    >
                      Clear
                    </button>
                  </div>
                  <div className="divide-y divide-white/[0.04]">
                    {pendingFiles.map((pf, idx) => (
                      <div key={idx} className="flex flex-wrap items-center gap-3 px-5 py-3">
                        <FileText className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                        <span className="flex-1 min-w-[8rem] font-mono text-xs text-text-secondary truncate">
                          {pf.file.name}
                        </span>
                        <span className="font-mono text-[10px] text-text-muted">
                          {(pf.file.size / 1024).toFixed(0)} KB
                        </span>
                        <select
                          value={pf.sourceType}
                          onChange={(e) => updateSourceType(idx, e.target.value)}
                          className="sovereign-input rounded-lg px-2.5 py-1 text-xs font-mono text-sm"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {SOURCE_TYPES.map((st) => (
                            <option key={st.value} value={st.value}>{st.label}</option>
                          ))}
                        </select>
                        <select
                          value={pf.ingestionMode}
                          onChange={(e) => updateIngestionMode(idx, e.target.value as 'parsers' | 'decoders')}
                          className="sovereign-input rounded-lg px-2.5 py-1 text-xs font-mono text-sm"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <option value="parsers">Parsers</option>
                          <option value="decoders">Decoders</option>
                        </select>
                        <button
                          onClick={() => removePending(idx)}
                          className="p-1 rounded hover:bg-rose-500/10 text-text-muted hover:text-rose-400 transition-colors"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                  {uploadError && (
                    <div className="px-5 py-2.5 border-t border-white/[0.04] font-mono text-xs text-rose-400">
                      {uploadError}
                    </div>
                  )}
                  <div className="px-5 py-3 border-t border-indigo-500/10 flex justify-end">
                    <button
                      onClick={handleUploadAll}
                      disabled={uploading}
                      className="btn-sovereign flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white disabled:opacity-60"
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
              <div className="rounded-2xl border border-white/[0.06] bg-surface/40 backdrop-blur overflow-hidden">
                <div className="px-5 py-3 border-b border-white/[0.06]">
                  <span className="font-mono text-[10px] text-text-muted tracking-widest uppercase">
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
                        className="flex items-center gap-4 px-5 py-3.5 group hover:bg-elevated/30 transition-all"
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
                            <span className="font-mono text-[10px] text-text-muted">{f.source_type}</span>
                            {f.event_count != null && (
                              <>
                                <span className="text-text-ghost">·</span>
                                <span className="font-mono text-[10px] text-text-muted">{f.event_count.toLocaleString()} events</span>
                              </>
                            )}
                          </div>
                        </div>
                        <span className={`font-mono text-[10px] px-2 py-0.5 rounded border uppercase tracking-wider flex-shrink-0 ${FILE_STATUS_STYLE[f.status] ?? FILE_STATUS_STYLE.pending}`}>
                          {f.status}
                        </span>
                        {canEdit && (
                          <button
                            onClick={() => handleDeleteFile(f.id)}
                            className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-rose-500/10 text-text-muted hover:text-rose-400 transition-all"
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
            <div className="rounded-2xl border border-white/[0.06] bg-surface/40 backdrop-blur overflow-hidden">
              <div className="px-5 py-3 border-b border-white/[0.06]">
                <span className="font-mono text-[10px] text-text-muted tracking-widest uppercase">Source type guide</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 divide-x divide-y divide-white/[0.04]">
                {SOURCE_TYPES.map(({ value, label, icon: Icon, color, extensions }) => (
                  <div key={value} className="flex items-center gap-2.5 p-4 hover:bg-elevated/30 transition-colors">
                    <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
                      style={{ background: `${color}12`, border: `1px solid ${color}25` }}>
                      <Icon className="w-3.5 h-3.5" style={{ color }} />
                    </div>
                    <div>
                      <div className="text-xs font-medium text-text-primary">{label}</div>
                      <div className="font-mono text-[10px] text-text-muted">{extensions}</div>
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
              className="rounded-2xl border border-white/[0.06] bg-surface/40 backdrop-blur overflow-hidden"
            >
              <div className="px-5 py-3 border-b border-white/[0.06] flex items-center gap-2">
                <Settings2 className="w-3.5 h-3.5 text-text-muted" />
                <span className="font-mono text-[10px] text-text-muted tracking-widest uppercase">Analysis options</span>
              </div>
              <div className="p-5 space-y-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <GitMerge className="w-3.5 h-3.5 text-indigo-400" />
                      <span className="text-sm font-medium text-text-primary">Cross-file correlation</span>
                    </div>
                    <p className="text-xs text-text-muted leading-relaxed">
                      Link events across log sources to surface multi-stage attack chains
                    </p>
                  </div>
                  <div className={`flex-shrink-0 w-10 h-5 rounded-full border relative ${
                    inv.correlation_enabled ? 'bg-indigo-500/40 border-indigo-500/50' : 'bg-white/5 border-white/10'
                  }`}>
                    <div className={`absolute top-0.5 w-3.5 h-3.5 rounded-full transition-all ${
                      inv.correlation_enabled ? 'left-[20px] bg-indigo-400' : 'left-[2px] bg-text-muted'
                    }`} />
                  </div>
                </div>
                <div className="h-px bg-white/[0.04]" />
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <Cpu className="w-3.5 h-3.5 text-violet-400" />
                      <span className="text-sm font-medium text-text-primary">AI analysis</span>
                      <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-violet-500/15 text-violet-400 border border-violet-500/20">
                        Gemini 1.5 Pro
                      </span>
                    </div>
                    <p className="text-xs text-text-muted leading-relaxed">
                      Contextualizes findings and generates executive summaries
                    </p>
                  </div>
                  <div className={`flex-shrink-0 w-10 h-5 rounded-full border relative ${
                    inv.cloud_ai_enabled ? 'bg-violet-500/40 border-violet-500/50' : 'bg-white/5 border-white/10'
                  }`}>
                    <div className={`absolute top-0.5 w-3.5 h-3.5 rounded-full transition-all ${
                      inv.cloud_ai_enabled ? 'left-[20px] bg-violet-400' : 'left-[2px] bg-text-muted'
                    }`} />
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Cloud AI consent */}
            {canEdit && inv.files && inv.files.length > 0 && inv.cloud_ai_enabled && (
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="rounded-2xl border border-amber-500/15 bg-amber-500/5 p-5"
              >
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={cloudAiConsent}
                    onChange={(e) => setCloudAiConsent(e.target.checked)}
                    className="mt-0.5 h-4 w-4 rounded border-white/20 bg-deep text-indigo-500 focus:ring-indigo-500"
                  />
                  <div>
                    <p className="text-xs text-text-secondary leading-relaxed">
                      I consent to sending investigation event data to cloud AI providers during analysis.
                    </p>
                    <p className="text-[10px] text-text-muted mt-1 font-mono">Required for cloud AI enrichment</p>
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
                className="rounded-2xl border border-white/[0.06] bg-surface/40 backdrop-blur p-5 space-y-3"
              >
                <span className="font-mono text-[10px] text-text-muted tracking-widest uppercase">Ready to analyze</span>
                {[
                  { label: `${inv.files.length} file${inv.files.length !== 1 ? 's' : ''} uploaded` },
                  { label: inv.correlation_enabled ? 'Correlation enabled' : 'Correlation disabled' },
                  { label: inv.cloud_ai_enabled ? 'AI enrichment enabled' : 'AI enrichment disabled' },
                ].map(({ label }) => (
                  <div key={label} className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-teal-400 flex-shrink-0" />
                    <span className="text-sm text-text-secondary">{label}</span>
                  </div>
                ))}
              </motion.div>
            )}

            {/* Analysis error */}
            {analysisError && (
              <div className="px-4 py-3 rounded-xl border border-rose-500/20 bg-rose-500/5 font-mono text-xs text-rose-400">
                {analysisError}
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
                  className="btn-sovereign w-full flex items-center justify-center gap-2.5 py-3.5 rounded-xl text-sm font-bold text-white disabled:opacity-60"
                >
                  {analyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                  {analyzing ? 'Starting analysis…' : 'Run analysis'}
                </button>
                <p className="text-center font-mono text-[10px] text-text-muted mt-2">
                  Estimated time: ~4 minutes
                </p>
              </motion.div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
