// LogRaven — Multi-Cloud SOC & Compliance Collapsible Navigation Sidebar
import { useState, useRef } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
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
  subItems?: { label: string; href: string }[]
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
  const [activeFlyout, setActiveFlyout] = useState<string | null>(null)
  const flyoutTimerRef = useRef<number | null>(null)

  const navGroups: NavGroup[] = [
    {
      group: 'Cloud Compliance',
      items: [
        {
          id: 'dashboard',
          label: 'Posture & Overview',
          href: '/dashboard',
          icon: LayoutDashboard,
          subItems: [
            { label: 'Executive Posture Command', href: '/dashboard' },
            { label: 'Attack Path Analysis', href: '/compliance?tab=posture' },
            { label: 'Adversary Threat Risks', href: '/dashboard' },
          ],
        },
        {
          id: 'accounts',
          label: 'Cloud Accounts',
          href: '/compliance?tab=accounts',
          icon: Cloud,
          badge: connectedAccountsCount > 0 ? connectedAccountsCount : undefined,
          badgeColor: 'bg-amber-400/15 text-amber-300 border-amber-400/30',
          subItems: [
            { label: 'Connected Fleets', href: '/compliance?tab=accounts' },
            { label: 'Register New Account', href: '/compliance/connect' },
          ],
        },
        {
          id: 'new-audit',
          label: 'New Audit Scan',
          href: '/compliance?tab=audit',
          icon: PlayCircle,
          subItems: [
            { label: 'Launch Compliance Audit', href: '/compliance?tab=audit' },
            { label: 'Audit Execution Progress', href: '/compliance?tab=audit' },
          ],
        },
        {
          id: 'history',
          label: 'Audit History',
          href: '/compliance?tab=history',
          icon: FileCheck2,
          subItems: [
            { label: 'Past Audits Ledger', href: '/compliance?tab=history' },
            { label: 'Export Evidence Pack', href: '/compliance?tab=history' },
          ],
        },
        {
          id: 'posture',
          label: 'Posture & Gaps',
          href: '/compliance?tab=posture',
          icon: Gauge,
          subItems: [
            { label: 'Controls Browser', href: '/compliance?tab=posture' },
            { label: 'Remediation Studio', href: '/compliance?tab=posture' },
          ],
        },
        {
          id: 'frameworks',
          label: 'Frameworks Catalog',
          href: '/compliance/frameworks',
          icon: Library,
          badge: '14',
          badgeColor: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
          subItems: [
            { label: 'All 14 Frameworks', href: '/compliance/frameworks' },
            { label: 'SOC 2 Type II', href: '/compliance/frameworks/soc2' },
            { label: 'CIS AWS Benchmark', href: '/compliance/frameworks/cis_aws' },
          ],
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
          subItems: [
            { label: 'Investigation Cases', href: '/investigations' },
            { label: 'New Investigation', href: '/investigations/new' },
          ],
        },
        {
          id: 'play-parser',
          label: 'PlayParser & Rules',
          href: '/play-parser',
          icon: Terminal,
          subItems: [
            { label: 'Rule Sandbox Lab', href: '/play-parser' },
            { label: 'Detection Playbooks', href: '/play-parser' },
          ],
        },
        {
          id: 'alerts',
          label: 'Security Alerts',
          href: '/alerts',
          icon: AlertTriangle,
          subItems: [
            { label: 'Live Detections Feed', href: '/alerts' },
            { label: 'MITRE ATT&CK Matrix', href: '/alerts' },
          ],
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

  const handleMouseEnter = (itemId: string) => {
    if (!collapsed) return
    if (flyoutTimerRef.current) window.clearTimeout(flyoutTimerRef.current)
    setActiveFlyout(itemId)
  }

  const handleMouseLeave = () => {
    if (!collapsed) return
    flyoutTimerRef.current = window.setTimeout(() => {
      setActiveFlyout(null)
    }, 200)
  }

  return (
    <aside
      className={`relative z-40 flex flex-col h-screen border-r border-white/[0.08] bg-deep/95 backdrop-blur-xl transition-colors duration-150 select-none flex-shrink-0 ${
        collapsed ? 'w-[72px]' : 'w-[240px]'
      }`}
    >
      {/* Brand Header */}
      <div
        className={`h-14 flex items-center border-b border-white/[0.06] ${
          collapsed ? 'justify-center px-2' : 'justify-between px-3.5'
        }`}
      >
        {collapsed ? (
          <button
            type="button"
            onClick={onToggle}
            aria-label="Expand sidebar"
            title="Expand sidebar"
            className="w-9 h-9 rounded-xl border border-white/[0.08] hover:border-amber-400/40 bg-white/[0.02] hover:bg-amber-400/10 flex items-center justify-center text-text-muted hover:text-amber-300 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer group"
          >
            <Shield className="w-4 h-4 text-amber-400 group-hover:scale-110 transition-transform duration-150 motion-reduce:transition-none" />
          </button>
        ) : (
          <>
            <Link
              to="/dashboard"
              className="flex items-center gap-2.5 min-w-0 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded-xl"
            >
              <div className="w-8 h-8 rounded-lg bg-amber-400/10 border border-amber-400/25 flex items-center justify-center flex-shrink-0 text-amber-400">
                <Shield className="w-4 h-4" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="font-display font-bold text-sm text-text-primary tracking-tight">
                    Log<span className="text-amber-400">Raven</span>
                  </span>
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                </div>
                <p className="text-[10px] text-text-muted truncate">
                  Cloud Security SOC
                </p>
              </div>
            </Link>

            <button
              type="button"
              onClick={onToggle}
              aria-label="Collapse sidebar"
              className="w-6 h-6 rounded-md border border-white/[0.06] hover:border-white/[0.15] bg-white/[0.02] hover:bg-white/[0.06] flex items-center justify-center text-text-muted hover:text-text-primary transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer flex-shrink-0"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
          </>
        )}
      </div>

      {/* Nav Groups Container */}
      <div className="flex-1 overflow-y-auto px-2 py-3 space-y-5 custom-scrollbar">
        {navGroups.map((group) => (
          <div key={group.group} className="space-y-1">
            {!collapsed ? (
              <div className="px-2.5 pb-1 text-[11px] font-semibold text-text-muted">
                {group.group}
              </div>
            ) : (
              <div className="h-1" />
            )}

            {group.items.map((item) => {
              const active = isCurrentActive(item.href)
              const Icon = item.icon
              const isFlyoutOpen = activeFlyout === item.id

              return (
                <div
                  key={item.id}
                  className="relative"
                  onMouseEnter={() => handleMouseEnter(item.id)}
                  onMouseLeave={handleMouseLeave}
                >
                  <Link
                    to={item.href}
                    className={`relative flex items-center gap-2.5 px-2.5 py-2 rounded-lg font-medium text-xs transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer group ${
                      active
                        ? 'bg-amber-400/10 text-text-primary border border-amber-400/25'
                        : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.04] border border-transparent'
                    } ${collapsed ? 'justify-center' : ''}`}
                  >
                    {active && (
                      <span className="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-r-full bg-amber-400" />
                    )}

                    <Icon
                      className={`w-4 h-4 flex-shrink-0 transition-transform duration-150 motion-reduce:transition-none group-hover:scale-105 ${
                        active ? 'text-amber-400' : 'text-text-muted group-hover:text-text-primary'
                      }`}
                    />

                    {!collapsed && (
                      <span className="truncate flex-1 tracking-tight">{item.label}</span>
                    )}

                    {!collapsed && item.badge && (
                      <span
                        className={`px-1.5 py-0.2 rounded text-[10px] border font-medium ${
                          item.badgeColor || 'bg-white/[0.06] text-text-muted border-white/[0.08]'
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </Link>

                  {/* Flyout Drawer Menu when Collapsed (CrowdStrike SIEM Pattern) */}
                  <AnimatePresence>
                    {collapsed && isFlyoutOpen && (
                      <motion.div
                        initial={{ opacity: 0, x: -6 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -4 }}
                        transition={{ duration: 0.12 }}
                        className="absolute left-full top-0 ml-2 w-56 rounded-xl border border-white/[0.12] bg-deep/98 shadow-2xl p-2 z-50 backdrop-blur-2xl pointer-events-auto"
                        onMouseEnter={() => handleMouseEnter(item.id)}
                        onMouseLeave={handleMouseLeave}
                      >
                        <div className="flex items-center justify-between pb-1.5 mb-1.5 border-b border-white/[0.08] px-1">
                          <span className="text-xs font-semibold text-text-primary">{item.label}</span>
                          {item.badge && (
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-400/20 text-amber-300 font-mono">
                              {item.badge}
                            </span>
                          )}
                        </div>

                        <div className="space-y-0.5">
                          <Link
                            to={item.href}
                            onClick={() => setActiveFlyout(null)}
                            className="block px-2 py-1.5 rounded-lg text-xs font-medium text-amber-300 hover:bg-amber-400/10 transition-colors duration-150"
                          >
                            Go to {item.label}
                          </Link>

                          {item.subItems?.map((sub, sIdx) => (
                            <Link
                              key={sIdx}
                              to={sub.href}
                              onClick={() => setActiveFlyout(null)}
                              className="block px-2 py-1 rounded-lg text-xs text-text-secondary hover:text-text-primary hover:bg-white/[0.04] transition-colors duration-150 truncate"
                            >
                              {sub.label}
                            </Link>
                          ))}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              )
            })}
          </div>
        ))}
      </div>
    </aside>
  )
}
