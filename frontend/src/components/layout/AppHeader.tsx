// LogRaven — Top Sub-Navigation Header & Cloud Account Switcher
import { useState, useRef, useEffect } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Plus,
  User as UserIcon,
  LogOut,
  Layers,
  Search,
  ListChecks,
  Flame,
  Network,
  ShieldAlert,
} from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import { useAuth } from '../../hooks/useAuth'
import { useAuditNavStore } from '../../store/auditNavStore'
import type { CloudAccount } from '../../types/audit'

interface AppHeaderProps {
  accounts?: CloudAccount[]
  activeAccount?: CloudAccount | null
  onSelectAccount?: (account: CloudAccount) => void
  onOpenConnectModal?: () => void
  onOpenAuditorModal?: () => void
  onOpenQuickScanModal?: () => void
  onToggleSidebar?: () => void
}

export default function AppHeader(_props: AppHeaderProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const { logout } = useAuth()
  const user = useAuthStore((s) => s.user)

  const displayName = user?.name ?? user?.email?.split('@')[0] ?? 'Operator'
  const initials = displayName.charAt(0).toUpperCase()
  const email = user?.email ?? ''

  const [profileOpen, setProfileOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  const profileRef = useRef<HTMLDivElement>(null)
  const [searchParams, setSearchParams] = useSearchParams()
  const isAuditResultsPage = location.pathname === '/compliance' && searchParams.get('tab') === 'results'
  const { totalExceptions } = useAuditNavStore()
  const showAuditNavbar = isAuditResultsPage
  const currentView = searchParams.get('view') || 'controls'

  const handleViewChange = (newView: string) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.set('view', newView)
      return next
    }, { replace: true })
  }

  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
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
        return { section: '', page: '' }
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
    <header className="h-16 border-b border-white/[0.08] bg-surface/70 backdrop-blur-xl px-4 sm:px-6 flex items-center justify-between gap-4 z-30 select-none">
      {/* Left: When on Audit Assessment Results, render Main Menu on the left (Breadcrumb removed per request) */}
      {showAuditNavbar ? (
        <div className="flex items-center gap-1.5 overflow-x-auto py-1 flex-shrink-0">
          {([
            { key: 'controls', label: 'Control browser', icon: ListChecks },
            { key: 'attack_path', label: 'Attack Path Graph', icon: Flame },
            { key: 'crosswalk', label: 'Crosswalk', icon: Network },
            { key: 'exceptions', label: `Exceptions (${totalExceptions})`, icon: ShieldAlert },
          ]).map(({ key, label, icon: Icon }) => {
            const isActive = currentView === key
            return (
              <button
                key={key}
                type="button"
                onClick={() => handleViewChange(key)}
                className={`inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-medium transition-all cursor-pointer whitespace-nowrap ${
                  isActive
                    ? 'border-amber-400/60 bg-amber-400/10 text-text-primary shadow-sm ring-1 ring-amber-400/30 font-semibold'
                    : 'border-white/[0.08] bg-white/[0.02] text-text-muted hover:text-text-secondary hover:border-white/[0.14]'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-amber-400' : 'text-text-muted'}`} />
                <span>{label}</span>
              </button>
            )
          })}
        </div>
      ) : page ? (
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

      {/* Right: Quick actions, search bar (right-aligned, left of profile), and profile */}
      <div className="flex items-center gap-2 sm:gap-3 ml-auto flex-shrink-0">
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

        {/* Global Omnibar Search — Posture and Gaps specification for all pages */}
        <form onSubmit={handleSearchSubmit} className="relative hidden sm:block w-48 sm:w-56 md:w-64">
          <Search className="w-3.5 h-3.5 text-text-muted absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            id="lograven-omnibar"
            type="search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search assets, rules…"
            className="w-full h-8 pl-8 pr-11 rounded-lg border border-white/[0.08] bg-void/70 hover:bg-void focus:bg-void text-xs text-text-primary placeholder:text-text-muted/60 focus:outline-none focus:border-amber-400/50 focus:ring-1 focus:ring-amber-400/40 transition-colors"
          />
          <kbd className="absolute right-2 top-1/2 -translate-y-1/2 text-[9px] text-text-muted bg-white/[0.06] border border-white/[0.08] rounded px-1 py-0.5 pointer-events-none font-mono">
            Ctrl K
          </kbd>
        </form>

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
    </header>
  )
}
