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
  Shield,
  Gauge,
  Menu,
} from 'lucide-react'

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
          badgeColor: 'bg-amber-400/15 text-amber-300 border-amber-400/30',
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
      className={`relative z-40 flex flex-col h-screen border-r border-white/[0.08] transition-colors duration-150 select-none flex-shrink-0 ${
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
            className="w-10 h-10 rounded-xl border border-white/[0.08] hover:border-amber-400/40 bg-white/[0.03] hover:bg-amber-400/10 flex items-center justify-center text-text-muted hover:text-amber-300 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed group cursor-pointer"
          >
            <Menu className="w-5 h-5 group-hover:scale-105 transition-transform duration-150" />
          </button>
        ) : (
          <>
            <Link
              to="/dashboard"
              className="flex items-center gap-3 min-w-0 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded-xl"
            >
              <div className="w-9 h-9 rounded-xl bg-amber-400/10 border border-amber-400/25 flex items-center justify-center flex-shrink-0 text-amber-400">
                <Shield className="w-4 h-4" />
              </div>
              <motion.div
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -6 }}
                className="min-w-0"
              >
                <div className="flex items-center gap-1.5">
                  <span className="font-display font-bold text-base text-text-primary tracking-tight">
                    Log<span className="text-amber-400">Raven</span>
                  </span>
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 motion-safe:animate-pulse motion-reduce:animate-none" />
                </div>
                <p className="text-[10px] text-text-muted truncate">
                  Cloud Security SOC
                </p>
              </motion.div>
            </Link>

            <button
              type="button"
              onClick={onToggle}
              aria-label="Collapse sidebar"
              className="w-7 h-7 rounded-lg border border-white/[0.06] hover:border-white/[0.15] bg-white/[0.02] hover:bg-white/[0.06] flex items-center justify-center text-text-muted hover:text-text-primary transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0 cursor-pointer"
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
              <div className="px-3 pb-1.5 text-xs font-semibold text-text-muted">
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
                    className={`relative flex items-center gap-3 px-3 py-2.5 rounded-xl font-medium text-xs transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] motion-reduce:transition-none group ${
                      active
                        ? 'bg-amber-400/10 text-text-primary border border-amber-400/25'
                        : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.04] border border-transparent'
                    }`}
                  >
                    {active && (
                      <span className="absolute left-0 top-2 bottom-2 w-1 rounded-r-full bg-amber-400" />
                    )}

                    <Icon
                      className={`w-4 h-4 flex-shrink-0 transition-transform duration-150 group-hover:scale-105 ${
                        active ? 'text-amber-400' : 'text-text-muted group-hover:text-text-primary'
                      }`}
                    />

                    {!collapsed && (
                      <span className="truncate flex-1 tracking-tight">{item.label}</span>
                    )}

                    {!collapsed && item.badge && (
                      <span
                        className={`px-1.5 py-0.5 rounded-md text-[10px] border font-medium ${
                          item.badgeColor || 'bg-white/[0.06] text-text-muted border-white/[0.08]'
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </Link>

                  {/* Floating tooltip when collapsed */}
                  {collapsed && activeTooltip === item.id && (
                    <div className="absolute left-[calc(100%+8px)] top-1/2 -translate-y-1/2 z-50 px-3 py-1.5 rounded-lg bg-surface/95 backdrop-blur-xl border border-white/[0.12] shadow-lg pointer-events-none whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-text-primary">{item.label}</span>
                        {item.badge && (
                          <span className="px-1.5 py-0.2 rounded text-[10px] bg-amber-400/20 text-amber-300">
                            {item.badge}
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] text-text-muted block mt-0.5">
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
    </aside>
  )
}
