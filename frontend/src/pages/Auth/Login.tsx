// LogRaven — Animated Characters Login Page
// All eye-tracking / blinking / peeking animation logic preserved exactly.
// Modern minimal sovereign styling, amber accent, zero arbitrary colors or blurred orbs.
// Auth wired to real useAuth().login() — no hardcoded credentials.

import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { Eye, EyeOff, Shield } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import LegalLinks from '../../components/layout/LegalLinks'


// ── Pupil ─────────────────────────────────────────────────────────────────────

interface PupilProps {
  size?: number
  maxDistance?: number
  forceLookX?: number
  forceLookY?: number
}

function Pupil({
  size = 12,
  maxDistance = 5,
  forceLookX,
  forceLookY,
}: PupilProps) {
  const [mouseX, setMouseX] = useState(0)
  const [mouseY, setMouseY] = useState(0)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const onMove = (e: MouseEvent) => { setMouseX(e.clientX); setMouseY(e.clientY) }
    window.addEventListener('mousemove', onMove)
    return () => window.removeEventListener('mousemove', onMove)
  }, [])

  const pos = () => {
    if (!ref.current) return { x: 0, y: 0 }
    if (forceLookX !== undefined && forceLookY !== undefined)
      return { x: forceLookX, y: forceLookY }
    const r = ref.current.getBoundingClientRect()
    const dx = mouseX - (r.left + r.width / 2)
    const dy = mouseY - (r.top + r.height / 2)
    const dist = Math.min(Math.sqrt(dx ** 2 + dy ** 2), maxDistance)
    const angle = Math.atan2(dy, dx)
    return { x: Math.cos(angle) * dist, y: Math.sin(angle) * dist }
  }

  const { x, y } = pos()
  return (
    <div
      ref={ref}
      className="rounded-full bg-stone-950 motion-safe:transition-transform motion-reduce:transition-none duration-100 ease-out"
      style={{
        width: size,
        height: size,
        transform: `translate(${x}px, ${y}px)`,
      }}
    />
  )
}


// ── EyeBall ───────────────────────────────────────────────────────────────────

interface EyeBallProps {
  size?: number
  pupilSize?: number
  maxDistance?: number
  isBlinking?: boolean
  forceLookX?: number
  forceLookY?: number
}

function EyeBall({
  size = 48,
  pupilSize = 16,
  maxDistance = 10,
  isBlinking = false,
  forceLookX,
  forceLookY,
}: EyeBallProps) {
  const [mouseX, setMouseX] = useState(0)
  const [mouseY, setMouseY] = useState(0)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const onMove = (e: MouseEvent) => { setMouseX(e.clientX); setMouseY(e.clientY) }
    window.addEventListener('mousemove', onMove)
    return () => window.removeEventListener('mousemove', onMove)
  }, [])

  const pos = () => {
    if (!ref.current) return { x: 0, y: 0 }
    if (forceLookX !== undefined && forceLookY !== undefined)
      return { x: forceLookX, y: forceLookY }
    const r = ref.current.getBoundingClientRect()
    const dx = mouseX - (r.left + r.width / 2)
    const dy = mouseY - (r.top + r.height / 2)
    const dist = Math.min(Math.sqrt(dx ** 2 + dy ** 2), maxDistance)
    const angle = Math.atan2(dy, dx)
    return { x: Math.cos(angle) * dist, y: Math.sin(angle) * dist }
  }

  const { x, y } = pos()
  return (
    <div
      ref={ref}
      className="rounded-full flex items-center justify-center bg-white overflow-hidden motion-safe:transition-transform motion-reduce:transition-none duration-150"
      style={{
        width: size,
        height: isBlinking ? 2 : size,
      }}
    >
      {!isBlinking && (
        <div
          className="rounded-full bg-stone-950 motion-safe:transition-transform motion-reduce:transition-none duration-100 ease-out"
          style={{
            width: pupilSize,
            height: pupilSize,
            transform: `translate(${x}px, ${y}px)`,
          }}
        />
      )}
    </div>
  )
}


// ── Login Page ────────────────────────────────────────────────────────────────

export default function Login() {
  const { login } = useAuth()

  const [showPassword, setShowPassword]                 = useState(false)
  const [email, setEmail]                               = useState('')
  const [password, setPassword]                         = useState('')
  const [error, setError]                               = useState<string | null>(null)
  const [loading, setLoading]                           = useState(false)
  const [mouseX, setMouseX]                             = useState(0)
  const [mouseY, setMouseY]                             = useState(0)
  const [isPurpleBlinking, setIsPurpleBlinking]         = useState(false)
  const [isBlackBlinking, setIsBlackBlinking]           = useState(false)
  const [isTyping, setIsTyping]                         = useState(false)
  const [isLookingAtEachOther, setIsLookingAtEachOther] = useState(false)
  const [isPurplePeeking, setIsPurplePeeking]           = useState(false)

  const purpleRef = useRef<HTMLDivElement>(null)
  const blackRef  = useRef<HTMLDivElement>(null)
  const yellowRef = useRef<HTMLDivElement>(null)
  const orangeRef = useRef<HTMLDivElement>(null)

  // Mouse tracking
  useEffect(() => {
    const onMove = (e: MouseEvent) => { setMouseX(e.clientX); setMouseY(e.clientY) }
    window.addEventListener('mousemove', onMove)
    return () => window.removeEventListener('mousemove', onMove)
  }, [])

  // Random blinking — purple
  useEffect(() => {
    const schedule = () => {
      const t = setTimeout(() => {
        setIsPurpleBlinking(true)
        setTimeout(() => { setIsPurpleBlinking(false); schedule() }, 150)
      }, Math.random() * 4000 + 3000)
      return t
    }
    const t = schedule()
    return () => clearTimeout(t)
  }, [])

  // Random blinking — black
  useEffect(() => {
    const schedule = () => {
      const t = setTimeout(() => {
        setIsBlackBlinking(true)
        setTimeout(() => { setIsBlackBlinking(false); schedule() }, 150)
      }, Math.random() * 4000 + 3000)
      return t
    }
    const t = schedule()
    return () => clearTimeout(t)
  }, [])

  // Look at each other on typing start
  useEffect(() => {
    if (isTyping) {
      setIsLookingAtEachOther(true)
      const t = setTimeout(() => setIsLookingAtEachOther(false), 800)
      return () => clearTimeout(t)
    } else {
      setIsLookingAtEachOther(false)
    }
  }, [isTyping])

  // Purple sneaky peek when password is visible
  useEffect(() => {
    if (password.length > 0 && showPassword) {
      const t = setTimeout(() => {
        setIsPurplePeeking(true)
        setTimeout(() => setIsPurplePeeking(false), 800)
      }, Math.random() * 3000 + 2000)
      return () => clearTimeout(t)
    } else {
      setIsPurplePeeking(false)
    }
  }, [password, showPassword, isPurplePeeking])

  const calcPos = (r: React.RefObject<HTMLDivElement | null>) => {
    if (!r.current) return { faceX: 0, faceY: 0, bodySkew: 0 }
    const rect = r.current.getBoundingClientRect()
    const cx = rect.left + rect.width / 2
    const cy = rect.top + rect.height / 3
    const dx = mouseX - cx
    const dy = mouseY - cy
    return {
      faceX:    Math.max(-15, Math.min(15,  dx / 20)),
      faceY:    Math.max(-10, Math.min(10,  dy / 30)),
      bodySkew: Math.max(-6,  Math.min(6,  -dx / 120)),
    }
  }

  const purplePos = calcPos(purpleRef)
  const blackPos  = calcPos(blackRef)
  const yellowPos = calcPos(yellowRef)
  const orangePos = calcPos(orangeRef)

  const hidingPassword = isTyping || (password.length > 0 && !showPassword)
  const passwordVisible = password.length > 0 && showPassword

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(email, password)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Authentication failed. Please verify your credentials.')
    } finally {
      setLoading(false)
    }
  }

  const inputClass =
    'w-full text-sm px-3.5 py-2.5 rounded-lg bg-surface border border-white/[0.08] text-text-primary placeholder:text-text-muted/50 focus:border-amber-400/60 focus:ring-1 focus:ring-amber-400/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 transition-colors duration-150'

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-void text-text-primary">

      {/* ── Left panel — dark + characters ─────────────────────────────────── */}
      <div className="relative hidden lg:flex flex-col justify-between bg-surface/30 p-12 border-r border-white/[0.06]">

        {/* Brand */}
        <div className="relative z-20">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-amber-400/10 border border-amber-400/20 flex items-center justify-center">
              <Shield className="w-4 h-4 text-amber-400" strokeWidth={2} />
            </div>
            <span className="font-display font-bold text-base text-text-primary tracking-tight">
              Log<span className="text-amber-400">Raven</span>
            </span>
          </div>
          <p className="text-text-muted text-xs mt-1.5">
            Watch your logs. Find the threat.
          </p>
        </div>

        {/* Characters stage */}
        <div className="relative z-20 flex items-end justify-center h-[500px]">
          <div className="relative" style={{ width: 550, height: 400 }}>

            {/* Purple — tall rectangle, back layer */}
            <div
              ref={purpleRef}
              className="absolute bottom-0 bg-indigo-600 rounded-t-lg motion-safe:transition-transform motion-reduce:transition-none duration-700 ease-in-out"
              style={{
                left: 70,
                width: 180,
                height: hidingPassword ? 440 : 400,
                zIndex: 1,
                transform: passwordVisible
                  ? 'skewX(0deg)'
                  : hidingPassword
                    ? `skewX(${(purplePos.bodySkew || 0) - 12}deg) translateX(40px)`
                    : `skewX(${purplePos.bodySkew || 0}deg)`,
                transformOrigin: 'bottom center',
              }}
            >
              <div
                className="absolute flex gap-8 motion-safe:transition-transform motion-reduce:transition-none duration-700 ease-in-out"
                style={{
                  left: passwordVisible ? 20 : isLookingAtEachOther ? 55 : 45 + purplePos.faceX,
                  top:  passwordVisible ? 35 : isLookingAtEachOther ? 65 : 40 + purplePos.faceY,
                }}
              >
                {[0, 1].map(i => (
                  <EyeBall key={i} size={18} pupilSize={7} maxDistance={5}
                    isBlinking={isPurpleBlinking}
                    forceLookX={passwordVisible ? (isPurplePeeking ? 4 : -4) : isLookingAtEachOther ? 3 : undefined}
                    forceLookY={passwordVisible ? (isPurplePeeking ? 5 : -4) : isLookingAtEachOther ? 4 : undefined}
                  />
                ))}
              </div>
            </div>

            {/* Black — middle layer */}
            <div
              ref={blackRef}
              className="absolute bottom-0 bg-zinc-800 rounded-t-lg motion-safe:transition-transform motion-reduce:transition-none duration-700 ease-in-out"
              style={{
                left: 240,
                width: 120,
                height: 310,
                zIndex: 2,
                transform: passwordVisible
                  ? 'skewX(0deg)'
                  : isLookingAtEachOther
                    ? `skewX(${(blackPos.bodySkew || 0) * 1.5 + 10}deg) translateX(20px)`
                    : hidingPassword
                      ? `skewX(${(blackPos.bodySkew || 0) * 1.5}deg)`
                      : `skewX(${blackPos.bodySkew || 0}deg)`,
                transformOrigin: 'bottom center',
              }}
            >
              <div
                className="absolute flex gap-6 motion-safe:transition-transform motion-reduce:transition-none duration-700 ease-in-out"
                style={{
                  left: passwordVisible ? 10 : isLookingAtEachOther ? 32 : 26 + blackPos.faceX,
                  top:  passwordVisible ? 28 : isLookingAtEachOther ? 12 : 32 + blackPos.faceY,
                }}
              >
                {[0, 1].map(i => (
                  <EyeBall key={i} size={16} pupilSize={6} maxDistance={4}
                    isBlinking={isBlackBlinking}
                    forceLookX={passwordVisible ? -4 : isLookingAtEachOther ? 0  : undefined}
                    forceLookY={passwordVisible ? -4 : isLookingAtEachOther ? -4 : undefined}
                  />
                ))}
              </div>
            </div>

            {/* Orange — front left semi-circle */}
            <div
              ref={orangeRef}
              className="absolute bottom-0 bg-orange-500 rounded-t-[120px] motion-safe:transition-transform motion-reduce:transition-none duration-700 ease-in-out"
              style={{
                left: 0,
                width: 240,
                height: 200,
                zIndex: 3,
                transform: passwordVisible ? 'skewX(0deg)' : `skewX(${orangePos.bodySkew || 0}deg)`,
                transformOrigin: 'bottom center',
              }}
            >
              <div
                className="absolute flex gap-8 motion-safe:transition-transform motion-reduce:transition-none duration-200 ease-out"
                style={{
                  left: passwordVisible ? 50 : 82 + (orangePos.faceX || 0),
                  top:  passwordVisible ? 85 : 90 + (orangePos.faceY || 0),
                }}
              >
                {[0, 1].map(i => (
                  <Pupil key={i} size={12} maxDistance={5}
                    forceLookX={passwordVisible ? -5 : undefined}
                    forceLookY={passwordVisible ? -4 : undefined}
                  />
                ))}
              </div>
            </div>

            {/* Yellow — front right rounded rectangle */}
            <div
              ref={yellowRef}
              className="absolute bottom-0 bg-amber-400 rounded-t-[70px] motion-safe:transition-transform motion-reduce:transition-none duration-700 ease-in-out"
              style={{
                left: 310,
                width: 140,
                height: 230,
                zIndex: 4,
                transform: passwordVisible ? 'skewX(0deg)' : `skewX(${yellowPos.bodySkew || 0}deg)`,
                transformOrigin: 'bottom center',
              }}
            >
              <div
                className="absolute flex gap-6 motion-safe:transition-transform motion-reduce:transition-none duration-200 ease-out"
                style={{
                  left: passwordVisible ? 20 : 52 + (yellowPos.faceX || 0),
                  top:  passwordVisible ? 35 : 40 + (yellowPos.faceY || 0),
                }}
              >
                {[0, 1].map(i => (
                  <Pupil key={i} size={12} maxDistance={5}
                    forceLookX={passwordVisible ? -5 : undefined}
                    forceLookY={passwordVisible ? -4 : undefined}
                  />
                ))}
              </div>
              {/* Mouth */}
              <div
                className="absolute h-1 bg-stone-900 rounded-full motion-safe:transition-transform motion-reduce:transition-none duration-200 ease-out"
                style={{
                  width: 80,
                  left: passwordVisible ? 10 : 40 + (yellowPos.faceX || 0),
                  top:  passwordVisible ? 88 : 88 + (yellowPos.faceY || 0),
                }}
              />
            </div>

          </div>
        </div>

        {/* Footer links */}
        <LegalLinks className="relative z-20 justify-start" />
      </div>

      {/* ── Right panel — login form ─────────────────────────────────────────── */}
      <div className="flex items-center justify-center p-8 bg-void">
        <div className="w-full max-w-sm">

          {/* Mobile brand */}
          <div className="lg:hidden flex flex-col items-center mb-10">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-amber-400/10 border border-amber-400/20 flex items-center justify-center">
                <Shield className="w-4 h-4 text-amber-400" strokeWidth={2} />
              </div>
              <span className="font-display font-bold text-base text-text-primary tracking-tight">
                Log<span className="text-amber-400">Raven</span>
              </span>
            </div>
            <p className="text-text-muted text-xs mt-1">
              Watch your logs. Find the threat.
            </p>
          </div>

          {/* Header */}
          <div className="mb-8">
            <h1 className="text-text-primary text-2xl font-semibold tracking-tight mb-1">
              Welcome back
            </h1>
            <p className="text-text-muted text-sm">
              Sign in to your workspace
            </p>
            <div className="mt-4 border-t border-white/[0.06]" />
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">

            <div>
              <label htmlFor="login-email" className="block text-xs font-medium text-text-muted mb-1.5">
                Email
              </label>
              <input
                id="login-email"
                type="email"
                required
                value={email}
                autoComplete="email"
                placeholder="operator@example.com"
                onChange={e => setEmail(e.target.value)}
                onFocus={() => setIsTyping(true)}
                onBlur={() => setIsTyping(false)}
                className={inputClass}
              />
            </div>

            <div>
              <label htmlFor="login-password" className="block text-xs font-medium text-text-muted mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  autoComplete="current-password"
                  placeholder="••••••••••••"
                  onChange={e => setPassword(e.target.value)}
                  className={`${inputClass} pr-10`}
                />
                <button
                  type="button"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  onClick={() => setShowPassword(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded transition-colors active:scale-95"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Forgot password */}
            <div className="flex items-center justify-end">
              <Link
                to="/forgot-password"
                className="text-xs text-amber-400 hover:text-amber-300 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded transition-colors"
              >
                Forgot password?
              </Link>
            </div>

            {error && (
              <p className="text-rose-400 text-xs border border-rose-500/20 bg-rose-500/10 px-3 py-2 rounded-lg">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full text-sm font-medium py-2.5 rounded-lg bg-amber-400 hover:bg-amber-300 text-stone-950 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed mt-2"
            >
              {loading ? 'Authenticating…' : 'Sign in'}
            </button>
          </form>

          {/* Register link */}
          <p className="text-text-muted text-xs mt-8 text-center">
            No account?{' '}
            <Link
              to="/register"
              className="text-amber-400 hover:text-amber-300 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded transition-colors"
            >
              Register
            </Link>
          </p>
          <LegalLinks className="lg:hidden mt-8" />
        </div>
      </div>

    </div>
  )
}
