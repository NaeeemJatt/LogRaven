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
    const search = new URLSearchParams(location.search)
    const tab = search.get('tab')

    if (p === '/dashboard') {
      return { section: 'Cloud Compliance', page: 'Executive Posture Overview' }
    }
    if (p === '/compliance') {
      if (tab === 'accounts') return { section: 'Cloud Compliance', page: 'Cloud Accounts & Fleets' }
      if (tab === 'audit') return { section: 'Cloud Compliance', page: 'New Compliance Audit' }
      if (tab === 'history') return { section: 'Cloud Compliance', page: 'Audit History & Evidence' }
      if (tab === 'attack-path') return { section: 'Cloud Compliance', page: 'Attack Path Graph' }
      if (tab === 'auditor') return { section: 'Governance', page: 'Auditor Vault & Sharing' }
      return { section: 'Cloud Compliance', page: 'Executive Posture Overview' }
    }
    if (p === '/compliance/frameworks') {
      return { section: 'Cloud Compliance', page: 'Supported Frameworks Catalog' }
    }
    if (p.startsWith('/compliance/frameworks/')) {
      return { section: 'Cloud Compliance', page: 'Framework Controls & Guidance' }
    }
    if (p.startsWith('/investigations')) {
      return { section: 'Threat Detection', page: 'Log Analysis & Investigations' }
    }
    if (p === '/play-parser') {
      return { section: 'SIEM Tools', page: 'PlayParser & Custom Rules' }
    }
    if (p === '/alerts') {
      return { section: 'Threat Detection', page: 'Security Alert Feed' }
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

  return (
    <header className="h-16 border-b border-white/[0.08] bg-surface/70 backdrop-blur-xl px-4 sm:px-6 flex items-center justify-between gap-4 z-30 select-none">
      {/* Left: Breadcrumbs & Context indicator */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="hidden sm:flex items-center gap-2 font-mono text-[11px] text-text-muted">
          <span className="text-text-muted/80">{section}</span>
          <span className="text-white/20">/</span>
          <span className="text-text-primary font-medium tracking-tight truncate">{page}</span>
        </div>
        <div className="sm:hidden font-display font-semibold text-sm text-text-primary truncate">
          {page}
        </div>
      </div>

      {/* Right: Cloud account switcher, Quick Actions, Profile */}
      <div className="flex items-center gap-2.5 sm:gap-3 ml-auto">
        {/* Cloud Account Switcher / Connection Warning */}
        <div ref={accountMenuRef} className="relative">
          {accounts.length > 0 ? (
            <button
              onClick={() => setAccountMenuOpen(!accountMenuOpen)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-white/[0.08] bg-white/[0.03] hover:bg-white/[0.06] transition-all text-left group"
            >
              <div className="w-5 h-5 rounded-md bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-300">
                <Cloud className="w-3 h-3" />
              </div>
              <div className="hidden md:block min-w-0">
                <div className="text-xs font-semibold text-text-primary truncate max-w-[130px]">
                  {activeAccount ? activeAccount.name : 'Select Account'}
                </div>
                <div className="font-mono text-[9px] text-text-muted flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  <span>{activeAccount?.provider?.toUpperCase() ?? 'AWS'} Connected</span>
                </div>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-text-muted group-hover:text-text-primary transition-transform duration-200" />
            </button>
          ) : (
            <button
              onClick={onOpenConnectModal}
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-amber-500/35 bg-amber-500/10 hover:bg-amber-500/15 text-amber-300 transition-all text-xs font-medium animate-pulse"
            >
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              <span className="hidden sm:inline">No Cloud Connected</span>
              <span className="underline font-semibold">+ Connect</span>
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
                className="absolute right-0 top-[calc(100%+8px)] w-64 rounded-2xl border border-white/[0.1] bg-[#0E1424] shadow-2xl p-2 z-50 backdrop-blur-2xl"
              >
                <div className="px-3 py-1.5 font-mono text-[9px] uppercase tracking-wider text-text-muted font-semibold">
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
                        className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-left transition-all ${
                          isSelected
                            ? 'bg-indigo-500/15 text-text-primary border border-indigo-500/30'
                            : 'hover:bg-white/[0.04] text-text-secondary'
                        }`}
                      >
                        <div className="min-w-0 pr-2">
                          <div className="text-xs font-semibold text-text-primary truncate">{acc.name}</div>
                          <div className="font-mono text-[10px] text-text-muted truncate">
                            {acc.provider?.toUpperCase()} · {acc.role_arn ? acc.role_arn.split('/').pop() : 'Direct'}
                          </div>
                        </div>
                        {isSelected && <Check className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />}
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
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium text-indigo-300 hover:bg-indigo-500/10 transition-colors"
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
          className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-indigo-500/35 bg-indigo-500/15 hover:bg-indigo-500/25 text-indigo-200 text-xs font-semibold transition-all hover:shadow-[0_0_15px_rgba(99,102,241,0.25)]"
        >
          <Play className="w-3.5 h-3.5 text-indigo-300 fill-indigo-300" />
          <span>Quick Scan</span>
        </button>

        {/* Auditor Share Link */}
        <button
          onClick={onOpenAuditorModal}
          title="Share Evidence Vault with External Auditor"
          className="hidden lg:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-white/[0.08] bg-white/[0.03] hover:bg-white/[0.06] text-text-secondary hover:text-text-primary text-xs font-medium transition-all"
        >
          <Share2 className="w-3.5 h-3.5 text-teal-400" />
          <span>Auditor Link</span>
        </button>

        {/* User Profile Avatar & Dropdown */}
        <div ref={profileRef} className="relative">
          <button
            onClick={() => setProfileOpen(!profileOpen)}
            aria-label="User Account Menu"
            className="w-9 h-9 rounded-xl border border-white/[0.08] bg-white/[0.03] hover:border-indigo-500/30 hover:bg-white/[0.06] flex items-center justify-center transition-all group"
          >
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500/40 to-teal-500/40 border border-indigo-500/30 flex items-center justify-center font-display font-bold text-xs text-indigo-200">
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
                className="absolute right-0 top-[calc(100%+8px)] w-56 rounded-2xl border border-white/[0.1] bg-[#0E1424] shadow-2xl p-1.5 z-50 backdrop-blur-2xl"
              >
                <div className="px-3 py-2 border-b border-white/[0.06] mb-1">
                  <div className="text-xs font-semibold text-text-primary truncate">{displayName}</div>
                  <div className="font-mono text-[10px] text-text-muted truncate">{email}</div>
                </div>

                <Link
                  to="/profile"
                  onClick={() => setProfileOpen(false)}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-text-secondary hover:text-text-primary hover:bg-white/[0.05] transition-colors"
                >
                  <UserIcon className="w-3.5 h-3.5 text-text-muted" /> My Profile & Security
                </Link>

                <Link
                  to="/compliance/frameworks"
                  onClick={() => setProfileOpen(false)}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-text-secondary hover:text-text-primary hover:bg-white/[0.05] transition-colors"
                >
                  <Layers className="w-3.5 h-3.5 text-text-muted" /> Frameworks Library
                </Link>

                <div className="border-t border-white/[0.06] my-1" />

                <button
                  onClick={handleSignOut}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-rose-400 hover:bg-rose-500/10 transition-colors text-left"
                >
                  <LogOut className="w-3.5 h-3.5 text-rose-400" /> Sign Out
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </header>
  )
}
