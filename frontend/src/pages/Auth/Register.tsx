// LogRaven — Register Page
import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'

export default function Register() {
  const { register } = useAuth()
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm]   = useState('')
  const [error, setError]       = useState<string | null>(null)
  const [loading, setLoading]   = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (password !== confirm) { setError('Passwords do not match.'); return }
    if (password.length < 8)  { setError('Password must be at least 8 characters.'); return }

    setLoading(true)
    try {
      await register(email, password)
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Registration failed.')
    } finally {
      setLoading(false)
    }
  }

  const inputClass =
    'w-full bg-raven-900 border border-raven-600 text-raven-200 text-sm px-3 py-2 rounded-none font-mono focus:outline-none focus:border-electric-500 transition-colors placeholder-raven-600'

  return (
    <div className="min-h-screen bg-raven-950 flex items-center justify-center px-4">
      <div className="w-full max-w-sm bg-raven-800 border border-raven-700 p-8">

        {/* Brand */}
        <div className="mb-6">
          <p className="font-mono font-bold tracking-widest text-electric-500 text-lg uppercase mb-1">
            LOGRAVEN
          </p>
          <p className="text-raven-400 text-xs tracking-widest uppercase">
            Watch your logs. Find the threat.
          </p>
          <div className="mt-4 border-t border-raven-700" />
        </div>

        <h2 className="text-raven-200 text-sm font-semibold mb-4 uppercase tracking-widest">
          Create Account
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs uppercase tracking-widest text-raven-400 mb-1">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="operator@example.com"
              className={inputClass}
            />
          </div>

          <div>
            <label className="block text-xs uppercase tracking-widest text-raven-400 mb-1">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="min 8 characters"
              className={inputClass}
            />
          </div>

          <div>
            <label className="block text-xs uppercase tracking-widest text-raven-400 mb-1">Confirm Password</label>
            <input
              type="password"
              required
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="repeat password"
              className={inputClass}
            />
          </div>

          {error && (
            <p className="text-red-400 text-xs font-mono">— {error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-electric-500 hover:bg-electric-400 disabled:opacity-60 text-white text-sm font-medium tracking-wide py-2 rounded-none transition-colors mt-2"
          >
            {loading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>

        <p className="text-raven-400 text-xs mt-6">
          Already have an account?{' '}
          <Link to="/login" className="text-electric-500 hover:text-electric-400 transition-colors">
            Sign In
          </Link>
        </p>
      </div>
    </div>
  )
}
