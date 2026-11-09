import Logo from '../../components/brand/Logo'
import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { Eye, EyeOff } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import PasswordStrengthMeter, { evaluatePasswordStrength } from '../../components/auth/PasswordStrengthMeter'
import LegalLinks from '../../components/layout/LegalLinks'

export default function Register() {
  const { register } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Evaluate NIST complexity criteria
    const { isCompliant } = evaluatePasswordStrength(password)
    if (!isCompliant) {
      setError('Please satisfy all password complexity requirements shown below.')
      return
    }

    if (password !== confirm) {
      setError('Passwords do not match.')
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
          <Link to="/" className="flex items-center gap-2.5 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded-lg">
            <Logo size={30} showSignal={false} />
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
            <form noValidate onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label htmlFor="register-email" className="block text-[11px] font-semibold uppercase tracking-[0.15em] text-text-muted mb-1.5">
                  Email
                </label>
                <input
                  id="register-email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value)
                    if (error) setError(null)
                  }}
                  placeholder="operator@example.com"
                  className="sovereign-input w-full text-sm px-3.5 py-2.5 font-mono rounded-lg"
                  autoComplete="email"
                />
              </div>

              <div>
                <label htmlFor="register-password" className="block text-[11px] font-semibold uppercase tracking-[0.15em] text-text-muted mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <input
                    id="register-password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value)
                      if (error) setError(null)
                    }}
                    placeholder="••••••••••••"
                    className="sovereign-input w-full text-sm px-3.5 py-2.5 font-mono rounded-lg pr-10"
                    autoComplete="new-password"
                    autoCorrect="off"
                    autoCapitalize="off"
                    spellCheck="false"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-ghost hover:text-text-muted transition-colors cursor-pointer"
                  >
                    {showPassword ? <EyeOff size={16} aria-hidden /> : <Eye size={16} aria-hidden />}
                  </button>
                </div>

                {/* Live Password Strength Tracker */}
                <PasswordStrengthMeter password={password} />
              </div>

              <div>
                <label htmlFor="register-confirm-password" className="block text-[11px] font-semibold uppercase tracking-[0.15em] text-text-muted mb-1.5">
                  Confirm password
                </label>
                <div className="relative">
                  <input
                    id="register-confirm-password"
                    type={showConfirm ? 'text' : 'password'}
                    required
                    value={confirm}
                    onChange={(e) => {
                      setConfirm(e.target.value)
                      if (error) setError(null)
                    }}
                    placeholder="Repeat password"
                    className="sovereign-input w-full text-sm px-3.5 py-2.5 font-mono rounded-lg pr-10"
                    autoComplete="new-password"
                    autoCorrect="off"
                    autoCapitalize="off"
                    spellCheck="false"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirm((v) => !v)}
                    aria-label={showConfirm ? 'Hide confirm password' : 'Show confirm password'}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-ghost hover:text-text-muted transition-colors cursor-pointer"
                  >
                    {showConfirm ? <EyeOff size={16} aria-hidden /> : <Eye size={16} aria-hidden />}
                  </button>
                </div>
              </div>

              {error && (
                <p className="text-rose-400 text-xs font-mono border border-rose-500/20 bg-rose-500/5 px-3 py-2 rounded-lg">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="btn-sovereign w-full text-sm font-semibold py-2.5 rounded-lg transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
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
      <LegalLinks className="px-4 pb-6" />
    </div>
  )
}
