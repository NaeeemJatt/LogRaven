// LogRaven — Total Open IOMs Count by Severity Donut Chart (CrowdStrike Visual Standard)
import { MoreVertical } from 'lucide-react'

interface PostureDonutChartProps {
  totalCount?: string
  highCount?: number
  mediumCount?: number
  infoCount?: number
  lastRefreshed?: string
}

export default function PostureDonutChart({
  totalCount = '7k',
  highCount = 540,
  mediumCount = 5329,
  infoCount = 1761,
  lastRefreshed = '19:05:06',
}: PostureDonutChartProps) {
  const total = highCount + mediumCount + infoCount
  const highPct = (highCount / total) * 100
  const medPct = (mediumCount / total) * 100
  const infoPct = (infoCount / total) * 100

  // SVG circular arc calculations
  const radius = 38
  const circumference = 2 * Math.PI * radius // ~238.76

  const highDash = (highPct / 100) * circumference
  const medDash = (medPct / 100) * circumference
  const infoDash = (infoPct / 100) * circumference

  const highOffset = 0
  const medOffset = -highDash
  const infoOffset = -(highDash + medDash)

  return (
    <div className="rounded-xl border border-white/[0.08] bg-surface p-4 flex flex-col justify-between">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
          <div className="text-xs font-semibold text-text-primary">
            Total open IOMs count by severity
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

        {/* Donut Chart Display */}
        <div className="py-6 flex flex-col items-center justify-center relative">
          <div className="relative w-40 h-40 flex items-center justify-center">
            <svg viewBox="0 0 100 100" aria-hidden="true" className="w-full h-full -rotate-90">
              {/* Background ring track */}
              <circle
                cx="50"
                cy="50"
                r={radius}
                fill="transparent"
                stroke="rgba(255, 255, 255, 0.04)"
                strokeWidth="12"
              />

              {/* Informational arc (Blue) */}
              <circle
                cx="50"
                cy="50"
                r={radius}
                fill="transparent"
                stroke="#5B9BEE"
                strokeWidth="12"
                strokeDasharray={`${infoDash} ${circumference}`}
                strokeDashoffset={infoOffset}
                strokeLinecap="butt"
              />

              {/* Medium arc (Gold) */}
              <circle
                cx="50"
                cy="50"
                r={radius}
                fill="transparent"
                stroke="#E8B84B"
                strokeWidth="12"
                strokeDasharray={`${medDash} ${circumference}`}
                strokeDashoffset={medOffset}
                strokeLinecap="butt"
              />

              {/* High arc (Orange) */}
              <circle
                cx="50"
                cy="50"
                r={radius}
                fill="transparent"
                stroke="#F2853C"
                strokeWidth="12"
                strokeDasharray={`${highDash} ${circumference}`}
                strokeDashoffset={highOffset}
                strokeLinecap="butt"
              />
            </svg>

            {/* Huge Center Metric Readout */}
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none">
              <span className="font-display font-bold text-3xl sm:text-4xl text-text-primary tracking-tight tabular-nums">
                {totalCount}
              </span>
            </div>
          </div>

          {/* Bottom Color Legend */}
          <div className="flex items-center justify-center gap-4 mt-4 text-xs font-medium text-text-secondary">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-threat-high" />
              <span>High</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-threat-medium" />
              <span>Medium</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-threat-info" />
              <span>Informational</span>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-3 pt-2 border-t border-white/[0.04] flex items-center justify-between text-[10px] text-text-muted">
        <span>Last refreshed: {lastRefreshed}</span>
      </div>
    </div>
  )
}
