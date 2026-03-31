// LogRaven — Register (dashboard-aligned; Login page unchanged)
import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { Shield } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'

export default function Register() {
  const { register } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }

    setLoading(true)
    try {
      await register(email, password)
    } catch (err: unknown) {
      const detail =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined
      setError(detail ?? 'Registration failed.')
    } finally {
      setLoading(false)
    }
  }

  const inputClass =
    'w-full rounded-lg bg-raven-900 border border-raven-600 text-raven-200 text-sm px-3 py-2.5 font-mono focus:outline-none focus:border-electric-500 focus:ring-1 focus:ring-electric-500/30 transition-colors placeholder-raven-600'

  return (
    <div className="min-h-screen bg-raven-950 text-raven-200 flex flex-col">
      <header className="border-b border-raven-800/90 bg-raven-950/95">
        <div className="mx-auto flex h-14 max-w-7xl items-center px-4 sm:px-6">
          <Link to="/" className="group flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-electric-500/35 bg-electric-500/10 text-electric-400">
              <Shield className="h-4 w-4" strokeWidth={2} aria-hidden />
            </span>
            <span className="text-base font-bold tracking-tight text-white">LogRaven</span>
          </Link>
        </div>
      </header>

      <div className="flex flex-1 items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          <div className="mb-8 text-center">
            <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight mb-1">Create account</h1>
            <p className="text-raven-500 text-sm">Watch your logs. Find the threat.</p>
          </div>

          <div className="rounded-xl border border-raven-700 bg-raven-900/80 p-6 sm:p-8 shadow-lg shadow-black/20">
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-[0.15em] text-raven-500 mb-1.5">
                  Email
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="operator@example.com"
                  className={inputClass}
                  autoComplete="email"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-[0.15em] text-raven-500 mb-1.5">
                  Password
                </label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 8 characters"
                  className={inputClass}
                  autoComplete="new-password"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-[0.15em] text-raven-500 mb-1.5">
                  Confirm password
                </label>
                <input
                  type="password"
                  required
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  placeholder="Repeat password"
                  className={inputClass}
                  autoComplete="new-password"
                />
              </div>

              {error && (
                <p className="text-rose-400 text-xs font-mono border border-rose-900/50 bg-rose-950/30 px-3 py-2 rounded-lg">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full inline-flex items-center justify-center rounded-lg bg-electric-500 hover:bg-electric-400 disabled:opacity-60 text-raven-950 text-sm font-semibold py-2.5 transition-colors"
              >
                {loading ? 'Creating account…' : 'Create account'}
              </button>
            </form>

            <p className="text-raven-500 text-sm mt-6 text-center">
              Already have an account?{' '}
              <Link to="/login" className="text-electric-400 hover:text-electric-300 font-medium transition-colors">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
