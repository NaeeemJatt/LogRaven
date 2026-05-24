// LogRaven — Job status (polls progress_stage for live pipeline)
import { useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'
import Navbar from '../components/layout/Navbar'
import { InvestigationSubNav } from '../components/investigation/InvestigationSubNav'
import { useJobStatus } from '../hooks/useJobStatus'

const STEPS = [
  { key: 'queued', label: 'Queued', desc: 'Analysis job received and waiting to start.' },
  { key: 'parsing', label: 'Processing files', desc: 'Parsing log formats and extracting events.' },
  { key: 'rule_engine', label: 'Rule engine', desc: 'Applying detection rules to flagged events.' },
  { key: 'correlation', label: 'Correlation', desc: 'Linking events across sources by entity.' },
  { key: 'ai_analysis', label: 'AI analysis', desc: 'Gemini analyzing events for threats.' },
  { key: 'building_report', label: 'Building report', desc: 'MITRE mapping, saving findings, generating PDF.' },
  { key: 'complete', label: 'Complete', desc: 'Analysis finished.' },
] as const

const STAGE_INDEX: Record<string, number> = {
  queued: 0,
  parsing: 1,
  rule_engine: 2,
  correlation: 3,
  ai_analysis: 4,
  building_report: 5,
  complete: 6,
}

function progressToIndex(progressStage: string | null | undefined, status: string | undefined): number {
  if (!status || status === 'draft') return 0
  if (status === 'complete') return 7
  if (status === 'failed') {
    // Highlight the last known pipeline step (ignore legacy "failed" or unknown strings)
    const raw = progressStage?.trim() || 'queued'
    const n = STAGE_INDEX[raw]
    if (n !== undefined && n >= 0) return n
    return 0
  }
  const stage =
    progressStage ||
    (status === 'queued' ? 'queued' : status === 'processing' ? 'parsing' : 'queued')
  const n = STAGE_INDEX[stage]
  if (n !== undefined && n >= 0) return n
  if (status === 'processing') return 1
  return 0
}

const FILE_STATUS: Record<string, string> = {
  pending: 'bg-raven-700/50 text-raven-400 border border-raven-600',
  parsing: 'bg-electric-500/10 text-electric-400 border border-electric-500/30',
  parsed: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30',
  failed: 'bg-rose-500/10 text-rose-400 border border-rose-500/30',
}

export default function JobStatus() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const {
    status,
    progressStage,
    errorMessage,
    files,
    isLoading,
    isError,
    isComplete,
    isFailed,
    isDraft,
  } = useJobStatus(id ?? null)

  useEffect(() => {
    if (isComplete) {
      const t = setTimeout(() => navigate(`/investigations/${id}/report`), 2000)
      return () => clearTimeout(t)
    }
  }, [isComplete, id, navigate])

  const currentIdx = progressToIndex(progressStage, status)
  const allDone = status === 'complete'

  if (isLoading) {
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
          <div className="flex items-center justify-center py-24">
            <div
              className="h-10 w-10 rounded-full border-2 border-raven-700 border-t-electric-500 animate-spin"
              aria-hidden
            />
          </div>
        </main>
      </div>
    )
  }

  if (isError || status === undefined) {
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
          <p className="text-rose-400 text-sm font-mono border border-rose-900/40 bg-rose-950/20 rounded-lg px-4 py-3">
            Could not load investigation status. Check that you are signed in and the investigation exists.
          </p>
        </main>
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

        {id && <InvestigationSubNav investigationId={id} active="progress" />}

        {isDraft ? (
          <div className="rounded-xl border border-raven-700 bg-raven-900/80 px-6 py-10 text-center max-w-lg mx-auto">
            <h1 className="text-xl font-semibold text-white mb-2">Analysis not started</h1>
            <p className="text-raven-500 text-sm mb-6">
              This investigation is still in draft. Upload log files and run analysis from the setup page to
              track the pipeline here.
            </p>
            <Link
              to={`/investigations/${id}`}
              className="inline-flex items-center justify-center rounded-lg bg-electric-500 hover:bg-electric-400 text-raven-950 text-sm font-semibold px-6 py-2.5 transition-colors"
            >
              Go to files & setup
            </Link>
          </div>
        ) : (
        <div className="w-full">
          <div className="flex flex-wrap items-center gap-3 mb-2">
            {!isFailed && !isComplete && (
              <span className="w-2.5 h-2.5 rounded-full bg-electric-500 animate-pulse" aria-hidden />
            )}
            {isComplete && <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" aria-hidden />}
            {isFailed && <span className="w-2.5 h-2.5 rounded-full bg-rose-400" aria-hidden />}
            <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
              {isFailed ? 'Analysis failed' : isComplete ? 'Analysis complete' : 'Analysis running'}
            </h1>
          </div>
          <p className="text-raven-500 text-sm mb-8">
            {isFailed
              ? errorMessage || 'Something went wrong during processing.'
              : isComplete
                ? 'Opening your report shortly.'
                : 'Pipeline progress updates every few seconds.'}
          </p>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start mb-6">
            <div className="lg:col-span-5 min-w-0">
              <div className="rounded-xl border border-raven-700 bg-raven-900/80 p-6 sm:p-8 shadow-lg shadow-black/20 h-full">
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-electric-400/90 mb-6">
                  Pipeline
                </p>
                <div className="space-y-0">
                  {STEPS.map((step, idx) => {
                    const stepDone = allDone || currentIdx > idx
                    const stepActive = !allDone && !isFailed && currentIdx === idx
                    const stepFailedHere = isFailed && currentIdx === idx

                    return (
                      <div key={step.key} className="flex gap-4">
                        <div className="flex flex-col items-center">
                          <div
                            className={`w-2.5 h-2.5 rounded-full mt-1 shrink-0 transition-colors ${
                              stepFailedHere
                                ? 'bg-rose-400'
                                : stepDone
                                  ? 'bg-emerald-400'
                                  : stepActive
                                    ? 'bg-electric-500 animate-pulse'
                                    : 'bg-raven-600'
                            }`}
                          />
                          {idx < STEPS.length - 1 && (
                            <div
                              className={`w-px flex-1 my-1 min-h-[24px] transition-colors ${
                                stepDone ? 'bg-emerald-500/40' : 'bg-raven-700'
                              }`}
                            />
                          )}
                        </div>

                        <div className="pb-5 flex-1 min-w-0">
                          <p
                            className={`text-sm font-medium leading-snug transition-colors ${
                              stepDone
                                ? 'text-raven-500 line-through'
                                : stepActive || stepFailedHere
                                  ? 'text-white'
                                  : 'text-raven-600'
                            }`}
                          >
                            {step.label}
                            {stepFailedHere && (
                              <span className="ml-2 text-[10px] font-semibold uppercase tracking-wider text-rose-400">
                                Failed
                              </span>
                            )}
                          </p>
                          {(stepActive || stepFailedHere) && (
                            <p className="text-raven-500 text-xs mt-1">{step.desc}</p>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>

            <div className="lg:col-span-7 min-w-0">
              <div className="rounded-xl border border-raven-700 bg-raven-900/80 overflow-hidden shadow-lg shadow-black/20 h-full flex flex-col">
                <div className="px-4 sm:px-5 py-3 border-b border-raven-700 bg-raven-950/80 shrink-0">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-electric-400/90">
                    Files
                  </span>
                </div>
                {files.length > 0 ? (
                  <div className="overflow-x-auto overflow-y-auto max-h-[min(70vh,520px)]">
                    <table className="w-full text-sm min-w-[480px]">
                      <thead className="sticky top-0 z-10 bg-raven-800/95 backdrop-blur-sm border-b border-raven-700">
                        <tr>
                          {['Filename', 'Source type', 'Ingestion', 'Status', 'Events'].map((h) => (
                            <th
                              key={h}
                              className="text-left px-4 py-3 text-[10px] font-semibold uppercase tracking-widest text-raven-500"
                            >
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {files.map((f) => (
                          <tr
                            key={f.id}
                            className="border-t border-raven-700/80 hover:bg-raven-800/40 transition-colors"
                          >
                            <td className="px-4 py-3 text-electric-400 font-mono text-xs truncate max-w-[220px]">
                              {f.filename}
                            </td>
                            <td className="px-4 py-3 text-raven-400 text-xs font-mono">{f.source_type}</td>
                            <td className="px-4 py-3 text-raven-500 text-xs font-mono max-w-[100px]">
                              {f.ingestion_mode ?? 'parsers'}
                            </td>
                            <td className="px-4 py-3">
                              <span
                                className={`inline-flex px-2.5 py-1 rounded-lg text-[10px] font-semibold uppercase tracking-wide ${
                                  FILE_STATUS[f.status] ?? FILE_STATUS.pending
                                }`}
                              >
                                {f.status}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-raven-300 font-mono text-xs tabular-nums">
                              {f.event_count ?? '—'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="px-5 py-12 text-center text-raven-500 text-sm">
                    No files listed for this run yet.
                  </div>
                )}
              </div>
            </div>
          </div>

          {isComplete && (
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 px-5 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <p className="text-emerald-400/90 text-sm">Analysis complete. Redirecting to report…</p>
              <button
                type="button"
                onClick={() => navigate(`/investigations/${id}/report`)}
                className="inline-flex items-center justify-center rounded-lg bg-electric-500 hover:bg-electric-400 text-raven-950 text-sm font-semibold px-5 py-2.5 transition-colors shrink-0"
              >
                View report
              </button>
            </div>
          )}

          {isFailed && (
            <div className="rounded-xl border border-rose-500/30 bg-rose-500/5 px-5 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <p className="text-rose-400 text-sm">{errorMessage || 'Analysis failed. Check server logs.'}</p>
              <button
                type="button"
                onClick={() => navigate(`/investigations/${id}`)}
                className="inline-flex items-center justify-center rounded-lg border border-raven-600 bg-raven-800/80 px-5 py-2.5 text-sm font-semibold text-raven-200 hover:border-electric-500/40 transition-colors shrink-0"
              >
                Back to files & setup
              </button>
            </div>
          )}
        </div>
        )}
      </main>
    </div>
  )
}
