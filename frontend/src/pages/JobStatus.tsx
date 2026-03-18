// LogRaven — Job Status Polling Page
import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Navbar from '../components/layout/Navbar'
import { useJobStatus } from '../hooks/useJobStatus'

const STEPS = [
  { key: 'queued',      label: 'Queued',            desc: 'Analysis job received and waiting to start.' },
  { key: 'processing',  label: 'Processing Files',   desc: 'Parsing log formats and extracting events.' },
  { key: 'rules',       label: 'Rule Engine',        desc: 'Applying detection rules to flagged events.' },
  { key: 'correlation', label: 'Correlation',        desc: 'Linking events across sources by entity.' },
  { key: 'ai',          label: 'AI Analysis',        desc: 'Gemini analyzing events for threats.' },
  { key: 'complete',    label: 'Complete',           desc: 'Analysis finished.' },
]

function statusToStep(status: string): number {
  if (status === 'queued')     return 0
  if (status === 'processing') return 1
  if (status === 'complete')   return 5
  if (status === 'failed')     return -1
  return 1
}

const FILE_STATUS: Record<string, string> = {
  pending: 'bg-raven-800 text-raven-400 border border-raven-600',
  parsing: 'bg-blue-950 text-blue-400 border border-blue-800',
  parsed:  'bg-green-950 text-green-400 border border-green-800',
  failed:  'bg-red-950 text-red-400 border border-red-800',
}

export default function JobStatus() {
  const { id }   = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { status, files, isComplete, isFailed } = useJobStatus(id ?? null)

  useEffect(() => {
    if (isComplete) {
      const t = setTimeout(() => navigate(`/investigations/${id}/report`), 2000)
      return () => clearTimeout(t)
    }
  }, [isComplete, id, navigate])

  const currentStep = statusToStep(status)

  return (
    <div className="min-h-screen bg-raven-900">
      <Navbar />

      <main className="max-w-2xl mx-auto px-6 py-10">

        {/* Title */}
        <div className="flex items-center gap-3 mb-8">
          {!isFailed && !isComplete && (
            <span className="w-2.5 h-2.5 rounded-full bg-electric-500 animate-pulse inline-block" />
          )}
          {isComplete && (
            <span className="w-2.5 h-2.5 rounded-full bg-green-400 inline-block" />
          )}
          {isFailed && (
            <span className="w-2.5 h-2.5 rounded-full bg-red-400 inline-block" />
          )}
          <h1 className="text-white text-xl font-semibold">
            {isFailed ? 'Analysis Failed' : isComplete ? 'Analysis Complete' : 'Analysis Running'}
          </h1>
        </div>

        {/* Vertical step list */}
        <div className="bg-raven-800 border border-raven-700 p-6 mb-6">
          <div className="space-y-0">
            {STEPS.map((step, idx) => {
              const isDone   = !isFailed && currentStep > idx
              const isActive = !isFailed && currentStep === idx
              const isPending = isFailed ? true : currentStep < idx

              return (
                <div key={step.key} className="flex gap-4">
                  {/* Connector column */}
                  <div className="flex flex-col items-center">
                    {/* Dot */}
                    <div className={`w-2.5 h-2.5 rounded-full mt-1 flex-shrink-0 transition-colors
                      ${isDone    ? 'bg-green-400' : ''}
                      ${isActive  ? 'bg-electric-500 animate-pulse' : ''}
                      ${isPending ? 'bg-raven-600' : ''}
                    `} />
                    {/* Line */}
                    {idx < STEPS.length - 1 && (
                      <div className={`w-px flex-1 my-1 min-h-[24px] transition-colors
                        ${isDone ? 'bg-green-800' : 'bg-raven-700'}
                      `} />
                    )}
                  </div>

                  {/* Content */}
                  <div className="pb-5 flex-1">
                    <p className={`text-sm font-medium leading-none transition-colors
                      ${isDone    ? 'text-raven-400 line-through' : ''}
                      ${isActive  ? 'text-white' : ''}
                      ${isPending ? 'text-raven-600' : ''}
                    `}>
                      {step.label}
                    </p>
                    {isActive && (
                      <p className="text-raven-400 text-xs mt-1">{step.desc}</p>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* File table */}
        {files.length > 0 && (
          <div className="border border-raven-700 mb-6">
            <div className="bg-raven-800 px-4 py-2.5 border-b border-raven-700">
              <span className="text-raven-400 text-xs uppercase tracking-widest">Files</span>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-raven-700">
                  {['Filename', 'Source Type', 'Status', 'Events'].map((h) => (
                    <th key={h} className="text-left px-4 py-2 text-raven-400 text-xs uppercase tracking-widest font-medium bg-raven-800/40">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {files.map((f) => (
                  <tr key={f.id} className="border-t border-raven-700">
                    <td className="px-4 py-2.5 text-electric-400 font-mono text-xs">{f.filename}</td>
                    <td className="px-4 py-2.5 text-raven-400 font-mono text-xs">{f.source_type}</td>
                    <td className="px-4 py-2.5">
                      <span className={`px-2 py-0.5 rounded-none text-xs font-mono uppercase tracking-wide ${FILE_STATUS[f.status] ?? FILE_STATUS.pending}`}>
                        {f.status}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-raven-400 font-mono text-xs">{f.event_count ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Complete state */}
        {isComplete && (
          <div className="border border-green-800 bg-green-950/30 p-5 flex items-center justify-between">
            <p className="text-green-400 text-sm font-mono">Analysis complete. Redirecting to report...</p>
            <button
              onClick={() => navigate(`/investigations/${id}/report`)}
              className="border border-electric-500 text-electric-500 text-xs px-4 py-2 rounded-none hover:bg-electric-900 transition-colors uppercase tracking-wide"
            >
              View Report →
            </button>
          </div>
        )}

        {/* Failed state */}
        {isFailed && (
          <div className="border border-red-800 bg-red-950/30 p-5 flex items-center justify-between">
            <p className="text-red-400 text-sm font-mono">— Analysis failed. Check server logs for details.</p>
            <button
              onClick={() => navigate(`/investigations/${id}`)}
              className="border border-raven-600 text-raven-400 text-xs px-4 py-2 rounded-none hover:border-raven-400 transition-colors uppercase tracking-wide"
            >
              ← Back
            </button>
          </div>
        )}
      </main>
    </div>
  )
}
