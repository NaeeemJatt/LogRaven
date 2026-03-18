// LogRaven — New Investigation Page
import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import Navbar from '../components/layout/Navbar'
import { investigationsApi } from '../api/investigations'

export default function NewInvestigation() {
  const navigate        = useNavigate()
  const [name, setName] = useState('')
  const [error, setError]     = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) { setError('Investigation name is required.'); return }
    setError(null)
    setLoading(true)
    try {
      const res = await investigationsApi.create(name.trim())
      navigate(`/investigations/${res.data.id}`)
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Failed to create investigation.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-raven-900">
      <Navbar />

      <main className="max-w-lg mx-auto px-6 py-10">
        <Link
          to="/dashboard"
          className="text-raven-400 text-xs hover:text-electric-500 transition-colors mb-6 inline-block tracking-wide"
        >
          ← Investigations
        </Link>

        <div className="bg-raven-800 border border-raven-700 p-8">
          <h1 className="text-white text-lg font-semibold mb-1">New Investigation</h1>
          <p className="text-raven-400 text-sm mb-6">
            Name this investigation to begin uploading log files.
          </p>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-xs uppercase tracking-widest text-raven-400 mb-1">
                Investigation Name
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Client ABC — March 2026 Incident"
                maxLength={200}
                className="w-full bg-raven-900 border border-raven-600 text-raven-200 text-sm px-3 py-2 rounded-none font-mono focus:outline-none focus:border-electric-500 transition-colors placeholder-raven-600"
              />
              <p className="text-raven-600 text-xs font-mono mt-1">{name.length}/200</p>
            </div>

            {error && (
              <p className="text-red-400 text-xs font-mono">— {error}</p>
            )}

            <div className="flex items-center justify-end gap-4 pt-2">
              <Link
                to="/dashboard"
                className="text-raven-400 text-xs hover:text-raven-200 transition-colors"
              >
                Cancel
              </Link>
              <button
                type="submit"
                disabled={loading}
                className="bg-electric-500 hover:bg-electric-400 disabled:opacity-60 text-white text-xs font-medium tracking-wide px-5 py-2 rounded-none transition-colors uppercase"
              >
                {loading ? 'Creating...' : 'Create Investigation'}
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  )
}
