import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ChevronLeft, CheckCircle2, Clock, Zap,
  GitMerge, FileText, ArrowRight, Cpu, Loader2
} from 'lucide-react'
import { useJobStatus } from '../hooks/useJobStatus'

const STEPS = [
  { key: 'queued',          label: 'Queued',               description: 'Investigation accepted and waiting to start.' },
  { key: 'parsing',         label: 'Log Parsing',          description: 'Extracting structured events from raw log files.' },
  { key: 'rule_engine',     label: 'Rule Engine',          description: 'Running detection rules against parsed events.' },
  { key: 'correlation',     label: 'Cross-File Correlation', description: 'Correlating events across multiple log sources.' },
  { key: 'ai_analysis',     label: 'AI Analysis',          description: 'Contextualizing and enriching findings.' },
  { key: 'building_report', label: 'Building Report',      description: 'Generating interactive findings view and PDF export.' },
  { key: 'complete',        label: 'Complete',             description: 'Analysis finished.' },
] as const

const STAGE_INDEX: Record<string, number> = {
  queued: 0, parsing: 1, rule_engine: 2, correlation: 3,
  ai_analysis: 4, building_report: 5, complete: 6,
}

const stageIcons: Record<string, React.ElementType> = {
  queued: Clock, parsing: FileText, rule_engine: Zap,
  correlation: GitMerge, ai_analysis: Cpu, building_report: FileText, complete: CheckCircle2,
}

function progressToIndex(progressStage: string | null | undefined, status: string | undefined): number {
  if (!status || status === 'draft') return 0
  if (status === 'complete') return 7
  if (status === 'failed') {
    const n = STAGE_INDEX[progressStage?.trim() ?? 'queued']
    return n !== undefined ? n : 0
  }
  const n = STAGE_INDEX[progressStage ?? (status === 'processing' ? 'parsing' : 'queued')]
  return n !== undefined ? n : (status === 'processing' ? 1 : 0)
}

const FILE_STATUS_STYLE: Record<string, string> = {
  pending: 'bg-white/[0.04] border-white/[0.08] text-text-muted',
  parsing: 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400',
  parsed:  'bg-teal-500/10 border-teal-500/20 text-teal-400',
  failed:  'bg-rose-500/10 border-rose-500/20 text-rose-400',
}

export default function JobStatus() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [elapsed, setElapsed] = useState(0)

  const {
    status, progressStage, errorMessage, files,
    isLoading, isError, isComplete, isFailed, isDraft,
  } = useJobStatus(id ?? null)

  useEffect(() => {
    if (!isComplete && !isFailed) {
      const t = setInterval(() => setElapsed((e) => e + 1), 1000)
      return () => clearInterval(t)
    }
  }, [isComplete, isFailed])

  useEffect(() => {
    if (isComplete) {
      const t = setTimeout(() => navigate(`/investigations/${id}/report`), 2000)
      return () => clearTimeout(t)
    }
  }, [isComplete, id, navigate])

  const formatTime = (s: number) => `${Math.floor(s / 60)}m ${s % 60}s`
  const currentIdx = progressToIndex(progressStage, status)
  const allDone = status === 'complete'
  const completedCount = allDone ? STEPS.length : currentIdx
  const progress = (completedCount / STEPS.length) * 100

  if (isLoading) {
    return (
      <div className="pt-16 min-h-screen flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
      </div>
    )
  }

  if (isError || status === undefined) {
    return (
      <div className="pt-16 min-h-screen flex flex-col items-center justify-center gap-4 px-4">
        <div className="px-5 py-4 rounded-xl border border-rose-500/20 bg-rose-500/5 text-rose-400 text-sm text-center max-w-md">
          Could not load investigation status. Check that you are signed in and the investigation exists.
        </div>
        <Link to="/dashboard" className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors">
          ← Back to dashboard
        </Link>
      </div>
    )
  }

  if (isDraft) {
    return (
      <div className="pt-16 min-h-screen flex flex-col items-center justify-center gap-4 px-4">
        <div className="text-center max-w-md">
          <h1 className="font-display text-xl font-semibold text-text-primary mb-2">Analysis not started</h1>
          <p className="text-text-muted text-sm mb-6">
            Upload log files and run analysis from the setup page to track the pipeline here.
          </p>
          <Link
            to={`/investigations/${id}`}
            className="btn-sovereign inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white"
          >
            Go to files &amp; setup
          </Link>
        </div>
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
          className="mb-6"
        >
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-1.5 text-text-muted hover:text-text-secondary text-sm mb-4 transition-colors"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            Back to investigations
          </Link>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 mb-0.5">
                {!isFailed && !isComplete && (
                  <motion.span
                    animate={{ opacity: [1, 0.4, 1] }}
                    transition={{ repeat: Infinity, duration: 1.2 }}
                    className="w-2 h-2 rounded-full bg-indigo-400"
                  />
                )}
                {isComplete && <span className="w-2 h-2 rounded-full bg-teal-400" />}
                {isFailed && <span className="w-2 h-2 rounded-full bg-rose-400" />}
                <h1 className="font-display font-bold text-text-primary text-2xl">
                  {isFailed ? 'Analysis failed' : isComplete ? 'Analysis complete' : 'Analysis running'}
                </h1>
              </div>
              <p className="text-text-secondary text-sm">
                {isFailed
                  ? errorMessage || 'Something went wrong during processing.'
                  : isComplete
                    ? 'Opening your report shortly…'
                    : `Pipeline running · ${formatTime(elapsed)} elapsed`}
              </p>
            </div>
            {isComplete && (
              <Link
                to={`/investigations/${id}/report`}
                className="btn-sovereign flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-semibold text-white self-start"
              >
                View report <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            )}
          </div>
        </motion.div>

        {/* Progress bar */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="mb-6"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="font-mono text-[10px] text-text-muted tracking-widest uppercase">
              {completedCount} of {STEPS.length} stages complete
            </span>
            <span className="font-mono text-sm font-bold text-indigo-400">{Math.round(progress)}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 1, ease: 'easeOut' }}
              className="h-full rounded-full bg-gradient-to-r from-indigo-600 to-indigo-400"
            />
          </div>
        </motion.div>

        {/* Two-column layout */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">

          {/* Pipeline stages */}
          <div className="xl:col-span-2">
            <div className="rounded-2xl border border-white/[0.06] bg-surface/40 backdrop-blur p-6">
              {STEPS.map((step, idx) => {
                const stepDone = allDone || currentIdx > idx
                const stepActive = !allDone && !isFailed && currentIdx === idx
                const stepFailedHere = isFailed && currentIdx === idx
                const isPending = !stepDone && !stepActive && !stepFailedHere
                const Icon = stageIcons[step.key] || Cpu
                const isLast = idx === STEPS.length - 1

                return (
                  <motion.div
                    key={step.key}
                    initial={{ opacity: 0, x: -16 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.07 }}
                    className="flex gap-5"
                  >
                    {/* Timeline column */}
                    <div className="flex flex-col items-center flex-shrink-0">
                      <div
                        className={`relative w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all duration-500 ${
                          stepDone ? 'border-teal-500/60 bg-teal-500/15'
                          : stepActive ? 'border-indigo-500/60 bg-indigo-500/15'
                          : stepFailedHere ? 'border-rose-500/60 bg-rose-500/15'
                          : 'border-white/10 bg-white/[0.03]'
                        }`}
                      >
                        {stepDone && <CheckCircle2 className="w-4 h-4 text-teal-400" />}
                        {stepActive && (
                          <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1.5, ease: 'linear' }}>
                            <Cpu className="w-4 h-4 text-indigo-400" />
                          </motion.div>
                        )}
                        {stepFailedHere && <Icon className="w-4 h-4 text-rose-400" />}
                        {isPending && <Icon className="w-4 h-4 text-text-muted" />}

                        {stepActive && (
                          <motion.div
                            animate={{ scale: [1, 1.6], opacity: [0.6, 0] }}
                            transition={{ repeat: Infinity, duration: 1.5 }}
                            className="absolute inset-0 rounded-full border-2 border-indigo-400"
                          />
                        )}
                      </div>
                      {!isLast && (
                        <div className={`w-0.5 flex-1 min-h-8 mt-2 transition-colors duration-500 ${
                          stepDone ? 'bg-teal-500/30' : 'bg-white/[0.06]'
                        }`} />
                      )}
                    </div>

                    {/* Content */}
                    <div className={`flex-1 ${isLast ? 'pb-0' : 'pb-8'}`}>
                      <div className="flex items-center justify-between gap-4 mb-1">
                        <div className="flex items-center gap-2">
                          <span className={`font-display font-semibold text-sm ${
                            stepDone ? 'text-text-secondary'
                            : stepActive ? 'text-indigo-300'
                            : stepFailedHere ? 'text-rose-300'
                            : 'text-text-muted'
                          }`}>
                            {step.label}
                            {stepFailedHere && (
                              <span className="ml-2 font-mono text-[10px] text-rose-400 uppercase tracking-wider">failed</span>
                            )}
                          </span>
                          {stepActive && (
                            <motion.span
                              animate={{ opacity: [1, 0.4, 1] }}
                              transition={{ repeat: Infinity, duration: 1.2 }}
                              className="font-mono text-[10px] text-indigo-400"
                            >
                              running
                            </motion.span>
                          )}
                        </div>
                      </div>
                      {(stepActive || stepFailedHere) && (
                        <p className="text-xs text-text-muted leading-relaxed">{step.description}</p>
                      )}
                    </div>
                  </motion.div>
                )
              })}
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            {/* Files uploaded stat */}
            <div className="grid grid-cols-3 xl:grid-cols-1 gap-3">
              {[
                { label: 'Files uploaded', value: String(files.length) },
                { label: 'Parsed files', value: String(files.filter(f => f.status === 'parsed').length) },
                { label: 'Events parsed', value: files.reduce((acc, f) => acc + (f.event_count ?? 0), 0).toLocaleString() },
              ].map(({ label, value }) => (
                <div key={label} className="p-4 rounded-xl border border-white/[0.06] bg-surface/40">
                  <div className="font-display font-bold text-xl text-text-primary">{value}</div>
                  <div className="font-mono text-[10px] text-text-muted tracking-wide mt-0.5">{label}</div>
                </div>
              ))}
            </div>

            {/* Complete CTA / report link */}
            {(isComplete || (!isFailed && files.length > 0)) && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className={`p-5 rounded-2xl border ${
                  isComplete
                    ? 'border-teal-500/20 bg-teal-500/5'
                    : 'border-indigo-500/15 bg-indigo-500/5'
                }`}
              >
                <div className="mb-4">
                  <div className="text-sm font-medium text-text-primary mb-0.5">
                    {isComplete ? 'Analysis complete' : 'Pipeline running'}
                  </div>
                  <div className="text-xs text-text-muted">
                    {isComplete ? 'Your report is ready to view.' : `${files.length} file${files.length !== 1 ? 's' : ''} being analyzed`}
                  </div>
                </div>
                <Link
                  to={`/investigations/${id}/report`}
                  className="btn-sovereign w-full flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-semibold text-white"
                >
                  View report <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </motion.div>
            )}

            {/* File table */}
            {files.length > 0 && (
              <div className="rounded-2xl border border-white/[0.06] bg-surface/40 overflow-hidden">
                <div className="px-4 py-3 border-b border-white/[0.06]">
                  <div className="font-mono text-[10px] text-text-muted tracking-widest uppercase">Files</div>
                </div>
                <div className="divide-y divide-white/[0.04]">
                  {files.map((f) => (
                    <div key={f.id} className="px-4 py-3">
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="font-mono text-xs text-text-secondary truncate">{f.filename}</span>
                        <span className={`font-mono text-[10px] px-2 py-0.5 rounded border uppercase tracking-wider flex-shrink-0 ${FILE_STATUS_STYLE[f.status] ?? FILE_STATUS_STYLE.pending}`}>
                          {f.status}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] text-text-ghost">{f.source_type}</span>
                        {f.event_count != null && (
                          <>
                            <span className="text-text-ghost">·</span>
                            <span className="font-mono text-[10px] text-text-ghost">{f.event_count.toLocaleString()} events</span>
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {isFailed && (
              <div className="p-4 rounded-xl border border-rose-500/20 bg-rose-500/5">
                <div className="text-sm font-medium text-rose-400 mb-2">Analysis failed</div>
                <p className="text-xs text-rose-400/70 mb-3">{errorMessage || 'Something went wrong during processing.'}</p>
                <Link
                  to={`/investigations/${id}`}
                  className="btn-ghost w-full flex items-center justify-center px-4 py-2 rounded-lg text-sm font-medium text-text-secondary"
                >
                  Back to files &amp; setup
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
