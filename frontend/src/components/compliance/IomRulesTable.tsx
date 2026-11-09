// LogRaven — Top Detected IOM Rules Operational Table
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Info, MoreVertical, ArrowUpDown } from 'lucide-react'
import SeverityHexBadge, { type SeverityLevel } from '../detections/SeverityHexBadge'

export interface IomRuleItem {
  id: string
  rule: string
  severity: SeverityLevel
  findings: number
}

interface IomRulesTableProps {
  lastRefreshed?: string
  onRuleClick?: (ruleId: string) => void
}

export default function IomRulesTable({
  lastRefreshed = '19:05:05',
}: IomRulesTableProps) {
  const [sortAsc, setSortAsc] = useState(false)

  const defaultRules: IomRuleItem[] = [
    {
      id: 'iom-1',
      rule: 'IAM Role inline policy allows all actions for a service on all resources',
      severity: 'high',
      findings: 101,
    },
    {
      id: 'iom-2',
      rule: 'ECR repository not set to Scan on Push',
      severity: 'high',
      findings: 60,
    },
    {
      id: 'iom-3',
      rule: 'ECS task definition root user found',
      severity: 'high',
      findings: 57,
    },
    {
      id: 'iom-4',
      rule: 'SQS Queue Not Configured with server-side encryption',
      severity: 'high',
      findings: 50,
    },
    {
      id: 'iom-5',
      rule: 'S3 Bucket allows public read access without server-side encryption',
      severity: 'high',
      findings: 42,
    },
    {
      id: 'iom-6',
      rule: 'Security Group allows 0.0.0.0/0 ingress on port 22 SSH',
      severity: 'high',
      findings: 36,
    },
    {
      id: 'iom-7',
      rule: 'RDS Database Instance is configured with public accessibility',
      severity: 'high',
      findings: 28,
    },
    {
      id: 'iom-8',
      rule: 'CloudTrail multi-region logging disabled or missing bucket encryption',
      severity: 'high',
      findings: 21,
    },
  ]

  const sortedRules = [...defaultRules].sort((a, b) =>
    sortAsc ? a.findings - b.findings : b.findings - a.findings
  )

  return (
    <div className="rounded-xl border border-white/[0.08] bg-surface p-4 flex flex-col justify-between">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
          <div>
            <div className="flex items-center gap-1.5 text-xs font-semibold text-text-primary">
              <span>Most detected IOM rules by severity</span>
              <Info className="w-3 h-3 text-text-muted/70" />
            </div>
            <div className="text-[11px] text-text-muted mt-0.5">Top 10</div>
          </div>
          <button
            type="button"
            title="Table options"
            aria-label="Table options"
            className="w-7 h-7 rounded-lg border border-white/[0.06] hover:border-white/[0.15] bg-white/[0.02] flex items-center justify-center text-text-muted hover:text-text-primary transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
          >
            <MoreVertical className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Table */}
        <div className="overflow-x-auto custom-scrollbar">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-white/[0.06] text-[11px] font-semibold text-text-muted">
                <th scope="col" className="py-2.5 px-2 font-medium">Severity</th>
                <th scope="col" className="py-2.5 px-2 font-medium">Rule</th>
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
              {sortedRules.map((item) => (
                <tr
                  key={item.id}
                  className="hover:bg-white/[0.02] transition-colors duration-150 group"
                >
                  <td className="py-2 px-2 whitespace-nowrap">
                    <SeverityHexBadge severity={item.severity} />
                  </td>
                  <td className="py-2 px-2">
                    <Link
                      to={`/compliance?tab=audit&rule=${item.id}`}
                      className="text-xs text-sky-400 hover:text-sky-300 hover:underline transition-colors duration-150 line-clamp-1"
                    >
                      {item.rule}
                    </Link>
                  </td>
                  <td className="py-2 px-2 text-right font-mono text-xs font-medium text-text-primary tabular-nums whitespace-nowrap">
                    {item.findings}
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

