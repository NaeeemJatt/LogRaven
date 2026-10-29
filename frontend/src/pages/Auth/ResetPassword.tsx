// LogRaven — Reset Password
//
// Sets a new password from the token in the emailed reset link
// (/reset-password?token=...).
//
// SECURITY:
//   - Idempotent pre-flight token check confirms validity before user types.
//   - URL scrubbing removes token from address bar immediately to prevent Referer leakage.
//   - NIST SP 800-63B live password strength meter enforces enterprise complexity.
//   - Web Crypto hybrid encryption ensures zero plaintext password over the wire (Burp Suite proof).
//   - Revokes all active sessions upon password reset.

import { useState, useEffect, useRef } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Lock, Eye, EyeOff, CheckCircle2, AlertTriangle, ShieldCheck, ArrowRight, Shield } from 'lucide-react'
import { authApi } from '../../api/auth'
import { encryptPayload } from '../../utils/crypto'
import PasswordStrengthMeter, { evaluatePasswordStrength } from '../../components/auth/PasswordStrengthMeter'
import LegalLinks from '../../components/layout/LegalLinks'

export default function ResetPassword() {
  const [params] = useSearchParams()
  const navigate = useNavigate()

  // Capture token from query param on initial render once via ref
  const initialTokenRef = useRef<string | null>(params.get('token'))
  const [token, setToken] = useState<string>(() => initialTokenRef.current ?? '')
  const [maskedEmail, setMaskedEmail] = useState<string | null>(null)
  const [verifying, setVerifying] = useState(true)
  const [tokenInvalid, setTokenInvalid] = useState(false)
  const [tokenErrorMsg, setTokenErrorMsg] = useState<string | null>(null)

  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [show, setShow] = useState(false)
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 1. Pre-flight token validation & URL scrubbing (runs once on mount)
  useEffect(() => {
    const rawToken = initialTokenRef.current
    if (!rawToken) {
      setVerifying(false)
      setTokenInvalid(true)
      setTokenErrorMsg('This reset link is missing its authentication token.')
      return
    }

    // Save token in memory state
    setToken(rawToken)

    // Scrub token from URL immediately to prevent Referer header leakage or browser history leaks
    try {
      window.history.replaceState({}, document.title, window.location.pathname)
    } catch {
      // Ignored in non-browser test environments
    }

    // Call pre-flight endpoint
    let isMounted = true
    authApi
      .verifyResetToken(rawToken)
      .then((res) => {
        if (!isMounted) return
        if (res.data.valid) {
          setMaskedEmail(res.data.email_masked ?? null)
          setTokenInvalid(false)
        } else {
          setTokenInvalid(true)
          setTokenErrorMsg(res.data.message ?? 'This reset link has expired or has already been used.')
        }
      })
      .catch((err: unknown) => {
        if (!isMounted) return
        setTokenInvalid(true)
        const detailMsg = (err as { response?: { data?: { detail?: { message?: string } | string } } })?.response?.data?.detail
        const message = typeof detailMsg === 'object' ? detailMsg?.message : detailMsg
        setTokenErrorMsg(message ?? 'This reset link is invalid, expired, or has already been used.')
      })
      .finally(() => {
        if (isMounted) setVerifying(false)
      })

    return () => {
      isMounted = false
    }
  }, [])

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
      // 2. Client-side Web Crypto hybrid encryption (Burp Suite inspection proof)
      const envelope = await encryptPayload({
        token,
        new_password: password,
      })

      // 3. Transmit encrypted ciphertext envelope
      await authApi.resetPassword({ envelope })
      setDone(true)
      setTimeout(() => navigate('/login'), 2500)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Password reset failed. The link may have expired.')
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
          {verifying ? (
            <div className="rounded-2xl border border-white/[0.06] bg-surface/60 backdrop-blur-xl p-8 sm:p-12 text-center" data-testid="reset-password-verifying">
              <div className="w-9 h-9 mx-auto mb-4 border-2 border-indigo-500/20 border-t-indigo-400 rounded-full animate-spin" />
              <p className="text-text-muted text-xs font-mono uppercase tracking-widest">
                Verifying cryptographic reset token…
              </p>
            </div>
          ) : done ? (
            <div className="rounded-2xl border border-white/[0.06] bg-surface/60 backdrop-blur-xl p-6 sm:p-8 text-center" data-testid="reset-password-success">
              <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-teal-500/10 border border-teal-500/25 flex items-center justify-center">
                <CheckCircle2 className="w-5 h-5 text-teal-400" aria-hidden />
              </div>
              <h1 className="font-display text-text-primary text-2xl font-bold mb-2">Password updated</h1>
              <p className="text-text-muted text-sm leading-relaxed mb-6">
                Your password has been securely updated. All existing sessions across your devices have been logged out.
              </p>
              <p className="text-text-ghost text-xs font-mono mb-6">Redirecting you to sign in…</p>
              <Link
                to="/login"
                className="btn-sovereign w-full text-xs font-semibold tracking-wide py-2.5 rounded-lg transition-colors uppercase inline-flex items-center justify-center gap-2"
              >
                Go to sign in <ArrowRight className="w-3.5 h-3.5" aria-hidden />
              </Link>
            </div>
          ) : tokenInvalid ? (
            <div className="rounded-2xl border border-white/[0.06] bg-surface/60 backdrop-blur-xl p-6 sm:p-8 text-center" data-testid="reset-password-invalid">
              <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-rose-500/10 border border-rose-500/25 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-rose-400" aria-hidden />
              </div>
              <h1 className="font-display text-text-primary text-2xl font-bold mb-2">Link Expired or Invalid</h1>
              <p className="text-text-muted text-sm leading-relaxed mb-6">
                {tokenErrorMsg ?? 'This password reset link is invalid, has expired, or has already been used.'}
              </p>
              <Link
                to="/forgot-password"
                className="btn-sovereign w-full text-xs font-semibold tracking-wide py-2.5 rounded-lg transition-colors uppercase inline-flex items-center justify-center gap-2"
              >
                Request a new reset link
              </Link>
            </div>
          ) : (
            <>
              <div className="mb-8 text-center">
                <div className="font-mono text-[10px] text-indigo-400 tracking-widest uppercase mb-2">Security Workspace</div>
                <h1 className="font-display text-2xl sm:text-3xl font-bold text-text-primary tracking-tight mb-1">Set a new password</h1>
                {maskedEmail ? (
                  <p className="text-text-muted text-xs font-mono">
                    Resetting credentials for <span className="text-indigo-400 font-medium">{maskedEmail}</span>
                  </p>
                ) : (
                  <p className="text-text-muted text-xs font-mono uppercase tracking-widest">
                    NIST SP 800-63B Compliant
                  </p>
                )}
              </div>

              <div className="rounded-2xl border border-white/[0.06] bg-surface/60 backdrop-blur-xl p-6 sm:p-8">
                <form noValidate onSubmit={(e) => { void handleSubmit(e) }} className="space-y-5">
                  <div>
                    <label htmlFor="rp-password" className="block text-[11px] font-semibold uppercase tracking-[0.15em] text-text-muted mb-1.5">
                      New password
                    </label>
                    <div className="relative">
                      <input
                        id="rp-password"
                        type={show ? 'text' : 'password'}
                        required
                        autoComplete="new-password"
                        autoCorrect="off"
                        autoCapitalize="off"
                        spellCheck="false"
                        value={password}
                        placeholder="••••••••••••"
                        onChange={(e) => {
                          setPassword(e.target.value)
                          if (error) setError(null)
                        }}
                        className="sovereign-input w-full text-sm px-3.5 py-2.5 font-mono rounded-lg pr-10"
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

                    {/* Live Password Strength Meter */}
                    <PasswordStrengthMeter password={password} />
                  </div>

                  <div>
                    <label htmlFor="rp-confirm" className="block text-[11px] font-semibold uppercase tracking-[0.15em] text-text-muted mb-1.5">
                      Confirm new password
                    </label>
                    <input
                      id="rp-confirm"
                      type={show ? 'text' : 'password'}
                      required
                      autoComplete="new-password"
                      autoCorrect="off"
                      autoCapitalize="off"
                      spellCheck="false"
                      value={confirm}
                      placeholder="Repeat new password"
                      onChange={(e) => {
                        setConfirm(e.target.value)
                        if (error) setError(null)
                      }}
                      className="sovereign-input w-full text-sm px-3.5 py-2.5 font-mono rounded-lg"
                    />
                  </div>

                  {error && (
                    <p className="text-rose-400 text-xs font-mono border border-rose-500/20 bg-rose-500/5 px-3 py-2 rounded-lg">
                      — {error}
                    </p>
                  )}

                  <button
                    type="submit"
                    disabled={loading || !password || !confirm}
                    className="btn-sovereign w-full text-sm font-semibold py-2.5 rounded-lg transition-colors uppercase mt-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center justify-center gap-2"
                  >
                    <Lock className="w-4 h-4" aria-hidden />
                    {loading ? 'Encrypting & updating…' : 'Update password'}
                  </button>
                </form>

                <div className="flex items-center justify-center gap-1.5 text-[11px] text-text-ghost font-mono mt-5">
                  <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" aria-hidden />
                  <span>Zero-plaintext payload encryption & session termination</span>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
      <LegalLinks className="px-4 pb-6" />
    </div>
  )
}
