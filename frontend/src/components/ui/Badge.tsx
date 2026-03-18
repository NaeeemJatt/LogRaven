// LogRaven — Severity / Status Badge

interface BadgeProps {
  value: string
  variant?: 'severity' | 'status'
}

const SEVERITY: Record<string, string> = {
  critical:      'bg-red-950 text-red-400 border border-red-800',
  high:          'bg-orange-950 text-orange-400 border border-orange-800',
  medium:        'bg-yellow-950 text-yellow-400 border border-yellow-800',
  low:           'bg-blue-950 text-blue-400 border border-blue-800',
  informational: 'bg-raven-800 text-raven-400 border border-raven-600',
}

const STATUS: Record<string, string> = {
  draft:      'bg-raven-800 text-raven-400 border border-raven-600',
  queued:     'bg-yellow-950 text-yellow-400 border border-yellow-800',
  processing: 'bg-blue-950 text-blue-400 border border-blue-800',
  complete:   'bg-green-950 text-green-400 border border-green-800',
  failed:     'bg-red-950 text-red-400 border border-red-800',
}

export default function Badge({ value, variant = 'severity' }: BadgeProps) {
  const map    = variant === 'status' ? STATUS : SEVERITY
  const cls    = map[value] ?? (variant === 'status' ? STATUS.draft : SEVERITY.informational)
  const isProc = variant === 'status' && value === 'processing'

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-none text-xs font-mono font-medium uppercase tracking-wider ${cls}`}>
      {isProc && (
        <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse inline-block" />
      )}
      {value}
    </span>
  )
}
