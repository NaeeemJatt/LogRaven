// LogRaven — Finding Card Component
import Badge from '../ui/Badge'
import type { Finding } from '../../types/report'

const LEFT_BORDER: Record<string, string> = {
  critical: 'border-l-red-500',
  high:     'border-l-orange-500',
  medium:   'border-l-yellow-500',
  low:      'border-l-blue-500',
  informational: 'border-l-raven-600',
}

interface FindingCardProps {
  finding: Finding
}

export default function FindingCard({ finding }: FindingCardProps) {
  const lbClass = LEFT_BORDER[finding.severity] ?? LEFT_BORDER.informational
  const isCorrelated = finding.finding_type === 'correlated'

  return (
    <div className={`border-l-4 ${lbClass} border border-raven-700 bg-raven-800 p-4 mb-3`}>
      {/* Header */}
      <div className="flex items-start gap-2 flex-wrap mb-2">
        <Badge value={finding.severity} variant="severity" />
        {isCorrelated && (
          <span className="inline-flex px-2 py-0.5 rounded-none text-xs font-mono font-medium uppercase tracking-wider bg-raven-700 text-electric-400 border border-raven-600">
            correlated
          </span>
        )}
        <span className="text-white font-medium text-sm flex-1 leading-snug">{finding.title}</span>
        {finding.mitre_technique_id && (
          <span className="text-raven-400 font-mono text-xs whitespace-nowrap">{finding.mitre_technique_id}</span>
        )}
      </div>

      {/* Description */}
      <p className="text-raven-300 text-sm leading-relaxed mt-2">{finding.description}</p>

      {/* IOCs */}
      {finding.iocs && finding.iocs.length > 0 && (
        <div className="mt-3">
          <span className="text-raven-400 text-xs uppercase tracking-widest block mb-1">IOCs</span>
          <div className="flex flex-wrap gap-1">
            {finding.iocs.map((ioc, i) => (
              <span
                key={i}
                className="bg-raven-900 border border-raven-700 px-2 py-0.5 text-electric-400 font-mono text-xs rounded-none"
              >
                {ioc}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Remediation */}
      {finding.remediation && (
        <div className="mt-3">
          <span className="text-orange-400 text-xs uppercase tracking-widest">Action</span>
          <p className="text-raven-300 text-sm mt-0.5">{finding.remediation}</p>
        </div>
      )}

      {/* MITRE detail */}
      {finding.mitre_technique_name && (
        <p className="text-raven-600 text-xs font-mono mt-3">
          {[finding.mitre_technique_id, finding.mitre_tactic, finding.mitre_technique_name]
            .filter(Boolean)
            .join('  ·  ')}
        </p>
      )}
    </div>
  )
}
