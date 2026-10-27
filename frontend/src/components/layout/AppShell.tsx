// LogRaven — Unified Application Shell & Navigation Frame
import { useState, useEffect } from 'react'
import AppSidebar from './AppSidebar'
import AppHeader from './AppHeader'
import ConnectAccountModal from '../compliance/ConnectAccountModal'
import AuditorShareModal from '../audit/AuditorShareModal'
import { listCloudAccounts } from '../../api/compliance'
import type { CloudAccount } from '../../types/audit'
import { useNavigate } from 'react-router-dom'

interface AppShellProps {
  children: React.ReactNode
}

export default function AppShell({ children }: AppShellProps) {
  const navigate = useNavigate()
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    return localStorage.getItem('lograven_sidebar_collapsed') === 'true'
  })

  const [accounts, setAccounts] = useState<CloudAccount[]>([])
  const [activeAccount, setActiveAccount] = useState<CloudAccount | null>(null)

  // Global modal triggers
  const [connectModalOpen, setConnectModalOpen] = useState(false)
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

  return (
    <div className="flex h-screen bg-void text-text-primary overflow-hidden">
      {/* Collapsible Left Mission Rail */}
      <AppSidebar
        collapsed={collapsed}
        onToggle={toggleCollapsed}
        connectedAccountsCount={accounts.length}
        onOpenConnectModal={() => setConnectModalOpen(true)}
        onOpenAuditorModal={() => setAuditorModalOpen(true)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header & Sub-Navigation */}
        <AppHeader
          accounts={accounts}
          activeAccount={activeAccount}
          onSelectAccount={(acc) => setActiveAccount(acc)}
          onOpenConnectModal={() => setConnectModalOpen(true)}
          onOpenAuditorModal={() => setAuditorModalOpen(true)}
          onOpenQuickScanModal={() => navigate('/compliance?tab=audit')}
        />

        {/* Scrollable Working Canvas */}
        <main className="flex-1 overflow-y-auto bg-void relative">
          {/* Subtle Cybernetic Grid Texture & Ambient Wash */}
          <div className="pointer-events-none fixed inset-0 grid-bg opacity-40" />
          <div
            className="pointer-events-none fixed -top-32 right-1/4 w-[600px] h-[600px] rounded-full blur-[140px] opacity-10"
            style={{
              background: 'radial-gradient(circle, #6366F1 0%, transparent 70%)',
            }}
          />

          <div className="relative">{children}</div>
        </main>
      </div>

      {/* Global Cloud Account Connect Modal */}
      <ConnectAccountModal
        isOpen={connectModalOpen}
        onClose={() => setConnectModalOpen(false)}
        onAccountConnected={(acc) => {
          setAccounts((prev) => [...prev, acc])
          setActiveAccount(acc)
          void refreshAccounts()
        }}
      />

      {/* Global Auditor Vault Share Modal */}
      <AuditorShareModal
        isOpen={auditorModalOpen}
        onClose={() => setAuditorModalOpen(false)}
        companyName={activeAccount?.name || 'My Organization'}
      />
    </div>
  )
}
