// LogRaven — Level 0 Top Masthead & Global Telemetry Header
import { useState, useRef, useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Cloud,
  Plus,
  ChevronDown,
  User as UserIcon,
  LogOut,
  AlertTriangle,
  Play,
  Check,
  Layers,
  Search,
  Sparkles,
  Bell,
  Home,
  Menu,
} from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import { useAuth } from '../../hooks/useAuth'
import type { CloudAccount } from '../../types/audit'

interface AppHeaderProps {
  accounts: CloudAccount[]
  activeAccount: CloudAccount | null
  onSelectAccount: (account: CloudAccount) => void
  onOpenConnectModal: () => void
  onOpenAuditorModal: () => void
  onOpenQuickScanModal: () => void
  onToggleSidebar?: () => void
}

export default function AppHeader({
  accounts,
  activeAccount,
  onSelectAccount,
  onOpenConnectModal,
  onOpenQuickScanModal,
  onToggleSidebar,
}: AppHeaderProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const { logout } = useAuth()
  const user = useAuthStore((s) => s.user)

  const displayName = user?.name ?? user?.email?.split('@')[0] ?? 'Operator'
  const initials = displayName.charAt(0).toUpperCase()
  const email = user?.email ?? ''

  const [accountMenuOpen, setAccountMenuOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const [suiteMenuOpen, setSuiteMenuOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [aiModalOpen, setAiModalOpen] = useState(false)

  const accountMenuRef = useRef<HTMLDivElement>(null)
  const profileRef = useRef<HTMLDivElement>(null)
  const suiteMenuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (accountMenuRef.current && !accountMenuRef.current.contains(e.target as Node)) {
        setAccountMenuOpen(false)
      }
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false)
      }
      if (suiteMenuRef.current && !suiteMenuRef.current.contains(e.target as Node)) {
        setSuiteMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleOutsideClick)
    return () => document.removeEventListener('mousedown', handleOutsideClick)
  }, [])

  // Keyboard shortcut Ctrl+K / Cmd+K for search omnibar
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        const el = document.getElementById('lograven-omnibar') as HTMLInputElement | null
        el?.focus()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const getBreadcrumbs = () => {
    const p = location.pathname
    if (p === '/dashboard' || p === '/') {
      return { section: 'Cloud Compliance', page: 'Executive Posture Overview' }
    }
    if (p.startsWith('/compliance/connect')) {
      return { section: 'Cloud Compliance', page: 'Connect Cloud Account' }
    }
    if (p === '/compliance') {
      return { section: 'Cloud Compliance', page: 'Compliance Control Room' }
    }
    if (p === '/compliance/frameworks') {
      return { section: 'Cloud Compliance', page: 'Supported Frameworks Catalog' }
    }
    if (p.startsWith('/compliance/frameworks/')) {
      return { section: 'Cloud Compliance', page: 'Framework Controls' }
    }
    if (p === '/investigations') {
      return { section: 'Threat Detection', page: 'Investigations Console' }
    }
    if (p === '/investigations/new') {
      return { section: 'Threat Detection', page: 'New Investigation' }
    }
    if (p.startsWith('/investigations/')) {
      return { section: 'Threat Detection', page: 'Investigation Details' }
    }
    if (p === '/play-parser') {
      return { section: 'Threat Detection', page: 'PlayParser Rules' }
    }
    if (p === '/alerts') {
      return { section: 'Threat Detection', page: 'Security Detections Feed' }
    }
    if (p === '/profile') {
      return { section: 'System', page: 'Settings and Security' }
    }
    return { section: 'Platform', page: 'Console' }
  }

  const { section, page } = getBreadcrumbs()

  const handleSignOut = async () => {
    await logout()
    navigate('/login')
  }

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!searchQuery.trim()) return
    navigate(`/alerts?q=${encodeURIComponent(searchQuery)}`)
  }

  return (
    <header className="h-14 border-b border-white/[0.08] bg-deep/95 backdrop-blur-xl px-4 sm:px-6 flex items-center justify-between gap-4 z-40 select-none">
      {/* Left: Suite Switcher & Breadcrumbs */}
      <div className="flex items-center gap-3 min-w-0 flex-shrink-0">
        {onToggleSidebar && (
          <button
            type="button"
            onClick={onToggleSidebar}
            aria-label="Toggle navigation rail"
            className="w-8 h-8 rounded-lg border border-white/[0.08] hover:border-amber-400/40 bg-white/[0.02] hover:bg-amber-400/10 flex items-center justify-center text-text-muted hover:text-amber-300 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer"
          >
            <Menu className="w-4 h-4" />
          </button>
        )}

        {/* Product Suite Selector */}
        <div ref={suiteMenuRef} className="relative">
          <button
            type="button"
            onClick={() => setSuiteMenuOpen(!suiteMenuOpen)}
            className="flex items-center gap-2 px-2.5 py-1 rounded-lg border border-white/[0.08] bg-white/[0.02] hover:bg-white/[0.05] text-xs font-semibold text-text-primary transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <div className="w-4 h-4 rounded bg-amber-400/15 border border-amber-400/30 flex items-center justify-center text-amber-400">
              <Cloud className="w-2.5 h-2.5" />
            </div>
            <span className="hidden md:inline font-display">LogRaven Cloud Security</span>
            <span className="md:hidden font-display">LogRaven</span>
            <ChevronDown className="w-3 h-3 text-text-muted" />
          </button>

          {suiteMenuOpen && (
            <div className="absolute left-0 top-full mt-1.5 w-56 rounded-xl border border-white/[0.12] bg-deep/95 backdrop-blur-2xl p-1.5 z-50 shadow-2xl space-y-0.5">
              <div className="px-2.5 py-1 text-[11px] font-semibold text-text-muted">Security Suites</div>
              <Link
                to="/dashboard"
                onClick={() => setSuiteMenuOpen(false)}
                className="flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs text-text-primary hover:bg-white/[0.05] transition-colors duration-150"
              >
                <span>Cloud Security Posture</span>
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
              </Link>
              <Link
                to="/alerts"
                onClick={() => setSuiteMenuOpen(false)}
                className="flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs text-text-secondary hover:text-text-primary hover:bg-white/[0.05] transition-colors duration-150"
              >
                <span>Next-Gen SIEM & Triage</span>
              </Link>
              <Link
                to="/compliance"
                onClick={() => setSuiteMenuOpen(false)}
                className="flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs text-text-secondary hover:text-text-primary hover:bg-white/[0.05] transition-colors duration-150"
              >
                <span>Compliance Control Room</span>
              </Link>
            </div>
          )}
        </div>

        {/* Breadcrumb Context */}
        <div className="hidden lg:flex items-center gap-2 text-xs text-text-muted border-l border-white/[0.08] pl-3">
          <span className="text-text-muted/80">{section}</span>
          <span className="text-white/20">/</span>
          <span className="text-text-primary font-medium tracking-tight truncate max-w-[180px]">
            {page}
          </span>
          <Link
            to="/dashboard"
            title="Overview home"
            className="text-text-muted hover:text-amber-400 transition-colors duration-150 ml-1"
          >
            <Home className="w-3 h-3" />
          </Link>
        </div>
      </div>

      {/* Center: Global Omnibar Search & Raven AI Button */}
      <div className="flex-1 max-w-xl hidden sm:flex items-center gap-2 mx-2">
        <form onSubmit={handleSearchSubmit} className="relative flex-1">
          <Search className="w-3.5 h-3.5 text-text-muted absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            id="lograven-omnibar"
            type="search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search assets, rules, detections..."
            className="w-full h-8 pl-8 pr-14 rounded-lg border border-white/[0.08] bg-void/60 text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-amber-400/50 focus:ring-1 focus:ring-amber-400/40 transition-colors duration-150"
          />
          <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] text-text-muted bg-white/[0.06] border border-white/[0.08] rounded px-1.5 py-0.5 pointer-events-none font-mono">
            Ctrl K
          </kbd>
        </form>

        {/* Raven AI Assistant Trigger (Falcon Charlotte AI Style) */}
        <button
          type="button"
          onClick={() => setAiModalOpen(true)}
          className="flex items-center gap-1.5 h-8 px-3 rounded-lg border border-amber-400/30 bg-amber-400/10 hover:bg-amber-400/20 text-amber-300 text-xs font-medium transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none motion-safe:active:scale-[0.98] motion-reduce:transform-none cursor-pointer whitespace-nowrap flex-shrink-0"
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          <span>Raven AI</span>
        </button>
      </div>

      {/* Right: Cloud account switcher, Quick Actions, Profile */}
      <div className="flex items-center gap-2 sm:gap-2.5 ml-auto flex-shrink-0">
        {/* Cloud Account Switcher */}
        <div ref={accountMenuRef} className="relative">
          {accounts.length > 0 ? (
            <button
              type="button"
              onClick={() => setAccountMenuOpen(!accountMenuOpen)}
              className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg border border-white/[0.08] bg-white/[0.02] hover:bg-white/[0.06] transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none motion-safe:active:scale-[0.98] motion-reduce:transform-none text-left group cursor-pointer"
            >
              <div className="w-4 h-4 rounded bg-emerald-400/15 border border-emerald-400/30 flex items-center justify-center text-emerald-400">
                <Cloud className="w-2.5 h-2.5" />
              </div>
              <div className="hidden md:block min-w-0">
                <div className="text-xs font-semibold text-text-primary truncate max-w-[120px]">
                  {activeAccount ? activeAccount.name : 'Select Account'}
                </div>
                <div className="text-[10px] text-text-muted flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  <span>{activeAccount?.provider?.toUpperCase() ?? 'AWS'} Connected</span>
                </div>
              </div>
              <ChevronDown className="w-3 h-3 text-text-muted group-hover:text-text-primary transition-transform duration-150 motion-reduce:transition-none" />
            </button>
          ) : (
            <button
              type="button"
              onClick={onOpenConnectModal}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-amber-400/35 bg-amber-400/10 hover:bg-amber-400/15 text-amber-300 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none text-xs font-medium cursor-pointer"
            >
              <AlertTriangle className="w-3 h-3 text-amber-400 flex-shrink-0" />
              <span>Connect Cloud</span>
            </button>
          )}

          {/* Account Dropdown */}
          <AnimatePresence>
            {accountMenuOpen && accounts.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 4, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 2, scale: 0.98 }}
                transition={{ duration: 0.12 }}
                className="absolute right-0 top-full mt-1.5 w-64 rounded-xl border border-white/[0.12] bg-deep/95 shadow-2xl p-1.5 z-50 backdrop-blur-2xl"
              >
                <div className="px-2.5 py-1 text-[11px] font-semibold text-text-muted">
                  Connected Cloud Accounts ({accounts.length})
                </div>

                <div className="space-y-0.5 max-h-56 overflow-y-auto my-1 custom-scrollbar">
                  {accounts.map((acc) => {
                    const isSelected = activeAccount?.id === acc.id
                    return (
                      <button
                        key={acc.id}
                        type="button"
                        onClick={() => {
                          onSelectAccount(acc)
                          setAccountMenuOpen(false)
                        }}
                        className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-left transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none ${
                          isSelected
                            ? 'bg-amber-400/10 text-text-primary border border-amber-400/25'
                            : 'hover:bg-white/[0.04] text-text-secondary border border-transparent'
                        }`}
                      >
                        <div className="min-w-0 pr-2">
                          <div className="text-xs font-semibold text-text-primary truncate">{acc.name}</div>
                          <div className="text-[10px] text-text-muted truncate">
                            {acc.provider?.toUpperCase()} · {acc.role_arn ? acc.role_arn.split('/').pop() : 'Direct'}
                          </div>
                        </div>
                        {isSelected && <Check className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />}
                      </button>
                    )
                  })}
                </div>

                <div className="border-t border-white/[0.06] pt-1 mt-1">
                  <button
                    type="button"
                    onClick={() => {
                      setAccountMenuOpen(false)
                      onOpenConnectModal()
                    }}
                    className="w-full flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-amber-300 hover:bg-amber-400/10 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
                  >
                    <Plus className="w-3.5 h-3.5" /> Connect Another Account
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Quick Scan Button */}
        <button
          type="button"
          onClick={onOpenQuickScanModal}
          className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-amber-400/30 bg-amber-400/10 hover:bg-amber-400/20 text-amber-300 text-xs font-semibold transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none motion-safe:active:scale-[0.98] motion-reduce:transform-none cursor-pointer"
        >
          <Play className="w-3 h-3 text-amber-300 fill-amber-300" />
          <span>Quick Scan</span>
        </button>

        {/* Notifications */}
        <button
          type="button"
          title="Notifications"
          aria-label="Notifications"
          className="w-8 h-8 rounded-lg border border-white/[0.08] hover:border-white/[0.15] bg-white/[0.02] hover:bg-white/[0.06] flex items-center justify-center text-text-muted hover:text-text-primary transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none relative"
        >
          <Bell className="w-3.5 h-3.5" />
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400 absolute top-2 right-2" />
        </button>

        {/* User Profile Avatar & Dropdown */}
        <div ref={profileRef} className="relative">
          <button
            type="button"
            onClick={() => setProfileOpen(!profileOpen)}
            aria-label="User Account Menu"
            className="w-8 h-8 rounded-lg border border-white/[0.08] bg-white/[0.02] hover:border-amber-400/30 hover:bg-white/[0.06] flex items-center justify-center transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none motion-safe:active:scale-[0.98] motion-reduce:transform-none group cursor-pointer"
          >
            <div className="w-6 h-6 rounded bg-amber-400/15 border border-amber-400/30 flex items-center justify-center font-display font-bold text-xs text-amber-300">
              {initials}
            </div>
          </button>

          <AnimatePresence>
            {profileOpen && (
              <motion.div
                initial={{ opacity: 0, y: 4, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 2, scale: 0.98 }}
                transition={{ duration: 0.12 }}
                className="absolute right-0 top-full mt-1.5 w-56 rounded-xl border border-white/[0.12] bg-deep/95 shadow-2xl p-1.5 z-50 backdrop-blur-2xl"
              >
                <div className="px-2.5 py-1.5 border-b border-white/[0.06] mb-1">
                  <div className="text-xs font-semibold text-text-primary truncate">{displayName}</div>
                  <div className="text-[10px] text-text-muted truncate">{email}</div>
                </div>

                <Link
                  to="/profile"
                  onClick={() => setProfileOpen(false)}
                  className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs text-text-secondary hover:text-text-primary hover:bg-white/[0.05] transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
                >
                  <UserIcon className="w-3.5 h-3.5 text-text-muted" /> Profile & Security
                </Link>

                <Link
                  to="/compliance/frameworks"
                  onClick={() => setProfileOpen(false)}
                  className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs text-text-secondary hover:text-text-primary hover:bg-white/[0.05] transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
                >
                  <Layers className="w-3.5 h-3.5 text-text-muted" /> Frameworks Library
                </Link>

                <div className="border-t border-white/[0.06] my-1" />

                <button
                  type="button"
                  onClick={handleSignOut}
                  className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs text-threat-critical hover:bg-threat-critical/10 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none motion-safe:active:scale-[0.98] motion-reduce:transform-none text-left cursor-pointer"
                >
                  <LogOut className="w-3.5 h-3.5 text-threat-critical" /> Sign Out
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Raven AI Copilot Modal Dialog */}
      <AnimatePresence>
        {aiModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-void/80 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              className="w-full max-w-lg rounded-2xl border border-white/[0.12] bg-deep p-5 shadow-2xl text-left"
            >
              <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-md bg-amber-400/15 border border-amber-400/30 flex items-center justify-center text-amber-400">
                    <Sparkles className="w-3.5 h-3.5" />
                  </div>
                  <span className="font-display font-semibold text-sm text-text-primary">Raven AI Security Copilot</span>
                </div>
                <button
                  type="button"
                  onClick={() => setAiModalOpen(false)}
                  className="text-text-muted hover:text-text-primary text-xs"
                >
                  Close
                </button>
              </div>

              <div className="py-4 space-y-3">
                <p className="text-xs text-text-secondary leading-relaxed">
                  Raven AI correlates telemetry feeds, multi-hop attack paths, and regulatory compliance baselines across your cloud accounts.
                </p>
                <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-1.5">
                  <div className="text-[11px] font-semibold text-amber-300">Suggested queries:</div>
                  <button
                    type="button"
                    onClick={() => {
                      setAiModalOpen(false)
                      navigate('/dashboard')
                    }}
                    className="block w-full text-left text-xs text-text-muted hover:text-text-primary py-0.5 whitespace-nowrap truncate disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    • &ldquo;Show critical attack paths exposing S3 buckets with admin roles&rdquo;
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setAiModalOpen(false)
                      navigate('/alerts')
                    }}
                    className="block w-full text-left text-xs text-text-muted hover:text-text-primary py-0.5 whitespace-nowrap truncate disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    • &ldquo;Correlate recent AWS CloudTrail failed logins with WAF alerts&rdquo;
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setAiModalOpen(false)
                      navigate('/compliance')
                    }}
                    className="block w-full text-left text-xs text-text-muted hover:text-text-primary py-0.5 whitespace-nowrap truncate disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    • &ldquo;Assess SOC 2 Type II readiness gaps for production fleet&rdquo;
                  </button>
                </div>
              </div>

              <div className="pt-2 flex justify-end">
                <button
                  type="button"
                  onClick={() => setAiModalOpen(false)}
                  className="px-3.5 py-1.5 rounded-lg bg-amber-400 text-void font-semibold text-xs hover:bg-amber-300 transition-colors duration-150"
                >
                  Got it
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </header>
  )
}
