// LogRaven — Level 1 Horizontal Sub-Navigation Ribbon (Falcon Cloud Security Dropdown Architecture)
import { useState, useRef, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ChevronDown,
  ExternalLink,
} from 'lucide-react'

interface SubMenuItem {
  label: string
  href: string
  badge?: 'New' | 'Updated'
  isExternal?: boolean
}

interface SubMenuGroup {
  title?: string
  items: SubMenuItem[]
}

interface SubMenuSection {
  id: string
  label: string
  groups: SubMenuGroup[]
}

export default function AppSubNav() {
  const location = useLocation()
  const [activeMenu, setActiveMenu] = useState<string | null>(null)
  const navRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (navRef.current && !navRef.current.contains(e.target as Node)) {
        setActiveMenu(null)
      }
    }
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setActiveMenu(null)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [])

  // Close menus on route change
  useEffect(() => {
    setActiveMenu(null)
  }, [location.pathname, location.search])

  const sections: SubMenuSection[] = [
    {
      id: 'dashboards',
      label: 'Dashboards',
      groups: [
        {
          title: 'Overview',
          items: [
            { label: 'Activity', href: '/dashboard' },
            { label: 'Cloud detections', href: '/alerts', badge: 'New' },
            { label: 'Cloud identities', href: '/investigations' },
            { label: 'Cloud posture', href: '/dashboard' },
            { label: 'Container compliance', href: '/compliance' },
            { label: 'AI security', href: '/compliance', badge: 'New' },
          ],
        },
        {
          title: 'Operations',
          items: [
            { label: 'Deployments', href: '/compliance/connect' },
            { label: 'Cloud assets', href: '/compliance?tab=accounts' },
            { label: 'Kubernetes and containers', href: '/compliance' },
            { label: 'Container detections', href: '/alerts' },
            { label: 'Agentless vulnerability scanning', href: '/compliance?tab=audit', badge: 'New' },
            { label: 'Image assessments', href: '/compliance/frameworks' },
            { label: 'Serverless functions', href: '/compliance' },
          ],
        },
      ],
    },
    {
      id: 'assets',
      label: 'Assets',
      groups: [
        {
          title: 'Inventory',
          items: [
            { label: 'Cloud accounts', href: '/compliance?tab=accounts' },
            { label: 'Asset inventory explorer', href: '/compliance?tab=posture' },
            { label: 'Topology and attack paths', href: '/compliance?tab=posture' },
            { label: 'Host setup and management', href: '/compliance/connect' },
          ],
        },
      ],
    },
    {
      id: 'posture',
      label: 'Posture and Compliance',
      groups: [
        {
          title: 'Cloud security posture',
          items: [
            { label: 'Cloud risks', href: '/compliance?tab=posture', badge: 'New' },
            { label: 'Attack path analysis', href: '/compliance?tab=posture', badge: 'New', isExternal: true },
            { label: 'Indicators of Misconfiguration (IOM)', href: '/compliance?tab=audit' },
            { label: 'Infrastructure as Code (IaC) findings', href: '/compliance', badge: 'Updated' },
            { label: 'Kubernetes misconfigurations', href: '/compliance' },
          ],
        },
        {
          title: 'Compliance',
          items: [
            { label: 'Cloud compliance overview', href: '/dashboard' },
            { label: 'Compliance control room', href: '/compliance' },
            { label: 'Kubernetes and containers compliance', href: '/compliance' },
            { label: 'Frameworks catalog', href: '/compliance/frameworks' },
          ],
        },
      ],
    },
    {
      id: 'vulnerabilities',
      label: 'Vulnerabilities',
      groups: [
        {
          items: [
            { label: 'Image assessments', href: '/compliance/frameworks' },
            { label: 'Agentless vulnerability scanning', href: '/compliance?tab=audit', badge: 'New' },
            { label: 'Serverless functions', href: '/compliance' },
          ],
        },
      ],
    },
    {
      id: 'detections',
      label: 'Detections',
      groups: [
        {
          title: 'Triage & Incidents',
          items: [
            { label: 'Security detections feed', href: '/alerts' },
            { label: 'Automated leads', href: '/alerts', badge: 'New' },
            { label: 'Incident investigation cases', href: '/investigations' },
            { label: 'New investigation workflow', href: '/investigations/new' },
          ],
        },
      ],
    },
    {
      id: 'rules',
      label: 'Rules and Policies',
      groups: [
        {
          title: 'Rules',
          items: [
            { label: 'Indicators of Misconfiguration (IOM) rules', href: '/compliance?tab=audit', badge: 'New' },
            { label: 'Cloud detection rules', href: '/play-parser', badge: 'New' },
            { label: 'Infrastructure as Code (IaC) rules', href: '/compliance', badge: 'Updated' },
            { label: 'Cloud risks rules', href: '/compliance?tab=posture', badge: 'New' },
          ],
        },
        {
          title: 'Policies',
          items: [
            { label: 'Admission control policies', href: '/compliance', badge: 'Updated' },
            { label: 'Image assessment policies', href: '/compliance/frameworks' },
            { label: 'Container drift exclusions', href: '/compliance', badge: 'New' },
          ],
        },
        {
          title: 'Management',
          items: [
            { label: 'Suppression rules', href: '/compliance?tab=auditor', badge: 'New' },
          ],
        },
      ],
    },
    {
      id: 'settings',
      label: 'Settings',
      groups: [
        {
          title: 'Integrations',
          items: [
            { label: 'Account registration', href: '/compliance/connect', badge: 'Updated' },
            { label: 'Image assessment settings', href: '/profile' },
          ],
        },
        {
          title: 'Operations',
          items: [
            { label: '1-Click sensor deployment', href: '/compliance/connect' },
            { label: 'Kubernetes deployment', href: '/compliance/connect' },
          ],
        },
        {
          title: 'Configure',
          items: [
            { label: 'Cloud groups', href: '/compliance?tab=accounts', badge: 'Updated' },
            { label: 'Cloud posture scan settings', href: '/compliance?tab=audit' },
            { label: 'Agentless scanning configuration', href: '/compliance/connect', badge: 'New' },
            { label: 'Operator security & credentials', href: '/profile' },
          ],
        },
      ],
    },
  ]

  const isSectionActive = (sec: SubMenuSection) => {
    const p = location.pathname
    if (sec.id === 'dashboards' && (p === '/dashboard' || p === '/')) return true
    if (sec.id === 'posture' && p.startsWith('/compliance')) return true
    if (sec.id === 'detections' && (p === '/alerts' || p.startsWith('/investigations'))) return true
    if (sec.id === 'rules' && p === '/play-parser') return true
    if (sec.id === 'settings' && p === '/profile') return true
    return false
  }

  return (
    <div
      ref={navRef}
      className="relative z-30 h-10 border-b border-white/[0.08] bg-surface/85 backdrop-blur-md px-4 sm:px-6 flex items-center select-none"
    >
      <nav aria-label="Cloud Security Sections" className="flex items-center gap-1 sm:gap-2 overflow-x-auto custom-scrollbar h-full">
        {sections.map((sec) => {
          const isOpen = activeMenu === sec.id
          const isActive = isSectionActive(sec)

          return (
            <div key={sec.id} className="relative h-full flex items-center">
              <button
                type="button"
                onClick={() => setActiveMenu(isOpen ? null : sec.id)}
                aria-expanded={isOpen}
                aria-haspopup="true"
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer whitespace-nowrap ${
                  isOpen
                    ? 'text-text-primary bg-white/[0.06]'
                    : isActive
                    ? 'text-text-primary'
                    : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.03]'
                }`}
              >
                <span>{sec.label}</span>
                <ChevronDown
                  className={`w-3 h-3 text-text-muted transition-transform duration-150 ${
                    isOpen ? 'rotate-180 text-amber-400' : ''
                  }`}
                />
              </button>

              {/* Active bottom underline indicator */}
              {isActive && (
                <div className="absolute bottom-0 left-2.5 right-2.5 h-[2px] bg-amber-400 rounded-full" />
              )}

              {/* Dropdown Flyout Panel */}
              <AnimatePresence>
                {isOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: 4, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 2, scale: 0.98 }}
                    transition={{ duration: 0.12 }}
                    className="absolute left-0 top-full mt-1 min-w-[240px] max-w-[340px] rounded-xl border border-white/[0.12] bg-deep/95 backdrop-blur-2xl shadow-2xl p-1.5 z-50 overflow-hidden"
                  >
                    <div className="max-h-[70vh] overflow-y-auto custom-scrollbar space-y-3 py-1">
                      {sec.groups.map((group, gIdx) => (
                        <div key={gIdx} className="space-y-0.5">
                          {group.title && (
                            <div className="px-3 pt-1 pb-1 text-[11px] font-semibold text-text-muted">
                              {group.title}
                            </div>
                          )}
                          <div className="space-y-0.5">
                            {group.items.map((item, iIdx) => {
                              const isCurrent = location.pathname + location.search === item.href
                              return (
                                <Link
                                  key={iIdx}
                                  to={item.href}
                                  onClick={() => setActiveMenu(null)}
                                  className={`flex items-center justify-between gap-2 px-3 py-1.5 rounded-lg text-xs transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none ${
                                    isCurrent
                                      ? 'bg-amber-400/10 text-amber-300 font-medium'
                                      : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.04]'
                                  }`}
                                >
                                  <span className="truncate">{item.label}</span>
                                  <div className="flex items-center gap-1.5 flex-shrink-0">
                                    {item.badge === 'New' && (
                                      <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-amber-400/15 text-amber-300 border border-amber-400/30">
                                        New
                                      </span>
                                    )}
                                    {item.badge === 'Updated' && (
                                      <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-cyan-400/15 text-cyan-300 border border-cyan-400/30">
                                        Updated
                                      </span>
                                    )}
                                    {item.isExternal && (
                                      <ExternalLink className="w-3 h-3 text-text-muted" />
                                    )}
                                  </div>
                                </Link>
                              )
                            })}
                          </div>
                        </div>
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )
        })}
      </nav>
    </div>
  )
}
