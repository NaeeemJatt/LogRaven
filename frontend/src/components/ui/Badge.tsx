// LogRaven — Severity Badge Component
// Color-coded severity indicator.
// critical=red, high=orange, medium=yellow, low=blue, informational=gray
// TODO Month 1 Week 3: Implement.

export default function Badge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    critical: 'bg-red-100 text-red-800',
    high:     'bg-orange-100 text-orange-800',
    medium:   'bg-yellow-100 text-yellow-800',
    low:      'bg-blue-100 text-blue-800',
    informational: 'bg-gray-100 text-gray-800',
  }
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[severity] || colors.informational}`}>
      {severity.toUpperCase()}
    </span>
  )
}
