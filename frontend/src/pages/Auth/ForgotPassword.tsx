// LogRaven — Forgot Password
//
// Requests a reset email. Always shows success (backend never reveals
// whether the address exists).

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { MailCheck, KeyRound, ArrowLeft } from 'lucide-react'
import { authApi } from '../../api/auth'

const inputClass =
  'login-input w-full px-4 py-3 rounded text-sm focus:outline-none'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await authApi.forgotPassword(email)
      setSent(true)
    } catch {
      setError('Something went wrong. Please try again in a moment.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-8 bg-[#030508]">
      <div className="w-full max-w-sm">
        <div className="text-center mb-10">
          <p className="font-mono font-bold tracking-widest text-[#818CF8] text-lg uppercase">LOGRAVEN</p>
          <p className="text-text-muted text-xs tracking-widest uppercase mt-1">Watch your logs. Find the threat.</p>
        </div>

        {sent ? (
          <div className="text-center">
            <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-teal-500/10 border border-teal-500/25 flex items-center justify-center">
              <MailCheck className="w-5 h-5 text-teal-400" aria-hidden />
            </div>
            <h1 className="text-text-primary text-xl font-semibold mb-2">Check your inbox</h1>
            <p className="text-text-muted text-sm leading-relaxed mb-8">
              If an account exists for <span className="font-mono text-text-secondary">{email}</span>,
              a reset link is on its way. The link expires in 1 hour.
            </p>
            <Link to="/login" className="inline-flex items-center gap-2 text-xs text-[#818CF8] hover:text-[#A5B4FC] font-mono transition-colors">
              <ArrowLeft className="w-3.5 h-3.5" aria-hidden /> Back to sign in
            </Link>
          </div>
        ) : (
          <>
            <div className="mb-8">
              <h1 className="text-text-primary text-2xl font-semibold tracking-tight mb-1">Reset your password</h1>
              <p className="text-text-muted text-xs font-mono uppercase tracking-widest">
                We'll email you a reset link
              </p>
              <div className="mt-4 border-t border-white/[0.06]" />
            </div>

            <form onSubmit={(e) => { void handleSubmit(e) }} className="space-y-4">
              <div>
                <label htmlFor="fp-email" className="block text-xs uppercase tracking-widest text-text-muted mb-1">
                  Email
                </label>
                <input
                  id="fp-email"
                  type="email"
                  required
                  value={email}
                  placeholder="operator@example.com"
                  onChange={(e) => setEmail(e.target.value)}
                  className={inputClass}
                />
              </div>

              {error && (
                <p className="text-rose-400 text-xs font-mono border border-rose-500/20 bg-rose-500/5 px-3 py-2 rounded">
                  — {error}
                </p>
              )}

              <button
                type="submit"
                disabled={loading || !email}
                className="btn-login w-full text-sm font-medium tracking-wide py-3 rounded transition-colors uppercase mt-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center justify-center gap-2"
              >
                <KeyRound className="w-4 h-4" aria-hidden />
                {loading ? 'Sending…' : 'Send reset link'}
              </button>
            </form>

            <p className="text-text-muted text-xs font-mono mt-8 text-center">
              Remembered it?{' '}
              <Link to="/login" className="text-[#818CF8] hover:text-[#A5B4FC] transition-colors">Sign in</Link>
            </p>
          </>
        )}
      </div>
    </div>
  )
}
