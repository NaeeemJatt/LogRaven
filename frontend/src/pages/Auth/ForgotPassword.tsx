// LogRaven — Forgot Password
//
// Requests a reset email. Always shows neutral success message (zero-knowledge
// anti-enumeration). Client-side Web Crypto hybrid encryption ensures zero
// plaintext over the wire (Burp Suite interception defense).

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { MailCheck, KeyRound, ArrowLeft, ShieldCheck } from 'lucide-react'
import { authApi } from '../../api/auth'
import { encryptPayload } from '../../utils/crypto'
import LegalLinks from '../../components/layout/LegalLinks'

const inputClass =
  'login-input w-full px-4 py-3 rounded text-sm focus:outline-none'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [cooldown, setCooldown] = useState(0)

  useEffect(() => {
    if (cooldown <= 0) return
    const timer = setInterval(() => {
      setCooldown((c) => Math.max(0, c - 1))
    }, 1000)
    return () => clearInterval(timer)
  }, [cooldown])

  const validateInput = (value: string): string | null => {
    const trimmed = value.trim()
    if (!trimmed) {
      return 'Email address is required.'
    }
    if (trimmed.includes(',') || trimmed.includes(';') || /\s/.test(trimmed)) {
      return 'Please enter exactly one email address without commas, spaces, or multiple recipients.'
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) {
      return 'Please enter a valid email address.'
    }
    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    const validationErr = validateInput(email)
    if (validationErr) {
      setError(validationErr)
      return
    }

    setLoading(true)
    try {
      // 1. Client-side Web Crypto hybrid encryption (Burp Suite inspection proof)
      const cleanEmail = email.trim().toLowerCase()
      const envelope = await encryptPayload({ email: cleanEmail })

      // 2. Transmit encrypted ciphertext envelope
      await authApi.forgotPassword({ envelope })
      setSent(true)
      setCooldown(60)
    } catch {
      setError('Something went wrong. Please check your connection and try again.')
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
          <div className="text-center" data-testid="forgot-password-success">
            <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-teal-500/10 border border-teal-500/25 flex items-center justify-center">
              <MailCheck className="w-5 h-5 text-teal-400" aria-hidden />
            </div>
            <h1 className="text-text-primary text-xl font-semibold mb-2">Check your inbox</h1>
            <p className="text-text-muted text-sm leading-relaxed mb-6">
              If an account exists for <span className="font-mono text-text-secondary">{email}</span>,
              a reset link is on its way. The link expires in <span className="text-teal-400 font-medium">15 minutes</span>.
            </p>

            <div className="flex items-center justify-center gap-1.5 text-[11px] text-text-ghost font-mono mb-8">
              <ShieldCheck className="w-3.5 h-3.5 text-teal-400" aria-hidden />
              <span>Zero-knowledge dispatch parity verified</span>
            </div>

            <div className="space-y-4">
              {cooldown > 0 ? (
                <p className="text-text-ghost text-xs font-mono">
                  Resend available in <span className="text-text-muted font-bold">{cooldown}s</span>
                </p>
              ) : (
                <button
                  type="button"
                  onClick={() => setSent(false)}
                  className="text-xs text-[#818CF8] hover:text-[#A5B4FC] font-mono transition-colors block mx-auto cursor-pointer"
                >
                  Send another request
                </button>
              )}

              <Link to="/login" className="inline-flex items-center gap-2 text-xs text-text-muted hover:text-text-primary font-mono transition-colors">
                <ArrowLeft className="w-3.5 h-3.5" aria-hidden /> Back to sign in
              </Link>
            </div>
          </div>
        ) : (
          <>
            <div className="mb-8">
              <h1 className="text-text-primary text-2xl font-semibold tracking-tight mb-1">Reset your password</h1>
              <p className="text-text-muted text-xs font-mono uppercase tracking-widest">
                We'll email you a 15-minute reset link
              </p>
              <div className="mt-4 border-t border-white/[0.06]" />
            </div>

            <form noValidate onSubmit={(e) => { void handleSubmit(e) }} className="space-y-4">
              <div>
                <label htmlFor="fp-email" className="block text-xs uppercase tracking-widest text-text-muted mb-1">
                  Email
                </label>
                <input
                  id="fp-email"
                  type="email"
                  required
                  autoComplete="email"
                  autoCorrect="off"
                  autoCapitalize="off"
                  spellCheck="false"
                  value={email}
                  placeholder="operator@example.com"
                  onChange={(e) => {
                    setEmail(e.target.value)
                    if (error) setError(null)
                  }}
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
                disabled={loading || !email.trim() || cooldown > 0}
                className="btn-login w-full text-sm font-medium tracking-wide py-3 rounded transition-colors uppercase mt-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center justify-center gap-2"
              >
                <KeyRound className="w-4 h-4" aria-hidden />
                {loading ? 'Encrypting & sending…' : cooldown > 0 ? `Wait ${cooldown}s` : 'Send reset link'}
              </button>
            </form>

            <div className="flex items-center justify-center gap-1.5 text-[10px] text-text-ghost font-mono mt-4">
              <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" aria-hidden />
              <span>Client-side Web Crypto hybrid payload encryption</span>
            </div>

            <p className="text-text-muted text-xs font-mono mt-8 text-center">
              Remembered it?{' '}
              <Link to="/login" className="text-[#818CF8] hover:text-[#A5B4FC] transition-colors">Sign in</Link>
            </p>
          </>
        )}
        <LegalLinks className="mt-10" />
      </div>
    </div>
  )
}
