// LogRaven — SOC 2 Audit Progress Component
//
// Polls /api/v1/audit/{auditId}/status every 5s.
// Shows animated progress bar, step checklist, and elapsed timer.
// Calls onComplete when done, onError on failure or cancel.

import { useEffect, useRef, useState } from 'react'
import type { AuditStatusResponse } from '../../types/audit'
import { getAuditStatus } from '../../api/compliance'

interface AuditProgressProps {
  auditId: string
  companyName: string
  onComplete: (results: AuditStatusResponse) => void
  onError: (error: string) => void
}

const STEPS = [
  'Connecting to AWS account',
  'Collecting CloudTrail evidence',
  'Analyzing controls with AI',
  'Generating evidence package',
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

export default function AuditProgress({
  auditId,
  companyName,
  onComplete,
  onError,
}: AuditProgressProps) {
  const [percent, setPercent]           = useState(0)
  const [currentStep, setCurrentStep]   = useState<string | null>(null)
  const [connectionLost, setConnectionLost] = useState(false)
  const [elapsed, setElapsed]           = useState(0)

  // Refs so the interval callbacks always have latest values without re-creating
  const doneRef     = useRef(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const timerRef    = useRef<ReturnType<typeof setInterval> | null>(null)

  // ── Elapsed timer ──────────────────────────────────────────────────────────
  useEffect(() => {
    timerRef.current = setInterval(() => {
      setElapsed((s) => s + 1)
    }, 1000)
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [])

  // ── Polling ────────────────────────────────────────────────────────────────
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

    // Poll immediately, then every 5 s
    void poll()
    intervalRef.current = setInterval(() => { void poll() }, 5000)

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
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

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div
        className="rounded-lg p-8 border"
        style={{ backgroundColor: '#161B22', borderColor: '#30363D' }}
      >
        {/* Header */}
        <h2 className="text-xl font-bold mb-1" style={{ color: '#E6EDF3' }}>
          Running SOC 2 Audit
        </h2>
        <p className="text-sm mb-6" style={{ color: '#8B949E' }}>
          {companyName}
        </p>

        {/* Progress bar */}
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-mono" style={{ color: '#8B949E' }}>
            {stepLabel(currentStep, percent)}
          </span>
          <span className="text-xs font-mono font-semibold" style={{ color: '#2F81F7' }}>
            {percent}%
          </span>
        </div>
        <div
          className="w-full h-2 rounded-full overflow-hidden mb-6"
          style={{ backgroundColor: '#0D1117' }}
        >
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{ width: `${percent}%`, backgroundColor: '#2F81F7' }}
          />
        </div>

        {/* Step checklist */}
        <div className="space-y-3 mb-6">
          {STEPS.map((label, i) => {
            const done = i < checked
            return (
              <div key={label} className="flex items-center gap-3">
                <span
                  className="w-5 h-5 flex items-center justify-center rounded-full text-xs font-bold flex-shrink-0"
                  style={{
                    backgroundColor: done ? '#3FB950' : '#30363D',
                    color: done ? '#0D1117' : '#8B949E',
                  }}
                >
                  {done ? '✓' : '○'}
                </span>
                <span
                  className="text-sm"
                  style={{ color: done ? '#3FB950' : '#8B949E' }}
                >
                  {label}
                </span>
              </div>
            )
          })}
        </div>

        {/* Elapsed time */}
        <p className="text-xs mb-6" style={{ color: '#8B949E' }}>
          Running for {minutes} minute{minutes !== 1 ? 's' : ''}{' '}
          {seconds} second{seconds !== 1 ? 's' : ''}
        </p>

        {/* Connection lost banner */}
        {connectionLost && (
          <p
            className="text-xs mb-4 px-3 py-2 rounded border"
            style={{
              color: '#D29922',
              backgroundColor: '#1a1800',
              borderColor: '#D29922',
            }}
          >
            Connection lost, retrying...
          </p>
        )}

        {/* Cancel button */}
        <button
          onClick={handleCancel}
          className="w-full py-2 rounded text-sm font-medium border transition-colors hover:opacity-80"
          style={{
            backgroundColor: 'transparent',
            borderColor: '#30363D',
            color: '#8B949E',
          }}
        >
          Cancel
        </button>
      </div>
    </div>
  )
}
