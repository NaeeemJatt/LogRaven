// LogRaven — Top Misconfigured Accounts Operational Table
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Info, ArrowUpDown, Cloud } from 'lucide-react'
import SeverityHexBadge, { type SeverityLevel } from '../detections/SeverityHexBadge'

export interface MisconfiguredAccountItem {
  id: string
  provider: 'aws' | 'azure' | 'gcp'
  accountId: string
  accountName: string
  severity: SeverityLevel
  findings: number
}

interface MisconfiguredAccountsTableProps {
  lastRefreshed?: string
}

export default function MisconfiguredAccountsTable({
  lastRefreshed = '19:05:05',
}: MisconfiguredAccountsTableProps) {
  const [sortAsc, setSortAsc] = useState(false)

  const defaultAccounts: MisconfiguredAccountItem[] = [
    {
      id: 'acc-1',
      provider: 'aws',
      accountId: '750283682324',
      accountName: 'cc-tech-prod',
      severity: 'high',
      findings: 398,
    },
    {
      id: 'acc-2',
      provider: 'aws',
      accountId: '750283682324',
      accountName: 'cc-tech-prod',
      severity: 'medium',
      findings: 4509,
    },
    {
      id: 'acc-3',
      provider: 'aws',
      accountId: '750283682324',
      accountName: 'cc-tech-prod',
      severity: 'info',
      findings: 1761,
    },
    {
      id: 'acc-4',
      provider: 'aws',
      accountId: '129845678901',
      accountName: 'cc-staging-eks',
      severity: 'high',
      findings: 142,
    },
    {
      id: 'acc-5',
      provider: 'aws',
      accountId: '129845678901',
      accountName: 'cc-staging-eks',
      severity: 'medium',
      findings: 820,
    },
  ]

  const sorted = [...defaultAccounts].sort((a, b) =>
    sortAsc ? a.findings - b.findings : b.findings - a.findings
  )

  return (
    <div className="rounded-xl border border-white/[0.08] bg-surface p-4 flex flex-col justify-between">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
          <div>
            <div className="flex items-center gap-1.5 text-xs font-semibold text-text-primary">
              <span>Top misconfigured accounts</span>
              <Info className="w-3 h-3 text-text-muted/70" />
            </div>
            <div className="text-[11px] text-text-muted mt-0.5">Top 10</div>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto custom-scrollbar">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-white/[0.06] text-[11px] font-semibold text-text-muted">
                <th scope="col" className="py-2.5 px-2 font-medium">Provider</th>
                <th scope="col" className="py-2.5 px-2 font-medium">Account ID</th>
                <th scope="col" className="py-2.5 px-2 font-medium">Account name</th>
                <th scope="col" className="py-2.5 px-2 font-medium">Severity</th>
                <th scope="col" className="py-2.5 px-2 text-right font-medium">
                  <button
                    type="button"
                    onClick={() => setSortAsc(!sortAsc)}
                    className="inline-flex items-center gap-1 hover:text-text-primary transition-colors duration-150 ml-auto focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded"
                  >
                    <span>Findings</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </button>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.03]">
              {sorted.map((item) => (
                <tr
                  key={item.id}
                  className="hover:bg-white/[0.02] transition-colors duration-150"
                >
                  <td className="py-2 px-2 whitespace-nowrap">
                    <div className="inline-flex items-center gap-1.5 text-text-secondary font-medium">
                      <Cloud className="w-3.5 h-3.5 text-amber-400" />
                      <span className="text-[11px]">{item.provider.toUpperCase()}</span>
                    </div>
                  </td>
                  <td className="py-2 px-2 whitespace-nowrap">
                    <Link
                      to={`/compliance?tab=accounts&acc=${item.accountId}`}
                      className="font-mono text-xs text-sky-400 hover:text-sky-300 hover:underline transition-colors duration-150"
                    >
                      {item.accountId}
                    </Link>
                  </td>
                  <td className="py-2 px-2 whitespace-nowrap text-text-secondary font-mono text-[11px]">
                    {item.accountName}
                  </td>
                  <td className="py-2 px-2 whitespace-nowrap">
                    <SeverityHexBadge severity={item.severity} />
                  </td>
                  <td className="py-2 px-2 text-right font-mono text-xs font-medium text-text-primary tabular-nums whitespace-nowrap">
                    {item.findings.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mt-3 pt-2 border-t border-white/[0.04] flex items-center justify-between text-[10px] text-text-muted">
        <span>Last refreshed: {lastRefreshed}</span>
      </div>
    </div>
  )
}
