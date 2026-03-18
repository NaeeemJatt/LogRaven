// LogRaven — Investigation Detail Page
import React, { useRef, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import Navbar from '../components/layout/Navbar'
import Badge from '../components/ui/Badge'
import { investigationsApi } from '../api/investigations'
import type { Investigation, InvestigationFile } from '../types/investigation'

const SOURCE_TYPES = [
  { value: 'windows_endpoint', label: 'Windows Endpoint' },
  { value: 'linux_endpoint',   label: 'Linux Endpoint' },
  { value: 'firewall',         label: 'Firewall' },
  { value: 'network',          label: 'Network' },
  { value: 'web_server',       label: 'Web Server' },
  { value: 'cloudtrail',       label: 'AWS CloudTrail' },
]

function guessSourceType(filename: string): string {
  const ext = filename.toLowerCase().split('.').pop() ?? ''
  if (ext === 'evtx') return 'windows_endpoint'
  if (ext === 'json') return 'cloudtrail'
  return 'linux_endpoint'
}

const FILE_STATUS: Record<string, string> = {
  pending: 'bg-raven-800 text-raven-400 border border-raven-600',
  parsing: 'bg-blue-950 text-blue-400 border border-blue-800',
  parsed:  'bg-green-950 text-green-400 border border-green-800',
  failed:  'bg-red-950 text-red-400 border border-red-800',
}

interface PendingFile { file: File; sourceType: string }

const inputClass =
  'bg-raven-900 border border-raven-600 text-raven-200 text-xs px-3 py-1.5 rounded-none font-mono focus:outline-none focus:border-electric-500 transition-colors'

export default function Investigation() {
  const { id }       = useParams<{ id: string }>()
  const navigate     = useNavigate()
  const queryClient  = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([])
  const [uploading, setUploading]       = useState(false)
  const [uploadError, setUploadError]   = useState<string | null>(null)
  const [analyzing, setAnalyzing]       = useState(false)

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

  const removePending = (idx: number) =>
    setPendingFiles((p) => p.filter((_, i) => i !== idx))

  const handleUploadAll = async () => {
    setUploading(true); setUploadError(null)
    try {
      for (const { file, sourceType } of pendingFiles) {
        await investigationsApi.uploadFile(id!, file, sourceType)
      }
      setPendingFiles([])
      queryClient.invalidateQueries({ queryKey: ['investigation', id] })
    } catch (err: any) {
      setUploadError(err?.response?.data?.detail ?? 'Upload failed.')
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
    } catch (err: any) {
      alert(err?.response?.data?.detail ?? 'Could not start analysis.')
    } finally {
      setAnalyzing(false)
    }
  }

  if (isLoading) return (
    <div className="min-h-screen bg-raven-900"><Navbar />
      <div className="flex items-center justify-center py-32 text-raven-400 text-sm font-mono">Loading...</div>
    </div>
  )

  if (!inv) return (
    <div className="min-h-screen bg-raven-900"><Navbar />
      <div className="flex items-center justify-center py-32 text-red-400 text-sm font-mono">— Investigation not found.</div>
    </div>
  )

  return (
    <div className="min-h-screen bg-raven-900">
      <Navbar />

      <main className="max-w-4xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-6">
          <Link to="/dashboard" className="text-raven-400 text-xs hover:text-electric-500 transition-colors mb-3 inline-block">
            ← Investigations
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-white text-xl font-semibold">{inv.name}</h1>
            <Badge value={inv.status} variant="status" />
          </div>
        </div>

        {/* Upload zone */}
        {canEdit && (
          <div className="mb-6">
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-raven-600 bg-raven-800/50 p-10 text-center cursor-pointer hover:border-electric-500 transition-colors"
            >
              <p className="text-raven-400 text-sm">Drop log files here or click to browse</p>
              <p className="text-raven-600 text-xs font-mono mt-2">.evtx  .log  .csv  .json  .txt</p>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              accept=".evtx,.csv,.log,.txt,.json"
              onChange={handleFilePick}
            />

            {/* Pending queue */}
            {pendingFiles.length > 0 && (
              <div className="mt-3 border border-raven-700">
                {pendingFiles.map((pf, idx) => (
                  <div key={idx} className="flex items-center gap-3 px-4 py-2.5 border-b border-raven-700 last:border-b-0 bg-raven-800">
                    <span className="flex-1 text-electric-400 font-mono text-xs truncate">{pf.file.name}</span>
                    <span className="text-raven-600 font-mono text-xs">
                      {(pf.file.size / 1024).toFixed(0)} KB
                    </span>
                    <select
                      value={pf.sourceType}
                      onChange={(e) => updateSourceType(idx, e.target.value)}
                      className={inputClass}
                    >
                      {SOURCE_TYPES.map((st) => (
                        <option key={st.value} value={st.value}>{st.label}</option>
                      ))}
                    </select>
                    <button
                      onClick={() => removePending(idx)}
                      className="text-raven-600 hover:text-red-400 text-xs transition-colors font-mono"
                    >
                      ✕
                    </button>
                  </div>
                ))}

                {uploadError && (
                  <p className="text-red-400 text-xs font-mono px-4 py-2">— {uploadError}</p>
                )}

                <div className="px-4 py-3 bg-raven-900 flex justify-end">
                  <button
                    onClick={handleUploadAll}
                    disabled={uploading}
                    className="bg-electric-500 hover:bg-electric-400 disabled:opacity-60 text-white text-xs font-medium tracking-wide px-4 py-2 rounded-none transition-colors uppercase"
                  >
                    {uploading ? 'Uploading...' : `Upload ${pendingFiles.length} file${pendingFiles.length > 1 ? 's' : ''}`}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* File list */}
        {inv.files && inv.files.length > 0 && (
          <div className="border border-raven-700 mb-6">
            <div className="bg-raven-800 px-4 py-3 border-b border-raven-700">
              <span className="text-raven-400 text-xs uppercase tracking-widest">Uploaded Files</span>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-raven-700">
                  {['Filename', 'Source Type', 'Status', 'Events', ...(canEdit ? [''] : [])].map((h) => (
                    <th key={h} className="text-left px-4 py-2 text-raven-400 text-xs uppercase tracking-widest font-medium bg-raven-800/50">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {inv.files.map((f: InvestigationFile) => (
                  <tr key={f.id} className="border-t border-raven-700 hover:bg-raven-800/50 transition-colors">
                    <td className="px-4 py-2.5 text-electric-400 font-mono text-xs truncate max-w-xs">{f.filename}</td>
                    <td className="px-4 py-2.5 text-raven-400 text-xs font-mono">{f.source_type}</td>
                    <td className="px-4 py-2.5">
                      <span className={`px-2 py-0.5 rounded-none text-xs font-mono uppercase tracking-wide ${FILE_STATUS[f.status] ?? FILE_STATUS.pending}`}>
                        {f.status}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-raven-400 font-mono text-xs">{f.event_count ?? '—'}</td>
                    {canEdit && (
                      <td className="px-4 py-2.5 text-right">
                        <button
                          onClick={() => handleDeleteFile(f.id)}
                          className="text-raven-600 hover:text-red-400 text-xs font-mono transition-colors"
                        >
                          remove
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3">
          {canEdit && inv.files && inv.files.length > 0 && (
            <button
              onClick={handleAnalyze}
              disabled={analyzing}
              className="bg-electric-500 hover:bg-electric-400 disabled:opacity-60 text-white text-xs font-medium tracking-wide px-6 py-2 rounded-none transition-colors uppercase"
            >
              {analyzing ? 'Starting...' : '▶ Run Analysis'}
            </button>
          )}
          {inv.status === 'complete' && (
            <button
              onClick={() => navigate(`/investigations/${id}/report`)}
              className="border border-electric-500 text-electric-500 text-xs px-6 py-2 rounded-none hover:bg-electric-900 transition-colors uppercase tracking-wide"
            >
              View Report →
            </button>
          )}
        </div>
      </main>
    </div>
  )
}
