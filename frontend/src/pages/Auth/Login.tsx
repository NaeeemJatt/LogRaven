// LogRaven — Animated Characters Login Page
// All eye-tracking / blinking / peeking animation logic preserved exactly.
// shadcn replaced with plain HTML using LogRaven's raven-* / electric-* palette.
// Auth wired to real useAuth().login() — no hardcoded credentials.

import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { Eye, EyeOff } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'


// ── Pupil ─────────────────────────────────────────────────────────────────────

interface PupilProps {
  size?: number
  maxDistance?: number
  pupilColor?: string
  forceLookX?: number
  forceLookY?: number
}

function Pupil({
  size = 12,
  maxDistance = 5,
  pupilColor = '#0D0F14',
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
      className="rounded-full"
      style={{
        width: size, height: size,
        backgroundColor: pupilColor,
        transform: `translate(${x}px, ${y}px)`,
        transition: 'transform 0.1s ease-out',
      }}
    />
  )
}


// ── EyeBall ───────────────────────────────────────────────────────────────────

interface EyeBallProps {
  size?: number
  pupilSize?: number
  maxDistance?: number
  eyeColor?: string
  pupilColor?: string
  isBlinking?: boolean
  forceLookX?: number
  forceLookY?: number
}

function EyeBall({
  size = 48,
  pupilSize = 16,
  maxDistance = 10,
  eyeColor = 'white',
  pupilColor = '#0D0F14',
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
      className="rounded-full flex items-center justify-center transition-all duration-150"
      style={{
        width: size,
        height: isBlinking ? 2 : size,
        backgroundColor: eyeColor,
        overflow: 'hidden',
      }}
    >
      {!isBlinking && (
        <div
          className="rounded-full"
          style={{
            width: pupilSize, height: pupilSize,
            backgroundColor: pupilColor,
            transform: `translate(${x}px, ${y}px)`,
            transition: 'transform 0.1s ease-out',
          }}
        />
      )}
    </div>
  )
}


// ── Login Page ────────────────────────────────────────────────────────────────

export default function Login() {
  const { login } = useAuth()

  const [showPassword, setShowPassword]           = useState(false)
  const [email, setEmail]                         = useState('')
  const [password, setPassword]                   = useState('')
  const [error, setError]                         = useState<string | null>(null)
  const [loading, setLoading]                     = useState(false)
  const [mouseX, setMouseX]                       = useState(0)
  const [mouseY, setMouseY]                       = useState(0)
  const [isPurpleBlinking, setIsPurpleBlinking]   = useState(false)
  const [isBlackBlinking, setIsBlackBlinking]     = useState(false)
  const [isTyping, setIsTyping]                   = useState(false)
  const [isLookingAtEachOther, setIsLookingAtEachOther] = useState(false)
  const [isPurplePeeking, setIsPurplePeeking]     = useState(false)

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

  const calcPos = (ref: React.RefObject<HTMLDivElement | null>) => {
    if (!ref.current) return { faceX: 0, faceY: 0, bodySkew: 0 }
    const rect = ref.current.getBoundingClientRect()
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
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Authentication failed.')
    } finally {
      setLoading(false)
    }
  }

  const inputClass =
    'w-full bg-raven-900 border border-raven-600 text-raven-200 text-sm px-3 py-3 rounded-none font-mono focus:outline-none focus:border-electric-500 transition-colors placeholder-raven-600'

  return (
    <div className="min-h-screen grid lg:grid-cols-2">

      {/* ── Left panel — dark + characters ─────────────────────────────────── */}
      <div className="relative hidden lg:flex flex-col justify-between bg-gradient-to-br from-raven-800 via-raven-900 to-raven-950 p-12">

        {/* Brand */}
        <div className="relative z-20">
          <p className="font-mono font-bold tracking-widest text-electric-500 text-lg uppercase">
            LOGRAVEN
          </p>
          <p className="text-raven-400 text-xs tracking-widest uppercase mt-0.5">
            Watch your logs. Find the threat.
          </p>
        </div>

        {/* Characters stage */}
        <div className="relative z-20 flex items-end justify-center h-[500px]">
          <div className="relative" style={{ width: 550, height: 400 }}>

            {/* Purple — tall rectangle, back layer */}
            <div
              ref={purpleRef}
              className="absolute bottom-0 transition-all duration-700 ease-in-out"
              style={{
                left: 70, width: 180,
                height: hidingPassword ? 440 : 400,
                backgroundColor: '#6C3FF5',
                borderRadius: '10px 10px 0 0',
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
                className="absolute flex gap-8 transition-all duration-700 ease-in-out"
                style={{
                  left: passwordVisible ? 20 : isLookingAtEachOther ? 55 : 45 + purplePos.faceX,
                  top:  passwordVisible ? 35 : isLookingAtEachOther ? 65 : 40 + purplePos.faceY,
                }}
              >
                {[0, 1].map(i => (
                  <EyeBall key={i} size={18} pupilSize={7} maxDistance={5}
                    eyeColor="white" pupilColor="#0D0F14"
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
              className="absolute bottom-0 transition-all duration-700 ease-in-out"
              style={{
                left: 240, width: 120, height: 310,
                backgroundColor: '#2D2D2D',
                borderRadius: '8px 8px 0 0',
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
                className="absolute flex gap-6 transition-all duration-700 ease-in-out"
                style={{
                  left: passwordVisible ? 10 : isLookingAtEachOther ? 32 : 26 + blackPos.faceX,
                  top:  passwordVisible ? 28 : isLookingAtEachOther ? 12 : 32 + blackPos.faceY,
                }}
              >
                {[0, 1].map(i => (
                  <EyeBall key={i} size={16} pupilSize={6} maxDistance={4}
                    eyeColor="white" pupilColor="#0D0F14"
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
              className="absolute bottom-0 transition-all duration-700 ease-in-out"
              style={{
                left: 0, width: 240, height: 200,
                zIndex: 3,
                backgroundColor: '#FF9B6B',
                borderRadius: '120px 120px 0 0',
                transform: passwordVisible ? 'skewX(0deg)' : `skewX(${orangePos.bodySkew || 0}deg)`,
                transformOrigin: 'bottom center',
              }}
            >
              <div
                className="absolute flex gap-8 transition-all duration-200 ease-out"
                style={{
                  left: passwordVisible ? 50 : 82 + (orangePos.faceX || 0),
                  top:  passwordVisible ? 85 : 90 + (orangePos.faceY || 0),
                }}
              >
                {[0, 1].map(i => (
                  <Pupil key={i} size={12} maxDistance={5} pupilColor="#0D0F14"
                    forceLookX={passwordVisible ? -5 : undefined}
                    forceLookY={passwordVisible ? -4 : undefined}
                  />
                ))}
              </div>
            </div>

            {/* Yellow — front right rounded rectangle */}
            <div
              ref={yellowRef}
              className="absolute bottom-0 transition-all duration-700 ease-in-out"
              style={{
                left: 310, width: 140, height: 230,
                backgroundColor: '#E8D754',
                borderRadius: '70px 70px 0 0',
                zIndex: 4,
                transform: passwordVisible ? 'skewX(0deg)' : `skewX(${yellowPos.bodySkew || 0}deg)`,
                transformOrigin: 'bottom center',
              }}
            >
              <div
                className="absolute flex gap-6 transition-all duration-200 ease-out"
                style={{
                  left: passwordVisible ? 20 : 52 + (yellowPos.faceX || 0),
                  top:  passwordVisible ? 35 : 40 + (yellowPos.faceY || 0),
                }}
              >
                {[0, 1].map(i => (
                  <Pupil key={i} size={12} maxDistance={5} pupilColor="#0D0F14"
                    forceLookX={passwordVisible ? -5 : undefined}
                    forceLookY={passwordVisible ? -4 : undefined}
                  />
                ))}
              </div>
              {/* Mouth */}
              <div
                className="absolute h-1 bg-raven-900 rounded-full transition-all duration-200 ease-out"
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
        <div className="relative z-20 flex items-center gap-8 text-xs text-raven-600 font-mono uppercase tracking-widest">
          <a href="#" className="hover:text-raven-400 transition-colors">Privacy</a>
          <a href="#" className="hover:text-raven-400 transition-colors">Terms</a>
          <a href="#" className="hover:text-raven-400 transition-colors">Contact</a>
        </div>

        {/* Decorative blobs */}
        <div className="absolute top-1/4 right-1/4 w-64 h-64 bg-electric-500/5 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-1/4 left-1/4 w-96 h-96 bg-electric-500/3 rounded-full blur-3xl pointer-events-none" />
      </div>

      {/* ── Right panel — login form ─────────────────────────────────────────── */}
      <div className="flex items-center justify-center p-8 bg-raven-950">
        <div className="w-full max-w-sm">

          {/* Mobile brand */}
          <div className="lg:hidden text-center mb-10">
            <p className="font-mono font-bold tracking-widest text-electric-500 text-lg uppercase">
              LOGRAVEN
            </p>
            <p className="text-raven-400 text-xs tracking-widest uppercase mt-1">
              Watch your logs. Find the threat.
            </p>
          </div>

          {/* Header */}
          <div className="mb-8">
            <h1 className="text-raven-200 text-2xl font-semibold tracking-tight mb-1">
              Welcome back
            </h1>
            <p className="text-raven-400 text-xs font-mono uppercase tracking-widest">
              Sign in to your workspace
            </p>
            <div className="mt-4 border-t border-raven-700" />
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">

            <div>
              <label className="block text-xs uppercase tracking-widest text-raven-400 mb-1">
                Email
              </label>
              <input
                type="email"
                required
                value={email}
                autoComplete="off"
                placeholder="operator@example.com"
                onChange={e => setEmail(e.target.value)}
                onFocus={() => setIsTyping(true)}
                onBlur={() => setIsTyping(false)}
                className={inputClass}
              />
            </div>

            <div>
              <label className="block text-xs uppercase tracking-widest text-raven-400 mb-1">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  placeholder="••••••••••••"
                  onChange={e => setPassword(e.target.value)}
                  className={`${inputClass} pr-10`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-raven-600 hover:text-raven-400 transition-colors"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Remember me + forgot */}
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="w-3.5 h-3.5 accent-electric-500 bg-raven-900 border-raven-600 rounded-none"
                />
                <span className="text-raven-400 text-xs font-mono">Remember me</span>
              </label>
              <a href="#" className="text-xs text-electric-500 hover:text-electric-400 font-mono transition-colors">
                Forgot password?
              </a>
            </div>

            {error && (
              <p className="text-red-400 text-xs font-mono border border-red-900/40 bg-red-950/20 px-3 py-2">
                — {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-electric-500 hover:bg-electric-400 disabled:opacity-60 text-white text-sm font-medium tracking-wide py-3 rounded-none transition-colors uppercase mt-2"
            >
              {loading ? 'Authenticating...' : 'Sign In'}
            </button>
          </form>

          {/* Register link */}
          <p className="text-raven-400 text-xs font-mono mt-8 text-center">
            No account?{' '}
            <Link to="/register" className="text-electric-500 hover:text-electric-400 transition-colors">
              Register
            </Link>
          </p>
        </div>
      </div>

    </div>
  )
}
