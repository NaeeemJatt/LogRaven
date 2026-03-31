// Correlated finding — emphasizes cross-source context

import Badge from '../ui/Badge'
import type { Finding } from '../../types/report'

const LEFT_BORDER: Record<string, string> = {
  critical: 'border-l-red-500',
  high: 'border-l-orange-500',
  medium: 'border-l-yellow-500',
  low: 'border-l-blue-500',
  informational: 'border-l-raven-600',
}

interface CorrelationCardProps {
  finding: Finding
}

export default function CorrelationCard({ finding }: CorrelationCardProps) {
  const lbClass = LEFT_BORDER[finding.severity] ?? LEFT_BORDER.informational

  return (
    <div
      className={`rounded-xl border border-electric-500/20 bg-gradient-to-br from-raven-800/95 to-raven-900/90 pl-1 shadow-lg shadow-electric-500/5 ${lbClass} border-l-4`}
    >
      <div className="rounded-r-[11px] p-5">
        <div className="flex flex-wrap items-start gap-2 mb-2">
          <Badge value={finding.severity} variant="severity" />
          <span className="inline-flex rounded-lg border border-electric-400/40 bg-electric-500/15 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-electric-300">
            Cross-source
          </span>
          {finding.mitre_technique_id && (
            <span className="text-raven-500 font-mono text-xs whitespace-nowrap ml-auto">
              {finding.mitre_technique_id}
            </span>
          )}
        </div>
        <h3 className="text-white font-semibold text-sm leading-snug mb-2">{finding.title}</h3>
        <p className="text-raven-300 text-sm leading-relaxed">{finding.description}</p>

        {finding.source_files && finding.source_files.length > 0 && (
          <div className="mt-4 pt-3 border-t border-raven-700/80">
            <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-raven-500 block mb-2">
              Contributing sources
            </span>
            <div className="flex flex-wrap gap-2">
              {finding.source_files.map((sf, i) => (
                <span
                  key={`${sf}-${i}`}
                  className="rounded-md border border-raven-600 bg-raven-900/60 px-2 py-1 text-[11px] font-mono text-raven-400"
                >
                  {sf}
                </span>
              ))}
            </div>
          </div>
        )}

        {finding.iocs && finding.iocs.length > 0 && (
          <div className="mt-4">
            <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-raven-500 block mb-2">
              IOCs
            </span>
            <div className="flex flex-wrap gap-2">
              {finding.iocs.map((ioc, i) => (
                <span
                  key={i}
                  className="rounded-lg border border-electric-500/25 bg-raven-900/80 px-2.5 py-1 text-electric-300 font-mono text-xs"
                >
                  {ioc}
                </span>
              ))}
            </div>
          </div>
        )}

        {finding.remediation && (
          <div className="mt-4 pt-4 border-t border-raven-700/80">
            <span className="text-orange-400/90 text-[10px] font-semibold uppercase tracking-[0.15em]">Action</span>
            <p className="text-raven-300 text-sm mt-1 leading-relaxed">{finding.remediation}</p>
          </div>
        )}
      </div>
    </div>
  )
}
