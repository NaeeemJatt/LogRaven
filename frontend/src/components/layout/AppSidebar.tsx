// LogRaven — Multi-Cloud SOC & Compliance Collapsible Navigation Sidebar
import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  LayoutDashboard,
  Cloud,
  PlayCircle,
  Library,
  FileCheck2,
  FileSearch,
  Terminal,
  AlertTriangle,
  KeyRound,
  Settings,
  ChevronLeft,
  ChevronRight,
  Shield,
  Gauge,
  Menu,
} from 'lucide-react'
import { useAuthStore } from '../../store/authStore'

interface SidebarNavProps {
  collapsed: boolean
  onToggle: () => void
  onOpenConnectModal?: () => void
  onOpenAuditorModal?: () => void
  connectedAccountsCount?: number
}

interface NavItem {
  id: string
  label: string
  href: string
  icon: React.ElementType
  badge?: string | number
  badgeColor?: string
}

interface NavGroup {
  group: string
  items: NavItem[]
}

export default function AppSidebar({
  collapsed,
  onToggle,
  connectedAccountsCount = 0,
}: SidebarNavProps) {
  const location = useLocation()
  const user = useAuthStore((s) => s.user)
  const displayName = user?.name ?? user?.email?.split('@')[0] ?? 'Operator'
  const initials = displayName.charAt(0).toUpperCase()
  const tier = (user?.tier ?? 'FREE').toUpperCase()

  const [activeTooltip, setActiveTooltip] = useState<string | null>(null)

  const navGroups: NavGroup[] = [
    {
      group: 'Cloud Compliance',
      items: [
        {
          id: 'dashboard',
          label: 'Posture & Overview',
          href: '/dashboard',
          icon: LayoutDashboard,
        },
        {
          id: 'accounts',
          label: 'Cloud Accounts',
          href: '/compliance?tab=accounts',
          icon: Cloud,
          badge: connectedAccountsCount > 0 ? connectedAccountsCount : undefined,
          badgeColor: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
        },
        {
          id: 'new-audit',
          label: 'New Audit Scan',
          href: '/compliance?tab=audit',
          icon: PlayCircle,
        },
        {
          id: 'history',
          label: 'Audit History',
          href: '/compliance?tab=history',
          icon: FileCheck2,
        },
        {
          id: 'posture',
          label: 'Posture & Gaps',
          href: '/compliance?tab=posture',
          icon: Gauge,
        },
        {
          id: 'frameworks',
          label: 'Frameworks Catalog',
          href: '/compliance/frameworks',
          icon: Library,
          badge: '14',
          badgeColor: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
        },
      ],
    },
    {
      group: 'Threat Detection & SIEM',
      items: [
        {
          id: 'investigations',
          label: 'Log Investigations',
          href: '/investigations',
          icon: FileSearch,
        },
        {
          id: 'play-parser',
          label: 'PlayParser & Rules',
          href: '/play-parser',
          icon: Terminal,
        },
        {
          id: 'alerts',
          label: 'Security Alerts',
          href: '/alerts',
          icon: AlertTriangle,
        },
      ],
    },
    {
      group: 'Governance & Access',
      items: [
        {
          id: 'auditor-portal',
          label: 'Auditor Vault',
          href: '/compliance?tab=auditor',
          icon: KeyRound,
        },
        {
          id: 'profile',
          label: 'Settings & Security',
          href: '/profile',
          icon: Settings,
        },
      ],
    },
  ]

  const isCurrentActive = (href: string) => {
    if (href.includes('?tab=')) {
      const [path, query] = href.split('?')
      const tabParam = new URLSearchParams(query).get('tab')
      const currentTab = new URLSearchParams(location.search).get('tab')
      return location.pathname === path && currentTab === tabParam
    }
    if (href === '/dashboard') {
      return location.pathname === '/dashboard' || (location.pathname === '/compliance' && !location.search)
    }
    return location.pathname.startsWith(href)
  }

  return (
    <aside
      className={`relative z-40 flex flex-col h-screen border-r border-white/[0.08] transition-all duration-300 ease-in-out select-none flex-shrink-0 ${
        collapsed ? 'w-[72px]' : 'w-[260px]'
      }`}
      style={{
        background: 'linear-gradient(180deg, rgba(11, 15, 25, 0.98) 0%, rgba(7, 10, 17, 0.99) 100%)',
        backdropFilter: 'blur(20px)',
      }}
    >
      {/* Brand Header */}
      <div
        className={`h-16 flex items-center border-b border-white/[0.06] ${
          collapsed ? 'justify-center px-2' : 'justify-between px-4'
        }`}
      >
        {collapsed ? (
          <button
            type="button"
            onClick={onToggle}
            aria-label="Expand sidebar"
            title="Expand sidebar"
            className="w-10 h-10 rounded-xl border border-white/[0.08] hover:border-indigo-500/40 bg-white/[0.03] hover:bg-indigo-500/10 flex items-center justify-center text-text-muted hover:text-indigo-300 transition-all shadow-sm group cursor-pointer"
          >
            <Menu className="w-5 h-5 group-hover:scale-110 transition-transform" />
          </button>
        ) : (
          <>
            <Link to="/dashboard" className="flex items-center gap-3 min-w-0">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500/25 to-teal-500/20 border border-indigo-500/40 flex items-center justify-center flex-shrink-0 shadow-[0_0_15px_rgba(99,102,241,0.25)]">
                <Shield className="w-4 h-4 text-indigo-300" />
              </div>
              <motion.div
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -6 }}
                className="min-w-0"
              >
                <div className="flex items-center gap-1.5">
                  <span className="font-display font-bold text-base text-text-primary tracking-tight">
                    Log<span className="text-indigo-400">Raven</span>
                  </span>
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                </div>
                <p className="font-mono text-[9px] text-text-muted tracking-widest uppercase truncate">
                  Cloud Security SOC
                </p>
              </motion.div>
            </Link>

            <button
              type="button"
              onClick={onToggle}
              aria-label="Collapse sidebar"
              className="w-7 h-7 rounded-lg border border-white/[0.06] hover:border-white/[0.15] bg-white/[0.02] hover:bg-white/[0.06] flex items-center justify-center text-text-muted hover:text-text-primary transition-colors flex-shrink-0 cursor-pointer"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
          </>
        )}
      </div>

      {/* Nav Groups Container */}
      <div className="flex-1 overflow-y-auto px-2 py-4 space-y-6 custom-scrollbar">
        {navGroups.map((group) => (
          <div key={group.group} className="space-y-1">
            {!collapsed ? (
              <div className="px-3 pb-1.5 font-mono text-[9px] uppercase tracking-[0.2em] text-text-muted font-medium">
                {group.group}
              </div>
            ) : (
              <div className="h-2" />
            )}

            {group.items.map((item) => {
              const active = isCurrentActive(item.href)
              const Icon = item.icon
              return (
                <div
                  key={item.id}
                  className="relative"
                  onMouseEnter={() => collapsed && setActiveTooltip(item.id)}
                  onMouseLeave={() => collapsed && setActiveTooltip(null)}
                >
                  <Link
                    to={item.href}
                    onClick={() => {
                      if (collapsed) onToggle()
                    }}
                    className={`relative flex items-center gap-3 px-3 py-2.5 rounded-xl font-medium text-xs transition-all duration-150 group ${
                      active
                        ? 'bg-indigo-500/15 text-text-primary border border-indigo-500/35 shadow-[0_0_20px_rgba(99,102,241,0.18)]'
                        : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.04] border border-transparent'
                    }`}
                  >
                    {active && (
                      <span className="absolute left-0 top-2 bottom-2 w-1 rounded-r-full bg-indigo-400 shadow-[0_0_8px_#818cf8]" />
                    )}

                    <Icon
                      className={`w-4 h-4 flex-shrink-0 transition-transform duration-200 group-hover:scale-110 ${
                        active ? 'text-indigo-400' : 'text-text-muted group-hover:text-text-primary'
                      }`}
                    />

                    {!collapsed && (
                      <span className="truncate flex-1 tracking-tight">{item.label}</span>
                    )}

                    {!collapsed && item.badge && (
                      <span
                        className={`px-1.5 py-0.5 rounded-md text-[10px] font-mono border font-medium ${
                          item.badgeColor || 'bg-white/[0.06] text-text-muted border-white/[0.08]'
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </Link>

                  {/* Floating tooltip when collapsed */}
                  {collapsed && activeTooltip === item.id && (
                    <div className="absolute left-[calc(100%+8px)] top-1/2 -translate-y-1/2 z-50 px-3 py-1.5 rounded-lg bg-surface/95 backdrop-blur-xl border border-white/[0.12] shadow-2xl pointer-events-none whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-text-primary">{item.label}</span>
                        {item.badge && (
                          <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-indigo-500/20 text-indigo-300">
                            {item.badge}
                          </span>
                        )}
                      </div>
                      <span className="font-mono text-[9px] text-text-muted uppercase tracking-wider block mt-0.5">
                        {group.group}
                      </span>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        ))}
      </div>

      {/* Sidebar Footer */}
      <div className="p-3 border-t border-white/[0.06] bg-black/20">
        {collapsed ? (
          <button
            onClick={onToggle}
            aria-label="Expand sidebar"
            className="w-full h-10 rounded-xl border border-white/[0.06] hover:border-white/[0.15] bg-white/[0.02] hover:bg-white/[0.05] flex items-center justify-center text-text-muted hover:text-text-primary transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        ) : (
          <div className="space-y-3">
            {/* User Mini Card */}
            <div className="flex items-center gap-3 p-2 rounded-xl bg-white/[0.02] border border-white/[0.05]">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500/40 to-teal-500/40 border border-indigo-500/30 flex items-center justify-center flex-shrink-0 text-xs font-display font-bold text-indigo-200">
                {initials}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-1">
                  <div className="text-xs font-semibold text-text-primary truncate">{displayName}</div>
                  <span className="px-1 py-0.2 rounded text-[9px] font-mono font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                    {tier}
                  </span>
                </div>
                <div className="font-mono text-[10px] text-text-muted truncate">{user?.email}</div>
              </div>
            </div>

            {/* Compliance Status summary badge */}
            <div className="flex items-center justify-between px-2 pt-1 text-[11px] font-mono text-text-muted">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-teal-400" />
                <span>Engine Active</span>
              </span>
              <span className="text-[10px] text-text-muted/70">v2.4.0</span>
            </div>
          </div>
        )}
      </div>
    </aside>
  )
}
