import { useState, useEffect, useRef } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Shield, LayoutDashboard, Terminal, CheckSquare,
  LogOut, ChevronDown, Menu, X, ChevronRight, Radio
} from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import { useAuth } from '../../hooks/useAuth'

const navLinks = [
  { label: 'Dashboard',  href: '/dashboard',  icon: LayoutDashboard },
  { label: 'Alerts',     href: '/alerts',     icon: Radio },
  { label: 'PlayParser', href: '/play-parser', icon: Terminal },
  { label: 'Compliance', href: '/compliance',  icon: CheckSquare },
]

// ── Main Navbar ───────────────────────────────────────────
export default function Navbar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { logout } = useAuth()
  const user = useAuthStore((s) => s.user)

  const [scrolled, setScrolled] = useState(false)
  const [lastY, setLastY] = useState(0)
  const [hidden, setHidden] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const profileRef = useRef<HTMLDivElement>(null)

  // Derive display values from real auth user
  const displayName = user?.email?.split('@')[0] ?? 'User'
  const initials = displayName.charAt(0).toUpperCase()
  const plan = user?.tier?.toUpperCase() ?? 'FREE'
  const email = user?.email ?? ''

  useEffect(() => {
    const handleScroll = () => {
      const y = window.scrollY
      setScrolled(y > 20)
      setHidden(y > lastY && y > 80)
      setLastY(y)
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [lastY])

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false)
      }
    }
    if (profileOpen) document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [profileOpen])

  const isActive = (href: string) =>
    location.pathname === href || location.pathname.startsWith(href + '/')

  const handleSignOut = async () => {
    setProfileOpen(false)
    await logout()
  }

  return (
    <motion.header
      initial={{ y: 0 }}
      animate={{ y: hidden ? -80 : 0 }}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'bg-deep/90 backdrop-blur-xl border-b border-white/5 shadow-[0_1px_0_rgba(255,255,255,0.04)]'
          : 'bg-transparent'
      }`}
    >
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex items-center h-16 gap-8">
          {/* Logo */}
          <Link to="/dashboard" className="flex items-center gap-2.5 group flex-shrink-0">
            <div className="relative">
              <div className="w-8 h-8 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center group-hover:border-indigo-400/60 transition-all duration-300">
                <Shield className="w-4 h-4 text-indigo-400" />
              </div>
              <div className="absolute inset-0 rounded-lg bg-indigo-500/10 blur-md group-hover:bg-indigo-500/20 transition-all duration-300" />
            </div>
            <span className="font-display font-bold text-lg text-text-primary tracking-tight">
              Log<span className="text-indigo-400">Raven</span>
            </span>
          </Link>

          {/* Nav links — desktop */}
          <nav className="hidden md:flex items-center gap-1 flex-1">
            {navLinks.map(({ label, href, icon: Icon }) => (
              <Link
                key={href}
                to={href}
                className={`relative flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                  isActive(href)
                    ? 'text-text-primary bg-indigo-500/10 border border-indigo-500/18'
                    : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.04]'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {label}
              </Link>
            ))}
          </nav>

          {/* Right side — profile trigger */}
          <div className="hidden md:flex items-center ml-auto">
            <div ref={profileRef} className="relative">
              <button
                onClick={() => setProfileOpen(!profileOpen)}
                className={`flex items-center gap-2.5 px-3 py-1.5 rounded-xl border transition-all duration-200 ${
                  profileOpen
                    ? 'border-indigo-500/30 bg-indigo-500/10'
                    : 'border-white/[0.06] bg-white/[0.03] hover:border-white/[0.1] hover:bg-white/[0.05]'
                }`}
              >
                <div className="relative">
                  <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-indigo-500/50 to-violet-500/50 border border-indigo-500/40 flex items-center justify-center">
                    <span className="font-display font-bold text-[10px] text-indigo-200">{initials}</span>
                  </div>
                  <span className="absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full bg-teal-400 border border-deep" />
                </div>
                <div className="text-left">
                  <div className="text-xs font-semibold text-text-primary leading-none mb-0.5">{displayName}</div>
                  <div className="font-mono text-[9px] text-text-muted leading-none">{plan} plan</div>
                </div>
                <ChevronDown className={`w-3 h-3 text-text-muted transition-transform duration-200 ${profileOpen ? 'rotate-180' : ''}`} />
              </button>

              {/* User info header injected above dropdown */}
              <AnimatePresence>
                {profileOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: 6, scale: 0.97 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 4, scale: 0.97 }}
                    transition={{ duration: 0.15, ease: 'easeOut' }}
                    className="absolute right-0 top-[calc(100%+8px)] w-72 rounded-2xl border border-white/[0.08] overflow-hidden z-50"
                    style={{
                      background: 'rgba(13, 17, 28, 0.97)',
                      backdropFilter: 'blur(24px)',
                      boxShadow: '0 8px 40px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.05)',
                    }}
                  >
                    {/* User identity header */}
                    <div className="px-4 py-4 border-b border-white/[0.06]">
                      <div className="flex items-center gap-3">
                        <div className="relative flex-shrink-0">
                          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500/40 to-violet-500/40 border border-indigo-500/30 flex items-center justify-center">
                            <span className="font-display font-bold text-sm text-indigo-200">{initials}</span>
                          </div>
                          <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-teal-400 border-2 border-[#0d111c]" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-display font-semibold text-sm text-text-primary truncate">{displayName}</div>
                          <div className="font-mono text-[10px] text-text-muted truncate">{email}</div>
                        </div>
                        <span className="flex-shrink-0 font-mono text-[9px] px-2 py-0.5 rounded-md bg-indigo-500/15 border border-indigo-500/25 text-indigo-400 tracking-wider">
                          {plan}
                        </span>
                      </div>
                    </div>

                    {/* Menu items */}
                    <div className="p-1.5">
                      {[
                        { label: 'Profile', sub: 'Account details & preferences', href: '/profile' },
                        { label: 'Activity log', sub: 'Your recent investigations', href: '/profile' },
                        { label: 'Billing & plan', sub: 'Manage subscription', href: '/profile' },
                        { label: 'API Keys', sub: 'Manage API credentials', href: '/profile' },
                        { label: 'Settings', sub: 'Integrations & preferences', href: '/profile' },
                      ].map(({ label, sub, href }) => (
                        <button
                          key={label}
                          onClick={() => { setProfileOpen(false); navigate(href) }}
                          className="w-full flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-white/[0.05] transition-all duration-150 group text-left"
                        >
                          <div className="min-w-0">
                            <div className="text-xs font-medium text-text-primary group-hover:text-white transition-colors">{label}</div>
                            <div className="font-mono text-[9px] text-text-muted truncate">{sub}</div>
                          </div>
                          <ChevronRight className="w-3 h-3 text-text-ghost group-hover:text-text-muted transition-colors flex-shrink-0 ml-2" />
                        </button>
                      ))}
                    </div>

                    <div className="mx-3 h-px bg-white/[0.05]" />

                    <div className="p-1.5">
                      <button
                        onClick={() => setProfileOpen(false)}
                        className="w-full flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-white/[0.05] transition-all duration-150 group text-left"
                      >
                        <div className="text-xs font-medium text-text-secondary group-hover:text-text-primary transition-colors">Help &amp; documentation</div>
                        <ChevronRight className="w-3 h-3 text-text-ghost group-hover:text-text-muted transition-colors" />
                      </button>

                      <button
                        onClick={handleSignOut}
                        className="w-full flex items-center px-3 py-2.5 rounded-xl hover:bg-rose-500/10 transition-all duration-150 group text-left gap-2"
                      >
                        <LogOut className="w-3.5 h-3.5 text-rose-400/70 group-hover:text-rose-400 transition-colors flex-shrink-0" />
                        <div className="text-xs font-medium text-rose-400/80 group-hover:text-rose-400 transition-colors">Sign out</div>
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>

          {/* Mobile menu toggle */}
          <button
            className="md:hidden ml-auto p-2 rounded-lg border border-white/[0.06] text-text-secondary"
            onClick={() => setMenuOpen(!menuOpen)}
          >
            {menuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden border-t border-white/[0.06] bg-deep/95 backdrop-blur-xl"
          >
            <div className="px-4 py-3 space-y-1">
              <div className="flex items-center gap-3 px-3 py-3 mb-2 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500/40 to-violet-500/40 border border-indigo-500/30 flex items-center justify-center">
                  <span className="font-display font-bold text-xs text-indigo-200">{initials}</span>
                </div>
                <div>
                  <div className="text-sm font-semibold text-text-primary">{displayName}</div>
                  <div className="font-mono text-[10px] text-text-muted">{email}</div>
                </div>
              </div>

              {navLinks.map(({ label, href, icon: Icon }) => (
                <Link
                  key={href}
                  to={href}
                  onClick={() => setMenuOpen(false)}
                  className={`flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm ${
                    isActive(href) ? 'text-text-primary bg-indigo-500/10 border border-indigo-500/15' : 'text-text-secondary'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </Link>
              ))}

              <div className="h-px bg-white/[0.05] my-1" />

              <button
                onClick={() => { setMenuOpen(false); void handleSignOut() }}
                className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm text-rose-400/80"
              >
                <LogOut className="w-4 h-4" />
                Sign out
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.header>
  )
}
