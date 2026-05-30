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

  return (
    <div className="min-h-screen bg-void text-text-primary flex flex-col">
      <header className="border-b border-white/[0.05] bg-void/95">
        <div className="flex h-14 items-center px-6">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center">
              <Shield className="w-4 h-4 text-indigo-400" strokeWidth={2} />
            </div>
            <span className="font-display font-bold text-base text-text-primary tracking-tight">
              Log<span className="text-indigo-400">Raven</span>
            </span>
          </Link>
        </div>
      </header>

      <div className="flex flex-1 items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          <div className="mb-8 text-center">
            <div className="font-mono text-[10px] text-indigo-400 tracking-widest uppercase mb-2">Security Workspace</div>
            <h1 className="font-display text-2xl sm:text-3xl font-bold text-text-primary tracking-tight mb-1">Create account</h1>
            <p className="text-text-muted text-sm">Watch your logs. Find the threat.</p>
          </div>

          <div className="rounded-2xl border border-white/[0.06] bg-surface/60 backdrop-blur-xl p-6 sm:p-8">
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-[0.15em] text-text-muted mb-1.5">
                  Email
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="operator@example.com"
                  className="sovereign-input w-full text-sm px-3 py-2.5 font-mono"
                  autoComplete="email"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-[0.15em] text-text-muted mb-1.5">
                  Password
                </label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 8 characters"
                  className="sovereign-input w-full text-sm px-3 py-2.5 font-mono"
                  autoComplete="new-password"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-[0.15em] text-text-muted mb-1.5">
                  Confirm password
                </label>
                <input
                  type="password"
                  required
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  placeholder="Repeat password"
                  className="sovereign-input w-full text-sm px-3 py-2.5 font-mono"
                  autoComplete="new-password"
                />
              </div>

              {error && (
                <p className="text-rose-400 text-xs font-mono border border-rose-500/20 bg-rose-500/5 px-3 py-2 rounded-lg">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="btn-sovereign w-full text-sm font-semibold py-2.5 rounded-lg transition-colors"
              >
                {loading ? 'Creating account…' : 'Create account'}
              </button>
            </form>

            <p className="text-text-muted text-sm mt-6 text-center">
              Already have an account?{' '}
              <Link to="/login" className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
