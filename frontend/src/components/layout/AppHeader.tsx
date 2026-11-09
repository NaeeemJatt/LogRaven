// LogRaven — Top Sub-Navigation Header & Cloud Account Switcher
import { useState, useRef, useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
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
  X,
  Send,
  Bot,
} from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import { useAuth } from '../../hooks/useAuth'
import type { CloudAccount } from '../../types/audit'

interface AppHeaderProps {
  accounts: CloudAccount[]
  activeAccount: CloudAccount | null
  onSelectAccount: (account: CloudAccount) => void
  onOpenConnectModal: () => void
  onOpenAuditorModal?: () => void
  onOpenQuickScanModal: () => void
  onToggleSidebar?: () => void
}

export default function AppHeader({
  accounts,
  activeAccount,
  onSelectAccount,
  onOpenConnectModal,
  onOpenQuickScanModal,
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
  const [searchQuery, setSearchQuery] = useState('')
  const [aiModalOpen, setAiModalOpen] = useState(false)
  const [aiPrompt, setAiPrompt] = useState('')

  const accountMenuRef = useRef<HTMLDivElement>(null)
  const profileRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (accountMenuRef.current && !accountMenuRef.current.contains(e.target as Node)) {
        setAccountMenuOpen(false)
      }
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false)
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

  // Derive contextual breadcrumb text
  const getBreadcrumbs = () => {
    const p = location.pathname

    if (p === '/dashboard' || p === '/') {
      return { section: '', page: 'Cloud Compliance Overview' }
    }
    if (p.startsWith('/compliance/connect')) {
      return { section: 'Cloud Compliance', page: 'Connect Cloud Account' }
    }
    if (p === '/compliance') {
      const currentTab = new URLSearchParams(location.search).get('tab')
      if (currentTab === 'results') {
        return { section: 'Cloud Compliance', page: 'Audit Assessment Results' }
      }
      return { section: '', page: 'Compliance Control Room' }
    }
    if (p === '/compliance/frameworks') {
      return { section: 'Cloud Compliance', page: 'Supported Frameworks Catalog' }
    }
    if (p.startsWith('/compliance/frameworks/')) {
      return { section: 'Cloud Compliance', page: 'Framework Controls & Guidance' }
    }
    if (p === '/investigations') {
      return { section: '', page: 'Investigations' }
    }
    if (p === '/investigations/new') {
      return { section: 'Investigations', page: 'New Investigation' }
    }
    if (p.startsWith('/investigations/')) {
      return { section: 'Investigations', page: 'Investigation Details' }
    }
    if (p === '/play-parser') {
      return { section: '', page: 'PlayParser' }
    }
    if (p === '/alerts') {
      return { section: '', page: 'Triage Console' }
    }
    if (p === '/profile') {
      return { section: 'System', page: 'Settings & Account Security' }
    }
    return { section: 'Platform', page: 'Console' }
  }

  const { section, page } = getBreadcrumbs()

  const isComplianceSection =
    location.pathname === '/' ||
    location.pathname.startsWith('/compliance') ||
    location.pathname === '/dashboard'

  const handleSignOut = async () => {
    await logout()
    navigate('/login')
  }

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!searchQuery.trim()) return
    navigate(`/alerts?q=${encodeURIComponent(searchQuery)}`)
  }

  const handleAiSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!aiPrompt.trim()) return
    navigate(`/alerts?q=${encodeURIComponent(aiPrompt)}`)
    setAiModalOpen(false)
    setAiPrompt('')
  }

  return (
    <header className="h-16 border-b border-white/[0.08] bg-surface/70 backdrop-blur-xl px-4 sm:px-6 flex items-center justify-between gap-4 z-30 select-none">
      {/* Left: Breadcrumbs & Context indicator (strictly preserving main's design) */}
      {page ? (
        <div className="flex items-center gap-3 min-w-0 flex-shrink-0">
          {section ? (
            <>
              <div className="hidden sm:flex items-center gap-2 text-xs text-text-muted">
                <span className="text-text-muted/80">{section}</span>
                <span className="text-white/20">/</span>
                <span className="text-text-primary font-medium tracking-tight truncate">{page}</span>
              </div>
              <div className="sm:hidden font-display font-semibold text-sm text-text-primary truncate">
                {page}
              </div>
            </>
          ) : (
            <div className="font-display font-bold text-base sm:text-lg text-text-primary tracking-tight truncate">
              {page}
            </div>
          )}
        </div>
      ) : (
        <div className="min-w-0" />
      )}

      {/* Center: Global Omnibar Search & Raven AI Assistant Trigger */}
      <div className="flex-1 max-w-xl hidden md:flex items-center gap-2 mx-2">
        <form onSubmit={handleSearchSubmit} className="relative flex-1">
          <Search className="w-3.5 h-3.5 text-text-muted absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            id="lograven-omnibar"
            type="search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search assets, rules, detections…"
            className="w-full h-8 pl-8 pr-14 rounded-lg border border-white/[0.08] bg-void/60 text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-amber-400/50 focus:ring-1 focus:ring-amber-400/40 transition-colors duration-150"
          />
          <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] text-text-muted bg-white/[0.06] border border-white/[0.08] rounded px-1.5 py-0.5 pointer-events-none font-mono">
            Ctrl K
          </kbd>
        </form>

        <button
          type="button"
          onClick={() => setAiModalOpen(true)}
          className="flex items-center gap-1.5 h-8 px-3 rounded-lg border border-amber-400/30 bg-amber-400/10 hover:bg-amber-400/20 text-amber-300 text-xs font-medium transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none motion-safe:active:scale-[0.98] motion-reduce:transform-none cursor-pointer whitespace-nowrap flex-shrink-0"
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          <span>Raven AI</span>
        </button>
      </div>

      {/* Right: Quick actions, account switcher & profile (strictly preserving main) */}
      <div className="flex items-center gap-2 sm:gap-3 ml-auto flex-shrink-0">
        {/* Cloud Account Selector */}
        {isComplianceSection && (
          <>
            <div ref={accountMenuRef} className="relative">
              {accounts.length > 0 ? (
                <button
                  type="button"
                  onClick={() => setAccountMenuOpen(!accountMenuOpen)}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-white/[0.08] bg-white/[0.02] hover:bg-white/[0.05] transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] motion-reduce:transition-none text-left group"
                >
                  <div className="w-2 h-2 rounded-full bg-emerald-400" />
                  <div className="hidden md:block min-w-0">
                    <div className="text-xs font-semibold text-text-primary truncate max-w-[130px]">
                      {activeAccount ? activeAccount.name : 'Select Account'}
                    </div>
                    <div className="text-[10px] text-text-muted">
                      {activeAccount?.provider?.toUpperCase() ?? 'AWS'} Connected
                    </div>
                  </div>
                  <ChevronDown className="w-3 h-3 text-text-muted group-hover:text-text-primary transition-transform duration-150" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={onOpenConnectModal}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-amber-400/30 bg-amber-400/10 hover:bg-amber-400/20 text-amber-300 text-xs font-medium transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] motion-reduce:transition-none"
                >
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                  <span>Connect Cloud</span>
                </button>
              )}

              {/* Account Dropdown */}
              <AnimatePresence>
                {accountMenuOpen && accounts.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, y: 6, scale: 0.97 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 4, scale: 0.97 }}
                    transition={{ duration: 0.15 }}
                    className="absolute right-0 top-[calc(100%+8px)] w-60 rounded-2xl border border-white/[0.1] bg-deep/95 p-1.5 z-50 backdrop-blur-2xl"
                  >
                    <div className="px-3 py-2 border-b border-white/[0.06] mb-1">
                      <div className="text-xs font-semibold text-text-primary">
                        Connected Accounts ({accounts.length})
                      </div>
                      <div className="text-[10px] text-text-muted">Active compliance fleet</div>
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
                            className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-left transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none ${
                              isSelected
                                ? 'bg-amber-400/10 text-text-primary border border-amber-400/25'
                                : 'hover:bg-white/[0.04] text-text-secondary border border-transparent'
                            }`}
                          >
                            <div className="min-w-0 pr-2">
                              <div className="text-xs font-medium text-text-primary truncate">{acc.name}</div>
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
                        className="w-full flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium text-amber-300 hover:bg-amber-400/10 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
                      >
                        <Plus className="w-3.5 h-3.5" /> Connect Another Account
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Quick Audit Scan Button */}
            <button
              type="button"
              onClick={onOpenQuickScanModal}
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-amber-400/30 bg-amber-400/10 hover:bg-amber-400/20 text-amber-300 text-xs font-semibold transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] motion-reduce:transition-none"
            >
              <Play className="w-3.5 h-3.5 text-amber-300 fill-amber-300" />
              <span>Quick Scan</span>
            </button>
          </>
        )}

        {/* Threat Detection / Investigations Quick Action */}
        {location.pathname === '/investigations' && (
          <Link
            to="/investigations/new"
            className="btn-sovereign inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold motion-safe:transition-transform motion-safe:active:scale-[0.98] motion-reduce:transition-none focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none whitespace-nowrap shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Investigation</span>
          </Link>
        )}

        {/* PlayParser Quick Indicator */}
        {location.pathname === '/play-parser' && (
          <span className="text-xs font-medium px-2.5 py-1 rounded-xl bg-amber-400/10 text-amber-300 border border-amber-400/25">
            Sandbox Lab
          </span>
        )}

        {/* Alerts / Triage Console Indicator */}
        {location.pathname === '/alerts' && (
          <span className="text-xs font-medium px-2.5 py-1 rounded-xl bg-amber-400/10 text-amber-300 border border-amber-400/25">
            Active Feed
          </span>
        )}

        {/* User Profile Avatar & Dropdown */}
        <div ref={profileRef} className="relative">
          <button
            type="button"
            onClick={() => setProfileOpen(!profileOpen)}
            aria-label="User Account Menu"
            className="w-9 h-9 rounded-xl border border-white/[0.08] bg-white/[0.03] hover:border-amber-400/30 hover:bg-white/[0.06] flex items-center justify-center transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] group"
          >
            <div className="w-7 h-7 rounded-lg bg-amber-400/10 border border-amber-400/25 flex items-center justify-center font-display font-bold text-xs text-amber-300">
              {initials}
            </div>
          </button>

          <AnimatePresence>
            {profileOpen && (
              <motion.div
                initial={{ opacity: 0, y: 6, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 4, scale: 0.97 }}
                transition={{ duration: 0.15 }}
                className="absolute right-0 top-[calc(100%+8px)] w-56 rounded-2xl border border-white/[0.1] bg-deep/95 shadow-lg p-1.5 z-50 backdrop-blur-2xl"
              >
                <div className="px-3 py-2 border-b border-white/[0.06] mb-1">
                  <div className="text-xs font-semibold text-text-primary truncate">{displayName}</div>
                  <div className="text-[10px] text-text-muted truncate">{email}</div>
                </div>

                <Link
                  to="/profile"
                  onClick={() => setProfileOpen(false)}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-text-secondary hover:text-text-primary hover:bg-white/[0.05] transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
                >
                  <UserIcon className="w-3.5 h-3.5 text-text-muted" /> My Profile & Security
                </Link>

                <Link
                  to="/compliance/frameworks"
                  onClick={() => setProfileOpen(false)}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-text-secondary hover:text-text-primary hover:bg-white/[0.05] transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
                >
                  <Layers className="w-3.5 h-3.5 text-text-muted" /> Frameworks Library
                </Link>

                <div className="border-t border-white/[0.06] my-1" />

                <button
                  type="button"
                  onClick={handleSignOut}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-threat-critical hover:bg-threat-critical/10 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] text-left cursor-pointer"
                >
                  <LogOut className="w-3.5 h-3.5 text-threat-critical" /> Sign Out
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Raven AI Assistant Modal */}
      {aiModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="raven-ai-title"
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4 select-text"
          onClick={() => setAiModalOpen(false)}
        >
          <div
            className="w-full max-w-lg rounded-2xl border border-white/[0.12] bg-deep/95 p-6 space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div className="flex items-center gap-2">
                <Bot className="w-5 h-5 text-amber-400" />
                <h3 id="raven-ai-title" className="text-sm font-semibold text-text-primary">
                  Raven AI Security Analyst
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setAiModalOpen(false)}
                className="p-1 rounded text-text-muted hover:text-text-primary cursor-pointer"
                aria-label="Close dialog"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-text-secondary leading-relaxed">
              Ask Raven AI about active attack paths, adversary tactics, automated remediation CLI commands, or compliance readiness.
            </p>

            <form onSubmit={handleAiSubmit} className="space-y-3">
              <div className="relative">
                <input
                  type="text"
                  value={aiPrompt}
                  onChange={(e) => setAiPrompt(e.target.value)}
                  placeholder="e.g. Find critical attack paths in production..."
                  className="w-full h-10 pl-3 pr-10 rounded-xl border border-white/[0.1] bg-void/60 text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-amber-400/50 focus:ring-1 focus:ring-amber-400/40"
                  autoFocus
                />
                <button
                  type="submit"
                  aria-label="Ask Raven AI"
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg bg-amber-400/15 text-amber-300 hover:bg-amber-400/25 transition-colors cursor-pointer"
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="flex flex-wrap items-center gap-1.5 pt-1">
                <span className="text-[11px] text-text-muted">Suggested:</span>
                <button
                  type="button"
                  onClick={() => setAiPrompt('Show critical attack paths')}
                  className="text-[11px] text-amber-300 hover:underline px-1.5 py-0.5 rounded bg-white/[0.03]"
                >
                  Show critical attack paths
                </button>
                <button
                  type="button"
                  onClick={() => setAiPrompt('Correlate recent AWS CloudTrail logs')}
                  className="text-[11px] text-amber-300 hover:underline px-1.5 py-0.5 rounded bg-white/[0.03]"
                >
                  Correlate AWS CloudTrail logs
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </header>
  )
}
