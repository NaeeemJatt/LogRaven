// LogRaven — Hexagonal Severity Marker Badge (Falcon & SIEM Visual Standard)
export type SeverityLevel = 'critical' | 'high' | 'medium' | 'info' | 'low'

interface SeverityHexBadgeProps {
  severity: SeverityLevel | string
  showLabel?: boolean
  className?: string
}

export default function SeverityHexBadge({
  severity,
  showLabel = true,
  className = '',
}: SeverityHexBadgeProps) {
  const norm = severity.toLowerCase()

  let colorClass = 'text-threat-info'
  let label = 'Informational'

  if (norm === 'critical') {
    colorClass = 'text-threat-critical'
    label = 'Critical'
  } else if (norm === 'high') {
    colorClass = 'text-threat-high'
    label = 'High'
  } else if (norm === 'medium' || norm === 'med') {
    colorClass = 'text-threat-medium'
    label = 'Medium'
  } else if (norm === 'low') {
    colorClass = 'text-threat-low'
    label = 'Low'
  }

  return (
    <div className={`inline-flex items-center gap-1.5 ${className}`}>
      {/* Regular Hexagon SVG Marker */}
      <svg
        viewBox="0 0 16 16"
        className={`w-3.5 h-3.5 shrink-0 ${colorClass}`}
        aria-hidden="true"
      >
        <polygon
          points="8,1.2 14.8,4.8 14.8,11.2 8,14.8 1.2,11.2 1.2,4.8"
          fill="currentColor"
          fillOpacity="0.9"
        />
      </svg>
      {showLabel && (
        <span className="text-xs font-medium text-text-primary capitalize">{label}</span>
      )}
    </div>
  )
}
