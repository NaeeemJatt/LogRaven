// LogRaven — Unified Application Shell & Navigation Frame (Falcon Cloud Security Architecture)
import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import AppSidebar from './AppSidebar'
import AppHeader from './AppHeader'
import AppSubNav from './AppSubNav'
import FilterBar from './FilterBar'
import AuditorShareModal from '../audit/AuditorShareModal'
import { listCloudAccounts } from '../../api/compliance'
import type { CloudAccount } from '../../types/audit'

interface AppShellProps {
  children: React.ReactNode
}

export default function AppShell({ children }: AppShellProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    return localStorage.getItem('lograven_sidebar_collapsed') === 'true'
  })

  const [accounts, setAccounts] = useState<CloudAccount[]>([])
  const [activeAccount, setActiveAccount] = useState<CloudAccount | null>(null)

  // Global modal triggers
  const [auditorModalOpen, setAuditorModalOpen] = useState(false)

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev
      localStorage.setItem('lograven_sidebar_collapsed', String(next))
      return next
    })
  }

  const refreshAccounts = async () => {
    try {
      const list = await listCloudAccounts()
      setAccounts(list)
      if (list.length > 0 && !activeAccount) {
        setActiveAccount(list[0])
      }
    } catch {
      // keep quiet if unauthenticated
    }
  }

  useEffect(() => {
    void refreshAccounts()
  }, [])

  // Show contextual query filter bar on primary monitoring & investigation views
  const showFilterBar =
    location.pathname === '/' ||
    location.pathname === '/dashboard' ||
    location.pathname === '/compliance' ||
    location.pathname === '/alerts' ||
    location.pathname.startsWith('/investigations')

  return (
    <div className="flex h-screen bg-void text-text-primary overflow-hidden">
      {/* Collapsible Left Mission Rail */}
      <AppSidebar
        collapsed={collapsed}
        onToggle={toggleCollapsed}
        connectedAccountsCount={accounts.length}
        onOpenConnectModal={() => navigate('/compliance/connect/step-1')}
        onOpenAuditorModal={() => setAuditorModalOpen(true)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Level 0 Top Masthead */}
        <AppHeader
          accounts={accounts}
          activeAccount={activeAccount}
          onSelectAccount={(acc) => setActiveAccount(acc)}
          onOpenConnectModal={() => navigate('/compliance/connect/step-1')}
          onOpenAuditorModal={() => setAuditorModalOpen(true)}
          onOpenQuickScanModal={() => navigate('/compliance?tab=audit')}
          onToggleSidebar={toggleCollapsed}
        />

        {/* Level 1 Horizontal Dropdown Sub-Nav Ribbon */}
        <AppSubNav />

        {/* Level 2 Contextual Filter Ribbon */}
        {showFilterBar && <FilterBar />}

        {/* Scrollable Working Canvas */}
        <main className="flex-1 overflow-y-auto bg-void relative">
          {/* Subtle Cybernetic Grid Texture & Telemetry Ambient Wash */}
          <div className="pointer-events-none fixed inset-0 grid-bg opacity-30" />
          <div
            className="pointer-events-none fixed -top-32 right-1/4 w-[600px] h-[600px] rounded-full blur-[140px] opacity-10"
            style={{
              background: 'radial-gradient(circle, rgba(227,181,126,0.15) 0%, transparent 70%)',
            }}
          />

          <div className="relative w-full">{children}</div>
        </main>
      </div>

      {/* Global Auditor Vault Share Modal */}
      <AuditorShareModal
        isOpen={auditorModalOpen}
        onClose={() => setAuditorModalOpen(false)}
        companyName={activeAccount?.name || 'My Organization'}
      />
    </div>
  )
}
