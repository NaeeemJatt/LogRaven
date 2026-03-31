// LogRaven — Investigation detail (matches dashboard chrome)
import React, { useRef, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, ChevronLeft } from 'lucide-react'
import Navbar from '../components/layout/Navbar'
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

  const { data: inv, isLoading } = useQuery<Investigation>({
    queryKey: ['investigation', id],
    queryFn: async () => (await investigationsApi.get(id!)).data,
    enabled: !!id,
  })

  const canEdit = inv?.status === 'draft' || inv?.status === 'failed'

  const handleFilePick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? [])
    setPendingFiles((p) => [...p, ...files.map((f) => ({ file: f, sourceType: guessSourceType(f.name) }))])
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    if (!canEdit) return
    const files = Array.from(e.dataTransfer.files)
    setPendingFiles((p) => [...p, ...files.map((f) => ({ file: f, sourceType: guessSourceType(f.name) }))])
  }

  const updateSourceType = (idx: number, sourceType: string) =>
    setPendingFiles((p) => p.map((x, i) => (i === idx ? { ...x, sourceType } : x)))

  const removePending = (idx: number) => setPendingFiles((p) => p.filter((_, i) => i !== idx))

  const handleUploadAll = async () => {
    setUploading(true)
    setUploadError(null)
    try {
      for (const { file, sourceType } of pendingFiles) {
        await investigationsApi.uploadFile(id!, file, sourceType)
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
    try {
      await investigationsApi.analyze(id!)
      navigate(`/investigations/${id}/status`)
    } catch (err: unknown) {
      const detail = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined
      alert(detail ?? 'Could not start analysis.')
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
          className="inline-flex items-center gap-1 text-sm text-raven-500 hover:text-electric-400 transition-colors mb-6"
        >
          <ChevronLeft className="h-4 w-4" />
          Investigations
        </Link>

        <div className="mb-8">
          <div className="flex flex-wrap items-center gap-3 mb-1">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">{inv.name}</h1>
            <Badge value={inv.status} variant="status" />
          </div>
          <p className="text-raven-500 text-sm">Upload logs, set source types, then run analysis.</p>
        </div>

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
                    {['Filename', 'Source type', 'Status', 'Events', ...(canEdit ? [''] : [])].map((h) => (
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

        <div className="flex flex-wrap justify-end gap-3">
          {canEdit && inv.files && inv.files.length > 0 && (
            <button
              type="button"
              onClick={handleAnalyze}
              disabled={analyzing}
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
      </main>
    </div>
  )
}
