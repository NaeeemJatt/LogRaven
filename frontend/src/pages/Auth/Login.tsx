// LogRaven — Login Page
import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'

export default function Login() {
  const { login } = useAuth()
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState<string | null>(null)
  const [loading, setLoading]   = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(email, password)
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Authentication failed.')
    } finally {
      setLoading(false)
    }
  }

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

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs uppercase tracking-widest text-raven-400 mb-1">
              Email
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="operator@example.com"
              className="w-full bg-raven-900 border border-raven-600 text-raven-200 text-sm px-3 py-2 rounded-none font-mono focus:outline-none focus:border-electric-500 transition-colors placeholder-raven-600"
            />
          </div>

          <div>
            <label className="block text-xs uppercase tracking-widest text-raven-400 mb-1">
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              className="w-full bg-raven-900 border border-raven-600 text-raven-200 text-sm px-3 py-2 rounded-none font-mono focus:outline-none focus:border-electric-500 transition-colors placeholder-raven-600"
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
            {loading ? 'Authenticating...' : 'Sign In'}
          </button>
        </form>

        <p className="text-raven-400 text-xs mt-6">
          No account?{' '}
          <Link to="/register" className="text-electric-500 hover:text-electric-400 transition-colors">
            Register
          </Link>
        </p>
      </div>
    </div>
  )
}
