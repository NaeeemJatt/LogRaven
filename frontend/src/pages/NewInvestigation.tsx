import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ChevronLeft, ArrowRight, Loader2, Tag, UploadCloud, Radar, Check, Clock,
} from 'lucide-react'
import { investigationsApi } from '../api/investigations'

const SUGGESTIONS = [
  'Production server anomaly',
  'CloudTrail lateral movement review',
  'Brute force detection sweep',
  'Privilege escalation audit',
  'Exfiltration detection',
  'Windows event log forensics',
]

const WIZARD_STEPS = [
  { n: 1, label: 'Name', hint: 'Identify the case', icon: Tag },
  { n: 2, label: 'Upload logs', hint: 'Add evidence', icon: UploadCloud },
  { n: 3, label: 'Analyze', hint: 'Detect & correlate', icon: Radar },
]

// ── Journey rail ──────────────────────────────────────────
function WizardRail({ active }: { active: number }) {
  return (
    <div className="flex items-center">
      {WIZARD_STEPS.map((s, i) => {
        const isActive = s.n === active
        const isDone = s.n < active
        const Icon = s.icon
        return (
          <React.Fragment key={s.n}>
            <div className="flex items-center gap-3 min-w-0">
              <span className={`w-10 h-10 rounded-xl flex items-center justify-center border flex-shrink-0 transition-colors ${
                isActive ? 'bg-indigo-500/15 border-indigo-500/40 text-indigo-300'
                : isDone ? 'bg-[#8FBDAD]/12 border-[#8FBDAD]/35 text-[#8FBDAD]'
                : 'bg-white/[0.02] border-white/[0.08] text-text-muted'
              }`}
                style={isActive ? { boxShadow: '0 0 0 1px rgba(227,181,126,0.22)' } : undefined}
              >
                {isDone ? <Check className="w-4 h-4" strokeWidth={3} /> : <Icon className="w-4 h-4" />}
              </span>
              <div className="hidden sm:block min-w-0">
                <div className={`text-sm font-semibold leading-tight ${isActive ? 'text-text-primary' : 'text-text-muted'}`}>
                  {s.label}
                </div>
                <div className="text-[10px] text-text-muted truncate">{s.hint}</div>
              </div>
            </div>
            {i < WIZARD_STEPS.length - 1 && (
              <div className={`flex-1 h-px mx-3 ${isDone ? 'bg-[#8FBDAD]/30' : 'bg-white/[0.08]'}`} />
            )}
          </React.Fragment>
        )
      })}
    </div>
  )
}

export default function NewInvestigation() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!name.trim()) {
      setError('Investigation name is required.')
      return
    }
    setError(null)
    setLoading(true)
    try {
      const res = await investigationsApi.create(name.trim())
      navigate(`/investigations/${res.data.id}`)
    } catch (err: unknown) {
      const detail =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined
      setError(detail ?? 'Failed to create investigation.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="pt-16 min-h-screen">
      <div className="px-4 sm:px-6 lg:px-8 py-8">

        {/* Header — matches Investigation / JobStatus pages */}
        <motion.div
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
          className="mb-6"
        >
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-1.5 text-text-muted hover:text-text-secondary text-sm mb-4 transition-colors"
          >
            <ChevronLeft className="w-3.5 h-3.5" /> Back to investigations
          </Link>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h1 className="font-display font-bold text-text-primary text-2xl">New investigation</h1>
              <p className="text-text-secondary text-sm">Name your case, then add evidence and run analysis.</p>
            </div>
            <span className="inline-flex items-center gap-1.5 font-mono text-[10px] text-text-muted self-start">
              <Clock className="w-3 h-3" /> Results in under 5 min
            </span>
          </div>
        </motion.div>

        {/* Journey rail */}
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
          className="ops-panel p-5 mb-5"
        >
          <WizardRail active={1} />
        </motion.div>

        {/* Two-column layout — mirrors JobStatus */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">

          {/* Step card */}
          <div className="xl:col-span-2">
            <motion.div
              initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.08 }}
              className="ops-panel overflow-hidden"
            >
              <div className="px-6 py-5 border-b border-white/[0.07]">
                <div className="font-mono text-[10px] text-indigo-400 tracking-[0.18em] uppercase mb-1">Step 1 of 3</div>
                <h2 className="font-display font-bold text-text-primary text-xl leading-tight">Name your investigation</h2>
                <p className="text-sm text-text-muted mt-1">A descriptive name helps you find this case later. You'll add log files next.</p>
              </div>

              <form onSubmit={handleSubmit} className="p-6 space-y-6">
                <div>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Prod server incident — May 28"
                    maxLength={200}
                    className="sovereign-input w-full px-4 py-4 rounded-xl text-lg"
                    autoFocus
                    onKeyDown={(e) => { if (e.key === 'Enter') void handleSubmit() }}
                  />
                  <div className="flex items-center justify-end mt-1.5">
                    <span className="font-mono text-[10px] text-text-ghost">{name.length}/200</span>
                  </div>
                </div>

                <div>
                  <div className="font-mono text-[10px] text-text-muted tracking-[0.16em] uppercase mb-2.5">Quick-start templates</div>
                  <div className="flex flex-wrap gap-2">
                    {SUGGESTIONS.map((s) => {
                      const sel = name === s
                      return (
                        <button
                          key={s}
                          type="button"
                          onClick={() => setName(s)}
                          className={`px-3 py-2 rounded-lg border text-xs text-left transition-all ${
                            sel ? 'border-indigo-500/45 bg-indigo-500/10 text-indigo-200'
                                : 'border-white/[0.07] text-text-muted hover:text-text-secondary hover:border-indigo-500/20 hover:bg-white/[0.02]'
                          }`}
                        >
                          {s}
                        </button>
                      )
                    })}
                  </div>
                </div>

                {error && (
                  <div className="px-4 py-3 rounded-xl border border-rose-500/20 bg-rose-500/5 font-mono text-xs text-rose-400">
                    {error}
                  </div>
                )}
              </form>

              <div className="px-6 py-4 border-t border-white/[0.07] flex items-center justify-end gap-2">
                <Link to="/dashboard" className="btn-ghost px-4 py-2.5 rounded-lg text-sm font-medium text-text-secondary">
                  Cancel
                </Link>
                <button
                  type="button"
                  onClick={() => void handleSubmit()}
                  disabled={loading || !name.trim()}
                  className="btn-sovereign flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                  {loading ? 'Creating…' : 'Continue to upload'}
                  {!loading && <ArrowRight className="w-4 h-4" />}
                </button>
              </div>
            </motion.div>
          </div>

          {/* Sidebar — what happens next */}
          <motion.div
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.16 }}
            className="space-y-4"
          >
            <div className="rounded-2xl border border-white/[0.06] bg-surface/40 overflow-hidden">
              <div className="px-4 py-3 border-b border-white/[0.06]">
                <div className="font-mono text-[10px] text-text-muted tracking-widest uppercase">What happens next</div>
              </div>
              <div className="divide-y divide-white/[0.04]">
                {WIZARD_STEPS.map((s) => {
                  const Icon = s.icon
                  return (
                    <div key={s.n} className="flex items-center gap-3 px-4 py-3.5">
                      <span className="w-8 h-8 rounded-lg border border-white/[0.08] bg-white/[0.02] flex items-center justify-center flex-shrink-0 text-text-muted">
                        <Icon className="w-4 h-4" />
                      </span>
                      <div className="min-w-0">
                        <div className="text-sm font-semibold text-text-secondary leading-tight">{s.label}</div>
                        <div className="text-[11px] text-text-muted truncate">{s.hint}</div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            <div className="p-4 rounded-2xl border border-indigo-500/15 bg-indigo-500/5">
              <div className="text-sm font-medium text-text-primary mb-1">Tip</div>
              <p className="text-xs text-text-muted leading-relaxed">
                Use a name that captures the incident and date so you can spot it later at a glance.
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  )
}
