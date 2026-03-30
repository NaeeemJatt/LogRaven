// LogRaven — Finding card (matches dashboard / report chrome)
import Badge from '../ui/Badge'
import type { Finding } from '../../types/report'

const LEFT_BORDER: Record<string, string> = {
  critical: 'border-l-red-500',
  high: 'border-l-orange-500',
  medium: 'border-l-yellow-500',
  low: 'border-l-blue-500',
  informational: 'border-l-raven-600',
}

interface FindingCardProps {
  finding: Finding
}

export default function FindingCard({ finding }: FindingCardProps) {
  const lbClass = LEFT_BORDER[finding.severity] ?? LEFT_BORDER.informational
  const isCorrelated = finding.finding_type === 'correlated'

  return (
    <div
      className={`rounded-xl border border-raven-700 bg-raven-800/90 pl-1 shadow-md shadow-black/20 ${lbClass} border-l-4`}
    >
      <div className="rounded-r-[11px] bg-raven-800/95 p-5">
        <div className="flex flex-wrap items-start gap-2 gap-y-2 mb-2">
          <Badge value={finding.severity} variant="severity" />
          {isCorrelated && (
            <span className="inline-flex rounded-lg border border-electric-500/30 bg-electric-500/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-electric-400">
              Correlated
            </span>
          )}
          <span className="text-white font-semibold text-sm flex-1 min-w-[12rem] leading-snug">
            {finding.title}
          </span>
          {finding.mitre_technique_id && (
            <span className="text-raven-500 font-mono text-xs whitespace-nowrap">{finding.mitre_technique_id}</span>
          )}
        </div>

        <p className="text-raven-300 text-sm leading-relaxed">{finding.description}</p>

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

        {finding.mitre_technique_name && (
          <p className="text-raven-600 text-xs font-mono mt-4 leading-relaxed">
            {[finding.mitre_technique_id, finding.mitre_tactic, finding.mitre_technique_name]
              .filter(Boolean)
              .join('  ·  ')}
          </p>
        )}
      </div>
    </div>
  )
}
