// LogRaven — Assets with IOMs & Multi-Line Time Series Charts (Falcon Visual Standard)
import { useState } from 'react'
import { Info, MoreVertical, ChevronDown } from 'lucide-react'

interface AssetsTimeSeriesChartProps {
  lastRefreshed?: string
}

export function AssetsBarChart({ lastRefreshed = '19:05:08' }: AssetsTimeSeriesChartProps) {
  const bars = [
    { label: 'High', count: 420, color: '#F2853C', heightPct: '14%' },
    { label: 'Medium', count: 2750, color: '#E8B84B', heightPct: '91%' },
    { label: 'Informational', count: 2310, color: '#5B9BEE', heightPct: '77%' },
  ]

  return (
    <div className="rounded-xl border border-white/[0.08] bg-surface p-4 flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-text-primary">
            <span>Assets with IOMs</span>
            <Info className="w-3 h-3 text-text-muted/70" />
          </div>
          <button
            type="button"
            title="Chart options"
            aria-label="Chart options"
            className="w-7 h-7 rounded-lg border border-white/[0.06] hover:border-white/[0.15] bg-white/[0.02] flex items-center justify-center text-text-muted hover:text-text-primary transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
          >
            <MoreVertical className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Bar Chart Visualization */}
        <div className="py-4">
          <div className="flex items-end justify-between h-44 gap-4 px-4 pt-4 border-b border-white/[0.08]">
            {bars.map((b) => (
              <div key={b.label} className="flex-1 flex flex-col items-center h-full justify-end">
                <div
                  className="w-full max-w-[48px] rounded-t-sm transition-transform duration-150 motion-reduce:transition-none"
                  style={{ height: b.heightPct, backgroundColor: b.color }}
                  title={`${b.label}: ${b.count}`}
                />
              </div>
            ))}
          </div>

          {/* X Axis Labels */}
          <div className="flex items-center justify-between gap-4 px-4 pt-2 text-xs font-medium text-text-muted">
            {bars.map((b) => (
              <div key={b.label} className="flex-1 text-center">
                <span>{b.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-3 pt-2 border-t border-white/[0.04] flex items-center justify-between text-[10px] text-text-muted">
        <span>Last refreshed: {lastRefreshed}</span>
      </div>
    </div>
  )
}

export function AssetsTimeSeriesChart({ lastRefreshed = '19:05:07' }: AssetsTimeSeriesChartProps) {
  const [provider, setProvider] = useState<'aws' | 'azure' | 'gcp'>('aws')

  const dates = ['Oct 29', 'Oct 30', 'Oct 31', 'Nov 01', 'Nov 02', 'Nov 03', 'Nov 04', 'Nov 05']

  const lines = [
    { name: 'ECS Task Definition', color: '#38BDF8', path: 'M 0 35 L 70 30 L 140 32 L 210 30 L 280 32 L 350 48 L 420 38 L 490 32' },
    { name: 'Logs Log Group', color: '#A855F7', path: 'M 0 110 L 70 110 L 140 110 L 210 110 L 280 110 L 350 110 L 420 110 L 490 110' },
    { name: 'CloudFormation Stack', color: '#FACC15', path: 'M 0 120 L 70 120 L 140 120 L 210 120 L 280 120 L 350 120 L 420 120 L 490 120' },
    { name: 'ECS Service', color: '#EC4899', path: 'M 0 130 L 70 130 L 140 130 L 210 130 L 280 130 L 350 130 L 420 130 L 490 130' },
    { name: 'SSM Parameter', color: '#6366F1', path: 'M 0 140 L 70 140 L 140 140 L 210 140 L 280 140 L 350 140 L 420 140 L 490 140' },
    { name: 'ECR Repository', color: '#10B981', path: 'M 0 150 L 70 150 L 140 150 L 210 150 L 280 150 L 350 150 L 420 150 L 490 150' },
    { name: 'Amazon Machine Image', color: '#F97316', path: 'M 0 160 L 70 160 L 140 160 L 210 160 L 280 160 L 350 160 L 420 160 L 490 160' },
  ]

  return (
    <div className="rounded-xl border border-white/[0.08] bg-surface p-4 flex flex-col justify-between">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-text-primary">
            <span>Assets with IOM&apos;s by asset type</span>
            <Info className="w-3 h-3 text-text-muted/70" />
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setProvider(provider === 'aws' ? 'azure' : 'aws')}
              className="flex items-center gap-1 px-2 py-0.5 rounded border border-white/[0.08] bg-white/[0.02] text-xs font-semibold text-text-primary focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
            >
              <span>{provider.toUpperCase()}</span>
              <ChevronDown className="w-3 h-3 text-text-muted" />
            </button>
            <button
              type="button"
              title="Chart options"
              aria-label="Chart options"
              className="w-7 h-7 rounded-lg border border-white/[0.06] hover:border-white/[0.15] bg-white/[0.02] flex items-center justify-center text-text-muted hover:text-text-primary transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
            >
              <MoreVertical className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Time Series SVG Graph */}
        <div className="py-4">
          <div className="h-44 w-full">
            <svg viewBox="0 0 490 180" aria-hidden="true" className="w-full h-full overflow-visible">
              {/* Horizontal Grid lines */}
              <line x1="0" y1="30" x2="490" y2="30" stroke="rgba(255,255,255,0.05)" strokeDasharray="3 3" />
              <line x1="0" y1="75" x2="490" y2="75" stroke="rgba(255,255,255,0.05)" strokeDasharray="3 3" />
              <line x1="0" y1="120" x2="490" y2="120" stroke="rgba(255,255,255,0.05)" strokeDasharray="3 3" />
              <line x1="0" y1="165" x2="490" y2="165" stroke="rgba(255,255,255,0.08)" />

              {/* Data lines */}
              {lines.map((l) => (
                <path
                  key={l.name}
                  d={l.path}
                  fill="none"
                  stroke={l.color}
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              ))}

              {/* Key points on top line */}
              <circle cx="0" cy="35" r="3.5" fill="#38BDF8" />
              <circle cx="70" cy="30" r="3.5" fill="#38BDF8" />
              <circle cx="140" cy="32" r="3.5" fill="#38BDF8" />
              <circle cx="210" cy="30" r="3.5" fill="#38BDF8" />
              <circle cx="280" cy="32" r="3.5" fill="#38BDF8" />
              <circle cx="350" cy="48" r="3.5" fill="#38BDF8" />
              <circle cx="420" cy="38" r="3.5" fill="#38BDF8" />
              <circle cx="490" cy="32" r="3.5" fill="#38BDF8" />
            </svg>
          </div>

          {/* Dates footer */}
          <div className="flex items-center justify-between text-[10px] font-mono text-text-muted pt-2 border-t border-white/[0.06]">
            {dates.map((d) => (
              <span key={d}>{d}</span>
            ))}
          </div>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-text-muted mt-2">
          {lines.map((l) => (
            <div key={l.name} className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: l.color }} />
              <span className="truncate max-w-[130px]">{l.name}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-3 pt-2 border-t border-white/[0.04] flex items-center justify-between text-[10px] text-text-muted">
        <span>Last refreshed: {lastRefreshed}</span>
      </div>
    </div>
  )
}
