// LogRaven — Reset Password
//
// Sets a new password from the token in the emailed reset link
// (/reset-password?token=...). Tokens are single-use and expire in 1 hour.

import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Lock, Eye, EyeOff, CheckCircle2 } from 'lucide-react'
import { authApi } from '../../api/auth'

const inputClass =
  'login-input w-full px-4 py-3 rounded text-sm focus:outline-none'

export default function ResetPassword() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const token = params.get('token') ?? ''

  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [show, setShow] = useState(false)
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (password.length < 8) { setError('Password must be at least 8 characters.'); return }
    if (password !== confirm) { setError('Passwords do not match.'); return }
    setLoading(true)
    try {
      await authApi.resetPassword(token, password)
      setDone(true)
      setTimeout(() => navigate('/login'), 2500)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail ?? 'Reset failed. The link may be invalid or expired.')
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

        {done ? (
          <div className="text-center">
            <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-teal-500/10 border border-teal-500/25 flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5 text-teal-400" aria-hidden />
            </div>
            <h1 className="text-text-primary text-xl font-semibold mb-2">Password updated</h1>
            <p className="text-text-muted text-sm mb-8">Redirecting you to sign in…</p>
            <Link to="/login" className="text-xs text-[#818CF8] hover:text-[#A5B4FC] font-mono transition-colors">
              Go to sign in
            </Link>
          </div>
        ) : !token ? (
          <div className="text-center">
            <h1 className="text-text-primary text-xl font-semibold mb-2">Invalid link</h1>
            <p className="text-text-muted text-sm mb-8">
              This reset link is missing its token. Request a new one.
            </p>
            <Link to="/forgot-password" className="text-xs text-[#818CF8] hover:text-[#A5B4FC] font-mono transition-colors">
              Request new link
            </Link>
          </div>
        ) : (
          <>
            <div className="mb-8">
              <h1 className="text-text-primary text-2xl font-semibold tracking-tight mb-1">Choose a new password</h1>
              <p className="text-text-muted text-xs font-mono uppercase tracking-widest">Minimum 8 characters</p>
              <div className="mt-4 border-t border-white/[0.06]" />
            </div>

            <form onSubmit={(e) => { void handleSubmit(e) }} className="space-y-4">
              <div>
                <label htmlFor="rp-password" className="block text-xs uppercase tracking-widest text-text-muted mb-1">
                  New password
                </label>
                <div className="relative">
                  <input
                    id="rp-password"
                    type={show ? 'text' : 'password'}
                    required
                    value={password}
                    placeholder="••••••••••••"
                    onChange={(e) => setPassword(e.target.value)}
                    className={`${inputClass} pr-10`}
                  />
                  <button
                    type="button"
                    onClick={() => setShow((v) => !v)}
                    aria-label={show ? 'Hide password' : 'Show password'}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-ghost hover:text-text-muted transition-colors cursor-pointer"
                  >
                    {show ? <EyeOff size={16} aria-hidden /> : <Eye size={16} aria-hidden />}
                  </button>
                </div>
              </div>

              <div>
                <label htmlFor="rp-confirm" className="block text-xs uppercase tracking-widest text-text-muted mb-1">
                  Confirm password
                </label>
                <input
                  id="rp-confirm"
                  type={show ? 'text' : 'password'}
                  required
                  value={confirm}
                  placeholder="Repeat new password"
                  onChange={(e) => setConfirm(e.target.value)}
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
                disabled={loading || !password || !confirm}
                className="btn-login w-full text-sm font-medium tracking-wide py-3 rounded transition-colors uppercase mt-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center justify-center gap-2"
              >
                <Lock className="w-4 h-4" aria-hidden />
                {loading ? 'Updating…' : 'Update password'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  )
}
