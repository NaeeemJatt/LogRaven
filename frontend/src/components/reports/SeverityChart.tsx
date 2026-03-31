// Severity distribution — compact visual for the report header

const COLORS: Record<string, string> = {
  critical: '#f87171',
  high: '#fb923c',
  medium: '#facc15',
  low: '#60a5fa',
  informational: '#64748b',
}

interface SeverityChartProps {
  counts: Record<string, number>
}

export default function SeverityChart({ counts }: SeverityChartProps) {
  const order = ['critical', 'high', 'medium', 'low', 'informational'] as const
  const total = order.reduce((s, k) => s + (counts[k] ?? 0), 0)
  if (total === 0) {
    return (
      <div className="rounded-xl border border-raven-700 bg-raven-800/50 px-6 py-8 text-center text-raven-500 text-sm">
        No severity data
      </div>
    )
  }

  let acc = 0
  const segments = order
    .map((key) => {
      const n = counts[key] ?? 0
      if (n <= 0) return null
      const pct = (n / total) * 100
      const start = acc
      acc += pct
      return { key, n, pct, start }
    })
    .filter(Boolean) as { key: string; n: number; pct: number; start: number }[]

  const gradient = segments
    .map((s) => {
      const c = COLORS[s.key] ?? COLORS.informational
      const a = s.start
      const b = s.start + s.pct
      return `${c} ${a}% ${b}%`
    })
    .join(', ')

  return (
    <div className="rounded-xl border border-raven-700 bg-raven-800/80 p-6 shadow-lg shadow-black/15">
      <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-raven-500 mb-4">
        Severity mix
      </p>
      <div className="flex flex-col sm:flex-row items-center gap-8">
        <div
          className="h-36 w-36 shrink-0 rounded-full border-4 border-raven-900 shadow-inner"
          style={{
            background: `conic-gradient(${gradient})`,
          }}
          aria-hidden
        />
        <ul className="flex-1 space-y-2 w-full min-w-0">
          {segments.map((s) => (
            <li key={s.key} className="flex items-center justify-between gap-3 text-sm">
              <span className="flex items-center gap-2 min-w-0">
                <span
                  className="h-2.5 w-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: COLORS[s.key] ?? COLORS.informational }}
                />
                <span className="text-raven-300 capitalize truncate">{s.key}</span>
              </span>
              <span className="text-white font-mono tabular-nums">{s.n}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
