import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ChevronLeft, ArrowRight, Shield, Loader2 } from 'lucide-react'
import { investigationsApi } from '../api/investigations'

const SUGGESTIONS = [
  'Production server anomaly',
  'CloudTrail lateral movement review',
  'Brute force detection sweep',
  'Privilege escalation audit',
  'Exfiltration detection',
  'Windows event log forensics',
]

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

        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1.5 text-text-muted hover:text-text-secondary text-sm mb-8 transition-colors"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
          Back to investigations
        </Link>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8 items-start">

          {/* Form */}
          <div className="xl:col-span-2">
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="rounded-2xl border border-white/[0.06] bg-surface/40 backdrop-blur overflow-hidden"
            >
              <div className="px-6 py-5 border-b border-white/[0.06]">
                <div className="font-mono text-[10px] text-indigo-400 tracking-widest uppercase mb-1">New investigation</div>
                <h1 className="font-display font-bold text-text-primary text-xl leading-tight">
                  Name your investigation
                </h1>
              </div>

              <form onSubmit={handleSubmit} className="p-6 space-y-5">
                <div>
                  <label className="block font-mono text-[10px] text-text-muted tracking-widest uppercase mb-2">
                    Investigation name
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Prod server incident — May 28"
                    maxLength={200}
                    className="sovereign-input w-full px-4 py-3.5 rounded-xl text-base"
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') void handleSubmit()
                    }}
                  />
                  <div className="flex items-center justify-between mt-1.5">
                    <p className="text-[11px] text-text-muted">
                      Give it a descriptive name — you&apos;ll add log files in the next step.
                    </p>
                    <span className="font-mono text-[10px] text-text-ghost">{name.length}/200</span>
                  </div>
                </div>

                {/* Suggestions */}
                <div>
                  <div className="font-mono text-[10px] text-text-muted tracking-widest uppercase mb-2.5">Quick start templates</div>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {SUGGESTIONS.map((s) => (
                      <button
                        key={s}
                        type="button"
                        onClick={() => setName(s)}
                        className="px-3 py-2.5 rounded-xl border border-white/[0.06] text-xs text-text-muted hover:text-text-secondary hover:border-indigo-500/20 hover:bg-indigo-500/5 transition-all text-left"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>

                {error && (
                  <div className="px-4 py-3 rounded-xl border border-rose-500/20 bg-rose-500/5 font-mono text-xs text-rose-400">
                    {error}
                  </div>
                )}

                <div className="flex items-center gap-3 pt-1">
                  <button
                    type="submit"
                    disabled={loading || !name.trim()}
                    className="btn-sovereign flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white disabled:opacity-40"
                  >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                    {loading ? 'Creating…' : 'Continue to file upload'}
                    {!loading && <ArrowRight className="w-4 h-4" />}
                  </button>
                  <Link to="/dashboard" className="btn-ghost px-4 py-3 rounded-xl text-sm font-medium text-text-secondary">
                    Cancel
                  </Link>
                </div>
              </form>
            </motion.div>
          </div>

          {/* Sidebar */}
          <motion.div
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.15 }}
            className="space-y-4"
          >
            <div className="rounded-2xl border border-white/[0.06] bg-surface/40 overflow-hidden">
              <div className="px-5 py-3.5 border-b border-white/[0.06]">
                <span className="font-mono text-[10px] text-text-muted tracking-widest uppercase">What happens next</span>
              </div>
              <div className="p-5 space-y-4">
                {[
                  { label: 'Upload log files', desc: 'Drag in any log format — EVTX, syslog, CloudTrail, Nginx' },
                  { label: 'Run 847 detection rules', desc: 'Every event checked against threat detection patterns' },
                  { label: 'Correlate across sources', desc: 'Find multi-stage attacks spanning multiple log files' },
                  { label: 'AI enrichment (optional)', desc: 'Gemini summarizes and contextualizes findings' },
                ].map(({ label, desc }, i) => (
                  <div key={label} className="flex gap-3 items-start">
                    <span className="font-mono text-[10px] text-indigo-400/60 mt-0.5 flex-shrink-0 w-4">
                      {String(i + 1).padStart(2, '0')}
                    </span>
                    <div>
                      <div className="text-sm font-medium text-text-primary mb-0.5">{label}</div>
                      <div className="text-xs text-text-muted leading-relaxed">{desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="p-4 rounded-xl border border-indigo-500/15 bg-indigo-500/5">
              <div className="flex items-center gap-2 mb-1.5">
                <Shield className="w-3.5 h-3.5 text-indigo-400" />
                <span className="font-mono text-[10px] text-indigo-400 tracking-widest uppercase">Avg time to results</span>
              </div>
              <p className="text-sm font-bold text-text-primary">Under 5 minutes</p>
              <p className="text-xs text-text-muted mt-0.5">for a typical 4-file investigation</p>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  )
}
