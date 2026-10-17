// LogRaven — Verify Email
//
// Landing page for the verification link (/verify-email?token=...).
// Confirms the token with the backend and reports the result.

import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import { authApi } from '../../api/auth'
import LegalLinks from '../../components/layout/LegalLinks'
import { useAuthStore } from '../../store/authStore'

type State = 'verifying' | 'success' | 'error'

export default function VerifyEmail() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  const [state, setState] = useState<State>(token ? 'verifying' : 'error')
  const [message, setMessage] = useState<string>('')
  const ran = useRef(false)
  const user = useAuthStore((s) => s.user)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const setUser = useAuthStore((s) => s.setUser)

  useEffect(() => {
    if (!token || ran.current) return
    ran.current = true
    authApi
      .verifyEmail(token)
      .then(() => {
        setState('success')
        if (user) setUser({ ...user, email_verified: true })
      })
      .catch((err: unknown) => {
        const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        setMessage(detail ?? 'Verification failed. The link may be invalid or expired.')
        setState('error')
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  return (
    <div className="min-h-screen flex items-center justify-center p-8 bg-[#030508]">
      <div className="w-full max-w-sm text-center">
        <p className="font-mono font-bold tracking-widest text-[#818CF8] text-lg uppercase mb-10">LOGRAVEN</p>

        <div role="status" aria-live="polite">
        {state === 'verifying' && (
          <>
            <Loader2 className="w-8 h-8 mx-auto mb-4 text-[#818CF8] animate-spin" aria-hidden />
            <h1 className="text-text-primary text-xl font-semibold">Verifying your email…</h1>
          </>
        )}

        {state === 'success' && (
          <>
            <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-teal-500/10 border border-teal-500/25 flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5 text-teal-400" aria-hidden />
            </div>
            <h1 className="text-text-primary text-xl font-semibold mb-2">Email verified</h1>
            <p className="text-text-muted text-sm mb-8">Your email address is confirmed. You're all set.</p>
            <Link to={isAuthenticated ? '/dashboard' : '/login'} className="btn-login inline-block text-sm font-medium tracking-wide py-3 px-8 rounded transition-colors uppercase cursor-pointer">
              {isAuthenticated ? 'Go to dashboard' : 'Go to sign in'}
            </Link>
          </>
        )}

        {state === 'error' && (
          <>
            <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-rose-500/10 border border-rose-500/25 flex items-center justify-center">
              <XCircle className="w-5 h-5 text-rose-400" aria-hidden />
            </div>
            <h1 className="text-text-primary text-xl font-semibold mb-2">Verification failed</h1>
            <p className="text-text-muted text-sm mb-8">
              {message || 'This verification link is missing its token.'}
              {' '}{isAuthenticated
                ? 'You can request a new link from your profile page.'
                : 'Sign in to request a new link.'}
            </p>
            <Link to={isAuthenticated ? '/profile' : '/login'} className="text-xs text-[#818CF8] hover:text-[#A5B4FC] font-mono transition-colors">
              {isAuthenticated ? 'Open profile' : 'Go to sign in'}
            </Link>
          </>
        )}
        </div>
        <LegalLinks className="mt-10" />
      </div>
    </div>
  )
}
