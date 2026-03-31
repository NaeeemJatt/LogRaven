// LogRaven — New Investigation (dashboard-aligned)
import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'
import Navbar from '../components/layout/Navbar'
import { investigationsApi } from '../api/investigations'

export default function NewInvestigation() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
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

  const inputClass =
    'w-full rounded-lg bg-raven-900 border border-raven-600 text-raven-200 text-sm px-3 py-2.5 font-mono focus:outline-none focus:border-electric-500 focus:ring-1 focus:ring-electric-500/30 transition-colors placeholder-raven-600'

  return (
    <div className="min-h-screen bg-raven-950 text-raven-200">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1 text-sm text-raven-500 hover:text-electric-400 transition-colors mb-8"
        >
          <ChevronLeft className="h-4 w-4" />
          Investigations
        </Link>

        <div className="max-w-xl">
          <div className="mb-8">
            <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight mb-1">New investigation</h1>
            <p className="text-raven-500 text-sm">Name this case to begin uploading log files.</p>
          </div>

          <div className="rounded-xl border border-raven-700 bg-raven-900/80 p-6 sm:p-8 shadow-lg shadow-black/20">
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-[0.15em] text-raven-500 mb-1.5">
                  Investigation name
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Client ABC — March 2026 incident"
                  maxLength={200}
                  className={inputClass}
                />
                <p className="text-raven-600 text-xs font-mono mt-1.5">{name.length}/200</p>
              </div>

              {error && (
                <p className="text-rose-400 text-xs font-mono border border-rose-900/50 bg-rose-950/30 px-3 py-2 rounded-lg">
                  {error}
                </p>
              )}

              <div className="flex flex-wrap items-center justify-end gap-3 pt-2">
                <Link
                  to="/dashboard"
                  className="text-sm text-raven-500 hover:text-raven-300 transition-colors px-2 py-2"
                >
                  Cancel
                </Link>
                <button
                  type="submit"
                  disabled={loading}
                  className="inline-flex items-center justify-center rounded-lg bg-electric-500 hover:bg-electric-400 disabled:opacity-60 text-raven-950 text-sm font-semibold px-6 py-2.5 transition-colors"
                >
                  {loading ? 'Creating…' : 'Create investigation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </main>
    </div>
  )
}
