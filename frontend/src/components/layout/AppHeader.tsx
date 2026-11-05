// LogRaven — Top Sub-Navigation Header & Cloud Account Switcher
import { useState, useRef, useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Cloud,
  Plus,
  Share2,
  ChevronDown,
  User as UserIcon,
  LogOut,
  AlertTriangle,
  Play,
  Check,
  Layers,
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
}

export default function AppHeader({
  accounts,
  activeAccount,
  onSelectAccount,
  onOpenConnectModal,
  onOpenAuditorModal,
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

  // Derive contextual breadcrumb text
  const getBreadcrumbs = () => {
    const p = location.pathname

    if (p === '/dashboard') {
      return { section: 'Cloud Compliance', page: 'Executive Posture Overview' }
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

  return (
    <header className="h-16 border-b border-white/[0.08] bg-surface/70 backdrop-blur-xl px-4 sm:px-6 flex items-center justify-between gap-4 z-30 select-none">
      {/* Left: Breadcrumbs & Context indicator */}
      {page ? (
        <div className="flex items-center gap-3 min-w-0">
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

      {/* Right: Cloud account switcher, Quick Actions, Profile */}
      <div className="flex items-center gap-2.5 sm:gap-3 ml-auto">
        {/* Compliance Controls: Cloud Account Switcher, Quick Scan, Auditor Link */}
        {isComplianceSection && (
          <>
            {/* Cloud Account Switcher / Connection Warning */}
            <div ref={accountMenuRef} className="relative">
              {accounts.length > 0 ? (
                <button
                  onClick={() => setAccountMenuOpen(!accountMenuOpen)}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-white/[0.08] bg-white/[0.03] hover:bg-white/[0.06] transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] text-left group"
                >
                  <div className="w-5 h-5 rounded-md bg-amber-400/10 border border-amber-400/20 flex items-center justify-center text-amber-400">
                    <Cloud className="w-3 h-3" />
                  </div>
                  <div className="hidden md:block min-w-0">
                    <div className="text-xs font-semibold text-text-primary truncate max-w-[130px]">
                      {activeAccount ? activeAccount.name : 'Select Account'}
                    </div>
                    <div className="text-[10px] text-text-muted flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                      <span>{activeAccount?.provider?.toUpperCase() ?? 'AWS'} Connected</span>
                    </div>
                  </div>
                  <ChevronDown className="w-3.5 h-3.5 text-text-muted group-hover:text-text-primary transition-transform duration-150" />
                </button>
              ) : (
                <button
                  onClick={onOpenConnectModal}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-amber-400/35 bg-amber-400/10 hover:bg-amber-400/15 text-amber-300 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] text-xs font-medium motion-safe:animate-pulse motion-reduce:animate-none whitespace-nowrap"
                >
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
                  <span className="whitespace-nowrap"><span className="hidden sm:inline">No Cloud Connected </span><span className="underline font-semibold">+ Connect</span></span>
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
                    className="absolute right-0 top-[calc(100%+8px)] w-64 rounded-2xl border border-white/[0.1] bg-deep/95 shadow-lg p-2 z-50 backdrop-blur-2xl"
                  >
                    <div className="px-3 py-1.5 text-xs font-semibold text-text-muted">
                      Connected Cloud Accounts ({accounts.length})
                    </div>

                    <div className="space-y-1 max-h-56 overflow-y-auto my-1 custom-scrollbar">
                      {accounts.map((acc) => {
                        const isSelected = activeAccount?.id === acc.id
                        return (
                          <button
                            key={acc.id}
                            onClick={() => {
                              onSelectAccount(acc)
                              setAccountMenuOpen(false)
                            }}
                            className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-left transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] ${
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
                        onClick={() => {
                          setAccountMenuOpen(false)
                          onOpenConnectModal()
                        }}
                        className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium text-amber-300 hover:bg-amber-400/10 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98]"
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
              onClick={onOpenQuickScanModal}
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-amber-400/30 bg-amber-400/10 hover:bg-amber-400/20 text-amber-300 text-xs font-semibold transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] motion-reduce:transition-none"
            >
              <Play className="w-3.5 h-3.5 text-amber-300 fill-amber-300" />
              <span>Quick Scan</span>
            </button>

            {/* Auditor Share Link */}
            <button
              onClick={onOpenAuditorModal}
              title="Share Evidence Vault with External Auditor"
              className="hidden lg:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-white/[0.08] bg-white/[0.03] hover:bg-white/[0.06] text-text-secondary hover:text-text-primary text-xs font-medium transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] motion-reduce:transition-none"
            >
              <Share2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>Auditor Link</span>
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
                  onClick={handleSignOut}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-threat-critical hover:bg-threat-critical/10 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] text-left"
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
