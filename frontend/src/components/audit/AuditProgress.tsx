// LogRaven — SOC 2 Audit Progress (Control Room stage)
//
// Polls /api/v1/audit/{auditId}/status every 5s. Renders a single-stage
// "scan console": prominent status, a horizontal pipeline, and a live log.

import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { Check, Loader2, WifiOff, Radio, Clock, X, Plug, Database, BrainCircuit, FileArchive } from 'lucide-react'
import type { AuditStatusResponse } from '../../types/audit'
import { getAuditStatus } from '../../api/compliance'

interface AuditProgressProps {
  auditId: string
  companyName: string
  onComplete: (results: AuditStatusResponse) => void
  onError: (error: string) => void
}

const STEPS = [
  { label: 'Connect',  detail: 'AWS account', icon: Plug },
  { label: 'Collect',  detail: 'CloudTrail evidence', icon: Database },
  { label: 'Analyze',  detail: 'Controls with AI', icon: BrainCircuit },
  { label: 'Package',  detail: 'Evidence pack', icon: FileArchive },
]

function checkedCount(percent: number): number {
  if (percent >= 75) return 4
  if (percent >= 50) return 3
  if (percent >= 30) return 2
  return 0
}

function stepLabel(step: string | null | undefined, percent: number): string {
  if (step === 'collecting') return 'Collecting AWS evidence...'
  if (step === 'sanitizing') return 'Sanitizing evidence...'
  if (step === 'mapping')    return 'Mapping to SOC 2 controls with AI...'
  if (step === 'saving')     return 'Saving results...'
  if (percent >= 75) return 'Generating evidence package...'
  if (percent >= 50) return 'Analyzing controls with AI...'
  if (percent >= 30) return 'Collecting AWS evidence...'
  return 'Connecting to AWS account...'
}

export default function AuditProgress({ auditId, companyName, onComplete, onError }: AuditProgressProps) {
  const [percent, setPercent]           = useState(0)
  const [currentStep, setCurrentStep]   = useState<string | null>(null)
  const [connectionLost, setConnectionLost] = useState(false)
  const [elapsed, setElapsed]           = useState(0)

  const doneRef     = useRef(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const timerRef    = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    timerRef.current = setInterval(() => setElapsed((s) => s + 1), 1000)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [])

  useEffect(() => {
    const poll = async () => {
      if (doneRef.current) return
      try {
        const data = await getAuditStatus(auditId)
        setConnectionLost(false)
        if (data.percent != null) setPercent(data.percent)
        setCurrentStep(data.step ?? null)
        if (data.status === 'complete') {
          doneRef.current = true
          if (intervalRef.current) clearInterval(intervalRef.current)
          if (timerRef.current)    clearInterval(timerRef.current)
          onComplete(data)
        } else if (data.status === 'failed') {
          doneRef.current = true
          if (intervalRef.current) clearInterval(intervalRef.current)
          if (timerRef.current)    clearInterval(timerRef.current)
          onError(data.error ?? 'Audit failed')
        }
      } catch {
        setConnectionLost(true)
      }
    }
    void poll()
    intervalRef.current = setInterval(() => { void poll() }, 5000)
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auditId])

  const handleCancel = () => {
    doneRef.current = true
    if (intervalRef.current) clearInterval(intervalRef.current)
    if (timerRef.current)    clearInterval(timerRef.current)
    onError('Audit cancelled by user')
  }

  const minutes = Math.floor(elapsed / 60)
  const seconds = elapsed % 60
  const checked = checkedCount(percent)

  // synthesize a small live log from progress
  const logLines = [
    ...STEPS.slice(0, checked).map((s) => ({ kind: 'done' as const, text: `${s.label.toLowerCase()} — ${s.detail} ✓` })),
    ...(checked < STEPS.length ? [{ kind: 'active' as const, text: stepLabel(currentStep, percent) }] : []),
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
      className="ops-panel overflow-hidden"
    >
      {/* Header */}
      <div className="px-6 py-4 border-b border-white/[0.07] flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 font-mono text-[10px] text-indigo-400 tracking-[0.22em] uppercase mb-0.5">
            <Radio className="w-3 h-3 animate-pulse" /> Assessing
          </div>
          <h2 className="font-display text-base font-bold text-text-primary truncate">{companyName}</h2>
        </div>
        <button
          onClick={handleCancel}
          className="btn-ghost px-3 py-1.5 rounded-lg text-xs font-medium text-text-secondary hover:text-text-primary inline-flex items-center gap-1.5 flex-shrink-0"
        >
          <X className="w-3.5 h-3.5" /> Cancel
        </button>
      </div>

      <div className="p-6 space-y-6">
        {/* Status block */}
        <div className="flex items-end justify-between gap-4">
          <div className="flex items-end gap-1.5">
            <span className="stat-value text-5xl font-semibold text-text-primary">{percent}</span>
            <span className="font-display text-2xl font-bold text-indigo-400 mb-1">%</span>
          </div>
          <span className="inline-flex items-center gap-1.5 text-xs text-text-muted font-mono mb-1">
            <Clock className="w-3.5 h-3.5" /> {minutes}m {String(seconds).padStart(2, '0')}s
          </span>
        </div>
        <div className="w-full h-2 rounded-full overflow-hidden bg-deep">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-indigo-600 to-indigo-400"
            animate={{ width: `${percent}%` }}
            transition={{ duration: 0.7, ease: 'easeOut' }}
          />
        </div>

        {/* Horizontal pipeline */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {STEPS.map(({ label, detail, icon: Icon }, i) => {
            const done = i < checked
            const active = i === checked
            return (
              <div
                key={label}
                className={`rounded-xl border p-3 transition-colors ${
                  done ? 'border-[#8FBDAD]/30 bg-[#8FBDAD]/[0.05]'
                  : active ? 'border-indigo-500/35 bg-indigo-500/[0.05]'
                  : 'border-white/[0.07] bg-white/[0.01]'
                }`}
              >
                <span className={`w-8 h-8 rounded-lg flex items-center justify-center border mb-2 ${
                  done ? 'bg-[#8FBDAD]/12 border-[#8FBDAD]/35 text-[#8FBDAD]'
                  : active ? 'bg-indigo-500/12 border-indigo-500/35 text-indigo-300'
                  : 'bg-white/[0.02] border-white/[0.08] text-text-muted'
                }`}>
                  {done ? <Check className="w-4 h-4" strokeWidth={3} />
                    : active ? <Loader2 className="w-4 h-4 animate-spin" />
                    : <Icon className="w-4 h-4" />}
                </span>
                <div className={`text-xs font-semibold ${done ? 'text-text-primary' : active ? 'text-indigo-300' : 'text-text-muted'}`}>{label}</div>
                <div className="text-[10px] text-text-muted truncate">{detail}</div>
              </div>
            )
          })}
        </div>

        {/* Live log */}
        <div className="rounded-xl border border-white/[0.07] bg-void/70 overflow-hidden">
          <div className="px-3 py-2 border-b border-white/[0.06] flex items-center justify-between">
            <span className="font-mono text-[10px] uppercase tracking-wider text-text-muted">Live log</span>
            <span className="font-mono text-[10px] text-text-ghost">polls every 5s</span>
          </div>
          <div className="p-3 font-mono text-[11px] space-y-1 min-h-[96px]">
            {logLines.map((l, i) => (
              <div key={i} className="flex gap-2">
                <span className={l.kind === 'done' ? 'text-[#8FBDAD]' : 'text-indigo-400'}>
                  {l.kind === 'done' ? '✓' : '▷'}
                </span>
                <span className={l.kind === 'done' ? 'text-text-muted' : 'text-text-secondary'}>{l.text}</span>
              </div>
            ))}
            <span className="inline-block w-1.5 h-3 bg-indigo-400/70 animate-pulse align-middle" />
          </div>
        </div>

        {connectionLost && (
          <div className="flex items-center gap-2 text-xs px-3 py-2.5 rounded-lg border border-threat-medium/30 bg-threat-medium/[0.07] text-threat-medium">
            <WifiOff className="w-4 h-4 flex-shrink-0" /> Connection lost, retrying…
          </div>
        )}
      </div>
    </motion.div>
  )
}
